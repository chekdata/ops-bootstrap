#######################################################
# 机构：CHEK车控
# 功能：小程序行程数据处理&合并&上传
# 版本：v1.0
# 时间：-
# 修改时间：2024.1.22
# 修改作者：zjx
#######################################################

import os
import sys
import glob
import folium
import time
import math
import grpc
import pandas as pd
import numpy as np
import argparse
from pathlib import Path, PurePath
from datetime import datetime

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from .proto_v1_0 import chek_message_pb2 as chek
from .proto_v1_0 import chek_message_pb2_grpc as chek_grpc

# @dataclass
class WeChatCSVProcess:
    def __init__(self, csv_files, user_id = 100001, user_name = 'dengnvshi', user_phone = '15320504550', user_MBTI = '内敛小i人',
                 car_brand = '理想', car_model = 'L9', car_version = 'V5.2.1',car_MBTI = '内敛小i人') -> None:
        self.g = 9.8
        self.max_dcc = -0.0009030855870323972 - 6 * math.sqrt(0.24770804630230028)
        self.max_acc = -0.0009030855870323972 + 6 * math.sqrt(0.24770804630230028)
        self.processed_frames = 0
        self.gps_interval = 25     # 采样率待测试，30帧率，1s1点
        self.journey_datetime = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
        self.url = '62.234.57.136:9090'
        self.highway_frames = 0
        self.urban_frames = 0

        self.df = None
        self.journey = None

        self.csv_name = '.csv'
        self.json_name = '.json'

        self.csv_files = csv_files

        self.user_id = user_id
        self.user_name = user_name
        self.user_phone = user_phone
        self.user_MBTI = user_MBTI
        # Set car information
        self.car_brand = car_brand
        self.car_model = car_model
        self.car_version = car_version
        self.car_MBTI = car_MBTI
        self.odometer_thresh = 5

    def change_road_state(self, row, model = 0):
        if model == 0:
            if row.get('state') == 'noa':
                return 'highway'
            else:
                return row.get('road_scene')
        elif model == 1:
            state = row.get('state')
            if not isinstance(row.get('state'), str) and np.isnan(float(row.get('state'))):
                return 'standby'
            else:
                return row.get('state')
        elif model == 2:
            if row.get('weather') == 'rainy':
                return 'sunny'
            else:
                return row.get('weather')


    # 对于driver 行程中存在接管点不参与降采样
    def add_to(self, sub_journey, d_odo, in_acc, in_dcc, pre_a, dt, v, a, in_state, gps_time, lon, lat, is_driver = False, is_intervention = False):
        sub_journey.odometer += d_odo
        sub_journey.speed_average += v
        sub_journey.speed_max = max(v, sub_journey.speed_max)
        sub_journey.dcc_cnt += 1 if in_dcc == 0 and a <= self.max_dcc else 0
        sub_journey.dcc_frequency = sub_journey.odometer / \
            sub_journey.dcc_cnt if sub_journey.dcc_cnt > 0 else 0
        sub_journey.dcc_average += a if in_dcc == 0 and a <= self.max_dcc else 0
        sub_journey.dcc_max = min(a, sub_journey.dcc_max)
        sub_journey.dcc_duration += dt if in_dcc > 0 and (
            pre_a <= self.max_dcc or a <= self.max_dcc) else 0
        sub_journey.acc_cnt += 1 if in_acc == 0 and a >= self.max_acc else 0
        sub_journey.acc_frequency = sub_journey.odometer / \
            sub_journey.acc_cnt if sub_journey.acc_cnt > 0 else 0
        sub_journey.acc_average += a if in_acc == 0 and a >= self.max_acc else 0
        sub_journey.acc_max = max(a, sub_journey.acc_max)
        sub_journey.acc_duration += dt if in_acc > 0 and (
            pre_a >= self.max_acc or a >= self.max_acc) else 0
        

        # Statistics journey frames
        sub_journey.frames += 1  if v > 0 else 0

        # TODO: truck
        if not in_state:
            sub_journey.gps_trajectories.add()
        
        # 对于gps没信号的状态不记录gps信息
        if math.isnan(lon) or math.isnan(lat):
            return 

        if lon < 1 or lat < 1:
            return
        # 

        if len(sub_journey.gps_trajectories) > 0 and len(sub_journey.gps_trajectories[-1].points) > 0:
            last_gps_point = sub_journey.gps_trajectories[-1].points[-1]
            if lon == last_gps_point.lon and lat == last_gps_point.lat:
                return

        # NOTE: 对于接管来讲，若gps信号丢失则也不记录该点的位置信息
        if (lon > 1 and lat > 1 and (self.processed_frames % self.gps_interval == 0) or (is_driver and is_intervention)):
            if len(sub_journey.gps_trajectories) == 0:
                sub_journey.gps_trajectories.add()
            gps_point = sub_journey.gps_trajectories[-1].points.add()
            gps_point.datetime = str(gps_time)
            gps_point.lon = lon
            gps_point.lat = lat


    # 对于接管点处无gps信息则不加入gps信息
    def calculate_intervention(self, sub_journey, near_max_dcc, gps_time, lon, lat):
        sub_journey.intervention += 1
        if near_max_dcc <= self.max_dcc:
            sub_journey.intervention_risk += 1
            if (lon < 1 or lat < 1) or (math.isnan(lon) or math.isnan(lat)):
                return
            gps_point = sub_journey.intervention_risk_gps_points.add()
        else:
            if (lon < 1 or lat < 1) or (math.isnan(lon) or math.isnan(lat)):
                return
            gps_point = sub_journey.intervention_gps_points.add()
        gps_point.datetime = str(gps_time)
        gps_point.lon = lon
        gps_point.lat = lat


    def post_caculate(self, sub_journey, frames, is_auto=True):
        sub_journey.speed_average /= frames if frames > 0 else 1
        sub_journey.dcc_average /= sub_journey.dcc_cnt if sub_journey.dcc_cnt > 0 else 1
        sub_journey.acc_average /= sub_journey.acc_cnt if sub_journey.acc_cnt > 0 else 1
        if is_auto:
            # sub_journey.mpi = sub_journey.odometer / \
            #     sub_journey.intervention if sub_journey.intervention > 0 else 1
            # sub_journey.mpi_risk = sub_journey.odometer / \
            #     sub_journey.intervention_risk if sub_journey.intervention_risk > 0 else 1

            # zjx 2024.03.29
            # 接管里程调整计算方式

            sub_journey.mpi = sub_journey.auto_odometer / \
                (sub_journey.intervention  + 1) 
            
            sub_journey.mpi_risk = sub_journey.auto_odometer / \
                (sub_journey.intervention_risk  + 1) 


            sub_journey.risk_rate = sub_journey.mpi / \
                sub_journey.mpi_risk if sub_journey.mpi_risk > 0 else 1
            
    def post_caculate(self, sub_journey, frames, auto_odometer,is_auto=True):
        sub_journey.speed_average /= frames if frames > 0 else 1e-5
        sub_journey.dcc_average /= sub_journey.dcc_cnt if sub_journey.dcc_cnt > 0 else -1*1e-5
        sub_journey.acc_average /= sub_journey.acc_cnt if sub_journey.acc_cnt > 0 else 1e-5
        if is_auto:
            # sub_journey.mpi = auto_odometer / \
            #     sub_journey.intervention if sub_journey.intervention > 0 else 1e-5 #1
            # sub_journey.mpi_risk = auto_odometer / \
            #     sub_journey.intervention_risk if sub_journey.intervention_risk > 0 else 1e-5 #1

            # zjx 2024.03.29
            # 接管里程调整计算方式

            sub_journey.mpi = auto_odometer / \
                (sub_journey.intervention  + 1) 
            
            sub_journey.mpi_risk = auto_odometer / \
                (sub_journey.intervention_risk  + 1) 

            sub_journey.risk_rate = sub_journey.mpi / \
                sub_journey.mpi_risk if sub_journey.mpi_risk > 0 else 1e-5 #1



    def set_journeyStatistics_global_data(self, journeyStatistics):
        # Complete journey
        # journey.datetime = start_gps_time if start_gps_time is not None else '1999.01.01 00:00:00'

        # modified by zjx 
        # 2023.10.12
        # 所有mpi数据调整为智驾里程处理
        odometer_total = journeyStatistics.auto.odometer + journeyStatistics.driver.odometer
        odometer_auto = journeyStatistics.auto.odometer  
        

        odometer_total = odometer_total if odometer_total > 0 else 0
        odometer_auto = odometer_auto if odometer_auto > 0 else 0
        

        journeyStatistics.datetime = self.journey_datetime  # TODO
        journeyStatistics.odometer_total = odometer_total
        journeyStatistics.odometer_auto = odometer_auto
        journeyStatistics.odometer_hmi = 73  # TODO: detect from hmi
        journeyStatistics.odometer_accuracy = (
            self.journey.odometer_total / self.journey.odometer_hmi)*100
    
        self.post_caculate(journeyStatistics.auto, journeyStatistics.noa.frames+journeyStatistics.lcc.frames, odometer_auto)
        self.post_caculate(journeyStatistics.noa, journeyStatistics.noa.frames, odometer_auto)
        self.post_caculate(journeyStatistics.lcc, journeyStatistics.lcc.frames, odometer_auto)
        self.post_caculate(journeyStatistics.driver, journeyStatistics.driver.frames, odometer_auto,is_auto=False)

    # 调整接管判定条件
    def extract_chek_message(self, csv_file: str):

        self.df = pd.read_csv(csv_file)

        chek_message = chek.ChekMessage()

        # csv文件是否为空判断
        if (self.df.empty) or (self.df is None):
            return chek_message


        self.journey = chek_message.journey


        # NOTE: ls7 nio特殊处理。noa只在高速上行驶
        # self.df['road_scene'] = self.df.apply(lambda row: self.change_road_state(row, model=0), axis=1)
        self.df['state'] = self.df.apply(lambda row: self.change_road_state(row, model=1), axis=1)
        # self.df['weather'] = self.df.apply(lambda row: self.change_road_state(row, model=2), axis=1)


        self.journey.duration = self.df['time'].iloc[-1]/3600.0

        pre_frame_id,  pre_lon, pre_lat = 0, 0, 0
        pre_gps_time = ""

        start_gps_time = None
        pre_state, pre_t, pre_v, pre_a = None, 0, 0, 0
        noa_frames, lcc_frames, driver_frames = 0, 0, 0
        in_acc, in_dcc = 0, 0  # pre 3s occur acc or dcc
        for i, (frams_id, state, t, v, a, gps_time, lon, lat) in enumerate(zip(self.df['frame'], self.df['state'], self.df['time'], 
                                                                               self.df['speed'], self.df['acc'], self.df['gps_timestamp'], 
                                                                               self.df['lon'], self.df['lat'])):

            # 速度保护，合理区间外使用pre_v做当前速度
            if v< 0  or v > 150:
                v = pre_v
            # added by zjx
            # 防止数据缺失，以上一帧数据补充到当前帧缺失数据项中        
            if math.isnan(frams_id):
                frams_id = pre_frame_id + 1

            if not isinstance(state, str) and np.isnan(float(state)):
                state = pre_state  

            if math.isnan(t):
                t = pre_t
            

            if math.isnan(v):
                v = pre_v       

            if math.isnan(a):
                a = pre_a

            # NOTE: 新数据gps_time维度调整  
            # if math.isnan(gps_time):
            #     gps_time = pre_gps_time
            if not isinstance(gps_time, str) and np.isnan(float(gps_time)):
                gps_time = pre_gps_time

            if math.isnan(lon):
                lon = pre_lon

            if math.isnan(lat):
                lat = pre_lat

            processed_frames = i

            start_gps_time = str(
                gps_time) if start_gps_time is None and gps_time != '' else None
            dt = t - pre_t
            d_odo = (pre_v/3.6*dt+1/2*pre_a*dt**2)/1000.0  # km
            if state == 'noa':
                noa_frames += 1 if v > 0 else 0
                self.add_to(self.journey.noa, d_odo, in_acc, in_dcc, pre_a, dt, v, a,
                    state == pre_state, gps_time, lon, lat)
                self.add_to(self.journey.auto, d_odo, in_acc, in_dcc, pre_a, dt, v, a,
                    state == pre_state, gps_time, lon, lat)
            elif state == 'lcc':
                lcc_frames += 1 if v > 0 else 0
                self.add_to(self.journey.lcc, d_odo, in_acc, in_dcc, pre_a, dt, v, a,
                    state == pre_state, gps_time, lon, lat)
                self.add_to(self.journey.auto, d_odo, in_acc, in_dcc, pre_a, dt, v, a,
                    state == pre_state, gps_time, lon, lat)
            else:  # state = 'driver'
                driver_frames += 1 if v > 0 else 0

                # Intervention
                near_max_dcc = self.df['acc'][max(0, i-3):i+3].min()

                is_intervention = False
                if pre_state == 'noa' or pre_state == 'lcc':
                    # print(f'intervention at {i}')

                    # NOTE 接管判定
                    isReal_driver = False
                    # 之前是智驾状态
                    isReal_auto_driver = True
                    # 后续状态真的保持driver
                    # 持续时间判定：阈值判定(s)

                    # 获取当前frams_time所在行索引
                    #time = df.loc[rows_id, 'time']
                    # 遍历后续所有连续driver 帧直到第一个非driver帧 
                    # 获取最后一个连续driver帧id
                    fps = 30
                    time_thre = 3
                    time_thre_before = 5#3
                    time_thre_after = 5#0.5

                    frames_time = self.df.iloc[i]['time']
                    for row in range(i, len(self.df)):
                        if self.df.iloc[row]['state'] != 'noa' and self.df.iloc[row]['state'] != 'lcc':
                            frams_time_next = self.df.iloc[row]['time']
                            if frams_time_next - frames_time > time_thre_after:
                                break
                        else:
                            break
                    
                    # 计算当前帧time_thre之前的连续状态为智驾
                    #start_frame_id = min(max(0,(rows_id - fps * time_thre)), len(df) - 1)
                    start_frame_id = min(max(0,(i - 1)), len(self.df) - 1)
                    for row in range(start_frame_id, -1, -1):
                        if start_frame_id == 11063:
                            a = 100
                        #if df.iloc[row]['state'] == pre_state:
                        k = self.df.iloc[row]['state'] 
                        if self.df.iloc[row]['state'] == 'noa' or self.df.iloc[row]['state'] == 'lcc':
                            frams_time_before = self.df.iloc[row]['time']
                            if frames_time - frams_time_before > time_thre_before:
                                break
                        else:
                            break

                    isReal_driver = True if frams_time_next - frames_time > time_thre_after else False
                    isReal_auto_driver = True if frames_time - frams_time_before> time_thre_before else False

                    
                    is_intervention = isReal_driver and isReal_auto_driver
                    #if isReal_driver and isReal_auto_driver:
                    if is_intervention:
                        self.calculate_intervention(
                                self.journey.auto, near_max_dcc, gps_time, lon, lat)
                        
                        road_scene = self.df.iloc[i]['road_scene']

                        # 若是在urban 则认为是lcc
                        if road_scene == 'urban':
                                self.calculate_intervention(
                                    self.journey.lcc, near_max_dcc, gps_time, lon, lat)                        
                        else:
                            if pre_state == 'noa':
                                self.calculate_intervention(
                                    self.journey.noa, near_max_dcc, gps_time, lon, lat)
                            elif pre_state == 'lcc':
                                self.calculate_intervention(
                                    self.journey.lcc, near_max_dcc, gps_time, lon, lat)
                                
                self.add_to(self.journey.driver, d_odo, in_acc, in_dcc, pre_a, dt, v, a,
                    state == pre_state, gps_time, lon, lat, is_driver=True, is_intervention=is_intervention)


                                
            in_acc = 3.0 if a >= self.max_acc else max(0, in_acc - dt)
            in_dcc = 3.0 if a <= self.max_dcc else max(0, in_dcc - dt)
            #pre_state, pre_t, pre_v, pre_a = state, t, v, a
            pre_state, pre_t, pre_a = state, t, a
            # 速度保护，合理区间内才更新速度
            if v >= 0  and v <= 150:
                pre_v = v 

        self.set_journeyStatistics_global_data(self.journey)
        # post_caculate(journey.auto, noa_frames+lcc_frames)
        # post_caculate(journey.noa, noa_frames)
        # post_caculate(journey.lcc, lcc_frames)
        # post_caculate(journey.driver, driver_frames, is_auto=False)

        # Return message
        return chek_message


    # 对行程数据没有赋值字段进行检查
    def check_subjourney(self, sub_journey, is_auto=True):

        if sub_journey.odometer == 0: sub_journey.odometer = 1e-5
        if sub_journey.frames == 0: sub_journey.frames = 1
        if sub_journey.speed_average == 0:sub_journey.speed_average = 1e-5
        if sub_journey.speed_max == 0:sub_journey.speed_max = 1e-5
        if sub_journey.dcc_cnt == 0: sub_journey.dcc_cnt = 4294967295
        if sub_journey.dcc_frequency == 0:sub_journey.dcc_frequency = 1e-5
        if sub_journey.dcc_average == 0:sub_journey.dcc_average = 1e-5
        if sub_journey.dcc_max == 0:sub_journey.dcc_max = 1e-5
        if sub_journey.acc_cnt == 0: sub_journey.acc_cnt = 4294967295
        if sub_journey.acc_frequency == 0: sub_journey.acc_frequency = 1e-5
        if sub_journey.acc_average == 0: sub_journey.acc_average = 1e-5
        if sub_journey.acc_max == 0: sub_journey.acc_max = 1e-5
        if sub_journey.acc_duration == 0: sub_journey.acc_duration = 1e-5

        if len(sub_journey.gps_trajectories) == 0:
            sub_journey.gps_trajectories.add()
            #gps_point = sub_journey.gps_trajectories[-1].points.add()
        #     gps_point.datetime = str("2023-10-17 17:39:51")
        #     gps_point.lon = 119.64581298828124
        #     gps_point.lat = 40.00307846069336
        else:
            # 对于非空gps点集合删除，保留带gps信息数组
            new_gps_trajectories = [gps_trajectorie for gps_trajectorie \
                                            in sub_journey.gps_trajectories if len(gps_trajectorie.points) != 0]
            del sub_journey.gps_trajectories[:]
            sub_journey.gps_trajectories.extend(new_gps_trajectories)

            # 对于所有点集均是空的情况，在更新后增加一个空信息组
            if len(sub_journey.gps_trajectories) == 0:
                sub_journey.gps_trajectories.add()
            




        if is_auto:
            if sub_journey.intervention == 0: sub_journey.intervention = 4294967295
            if sub_journey.intervention_risk == 0: sub_journey.intervention_risk = 4294967295
            if sub_journey.mpi == 0: sub_journey.mpi = 1e-5
            if sub_journey.mpi_risk == 0: sub_journey.mpi_risk = 1e-5
            if sub_journey.risk_rate == 0: sub_journey.risk_rate = 1e-5

            if len(sub_journey.intervention_gps_points) == 0:
                #sub_journey.intervention_gps_points.add()
                gps_point = sub_journey.intervention_gps_points.add()
            #     gps_point.datetime = str("2023-10-17 17:39:51")
            #     gps_point.lon = 119.64581298828124
            #     gps_point.lat = 40.00307846069336
            
            if len(sub_journey.intervention_risk_gps_points) == 0:
                #sub_journey.intervention_risk_gps_points.add()
                gps_point = sub_journey.intervention_risk_gps_points.add()
            #     gps_point.datetime = str("2023-10-17 17:39:51")
            #     gps_point.lon = 119.64581298828124
            #     gps_point.lat = 40.00307846069336


    def check_chek_message(self, chek_message):
        journey = chek_message.journey

        if journey.odometer_total == 0: journey.odometer_total = 1e-5#odometer_total#float(int(journey.odometer_total * 100) / 100)#round(journey.odometer_total, 2)
        if journey.odometer_auto == 0: journey.odometer_auto = 1e-5 #round(journey.odometer_auto, 2)
        if journey.duration == 0: journey.duration = 1e-5#round(journey.duration, 2)
        if journey.odometer_accuracy == 0: journey.odometer_accuracy = 1e-5#round(journey.odometer_accuracy, 2)

        self.check_subjourney(journey.auto)
        self.check_subjourney(journey.noa)
        self.check_subjourney(journey.lcc)
        self.check_subjourney(journey.driver, is_auto=False)


    def merge_messages(self, messages: list):
        if len(messages) == 0:
            return None
        merged_message = chek.ChekMessage()
        # # merged user information
        # merged_message.user = messages[0].user
        # # merged car information
        # merged_message.car = messages[0].car
        # Set user information
        merged_message.user.id = messages[0].user.id
        merged_message.user.name = messages[0].user.name
        merged_message.user.phone = messages[0].user.phone
        merged_message.user.MBTI = messages[0].user.MBTI
        # Set car information
        merged_message.car.brand = messages[0].car.brand
        merged_message.car.model = messages[0].car.model 
        merged_message.car.version = messages[0].car.version 
        merged_message.car.MBTI = messages[0].car.MBTI

        # set journey datetime
        merged_message.journey.datetime = messages[0].journey.datetime

        def add_journey(sub_journey1, sub_journey2, is_driver=False):
            sub_journey1.odometer += sub_journey2.odometer
            #sub_journey1.speed_average += sub_journey2.speed_average  # TODO

            if sub_journey1.frames == 0 or sub_journey2.frames == 0:
                sub_journey1.speed_average += sub_journey2.speed_average 
            else:
                sub_journey1.speed_average = (sub_journey1.speed_average * sub_journey1.frames \
                                            + sub_journey2.speed_average * sub_journey2.frames) \
                                                / (sub_journey1.frames + sub_journey2.frames)
            
            sub_journey1.frames += sub_journey2.frames

            sub_journey1.speed_max = max(
                sub_journey1.speed_max, sub_journey2.speed_max)
            sub_journey1.dcc_cnt += sub_journey2.dcc_cnt
            sub_journey1.dcc_frequency = sub_journey1.odometer / \
                sub_journey1.dcc_cnt if sub_journey1.dcc_cnt > 0 else 0
            #sub_journey1.dcc_average += sub_journey2.dcc_average  # TODO

            if sub_journey1.dcc_cnt == 0 or sub_journey2.dcc_cnt == 0:
                sub_journey1.dcc_average += sub_journey2.dcc_average 
            else:
                sub_journey1.dcc_average = (sub_journey1.dcc_average * sub_journey1.dcc_cnt \
                                            + sub_journey2.dcc_average * sub_journey2.dcc_cnt) \
                                                / (sub_journey1.dcc_cnt + sub_journey2.dcc_cnt)
                
            sub_journey1.dcc_max = min(sub_journey1.dcc_max, sub_journey2.dcc_max)
            sub_journey1.dcc_duration += sub_journey2.dcc_duration
            sub_journey1.acc_cnt += sub_journey2.acc_cnt
            sub_journey1.acc_frequency = sub_journey1.odometer / \
                sub_journey1.acc_cnt if sub_journey1.acc_cnt > 0 else 0
            #sub_journey1.acc_average += sub_journey2.acc_average  # TODO
            if sub_journey1.acc_cnt == 0 or sub_journey2.acc_cnt == 0:
                sub_journey1.acc_average += sub_journey2.acc_average 
            else:
                sub_journey1.acc_average = (sub_journey1.acc_average * sub_journey1.acc_cnt \
                                            + sub_journey2.acc_average * sub_journey2.acc_cnt) \
                                                / (sub_journey1.acc_cnt + sub_journey2.acc_cnt)
            sub_journey1.acc_max = max(sub_journey1.acc_max, sub_journey2.acc_max)
            sub_journey1.acc_duration += sub_journey2.acc_duration
            sub_journey1.truck_avoid_cnt += sub_journey2.truck_avoid_cnt
            sub_journey1.truck_avoid_speed_average += sub_journey2.truck_avoid_speed_average  # TODO
            sub_journey1.gps_trajectories.extend(sub_journey2.gps_trajectories)

            if not is_driver:
                sub_journey1.intervention_gps_points.extend(
                    sub_journey2.intervention_gps_points)
                sub_journey1.intervention_risk_gps_points.extend(
                    sub_journey2.intervention_risk_gps_points)
                sub_journey1.truck_avoid_intervention += sub_journey2.truck_avoid_intervention
                sub_journey1.truck_avoid_intervention_risk += sub_journey2.truck_avoid_intervention_risk
                sub_journey1.intervention += sub_journey2.intervention
                sub_journey1.intervention_risk += sub_journey2.intervention_risk
                # sub_journey1.mpi = sub_journey1.odometer / \
                #     sub_journey1.intervention if sub_journey1.intervention > 0 else 0
                # sub_journey1.mpi_risk = sub_journey1.odometer / \
                #     sub_journey1.intervention_risk if sub_journey1.intervention_risk > 0 else 0

                # zjx 2024.03.29
                # 接管里程调整计算方式

                sub_journey1.mpi = sub_journey1.odometer / \
                    (sub_journey1.intervention  + 1) 
                
                sub_journey1.mpi_risk = sub_journey1.odometer / \
                    (sub_journey1.intervention_risk  + 1) 

                sub_journey1.risk_rate = (
                    sub_journey1.mpi_risk / sub_journey1.mpi) * 100 if sub_journey1.mpi > 0 else 0

        journey = merged_message.journey

        for msg in messages:
            journey.duration += msg.journey.duration
            journey.odometer_total += msg.journey.odometer_total
            journey.odometer_auto += msg.journey.odometer_auto
            journey.odometer_hmi += msg.journey.odometer_hmi
            journey.odometer_accuracy = (
                journey.odometer_total / journey.odometer_hmi)*100
            journey.is_break = False
            journey.index = 0
            add_journey(journey.auto, msg.journey.auto)
            add_journey(journey.noa, msg.journey.noa)
            add_journey(journey.lcc, msg.journey.lcc)
            add_journey(journey.driver, msg.journey.driver, is_driver=True)
        return merged_message

    def publish_message(self, chek_message: chek.ChekMessage):
        # Create gprc client
        #channel = grpc.insecure_channel('152.136.205.136:9090')
        #channel = grpc.insecure_channel('62.234.57.136:9090')
        # 增加序列化操作中保留默认值字段设置
        # 
        options = [('grpc.include_default_values', True)]

        channel = grpc.insecure_channel(self.url, options=options)
        # channel = grpc.insecure_channel('62.234.57.136:9090', options=options)
        #channel = grpc.insecure_channel('localhost:9090')
        
        stub = chek_grpc.ResourceMessageHandleStub(channel=channel)
        print('#'*50)
        #print("传输前chek_message:", chek_message)
        print('Request chek server...')
        try:
            t1 = time.time()
            response = stub.saveResource(chek_message, timeout=3)
            print(f'Request time: {time.time()-t1:.2f} s')
            print(f'Chek server response:\n{response}')
            message = response.msg
            print(f"Response message :\n{message}")
            time.sleep(3)
            
        except Exception as e:
            print('Request failed, error msg:\n', e)
            print('Try again after 3s...')
            time.sleep(3)
        print('#'*50)  
    
    def process(self):
        files = self.csv_files
        message = []
        for file_name in files:
            print("processed csv is: " + file_name)
            chek_message = self.extract_chek_message(file_name)
            # Set user information
            chek_message.user.id = self.user_id
            chek_message.user.name = self.user_name
            chek_message.user.phone = self.user_phone
            chek_message.user.MBTI = self.user_MBTI
            # Set car information
            chek_message.car.brand = self.car_brand
            chek_message.car.model = self.car_model
            chek_message.car.version = self.car_version
            chek_message.car.MBTI = self.car_MBTI
            message.append(chek_message)

        total_message = self.merge_messages(message)
        self.check_chek_message(total_message)
        if total_message.journey.odometer_total > self.odometer_thresh:
            self.publish_message(total_message)  
        else:
            print(f"The odometer is {total_message.journey.odometer_total} not satisfy bigger than {self.odometer_thresh}")




if __name__ == "__main__":

    pro_csv_list = []
    user_id = 100008
    user_name =  '洪泽鑫'
    user_phone = '15117929459'#'13212728954'
    user_MBTI = '内敛小i人'
    car_brand = '问界'
    car_model = '新M7 2024款智驾版'
    car_version = 'ADS Pro V2.0_2023.48.0d0a56884330'
    car_MBTI = '内敛小i人'
    csvProcess = WeChatCSVProcess(pro_csv_list,user_id, user_name, user_phone, user_MBTI,
                 car_brand, car_model, car_version ,car_MBTI)
    csvProcess.process()

