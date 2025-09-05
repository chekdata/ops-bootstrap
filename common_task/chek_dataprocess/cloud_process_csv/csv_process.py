import os
import sys
import re
import time as run_time
import math
import grpc
import json
import copy
import pandas as pd
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePath
from datetime import datetime, timedelta
from google.protobuf.json_format import MessageToJson
from geopy.geocoders import Nominatim
from collections import deque

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)


from .file_operater import save_to_json, get_all_specify_filename_files,  create_folders_from_filename

# from file_operater import save_to_json, get_all_specify_filename_files,  create_folders_from_filename

from proto_v1_2 import chek_message_pb2 as chek
from proto_v1_2 import chek_message_pb2_grpc as chek_grpc
# from chek_gps2city import regeocode

# @history
class HistoryAcc:
    def __init__(self, max_length=7):
        self.acc_history = deque(maxlen=max_length)
        self.delta_acc_history = deque(maxlen=max_length)
        self.potential_forward_acc_history = deque(maxlen=max_length)
        self.last_acc = None
        self.gravity_vec = None
        self.forward_vec = np.zeros(3)
        
    def add(self, acc):
        delta_acc = abs(acc - self.last_acc) if self.last_acc is not None else np.zeros(3)
        self.acc_history.append(acc.copy())
        self.delta_acc_history.append(delta_acc.copy())
        # 更新稳定状态下的重力向量
        self._update_gravity_vec()
        # 更新前向向量
        potential_forward_acc = acc - self.gravity_vec if self.gravity_vec is not None else np.zeros(3)
        if np.linalg.norm(potential_forward_acc) > 1.0:
            self.potential_forward_acc_history.append(potential_forward_acc.copy())
            self._update_forward_vec()
        # 更新最后一次的加速度
        self.last_acc = acc

    def _update_forward_vec(self):
        forward_vec = np.mean(self.potential_forward_acc_history, axis=0)
        self.forward_vec = forward_vec / np.linalg.norm(forward_vec)


    def _update_gravity_vec(self):
        delta_accs = np.array(self.delta_acc_history)
        accs = np.array(self.acc_history)
        if accs.std(axis=0).max() < 1.0 and delta_accs.mean(axis=0).max() < 1.0:
            # 如果加速度变化很小，认为是稳定状态
            self.gravity_vec = np.mean(accs, axis=0)


    def infer_real_acc(self, acc):
        if self.gravity_vec is None:
            return 0
        real_acc = abs(np.dot(acc - self.gravity_vec, self.forward_vec))
        if real_acc < 0.5:
            return 0
        return real_acc
        



# @dataclass
class CSVProcess:
    def __init__(self, csv_files, user_id = 100001, user_name = 'dengnvshi', user_phone = '15320504550', 
                 car_brand = 'Lixiang', car_model = 'L9', car_hardware_version = 'V5.2.1', car_software_version = 'V5.2.1',user_MBTI = '内敛小i人',car_MBTI = '内敛小i人', ) -> None:
        self.g = 9.8
        self.max_dcc = -0.0009030855870323972 - 6 * math.sqrt(0.24770804630230028)
        self.max_acc = -0.0009030855870323972 + 6 * math.sqrt(0.24770804630230028)
        self.journey_datetime = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
        self.processed_frames = 0
        self.gps_interval = 25     # 采样率待测试，30帧率，1s1点
        self.url = '62.234.57.136:9090'
        self.highway_frames = 0
        self.urban_frames = 0
        self.frame_intervention_file = {}
        self.frame_intervention_risk_file = {}
        self.gps_status_lcc_noa = {'intervention': [], 'intervention_risk': []}
        self.truck_avoidance_list = []

        self.df = None
        self.scenes = None
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
        self.car_hardware_version = car_hardware_version
        self.car_software_version = car_software_version
        self.car_MBTI = car_MBTI

        self.description_noa_road_status_code = 0    
        self.description_city_noa_merge_code  = 0   
        self.description_city                 = ''   
        self.description_evaluated_scenarios  = ''   
        self.description_pdf_file_path        = '' 
        self.odometer_thresh = 0 

        self.total_message = None
        self.pre_intervention_time = None

        self.average_speed_thre = 30
        self.MBTI_i = '内敛小i人'
        self.MBTI_e = '狂飙小e人'



    def get_data_list(self):
        # 文件路径构成： **/data/xx/xx.csv
        data_list = set()
        root_path = ''
        #暂停使用
        # for filename in self.csv_files:
        #     file_path_parts = filename.split('/')
        #     end_path = file_path_parts[-3]
        #     data_list.add(end_path)
        # file_path_parts = self.csv_files[0].split('/')
        # root_path = '/'.join(file_path_parts[:-4])
        return data_list, root_path


    def change_road_state(self, row, model = 0):
        if model == 0:
            if row.get('state') == 'noa' or row.get('state') == 'lcc':
                return 'highway'
            else:
                return row.get('road_scene')
        elif model == 1:
            state = row.get('state')
            if not row.get('state'):
                return 'standby'
            elif not isinstance(row.get('state'), str) and np.isnan(float(row.get('state'))):
                return 'standby'
            else:
                return row.get('state')
        elif model == 2:
            if row.get('weather') == 'rainy':
                return 'sunny'
            else:
                return row.get('weather')

    
    def extract_chek_message(self, csv_file: str, need_post_process=False):
        if need_post_process:
            #df = util.post_process_csv(csv_file)
            test = 0
        else:
            # self.df = pd.read_csv(csv_file)
            self.df = csv_file
            #嵌套for循环提取
            self.states = self.df['state'].values
            self.times = self.df['time'].values
            self.accs = self.df['acc'].values

        chek_message = chek.ChekMessage()

        # csv文件是否为空判断
        if (self.df.empty) or (self.df is None):
            return chek_message

        self.highway_frames = 0
        self.urban_frames = 0

        # 清空状态
        self.gps_status_lcc_noa['intervention'].clear()
        self.gps_status_lcc_noa['intervention_risk'].clear()
        self.truck_avoidance_list.clear()


        self.scenes = chek_message.scene
        self.journey = chek_message.journeyStatistics


        # NOTE: ls7 nio特殊处理。noa只在高速上行驶
        self.df['state'] = self.df.apply(lambda row: self.change_road_state(row, model=1), axis=1)
        # self.df['road_scene'] = self.df.apply(lambda row: self.change_road_state(row, model=0), axis=1)




        # NOTE: 新数据gps_time维度调整
        # pre_frame_id, pre_gps_time, pre_lon, pre_lat = 0, 0, 0, 0
        pre_frame_id,  pre_lon, pre_lat = 0, 0, 0
        pre_gps_time = ""
        start_gps_time = None
        pre_state, pre_t, pre_v, pre_a = None, 0, 0, 0
        pre_weather,pre_road_scene,pre_light = None, None, None
        noa_frames, lcc_frames, driver_frames = 0, 0, 0
        in_acc, in_dcc = 0, 0  # pre 3s occur acc or dcc


        for i, (frams_id, state, t, v, a, gps_time, lon, lat, weather,road_scene,light) in \
            enumerate(zip(self.df['frame'],self.df['state'], self.df['time'], self.df['speed'], self.df['acc'], \
                        self.df['gps_timestamp'], self.df['lon'], self.df['lat'], self.df['weather'], self.df['road_scene'],self.df['light'],self.df['recorder_accX'],self.df['recorder_accY'],self.df['recorder_accZ'])):
            
            x_acc = recorder_accX
            y_acc = recorder_accY
            z_acc = recorder_accZ
            acc = np.array([x_acc, y_acc, z_acc])
            acc_norm = np.linalg.norm(acc)
            # his_acc.add(acc)
            # delta_acc_norm = abs(np.linalg.norm(acc - last_acc)) if last_acc is not None else 0
            # last_acc = acc
            a = acc_norm
            
            # print("="*10 + f'frame index is {i}' + "="*10)
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
            if gps_time:
                if not isinstance(gps_time, str) and np.isnan(float(gps_time)):
                    gps_time = pre_gps_time

            if math.isnan(lon):
                lon = pre_lon

            if math.isnan(lat):
                lat = pre_lat
            
            if not isinstance(weather, str) and np.isnan(float(weather)):
                weather = pre_weather

            if not isinstance(road_scene, str) and np.isnan(float(road_scene)):
                road_scene = pre_road_scene

            if not isinstance(light, str) and np.isnan(float(light)):
                light = pre_light


            # 计算帧计数
            self.processed_frames = i

            # 开始正式计算
            start_gps_time = str(
                gps_time) if start_gps_time is None and gps_time != '' else None
            dt = t - pre_t
            d_odo = (pre_v/3.6*dt+1/2*pre_a*dt**2)/1000.0  # km

            # NOTE 接管driver状态连续判定
            self.calculate_JourneyStatistics(self.journey, d_odo, in_acc, in_dcc, pre_state, pre_t, pre_v, pre_a, dt, t, v, a, state, gps_time, lon, lat, frams_id, i)



            self.calculate_SceneStatistics(self.scenes, d_odo, in_acc, in_dcc, pre_state, pre_t, pre_v, pre_a, pre_weather,pre_road_scene,pre_light, \
                                    dt, t, v, a, state, weather, road_scene, light, gps_time, lon, lat, frams_id, i)

            in_acc = 3.0 if a >= self.max_acc else max(0, in_acc - dt)
            in_dcc = 3.0 if a <= self.max_dcc else max(0, in_dcc - dt)

            pre_frame_id, pre_gps_time, pre_lon, pre_lat = frams_id, gps_time, lon, lat

            pre_state, pre_t, pre_a = state, t, a

            # 速度保护，合理区间内才更新速度
            if v >= 0  and v <= 150:
                pre_v = v 

            pre_weather,pre_road_scene,pre_light = weather, road_scene, light


        total_frames = self.df['frame'].iloc[-1]

        # set all journey time
        self.journey.duration = self.df['time'].iloc[-1]/3600.0
        self.set_journeyStatistics_global_data(self.journey)


        is_urban = False

        polarStarhighway_dict = {
            "lane_change_cnt"                      : 10,  
            "lane_change_successful_cnt"           : 8,  
            "up_down_ramps_cnt"                    : 10,  
            "up_down_ramps_successful_cnt"         : 8,  
            "construction_scene_cnt"               : 10,  
            "construction_scene_successful_cnt"    : 8,  
            "lane_change_rate"                     : 0.8,  
            "up_down_ramps_successful_rate"        : 0.8,  
            "construction_scene_successful_rate"   : 0.8  
        }
        polarStarurban_dict = {
            "turn_cnt"                            : 1, 
            "turn_pass_cnt"                       : 2, 
            "turn_pass_rate"                      : 3, 
            "urban_road_coverage"                 : 4, 
            "auto_driving_efficiency"             : 5
        }


        CityNoaInterventionReseason = {
            "exceeding_speed_limit"                   : 1,
            "illegal_lane_change"                     : 2,
            "start_slowly"                            : 3,
            "braking_decelerating_slowly"             : 4,
            "running_traffic_lights"                  : 5,
            "failure_yield_pedestrians_crosswalks"    : 6,
            "failure_overtake_detour"                 : 7,
            "failure_follow_lane"                     : 8,
            "speed_slow"                              : 9,
            "speed_fast"                              : 10,
            "driving_without_following_directions"    : 11,
            "turn_early"                              : 12,
            "turn_late"                               : 13,
            "others"                                  : 14,
        }

        self.set_journeyStatistics_global_special_data(self.journey, polarStarhighway_dict,polarStarurban_dict, is_urban, CityNoaInterventionReseason)

        self.set_sceneStatistics_global_data(self.scenes.sunny)
        self.set_sceneStatistics_global_data(self.scenes.rainy)
        self.set_sceneStatistics_global_data(self.scenes.highway)
        self.set_sceneStatistics_global_data(self.scenes.expressway)
        self.set_sceneStatistics_global_data(self.scenes.urban)
        self.set_sceneStatistics_global_data(self.scenes.day)
        self.set_sceneStatistics_global_data(self.scenes.night)

        self.set_sceneStatistics_global_special_data(self.scenes.sunny, polarStarhighway_dict,polarStarurban_dict, is_urban, CityNoaInterventionReseason)
        self.set_sceneStatistics_global_special_data(self.scenes.rainy, polarStarhighway_dict,polarStarurban_dict, is_urban, CityNoaInterventionReseason)
        self.set_sceneStatistics_global_special_data(self.scenes.highway, polarStarhighway_dict,polarStarurban_dict, is_urban, CityNoaInterventionReseason)
        self.set_sceneStatistics_global_special_data(self.scenes.expressway, polarStarhighway_dict,polarStarurban_dict, is_urban, CityNoaInterventionReseason)
        self.set_sceneStatistics_global_special_data(self.scenes.urban, polarStarhighway_dict,polarStarurban_dict, is_urban, CityNoaInterventionReseason)
        self.set_sceneStatistics_global_special_data(self.scenes.day, polarStarhighway_dict,polarStarurban_dict, is_urban, CityNoaInterventionReseason)
        self.set_sceneStatistics_global_special_data(self.scenes.night, polarStarhighway_dict,polarStarurban_dict, is_urban, CityNoaInterventionReseason)

        # truck_avoidance_statistics
        print("="*10 + f'start cal  truck_avoidance_statistics' + "="*10)
        dict_avoid = self.cal_truck_avoidance_statistics()
        self.add_truck_avoidance_statistics(self.journey.auto, dict_avoid)
        self.add_truck_avoidance_statistics(self.journey.noa, dict_avoid,noa=True)
        self.add_truck_avoidance_statistics(self.journey.lcc, dict_avoid,lcc=True)
        self.add_truck_avoidance_statistics(self.journey.driver, dict_avoid,driving=True)

        # 设置MBTI 暂时服务于小程序
        if self.journey.driver.speed_average > self.average_speed_thre:
            chek_message.user.MBTI = self.MBTI_e
        else:
            chek_message.user.MBTI = self.MBTI_i

        if self.journey.auto.speed_average > self.average_speed_thre:
            chek_message.car.MBTI = self.MBTI_e
        else:
            chek_message.car.MBTI = self.MBTI_i    

        return chek_message


    def juege_status(self, state,acc,single_truck_avoid_noa_num,single_truck_avoid_lcc_num,single_truck_avoid_category,frame_id):

        if frame_id in self.gps_status_lcc_noa['intervention']:
            single_truck_avoid_noa_num = True
        if frame_id in self.gps_status_lcc_noa['intervention_risk']:
            single_truck_avoid_lcc_num = True

        if acc >= 1:
            single_truck_avoid_category = 'Acc'
        elif acc <= -1:
            single_truck_avoid_category = 'Dcc'
        else: # added by zjx category none to 'none'
            single_truck_avoid_category = 'None'

        return single_truck_avoid_noa_num,single_truck_avoid_lcc_num,single_truck_avoid_category


    def  cal_truck_avoidance_statistics(self):

        data_avoid = {}
        data_avoid['single'] = []

        #大车避让统计数据
        truck_avoid_num =0                    #大车避让次数
        truck_avoid_total_time = 0            #大车避让总时间
        truck_avoid_noa_num = 0               #大车避让接管次数
        truck_avoid_lcc_num = 0               #大车避让危险接管次数
        truck_avoid_average_lat_max_dis = 0   #大车避让总横向最大距离
        truck_avoid_average_lat_min_dis = 0   #大车避让总横向最小距离


        #每次大车避让数据
        single_truck_avoid_category = None         #每次避让策略   无/加速驶离/减速驶离
        single_initial_truck_avoid_time = 0        #每次大车避让开始时间点
        single_truck_avoid_total_time = 0          #每次大车避让总时间
        single_truck_avoid_noa_num = False         #每次大车避让noa接管
        single_truck_avoid_lcc_num = False         #每次大车避让lcc接管
        single_truck_avoid_lat_min_dis = 0         #每次大车避让总横向最小距离
        single_truck_avoid_lat_max_dis = 0         #每次大车避让总横向最大距离
        single_truck_frame_id = 0                  #每次大车避让开始id
        # single_truck_avoid_time = 0
        acc_state = 0   #加速度状态
        avoid_state = 0
        complete_truck_avoid_time = 0              #

        for i in self.df.index:
            time = self.df.loc[i,'time']
            
            truck_lon_dis = self.df.loc[i,'truck_lon_dis']
            truck_lat_dis = self.df.loc[i,'truck_lat_dis']
            truck_min_dis = self.df.loc[i,'truck_min_dis']
            acc = self.df.loc[i,'acc']
            state = self.df.loc[i,'state']
            frame_id = self.df.loc[i,'frame']

            if truck_lat_dis <=2 and not avoid_state:
                avoid_state = 1
                single_initial_truck_avoid_time = time
                single_truck_avoid_lat_min_dis = truck_min_dis
                single_truck_avoid_lat_max_dis = truck_min_dis
                single_truck_frame_id = frame_id

                #接管情况与避让策略
                single_truck_avoid_noa_num, single_truck_avoid_lcc_num,single_truck_avoid_category \
                    = self.juege_status(state, acc, single_truck_avoid_noa_num, single_truck_avoid_lcc_num,
                            single_truck_avoid_category,frame_id)

            if avoid_state:
                
                if truck_lon_dis >2 and truck_lat_dis>2:
                    # 结束避让状态
                    if not complete_truck_avoid_time:
                        complete_truck_avoid_time = time
                    avoid_state = 0
                    if time - single_initial_truck_avoid_time>1 and time - complete_truck_avoid_time>1:
                        complete_truck_avoid_time = 0
                        # added by zjx
                        # 2023.11.20
                        # 行程计算得到的接管点进行普通和危险接管过滤
                        # 行程列表中的点则加入大车必然接管最终结果列表
                        # 当前接管区间包含行程接管列表中的点

                        # 普通接管
                        single_truck_avoid_noa_num = False
                        single_truck_avoid_lcc_num = False
                        for frame in self.gps_status_lcc_noa['intervention']:
                            if frame <= frame_id and frame >= single_truck_frame_id:
                                single_truck_avoid_noa_num = True
                                break

                        # 危险接管
                        for frame in self.gps_status_lcc_noa['intervention_risk']:
                            if frame <= frame_id and frame >= single_truck_frame_id:
                                single_truck_avoid_lcc_num = True
                                break
                        #单次避让情况
                        item_avoid_single = {}
                        item_avoid_single['policy'] = single_truck_avoid_category
                        item_avoid_single['initial_time'] = single_initial_truck_avoid_time
                        item_avoid_single['duration'] = time - single_initial_truck_avoid_time
                        item_avoid_single['has_intervention'] = single_truck_avoid_noa_num
                        item_avoid_single['has_intervention_risk'] = single_truck_avoid_lcc_num
                        item_avoid_single['min_lat_distance'] = single_truck_avoid_lat_min_dis
                        item_avoid_single['max_lat_distance'] = single_truck_avoid_lat_max_dis
                        item_avoid_single['start_frame_id'] = single_truck_frame_id
                        item_avoid_single['end_frame_id'] = frame_id
                        data_avoid['single'].append(item_avoid_single)

                        # 避让类别
                        if item_avoid_single['has_intervention_risk']:
                            item_avoid_single['state_drive'] = 'lcc'
                        if item_avoid_single['has_intervention']:
                            item_avoid_single['state_drive'] = 'noa'
                        if 'state_drive' not in item_avoid_single.keys():
                            item_avoid_single['state_drive'] = 'driving'

                        #总避让统计情况
                        truck_avoid_num +=1
                        truck_avoid_total_time += item_avoid_single['duration']
                        truck_avoid_average_lat_max_dis += item_avoid_single['max_lat_distance']
                        truck_avoid_average_lat_min_dis += item_avoid_single['min_lat_distance']
                        if item_avoid_single['has_intervention']:
                            truck_avoid_noa_num +=1

                        if item_avoid_single['has_intervention_risk']:
                            truck_avoid_lcc_num +=1

                    elif truck_lat_dis ==999 and truck_lon_dis ==999:

                        # 每次大车避让数据
                        single_truck_avoid_category = None  # 每次避让策略   无/加速驶离/减速驶离
                        single_initial_truck_avoid_time = 0  # 每次大车避让开始时间点
                        single_truck_avoid_total_time = 0  # 每次大车避让总时间
                        single_truck_avoid_noa_num = False  # 每次大车避让noa接管
                        single_truck_avoid_lcc_num = False  # 每次大车避让lcc接管
                        single_truck_avoid_lat_min_dis = 0  # 每次大车避让总横向最小距离
                        single_truck_avoid_lat_max_dis = 0  # 每次大车避让总横向最大距离
                        single_truck_frame_id = 0  # 每次大车避让开始id
                        # single_truck_avoid_time = 0
                        acc_state = 0  # 加速度状态
                        avoid_state = 0
                        complete_truck_avoid_time = 0
                    else:
                        single_truck_avoid_lat_min_dis = min(single_truck_avoid_lat_min_dis, truck_min_dis)
                        single_truck_avoid_lat_max_dis = max(single_truck_avoid_lat_max_dis, truck_min_dis)

                        # 接管情况与避让策略
                        single_truck_avoid_noa_num, single_truck_avoid_lcc_num, single_truck_avoid_category \
                            = self.juege_status(state, acc, single_truck_avoid_noa_num, single_truck_avoid_lcc_num,
                                           single_truck_avoid_category,frame_id)


                else:
                    single_truck_avoid_lat_min_dis = min(single_truck_avoid_lat_min_dis,truck_min_dis)
                    single_truck_avoid_lat_max_dis = max(single_truck_avoid_lat_max_dis,truck_min_dis)

                    # 接管情况与避让策略
                    single_truck_avoid_noa_num, single_truck_avoid_lcc_num, single_truck_avoid_category \
                        = self.juege_status(state, acc, single_truck_avoid_noa_num, single_truck_avoid_lcc_num,
                                    single_truck_avoid_category,frame_id)

        data_avoid['avoid_cnt'] = truck_avoid_num
        data_avoid['average_duration'] = truck_avoid_total_time/(truck_avoid_num + 1e-5)
        data_avoid['intervention_cnt'] = truck_avoid_noa_num
        data_avoid['intervention_risk_cnt'] = truck_avoid_lcc_num
        data_avoid['average_min_lat_distance'] = truck_avoid_average_lat_min_dis/(truck_avoid_num + 1e-5)
        data_avoid['average_max_lat_distance'] = truck_avoid_average_lat_max_dis/(truck_avoid_num + 1e-5)
        return data_avoid

    def add_truck_avoidance(self, truck_avoidance_statistics,_):
        truckavoidance = truck_avoidance_statistics.truck_avoidances.add()
        truckavoidance.policy = _['policy']
        # truckavoidance.initial_time = _['initial_time']  #开始时间
        truckavoidance.duration = _['duration']
        truckavoidance.has_intervention = _['has_intervention']
        truckavoidance.has_intervention_risk = _['has_intervention_risk']
        truckavoidance.min_lat_distance = _['min_lat_distance']
        truckavoidance.max_lat_distance = _['max_lat_distance']
        truckavoidance.start_frame_id = _['start_frame_id']
        truckavoidance.end_frame_id = _['end_frame_id']
        # added by zjx
        # recorder truck_avoidance_list
        self.truck_avoidance_list.append((truckavoidance.start_frame_id, truckavoidance.end_frame_id))


    def add_truck_avoidance_statistics(self, truck_avoidance_statistics_sub,dict_avoid,lcc=False,noa=False,driving=False):
        #大车避让统计数据
        truck_avoid_num =0                    #大车避让次数
        truck_avoid_total_time = 0            #大车避让总时间
        truck_avoid_noa_num = 0               #大车避让接管次数
        truck_avoid_lcc_num = 0               #大车避让危险接管次数
        truck_avoid_average_lat_max_dis = 0   #大车避让总横向最大距离
        truck_avoid_average_lat_min_dis = 0   #大车避让总横向最小距离
        if not lcc and not noa and not driving:
            truck_avoidance_statistics = truck_avoidance_statistics_sub.truck_avoidance_statistics
            truck_avoidance_statistics.avoid_cnt = dict_avoid['avoid_cnt']
            truck_avoidance_statistics.average_duration = dict_avoid['average_duration']
            truck_avoidance_statistics.intervention_cnt = dict_avoid['intervention_cnt']
            truck_avoidance_statistics.intervention_risk_cnt = dict_avoid['intervention_risk_cnt']
            truck_avoidance_statistics.average_min_lat_distance = dict_avoid['average_min_lat_distance']
            truck_avoidance_statistics.average_max_lat_distance = dict_avoid['average_max_lat_distance']
            list_avoid = dict_avoid['single']
            for _ in list_avoid:
                self.add_truck_avoidance(truck_avoidance_statistics, _)

        elif noa:
            truck_avoidance_statistics = truck_avoidance_statistics_sub.truck_avoidance_statistics
            list_avoid = dict_avoid['single']
            for _ in list_avoid:
                if _['has_intervention']:
                    self.add_truck_avoidance(truck_avoidance_statistics, _)
                    truck_avoid_num += 1
                    truck_avoid_total_time += _['duration']
                    if _['has_intervention']:
                        truck_avoid_noa_num += 1
                    if _['has_intervention_risk']:
                        truck_avoid_lcc_num += 1
                    truck_avoid_average_lat_max_dis += _['max_lat_distance']
                    truck_avoid_average_lat_min_dis += _['min_lat_distance']

        elif lcc:
            truck_avoidance_statistics = truck_avoidance_statistics_sub.truck_avoidance_statistics
            list_avoid = dict_avoid['single']
            for _ in list_avoid:
                if _['has_intervention_risk']:
                    self.add_truck_avoidance(truck_avoidance_statistics, _)
                    truck_avoid_num += 1
                    truck_avoid_total_time += _['duration']
                    if _['has_intervention']:
                        truck_avoid_noa_num += 1
                    if _['has_intervention_risk']:
                        truck_avoid_lcc_num += 1
                    truck_avoid_average_lat_max_dis += _['max_lat_distance']
                    truck_avoid_average_lat_min_dis += _['min_lat_distance']

        elif driving:
            truck_avoidance_statistics = truck_avoidance_statistics_sub.truck_avoidance_statistics
            list_avoid = dict_avoid['single']
            for _ in list_avoid:
                if _['state_drive'] == 'driving':
                    self.add_truck_avoidance(truck_avoidance_statistics, _)
                    truck_avoid_num += 1
                    truck_avoid_total_time += _['duration']
                    if _['has_intervention']:
                        truck_avoid_noa_num += 1
                    if _['has_intervention_risk']:
                        truck_avoid_lcc_num += 1
                    truck_avoid_average_lat_max_dis += _['max_lat_distance']
                    truck_avoid_average_lat_min_dis += _['min_lat_distance']


        if truck_avoid_num > 0:
            truck_avoidance_statistics.avoid_cnt = truck_avoid_num
            truck_avoidance_statistics.average_duration = truck_avoid_total_time / truck_avoid_num
            truck_avoidance_statistics.intervention_cnt = truck_avoid_noa_num
            truck_avoidance_statistics.intervention_risk_cnt = truck_avoid_lcc_num
            truck_avoidance_statistics.average_min_lat_distance = truck_avoid_average_lat_min_dis / truck_avoid_num
            truck_avoidance_statistics.average_max_lat_distance = truck_avoid_average_lat_max_dis / truck_avoid_num
    

    # Set Jounry basic information
    def add_to(self, sub_journey, d_odo, in_acc, in_dcc, pre_a, dt, v, a, in_state, gps_time, lon, lat, time_interval, pre_v, is_driver = False, is_intervention = False):
        sub_journey.odometer += d_odo
        sub_journey.speed_average += v
        sub_journey.speed_max = max(v, sub_journey.speed_max)
        sub_journey.dcc_cnt += 1 if in_dcc == 0 and a <= self.max_dcc else 0
        sub_journey.dcc_frequency = sub_journey.odometer / \
            sub_journey.dcc_cnt if sub_journey.dcc_cnt > 0 else 0
        # sub_journey.dcc_average += a if in_dcc == 0 and a <= self.max_dcc else 0
        sub_journey.dcc_average += (
            -0.9 * self.g  if in_dcc == 0 and  a < -0.9 * self.g
            else (a if in_dcc == 0 and a <= self.max_dcc else 0)
        )


        # NOTE: 限制加速度
        #sub_journey.dcc_max = min(a, sub_journey.dcc_max)
        sub_journey.dcc_max = max(min(a, sub_journey.dcc_max), -0.9 * self.g)
        sub_journey.dcc_duration += dt if in_dcc > 0 and (
            pre_a <= self.max_dcc or a <= self.max_dcc) else 0
        sub_journey.acc_cnt += 1 if in_acc == 0 and a >= self.max_acc else 0
        sub_journey.acc_frequency = sub_journey.odometer / \
            sub_journey.acc_cnt if sub_journey.acc_cnt > 0 else 0
        # sub_journey.acc_average += a if in_acc == 0 and a >= self.max_acc else 0
        sub_journey.acc_average += (
            0.9 * self.g  if in_acc == 0 and  a > 0.9 * self.g
            else (a if a >= self.max_acc else 0)
        )

        # NOTE: 限制加速度
        #sub_journey.acc_max = max(a, sub_journey.acc_max)
        sub_journey.acc_max = min(0.9 * self.g, max(a, sub_journey.acc_max))
        sub_journey.acc_duration += dt if in_acc > 0 and (
            pre_a >= self.max_acc or a >= self.max_acc) else 0
        
        # Statistics journey runtime
        sub_journey.duration += (time_interval) / 3600.0 if pre_v > 0 else 0
        # Statistics journey frames
        sub_journey.frames += 1  if v > 0 else 0

        # TODO: truck
        if not in_state:
            sub_journey.gps_trajectories.add()
        if lon < 1 or lat < 1:
            return
        if len(sub_journey.gps_trajectories) > 0 and len(sub_journey.gps_trajectories[-1].points) > 0:
            last_gps_point = sub_journey.gps_trajectories[-1].points[-1]
            if lon == last_gps_point.lon and lat == last_gps_point.lat:
                return
        # if lon > 1 and lat > 1:
        #     if len(sub_journey.gps_trajectories) == 0:
        #         sub_journey.gps_trajectories.add()
        #     gps_point = sub_journey.gps_trajectories[-1].points.add()
        #     gps_point.datetime = str(gps_time)
        #     gps_point.lon = lon
        #     gps_point.lat = lat

        # NOTE: 对于接管来讲，若gps信号丢失则也不记录该点的位置信息
        if (lon > 1 and lat > 1 and (self.processed_frames % self.gps_interval == 0) or (is_driver and is_intervention)):
            if len(sub_journey.gps_trajectories) == 0:
                sub_journey.gps_trajectories.add()
            gps_point = sub_journey.gps_trajectories[-1].points.add()
            gps_point.datetime = str(gps_time)
            gps_point.lon = lon
            gps_point.lat = lat

    # 对于gps数据异常的帧
    # 接管数据依然计算在内
    # NOTE 接管gps点默认一个(0, 0)
    # 若前端使用该数据记得提醒要做一个是否有效gps点判断
    def calculate_intervention(self, sub_intervention_statistics, near_max_dcc, gps_time, lon, lat, frames_id):
        sub_intervention_statistics.cnt += 1
        if near_max_dcc <= self.max_dcc:
            sub_intervention_statistics.risk_cnt += 1
            # if lon < 1 or lat < 1:
            #     return
            if (lon < 1 or lat < 1) or (math.isnan(lon) or math.isnan(lat)):
                return
            intervention = sub_intervention_statistics.interventions.add()
            intervention.is_risk = True
        else:
            # if lon < 1 or lat < 1:
            #     return
            if (lon < 1 or lat < 1) or (math.isnan(lon) or math.isnan(lat)):
                return
            intervention = sub_intervention_statistics.interventions.add()
            intervention.is_risk = False
        intervention.frame_id = frames_id
        intervention.gps_position.datetime = str(gps_time)
        intervention.gps_position.lon = lon
        intervention.gps_position.lat = lat
        if intervention.is_risk and frames_id not in self.gps_status_lcc_noa['intervention_risk']:
            self.gps_status_lcc_noa['intervention_risk'].append(frames_id)

        if not intervention.is_risk and frames_id not in self.gps_status_lcc_noa['intervention']:
            self.gps_status_lcc_noa['intervention'].append(frames_id)

    #小程序参考代码calculate_intervention
    # def calculate_intervention(self, sub_journey, near_max_dcc, gps_time, lon, lat):
    #     sub_journey.intervention += 1
    #     if near_max_dcc <= self.max_dcc:
    #         sub_journey.intervention_risk += 1
    #         if (lon < 1 or lat < 1) or (math.isnan(lon) or math.isnan(lat)):
    #             return
    #         gps_point = sub_journey.intervention_risk_gps_points.add()
    #     else:
    #         if (lon < 1 or lat < 1) or (math.isnan(lon) or math.isnan(lat)):
    #             return
    #         gps_point = sub_journey.intervention_gps_points.add()
    #     # gps_point.datetime = str(gps_time)
    #     gps_point.lon = lon
    #     gps_point.lat = lat

    def post_caculate(self, sub_journey, frames, auto_odometer,is_auto=True):
        sub_journey.speed_average /= frames if frames > 0 else 1e-5
        sub_journey.dcc_average /= sub_journey.dcc_cnt if sub_journey.dcc_cnt > 0 else -1*1e-5
        sub_journey.acc_average /= sub_journey.acc_cnt if sub_journey.acc_cnt > 0 else 1e-5
        if is_auto:

            # sub_journey.intervention_statistics.mpi = auto_odometer / \
            #     (sub_journey.intervention_statistics.cnt + 1) 
            # sub_journey.intervention_statistics.risk_mpi = auto_odometer / \
            #     (sub_journey.intervention_statistics.risk_cnt + 1) 

            # sub_journey.intervention_statistics.risk_proportion = sub_journey.intervention_statistics.mpi / \
            #     sub_journey.intervention_statistics.risk_mpi if sub_journey.intervention_statistics.risk_mpi > 0 else 1e-5 #1

            #2025.05.14 
            #调整接管返回结果 key
            if sub_journey.intervention_statistics.cnt!=0:
                sub_journey.intervention_statistics.mpi = auto_odometer / \
                    (sub_journey.intervention_statistics.cnt ) 
        
            else:
                sub_journey.intervention_statistics.mpi = 0.0
              

            if sub_journey.intervention_statistics.risk_cnt!=0:
                    
                sub_journey.intervention_statistics.risk_mpi = auto_odometer / \
                    (sub_journey.intervention_statistics.risk_cnt ) 
            else:
                sub_journey.intervention_statistics.risk_mpi = 0.0

            if sub_journey.intervention_statistics.risk_mpi>0 and sub_journey.intervention_statistics.mpi>0:
                sub_journey.intervention_statistics.risk_proportion = sub_journey.intervention_statistics.mpi / \
                sub_journey.intervention_statistics.risk_mpi if sub_journey.intervention_statistics.risk_mpi > 0 else 1e-5 #1
            else:
                sub_journey.intervention_statistics.risk_proportion = 1e-5

    def set_journeyStatistics_global_data(self, journeyStatistics):
        # Complete journey
        # journey.datetime = start_gps_time if start_gps_time is not None else '1999.01.01 00:00:00'

        # modified by zjx 
        # 2023.10.12
        # 所有mpi数据调整为智驾里程处理
        odometer_total = journeyStatistics.auto.odometer + journeyStatistics.driver.odometer
        odometer_auto = journeyStatistics.auto.odometer  
        duration_total = journeyStatistics.auto.duration + journeyStatistics.driver.duration

        odometer_total = odometer_total if odometer_total > 0 else 0
        odometer_auto = odometer_auto if odometer_auto > 0 else 0
        duration_total = duration_total if duration_total > 0 else 0

        journeyStatistics.datetime = self.journey_datetime  # TODO
        journeyStatistics.duration = duration_total if duration_total >journeyStatistics.duration else journeyStatistics.duration
        journeyStatistics.odometer_total = odometer_total
        journeyStatistics.odometer_auto = odometer_auto
        journeyStatistics.odometer_hmi = 73  # TODO: detect from hmi
        journeyStatistics.odometer_accuracy = (
            self.journey.odometer_total / self.journey.odometer_hmi)*100
    
        self.post_caculate(journeyStatistics.auto, journeyStatistics.noa.frames+journeyStatistics.lcc.frames, odometer_auto)
        self.post_caculate(journeyStatistics.noa, journeyStatistics.noa.frames, odometer_auto)
        self.post_caculate(journeyStatistics.lcc, journeyStatistics.lcc.frames, odometer_auto)
        self.post_caculate(journeyStatistics.driver, journeyStatistics.driver.frames, odometer_auto,is_auto=False)  

    # NOTE 接管状态中，noa lcc -> driver
    #      状态转换后，driver状态保持判断
    def calculate_JourneyStatistics(self, sub_journeyStatistics, d_odo, in_acc, in_dcc, pre_state, pre_t, pre_v, pre_a, dt, time, speed, acc, state, gps_time, lon, lat, frams_id, rows_id,in_state_scene=True):
        """
        in_state_scence: pre frame and cur frame are in same scence 
        """
        # 
        if state == 'noa':
            #noa_frames += 1 if v > 0 else 0
            # Statistics noa runtime
            # calculate time_interval i - 1 -> i 
            # pre_state == 'noa' means in noa journey
            # in_state_scence means in same scene
            time_interval = time - pre_t if (pre_state == 'noa') and in_state_scene else 0


            self.add_to(sub_journeyStatistics.noa, d_odo, in_acc, in_dcc, pre_a, dt, speed, acc,
                   (state == pre_state) and in_state_scene, gps_time, lon, lat, time_interval, pre_v)
            self.add_to(sub_journeyStatistics.auto, d_odo, in_acc, in_dcc, pre_a, dt, speed, acc,
                   (state == pre_state) and in_state_scene, gps_time, lon, lat, time_interval, pre_v)
        elif state == 'lcc':
            #lcc_frames += 1 if v > 0 else 0
            # Statistics lcc runtime
            # calculate time_interval i - 1 -> i 
            # pre_state == 'lcc' means in lcc journey
            # in_state_scence means in same scene
            time_interval = time - pre_t if (pre_state == 'lcc') and in_state_scene else 0
            #lcc_runtime += time_interval if pre_v > 0 else 0

            self.add_to(sub_journeyStatistics.lcc, d_odo, in_acc, in_dcc, pre_a, dt, speed, acc,
                   (state == pre_state) and in_state_scene, gps_time, lon, lat, time_interval, pre_v)
            self.add_to(sub_journeyStatistics.auto, d_odo, in_acc, in_dcc, pre_a, dt, speed, acc,
                   (state == pre_state) and in_state_scene, gps_time, lon, lat, time_interval, pre_v)
        else:  # state = 'driver'
            
            is_intervention = False
            #driver_frames += 1 if v > 0 else 0
            # Statistics driver runtime
            # calculate time_interval i - 1 -> i 
            # pre_state == 'driver' means in driver journey
            # in_state_scence means in same scene
            time_interval = time - pre_t if (pre_state == 'standby') and in_state_scene else 0
            #driver_runtime += time_interval if pre_v > 0 else 0

            # self.add_to(sub_journeyStatistics.driver, d_odo, in_acc, in_dcc, pre_a, dt, speed, acc,
            #        (state == pre_state) and in_state_scene, gps_time, lon, lat, time_interval, pre_v)
            # Intervention
            rows = self.df.shape[0]
            
            # near_max_dcc = self.df['acc'][max(0, rows_id-3):rows_id+3].min()
            near_window_start = max(0, rows_id - 3)
            near_window_end = min(len(self.accs), rows_id + 3)
            near_max_dcc = self.accs[near_window_start:near_window_end].min()
            if pre_state == 'noa' or pre_state == 'lcc':
                # print(f'intervention at {i}')

                # NOTE 接管判定
                isReal_driver = False
                # 之前是智驾状态
                isReal_auto_driver = True
                # 后续状态真的保持driver
                # 持续时间判定：阈值判定(s)

                # modified by zjx 2023.12.15
                # 降低状态后置切换时间阈值
                fps = 30
                # modified by zjx
                # 城区路况复杂，人为驾驶0.5s可能直接能转智驾
                # 
                time_thre_before = 5
                time_thre_after = 5 #0.5
                # if rows_id == 5081:
                #     k = 100

                # frames_time = self.df.iloc[rows_id]['time']

                frames_time = self.times[rows_id]
                # NOTE: frams_time_next 赋初值
                frams_time_next = frames_time
                #20250623暂停使用
                # for i in range(rows_id, len(self.df)):
                #     if self.df.iloc[i]['state'] != 'noa' and self.df.iloc[i]['state'] != 'lcc':
                #         frams_time_next = self.df.iloc[i]['time']
                #         if frams_time_next - frames_time > time_thre_after:
                #             break
                #     else:
                #         break
     

                #key
                for i in range(rows_id, len(self.states)):
                    s = self.states[i]
                    if s not in ('noa', 'lcc'):
                        frams_time_next = self.times[i]
                        if frams_time_next - frames_time > time_thre_after:
                            break
                    else:
                        break
                    
                # 计算当前帧time_thre之前的连续状态为智驾
                #start_frame_id = min(max(0,(rows_id - fps * time_thre)), len(df) - 1)
                
                start_frame_id = min(max(0,(rows_id - 1)), len(self.df) - 1)
                # NOTE： frames_time_before 赋初值
                # frames_time_before = self.df.iloc[start_frame_id]['time']
                # for i in range(start_frame_id, -1, -1):
                #     # if start_frame_id == 11063:
                #     #     a = 100
                #     #if df.iloc[i]['state'] == pre_state:
                #     if self.df.iloc[i]['state'] == 'noa' or self.df.iloc[i]['state'] == 'lcc':
                #         frames_time_before = self.df.iloc[i]['time']
                #         if frames_time - frames_time_before > time_thre_before:
                #             break
                #     else:
                #         break

                #           start_idx = max(0, rows_id - 1)

                start_idx = max(0, rows_id - 1)
                frames_time_before = self.times[start_idx]
                for i in range(start_idx, -1, -1):
                    s = self.states[i]
                    if s in ('noa', 'lcc'):
                        frames_time_before = self.times[i]
                        if frames_time - frames_time_before > time_thre_before:
                            break
                    else:
                        break
                
                isReal_driver = True if frams_time_next - frames_time > time_thre_after else False
                isReal_auto_driver = True if frames_time - frames_time_before> time_thre_before else False

                is_intervention = isReal_driver and isReal_auto_driver

                if isReal_driver and isReal_auto_driver:
                    self.calculate_intervention(
                        sub_journeyStatistics.auto.intervention_statistics, near_max_dcc, gps_time, lon, lat, frams_id)
                    
                    if pre_state == 'noa':
                        self.calculate_intervention(
                            sub_journeyStatistics.noa.intervention_statistics, near_max_dcc, gps_time, lon, lat, frams_id)
                    elif pre_state == 'lcc':
                        self.calculate_intervention(
                            sub_journeyStatistics.lcc.intervention_statistics, near_max_dcc, gps_time, lon, lat, frams_id)

                    #2025.05.14 
                    #调整接管返回结果 key
                    #当“接管”或“危险接管”在3秒内连续出现时，记为1次
                    # if not self.pre_intervention_time :
                    #     self.calculate_intervention(
                    #     sub_journeyStatistics.auto.intervention_statistics, near_max_dcc, gps_time, lon, lat, frams_id)
                    
                    #     if pre_state == 'noa':
                    #         self.calculate_intervention(
                    #             sub_journeyStatistics.noa.intervention_statistics, near_max_dcc, gps_time, lon, lat, frams_id)
                    #     elif pre_state == 'lcc':
                    #         self.calculate_intervention(
                    #             sub_journeyStatistics.lcc.intervention_statistics, near_max_dcc, gps_time, lon, lat, frams_id)
                    #     self.pre_intervention_time = frames_time

                    # elif frames_time - self.pre_intervention_time>3:
                    #     self.calculate_intervention(
                    #     sub_journeyStatistics.auto.intervention_statistics, near_max_dcc, gps_time, lon, lat, frams_id)
                    
                    #     if pre_state == 'noa':
                    #         self.calculate_intervention(
                    #             sub_journeyStatistics.noa.intervention_statistics, near_max_dcc, gps_time, lon, lat, frams_id)
                    #     elif pre_state == 'lcc':
                    #         self.calculate_intervention(
                    #             sub_journeyStatistics.lcc.intervention_statistics, near_max_dcc, gps_time, lon, lat, frams_id)
                    #     self.pre_intervention_time = frames_time


            self.add_to(sub_journeyStatistics.driver, d_odo, in_acc, in_dcc, pre_a, dt, speed, acc,
                   (state == pre_state) and in_state_scene, gps_time, lon, lat, time_interval, pre_v, is_driver=True, is_intervention=is_intervention)

    #calculate SceneStatistics data
    # 增加csv行数据， 利于csv基于当前行上下索引
    def calculate_SceneStatistics(self, sub_scenes, d_odo, in_acc, in_dcc, pre_state, pre_t, pre_v, pre_a, pre_weather,pre_road_scene,pre_light, \
                                   dt, time, speed, acc, state, weather, road_scene, light, gps_time, lon, lat, frams_id, rows_id):
        # get city gps point in
        # start_time = run_time.time()
        # lon_tmp = "%.6f" % lon
        # lat_tmp = "%.6f" % lat
        # city = []
        # if lon > 1 and lat > 1:
        #     location = lon_tmp + ',' + lat_tmp
        #     city = regeocode(location)
        #     end_time = run_time.time()
        #     spend_time = end_time - start_time
        #     print("="*10 + f'get_city_name spend time: {spend_time}' + "="*10)

        # city = []
        # item = {}
        # if lon > 1 and lat > 1:
        #     start_time = run_time.time()
        #     #item = query_region_info(lon, lat)
        #     item = start_query_region_info(db, cur, lon, lat)
        #     end_time = run_time.time()
        #     spend_time = end_time - start_time
        #     print("="*10 + f'get_city_name spend time: {spend_time}' + "="*10)
        # if item != {}:
        #     city = item['city']



        if weather == 'sunny':

            self.calculate_JourneyStatistics(sub_scenes.sunny.journeyStatistics, d_odo, in_acc, in_dcc, \
                                        pre_state, pre_t, pre_v, pre_a, dt, time, speed, acc, state, gps_time, lon, lat, frams_id,rows_id, pre_weather == 'sunny')
            
            
            
            # if city != []:
            #     sub_scenes.sunny.city_dict[city] += 1 

        elif weather == 'rainy':

            self.calculate_JourneyStatistics(sub_scenes.rainy.journeyStatistics, d_odo, in_acc, in_dcc, \
                                        pre_state, pre_t, pre_v, pre_a, dt, time, speed, acc, state, gps_time, lon, lat, frams_id,rows_id, pre_weather == 'rainy')
            
            # if city != []:
            #     sub_scenes.rainy.city_dict[city] += 1 


        if road_scene =='highway':

            self.calculate_JourneyStatistics(sub_scenes.highway.journeyStatistics, d_odo, in_acc, in_dcc, \
                                        pre_state, pre_t, pre_v, pre_a, dt, time, speed, acc, state, gps_time, lon, lat, frams_id,rows_id, pre_road_scene == 'highway')     
            
            # if city != []:
            #     sub_scenes.highway.city_dict[city] += 1      

            self.highway_frames += 1


        elif road_scene =='expressway':

            self.calculate_JourneyStatistics(sub_scenes.expressway.journeyStatistics, d_odo, in_acc, in_dcc, \
                                        pre_state, pre_t, pre_v, pre_a, dt, time, speed, acc, state, gps_time, lon, lat, frams_id,rows_id, pre_road_scene == 'expressway')     
            
            # if city != []:
            #     sub_scenes.expressway.city_dict[city] += 1        

        elif road_scene == 'urban':
            self.calculate_JourneyStatistics(sub_scenes.urban.journeyStatistics, d_odo, in_acc, in_dcc, \
                                        pre_state, pre_t, pre_v, pre_a, dt, time, speed, acc, state, gps_time, lon, lat, frams_id,rows_id, pre_road_scene == 'urban')   
            
            # if city != []:
            #     sub_scenes.urban.city_dict[city] += 1    

            self.urban_frames += 1 
            
        if light == 'day':
            self.calculate_JourneyStatistics(sub_scenes.day.journeyStatistics, d_odo, in_acc, in_dcc, \
                                        pre_state, pre_t, pre_v, pre_a, dt, time, speed, acc, state, gps_time, lon, lat, frams_id,rows_id, pre_light == 'day')   

            # if city != []:
            #     sub_scenes.day.city_dict[city] += 1   

        elif  light == 'night':
            self.calculate_JourneyStatistics(sub_scenes.night.journeyStatistics, d_odo, in_acc, in_dcc, \
                                        pre_state, pre_t, pre_v, pre_a, dt, time, speed, acc, state, gps_time, lon, lat, frams_id,rows_id, pre_light == 'night')    
            
            # if city != []:
            #     sub_scenes.night.city_dict[city] += 1   



    def set_sceneStatistics_global_data(self, sub_scene):
        # Complete journey
        odometer = (sub_scene.journeyStatistics.auto.odometer + sub_scene.journeyStatistics.driver.odometer) 
        auto_odometer = sub_scene.journeyStatistics.auto.odometer
        Intervention = sub_scene.journeyStatistics.auto.intervention_statistics.cnt 
        risk_intervention = sub_scene.journeyStatistics.auto.intervention_statistics.risk_cnt

        sub_scene.odometer = odometer if odometer > 0 else 0
        sub_scene.auto_odometer = auto_odometer if auto_odometer > 0 else 0
        sub_scene.Intervention = Intervention if Intervention > 0 else 0 
        sub_scene.risk_intervention = risk_intervention if risk_intervention > 0 else 0

        self.set_journeyStatistics_global_data(sub_scene.journeyStatistics)



    # aws function
    # 接管视频和危险接管视频都切
    def process_list_csv_save_journey(self, upload_journey = False):

        # files = get_all_specify_filename_files(self.csv_root_path, self.csv_name)

        json_file_list = []

        message = []
        frame_intervention_file = {}
        frame_intervention_risk_file = {}

        for file_name in self.csv_files:
            # file_name = str(file_name)
            # print("processed csv is: " + file_name)
            chek_message = self.extract_chek_message(file_name)

            # Set user information
            chek_message.user.id = self.user_id
            chek_message.user.name = self.user_name
            chek_message.user.phone = self.user_phone
            chek_message.user.MBTI = self.user_MBTI
            # Set car information
            chek_message.car.brand    = self.car_brand
            chek_message.car.model    = self.car_model
            chek_message.car.car_name = self.car_brand + self.car_model
            chek_message.car.hardware_version = self.car_hardware_version
            chek_message.car.software_version = self.car_software_version
            chek_message.car.MBTI = self.car_MBTI

            # set description
            chek_message.description.noa_road_status_code = self.description_noa_road_status_code    
            chek_message.description.city_noa_merge_code  = self.description_city_noa_merge_code  
            chek_message.description.city                 = self.description_city 
            chek_message.description.evaluated_scenarios  = self.description_evaluated_scenarios   
            chek_message.description.pdf_file_path        = self.description_pdf_file_path

            # path = create_folders_from_filename(self.json_root_path, file_name, self.json_name, start_index = 8)
            #暂停使用
            # file_path_parts = file_name.split('/')
            # end_path = file_path_parts[-1]
            # end_path = re.sub(r'\.pro\.csv', '.json', end_path)
            # file_path_parts[-1] = end_path
            # json_file = '/'.join(file_path_parts)
            
            # save_to_json(chek_message, json_file)
            # json_file_list.append(json_file)
            message.append(chek_message)

            # 统计接管每一个文件帧
            #暂停使用
            # new_file = file_name #"/".join(file_name.split('/')[1:])
            # file_path_parts = new_file.split('/')
            # fileName = file_path_parts[-1]
            # new_file_name = re.sub(r'\.pro(?=\.csv)','',fileName)
            # file_path_parts[-1] = new_file_name
            # new_file = '/'.join(file_path_parts)

            # if len(self.gps_status_lcc_noa['intervention']) > 0:
            #     frame_intervention_file[new_file] = copy.deepcopy(self.gps_status_lcc_noa['intervention'])
            
            # if len(self.gps_status_lcc_noa['intervention_risk']) > 0: 
            #     frame_intervention_risk_file[new_file] = copy.deepcopy(self.gps_status_lcc_noa['intervention_risk'])


        total_message = merge_messages(message)    
        
        # 计算 total_message file name
        total_message_name = 'total_message_' 
        now = datetime.now()
        total_message_name += now.strftime("%Y-%m-%d %H:%M:%S") + "_"
        data_list, _save_root_path = self.get_data_list()
        for data in data_list:
            total_message_name += data + '_'
        
        total_message_name += '.json'

        # save_to_json(total_message, _save_root_path + total_message_name)
        # json_file_list.append(_save_root_path + total_message_name)
        print("all pro csv have been successfully completed!")

        # if (upload_journey and total_message.journey.odometer_total > self.odometer_thresh):
        # 没有里程限制
        if (upload_journey):
            self.publish_message(total_message) 
        else:
            print(f"The odometer is {total_message.journey.odometer_total} not satisfy bigger than {self.odometer_thresh}")


        return frame_intervention_file, frame_intervention_risk_file, json_file_list,total_message



    # aws function
    # 接管视频和危险接管视频都切
    def process_save_journey(self, upload_journey = False):

        # files = get_all_specify_filename_files(self.csv_root_path, self.csv_name)

        json_file_list = []

        message = []
        frame_intervention_file = {}
        frame_intervention_risk_file = {}
        if len(self.csv_files) == 1:
            file_name = self.csv_files[0]
            file_name = str(file_name)
            print("processed csv is: " + file_name)
            chek_message = self.extract_chek_message(file_name)

            # Set user information
            chek_message.user.id = self.user_id
            chek_message.user.name = self.user_name
            chek_message.user.phone = self.user_phone
            chek_message.user.MBTI = self.user_MBTI
            # Set car information
            chek_message.car.brand    = self.car_brand
            chek_message.car.model    = self.car_model
            chek_message.car.car_name = self.car_brand + self.car_model
            chek_message.car.hardware_version = self.car_hardware_version
            chek_message.car.software_version = self.car_software_version
            chek_message.car.MBTI = self.car_MBTI

            # set description
            chek_message.description.noa_road_status_code = self.description_noa_road_status_code    
            chek_message.description.city_noa_merge_code  = self.description_city_noa_merge_code  
            chek_message.description.city                 = self.description_city 
            chek_message.description.evaluated_scenarios  = self.description_evaluated_scenarios   
            chek_message.description.pdf_file_path        = self.description_pdf_file_path

            # path = create_folders_from_filename(self.json_root_path, file_name, self.json_name, start_index = 8)
            file_path_parts = file_name.split('/')
            end_path = file_path_parts[-1]
            end_path = re.sub(r'\.pro\.csv', '.json', end_path)
            file_path_parts[-1] = end_path
            json_file = '/'.join(file_path_parts)
            save_to_json(chek_message, json_file)
            json_file_list.append(json_file)
            message.append(chek_message)

            # 统计接管每一个文件帧
            new_file = file_name #"/".join(file_name.split('/')[1:])
            file_path_parts = new_file.split('/')
            fileName = file_path_parts[-1]
            new_file_name = re.sub(r'\.pro(?=\.csv)','',fileName)
            file_path_parts[-1] = new_file_name
            new_file = '/'.join(file_path_parts)
            if len(self.gps_status_lcc_noa['intervention']) > 0:
                frame_intervention_file[new_file] = copy.deepcopy(self.gps_status_lcc_noa['intervention'])
            
            if len(self.gps_status_lcc_noa['intervention_risk']) > 0: 
                frame_intervention_risk_file[new_file] = copy.deepcopy(self.gps_status_lcc_noa['intervention_risk'])

            print("all pro csv have been successfully completed!")
            if (upload_journey and chek_message.journeyStatistics.odometer_total > self.odometer_thresh):
                self.publish_message(chek_message) 
            else:
                print(f"The odometer is {chek_message.journeyStatistics.odometer_total} not satisfy bigger than {self.odometer_thresh}")
            
        else:
            print(f"There has no journey to be processed!")

        return frame_intervention_file, frame_intervention_risk_file, json_file_list


    def set_sceneStatistics_global_special_data(self, sub_scene, polarStarhighway_dict,polarStarurban_dict, is_urban = False, interventionReseason={}):
        """
        北极星、接管原因赋值
        """

        # highway polarstar
        sub_scene.journeyStatistics.polarStarhighway.lane_change_cnt = polarStarhighway_dict["lane_change_cnt"]
        sub_scene.journeyStatistics.polarStarhighway.lane_change_successful_cnt = polarStarhighway_dict["lane_change_successful_cnt"]
        sub_scene.journeyStatistics.polarStarhighway.up_down_ramps_cnt = polarStarhighway_dict["up_down_ramps_cnt"]
        sub_scene.journeyStatistics.polarStarhighway.up_down_ramps_successful_cnt = polarStarhighway_dict["up_down_ramps_successful_cnt"]
        sub_scene.journeyStatistics.polarStarhighway.construction_scene_cnt = polarStarhighway_dict["construction_scene_cnt"]
        sub_scene.journeyStatistics.polarStarhighway.construction_scene_successful_cnt = polarStarhighway_dict["construction_scene_successful_cnt"]
        sub_scene.journeyStatistics.polarStarhighway.lane_change_rate = polarStarhighway_dict["lane_change_rate"]
        sub_scene.journeyStatistics.polarStarhighway.up_down_ramps_successful_rate = polarStarhighway_dict["up_down_ramps_successful_rate"]
        sub_scene.journeyStatistics.polarStarhighway.construction_scene_successful_rate = polarStarhighway_dict["construction_scene_successful_rate"]

        # Urban polarstar
        sub_scene.journeyStatistics.polarStarUrban.turn_cnt = polarStarurban_dict["turn_cnt"]
        sub_scene.journeyStatistics.polarStarUrban.turn_pass_cnt = polarStarurban_dict["turn_pass_cnt"]
        sub_scene.journeyStatistics.polarStarUrban.turn_pass_rate = polarStarurban_dict["turn_pass_rate"]
        sub_scene.journeyStatistics.polarStarUrban.urban_road_coverage = polarStarurban_dict["urban_road_coverage"]
        sub_scene.journeyStatistics.polarStarUrban.auto_driving_efficiency = polarStarurban_dict["auto_driving_efficiency"]

        if is_urban:
            # highway CityNoaInterventionReseason
            sub_scene.journeyStatistics.cityNoaInterventionReseason.exceeding_speed_limit = interventionReseason["exceeding_speed_limit"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.illegal_lane_change = interventionReseason["illegal_lane_change"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.start_slowly = interventionReseason["start_slowly"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.braking_decelerating_slowly = interventionReseason["braking_decelerating_slowly"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.running_traffic_lights = interventionReseason["running_traffic_lights"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.failure_yield_pedestrians_crosswalks = interventionReseason["failure_yield_pedestrians_crosswalks"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.failure_overtake_detour = interventionReseason["failure_overtake_detour"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.failure_follow_lane = interventionReseason["failure_follow_lane"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.speed_slow = interventionReseason["speed_slow"]

            # Urban polarstar
            sub_scene.journeyStatistics.cityNoaInterventionReseason.speed_fast = interventionReseason["speed_fast"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.driving_without_following_directions = interventionReseason["driving_without_following_directions"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.turn_early = interventionReseason["turn_early"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.turn_late = interventionReseason["turn_late"]
            sub_scene.journeyStatistics.cityNoaInterventionReseason.others = interventionReseason["others"]  
        else:
            sub_scene.journeyStatistics.cityNoaInterventionReseason.exceeding_speed_limit     = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.illegal_lane_change       = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.start_slowly              = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.braking_decelerating_slowly = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.running_traffic_lights = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.failure_yield_pedestrians_crosswalks = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.failure_overtake_detour = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.failure_follow_lane = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.speed_slow = 0

            sub_scene.journeyStatistics.cityNoaInterventionReseason.speed_fast = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.driving_without_following_directions = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.turn_early = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.turn_late = 0
            sub_scene.journeyStatistics.cityNoaInterventionReseason.others = 0           


    def set_journeyStatistics_global_special_data(self, journeyStatistics, polarStarhighway_dict,polarStarurban_dict, is_urban = False, interventionReseason={}):
        """
        北极星、接管原因赋值
        """

        # highway polarstar
        journeyStatistics.polarStarhighway.lane_change_cnt = polarStarhighway_dict["lane_change_cnt"]
        journeyStatistics.polarStarhighway.lane_change_successful_cnt = polarStarhighway_dict["lane_change_successful_cnt"]
        journeyStatistics.polarStarhighway.up_down_ramps_cnt = polarStarhighway_dict["up_down_ramps_cnt"]
        journeyStatistics.polarStarhighway.up_down_ramps_successful_cnt = polarStarhighway_dict["up_down_ramps_successful_cnt"]
        journeyStatistics.polarStarhighway.construction_scene_cnt = polarStarhighway_dict["construction_scene_cnt"]
        journeyStatistics.polarStarhighway.construction_scene_successful_cnt = polarStarhighway_dict["construction_scene_successful_cnt"]
        journeyStatistics.polarStarhighway.lane_change_rate = polarStarhighway_dict["lane_change_rate"]
        journeyStatistics.polarStarhighway.up_down_ramps_successful_rate = polarStarhighway_dict["up_down_ramps_successful_rate"]
        journeyStatistics.polarStarhighway.construction_scene_successful_rate = polarStarhighway_dict["construction_scene_successful_rate"]

        # Urban polarstar
        journeyStatistics.polarStarUrban.turn_cnt = polarStarurban_dict["turn_cnt"]
        journeyStatistics.polarStarUrban.turn_pass_cnt = polarStarurban_dict["turn_pass_cnt"]
        journeyStatistics.polarStarUrban.turn_pass_rate = polarStarurban_dict["turn_pass_rate"]
        journeyStatistics.polarStarUrban.urban_road_coverage = polarStarurban_dict["urban_road_coverage"]
        journeyStatistics.polarStarUrban.auto_driving_efficiency = polarStarurban_dict["auto_driving_efficiency"]

        if is_urban:
            # highway CityNoaInterventionReseason
            journeyStatistics.cityNoaInterventionReseason.exceeding_speed_limit = interventionReseason["exceeding_speed_limit"]
            journeyStatistics.cityNoaInterventionReseason.illegal_lane_change = interventionReseason["illegal_lane_change"]
            journeyStatistics.cityNoaInterventionReseason.start_slowly = interventionReseason["start_slowly"]
            journeyStatistics.cityNoaInterventionReseason.braking_decelerating_slowly = interventionReseason["braking_decelerating_slowly"]
            journeyStatistics.cityNoaInterventionReseason.running_traffic_lights = interventionReseason["running_traffic_lights"]
            journeyStatistics.cityNoaInterventionReseason.failure_yield_pedestrians_crosswalks = interventionReseason["failure_yield_pedestrians_crosswalks"]
            journeyStatistics.cityNoaInterventionReseason.failure_overtake_detour = interventionReseason["failure_overtake_detour"]
            journeyStatistics.cityNoaInterventionReseason.failure_follow_lane = interventionReseason["failure_follow_lane"]
            journeyStatistics.cityNoaInterventionReseason.speed_slow = interventionReseason["speed_slow"]

            
            journeyStatistics.cityNoaInterventionReseason.speed_fast = interventionReseason["speed_fast"]
            journeyStatistics.cityNoaInterventionReseason.driving_without_following_directions = interventionReseason["driving_without_following_directions"]
            journeyStatistics.cityNoaInterventionReseason.turn_early = interventionReseason["turn_early"]
            journeyStatistics.cityNoaInterventionReseason.turn_late = interventionReseason["turn_late"]
            journeyStatistics.cityNoaInterventionReseason.others = interventionReseason["others"] 
        else:
            journeyStatistics.cityNoaInterventionReseason.exceeding_speed_limit     = 0
            journeyStatistics.cityNoaInterventionReseason.illegal_lane_change       = 0
            journeyStatistics.cityNoaInterventionReseason.start_slowly              = 0
            journeyStatistics.cityNoaInterventionReseason.braking_decelerating_slowly = 0
            journeyStatistics.cityNoaInterventionReseason.running_traffic_lights = 0
            journeyStatistics.cityNoaInterventionReseason.failure_yield_pedestrians_crosswalks = 0
            journeyStatistics.cityNoaInterventionReseason.failure_overtake_detour = 0
            journeyStatistics.cityNoaInterventionReseason.failure_follow_lane = 0
            journeyStatistics.cityNoaInterventionReseason.speed_slow = 0

            
            journeyStatistics.cityNoaInterventionReseason.speed_fast = 0
            journeyStatistics.cityNoaInterventionReseason.driving_without_following_directions = 0
            journeyStatistics.cityNoaInterventionReseason.turn_early = 0
            journeyStatistics.cityNoaInterventionReseason.turn_late = 0
            journeyStatistics.cityNoaInterventionReseason.others = 0  


# def truck_avoidance_statistics(journeyStatistics):
#     #大车避让统计起止帧

#     auto_truck_avoidance_statistics = journeyStatistics.auto.truck_avoidance_statistics
#     driver_truck_avoidance_statistics = journeyStatistics.driver.truck_avoidance_statistics

#     auto_truck_avoidances = auto_truck_avoidance_statistics.truck_avoidances
#     driver_truck_avoidances = driver_truck_avoidance_statistics.truck_avoidances

#     for avoidances in auto_truck_avoidances:
#         truck_avoidance_list.append((avoidances.start_frame_id, avoidances.end_frame_id))

#     for avoidances in driver_truck_avoidances:
#         truck_avoidance_list.append((avoidances.start_frame_id, avoidances.end_frame_id))
    
#     truck_avoidance_list.sort()

    

# def publish_message(chek_message: chek.ChekMessage):
#     # Create gprc client
#     channel = grpc.insecure_channel('62.234.57.136:9090')
#     stub = chek_grpc.ResourceMessageHandleStub(channel=channel)
#     print('Request chek server...')
#     #while True:
#     try:
#         t1 = run_time.time()
#         response = stub.saveResource(chek_message, timeout=3)
#         print(f'Request time: {run_time.time()-t1:.2f} s')
#         print(f'Chek server response:\n{response}')
#         #break
#     except Exception as e:
#         print('Request failed, error msg:\n', e)
#         print('Try again after 3s...')
#         run_time.sleep(3)

    def publish_message(self, chek_message: chek.ChekMessage):
        # Create gprc client
        #channel = grpc.insecure_channel('152.136.205.136:9090')
        #channel = grpc.insecure_channel('62.234.57.136:9090')
        # 增加序列化操作中保留默认值字段设置
        # 
        options = [('grpc.include_default_values', True)]

        #channel = grpc.insecure_channel('62.234.57.136:9090', options=options)
        channel = grpc.insecure_channel(self.url, options=[
        ('grpc.max_send_message_length', 10 * 1024 * 1024),  # 设置为10MB
        ('grpc.max_receive_message_length', 10 * 1024 * 1024)  # 设置为10MB
        ])
        
        stub = chek_grpc.SaasChekMessageHandleRStub(channel=channel)
        print('#'*50)
        #print("传输前chek_message:", chek_message)
        print('Request chek server...')
        try:
            t1 = run_time.time()
            response = stub.saveResource(chek_message, timeout=3000)
            print(f'Request time: {run_time.time()-t1:.2f} s')
            print(f'Chek server response:\n{response}')
            run_time.sleep(3)
            
        except Exception as e:
            print('Request failed, error msg:\n', e)
            print('Try again after 3s...')
            run_time.sleep(3)
        print('#'*50)


def publish_message_list(chek_message_list):
    # Create gprc client
    channel = grpc.insecure_channel('62.234.57.136:9090')
    stub = chek_grpc.ResourceMessageHandleStub(channel=channel)
    print('Request chek server...')
    for chek_message in chek_message_list:
        try:
            t1 = run_time.time()
            response = stub.saveResource(chek_message, timeout=3)
            print(f'Request time: {run_time.time()-t1:.2f} s')
            print(f'Chek server response:\n{response}')
            #continue
        except Exception as e:
            print('Request failed, error msg:\n', e)
            print('Try again after 3s...')
            run_time.sleep(3)



def merge_messages(messages: list):
    if len(messages) == 0:
        return None
    merged_message = chek.ChekMessage()

    average_speed_thre = 30
    MBTI_i = '内敛小i人'
    MBTI_e = '狂飙小e人'

    # merged user information
    merged_message.user.id = messages[0].user.id
    merged_message.user.name = messages[0].user.name
    merged_message.user.phone = messages[0].user.phone
    merged_message.user.MBTI = messages[0].user.MBTI

    # merged car information
    merged_message.car.brand = messages[0].car.brand
    merged_message.car.model = messages[0].car.model
    merged_message.car.car_name = messages[0].car.car_name
    merged_message.car.hardware_version = messages[0].car.hardware_version
    merged_message.car.software_version = messages[0].car.software_version
    merged_message.car.MBTI = messages[0].car.MBTI
    # set journey datetime
    merged_message.journeyStatistics.datetime = messages[0].journeyStatistics.datetime

    # set description
    merged_message.description.noa_road_status_code = messages[0].description.noa_road_status_code   
    merged_message.description.city_noa_merge_code  = messages[0].description.city_noa_merge_code  
    merged_message.description.city                 = messages[0].description.city 
    merged_message.description.evaluated_scenarios  = messages[0].description.evaluated_scenarios   
    merged_message.description.pdf_file_path        = messages[0].description.pdf_file_path

    def cal_average_column(truck_avoidances):
        # 大车避让统计数据
        truck_avoid_num = 0  # 大车避让次数
        truck_avoid_total_time = 0  # 大车避让总时间
        truck_avoid_noa_num = 0  # 大车避让接管次数
        truck_avoid_lcc_num = 0  # 大车避让危险接管次数
        truck_avoid_average_lat_max_dis = 0  # 大车避让总横向最大距离
        truck_avoid_average_lat_min_dis = 0  # 大车避让总横向最小距离

        # added by zjx 20231008
        # average value
        average_duration = 0
        average_min_lat_distance = 0
        average_max_lat_distance = 0
        for _ in truck_avoidances:
            truck_avoid_num += 1
            truck_avoid_total_time += _.duration
            if _.has_intervention:
                truck_avoid_noa_num += 1
            if _.has_intervention_risk:
                truck_avoid_lcc_num += 1
            truck_avoid_average_lat_max_dis += _.max_lat_distance
            truck_avoid_average_lat_min_dis += _.min_lat_distance

        if truck_avoid_num>0:
            average_duration = truck_avoid_total_time / truck_avoid_num
            average_min_lat_distance = truck_avoid_average_lat_min_dis / truck_avoid_num
            average_max_lat_distance = truck_avoid_average_lat_max_dis / truck_avoid_num

        return average_duration,average_min_lat_distance,average_max_lat_distance

    def add_truck_avoidance_statistics(truck_avoidance_statistics1,truck_avoidance_statistics2):
        truck_avoidance_statistics1.avoid_cnt += truck_avoidance_statistics2.avoid_cnt
        truck_avoidance_statistics1.intervention_cnt += truck_avoidance_statistics2.intervention_cnt
        truck_avoidance_statistics1.intervention_risk_cnt += truck_avoidance_statistics2.intervention_risk_cnt
        truck_avoidance_statistics1.truck_avoidances.extend(truck_avoidance_statistics2.truck_avoidances)

        average_duration,average_min_lat_distance,average_max_lat_distance = cal_average_column(truck_avoidance_statistics1.truck_avoidances)
        truck_avoidance_statistics1.average_duration = average_duration
        truck_avoidance_statistics1.average_min_lat_distance = average_min_lat_distance
        truck_avoidance_statistics1.average_max_lat_distance = average_max_lat_distance




    def add_journey(sub_journey1, sub_journey2, is_driver=False):
        sub_journey1.odometer += sub_journey2.odometer
        sub_journey1.duration += sub_journey2.duration 

        if sub_journey1.frames == 0 or sub_journey2.frames == 0:
            sub_journey1.speed_average += sub_journey2.speed_average 
        else:
            sub_journey1.speed_average = (sub_journey1.speed_average * sub_journey1.frames \
                                          + sub_journey2.speed_average * sub_journey2.frames) \
                                            / (sub_journey1.frames + sub_journey2.frames)
        #sub_journey1.speed_average += sub_journey2.speed_average  # TODO: 不能直接相加，需要根据帧数占比相加
        sub_journey1.frames += sub_journey2.frames 
        sub_journey1.speed_max = max(
            sub_journey1.speed_max, sub_journey2.speed_max)

        if sub_journey1.dcc_cnt == 0 or sub_journey2.dcc_cnt == 0:
            sub_journey1.dcc_average += sub_journey2.dcc_average 
        else:
            sub_journey1.dcc_average = (sub_journey1.dcc_average * sub_journey1.dcc_cnt \
                                          + sub_journey2.dcc_average * sub_journey2.dcc_cnt) \
                                            / (sub_journey1.dcc_cnt + sub_journey2.dcc_cnt)
        #sub_journey1.dcc_average += sub_journey2.dcc_average  # TODO: 取平均？
        sub_journey1.dcc_cnt += sub_journey2.dcc_cnt
        sub_journey1.dcc_frequency = sub_journey1.odometer / \
            sub_journey1.dcc_cnt if sub_journey1.dcc_cnt > 0 else 0
        
        sub_journey1.dcc_max = min(sub_journey1.dcc_max, sub_journey2.dcc_max)
        sub_journey1.dcc_duration += sub_journey2.dcc_duration

        if sub_journey1.acc_cnt == 0 or sub_journey2.acc_cnt == 0:
            sub_journey1.acc_average += sub_journey2.acc_average 
        else:
            sub_journey1.acc_average = (sub_journey1.acc_average * sub_journey1.acc_cnt \
                                          + sub_journey2.acc_average * sub_journey2.acc_cnt) \
                                            / (sub_journey1.acc_cnt + sub_journey2.acc_cnt)
        #sub_journey1.acc_average += sub_journey2.acc_average  # TODO： 取平均？
        sub_journey1.acc_cnt += sub_journey2.acc_cnt
        sub_journey1.acc_frequency = sub_journey1.odometer / \
            sub_journey1.acc_cnt if sub_journey1.acc_cnt > 0 else 0
        sub_journey1.acc_max = max(sub_journey1.acc_max, sub_journey2.acc_max)
        sub_journey1.acc_duration += sub_journey2.acc_duration
        sub_journey1.gps_trajectories.extend(sub_journey2.gps_trajectories)
        add_truck_avoidance_statistics(sub_journey1.truck_avoidance_statistics,sub_journey2.truck_avoidance_statistics)

        if not is_driver:
            sub_journey1.intervention_statistics.cnt += sub_journey2.intervention_statistics.cnt
            sub_journey1.intervention_statistics.risk_cnt += sub_journey2.intervention_statistics.risk_cnt
            
            # sub_journey1.intervention_statistics.mpi = sub_journey1.odometer / \
            #     (sub_journey1.intervention_statistics.cnt  + 1) 
            
            # sub_journey1.intervention_statistics.risk_mpi = sub_journey1.odometer / \
            #     (sub_journey1.intervention_statistics.risk_cnt  + 1) 


            sub_journey1.intervention_statistics.risk_proportion = (
                sub_journey1.intervention_statistics.risk_cnt / sub_journey1.intervention_statistics.cnt) * 100 \
                    if sub_journey1.intervention_statistics.cnt > 0 else 0

            #2025.05.14 
            #调整接管返回结果 key
            if sub_journey1.intervention_statistics.cnt  !=0:
                sub_journey1.intervention_statistics.mpi = sub_journey1.odometer / sub_journey1.intervention_statistics.cnt 
            else:
                sub_journey1.intervention_statistics.mpi = 0.0

            if sub_journey1.intervention_statistics.risk_cnt!=0:
                sub_journey1.intervention_statistics.risk_mpi = sub_journey1.odometer / \
                (sub_journey1.intervention_statistics.risk_cnt  ) 
            else:
                sub_journey1.intervention_statistics.risk_mpi = 0.0
            
            sub_journey1.intervention_statistics.interventions.extend(sub_journey2.intervention_statistics.interventions)



    def add_polarStarhighway(polarStarhighway1, polarStarhighway2):
        """
        北极星、接管原因赋值
        """

        # highway polarstar
        polarStarhighway1.lane_change_cnt                       += polarStarhighway2.lane_change_cnt                   
        polarStarhighway1.lane_change_successful_cnt            += polarStarhighway2.lane_change_successful_cnt        
        polarStarhighway1.up_down_ramps_cnt                     += polarStarhighway2.up_down_ramps_cnt                 
        polarStarhighway1.up_down_ramps_successful_cnt          += polarStarhighway2.up_down_ramps_successful_cnt      
        polarStarhighway1.construction_scene_cnt                += polarStarhighway2.construction_scene_cnt            
        polarStarhighway1.construction_scene_successful_cnt     += polarStarhighway2.construction_scene_successful_cnt 
        polarStarhighway1.lane_change_rate                       = polarStarhighway1.lane_change_successful_cnt / (polarStarhighway1.lane_change_cnt + 1e-5)                  
        polarStarhighway1.up_down_ramps_successful_rate          = polarStarhighway1.up_down_ramps_successful_cnt / (polarStarhighway1.up_down_ramps_cnt + 1e-5)      
        polarStarhighway1.construction_scene_successful_rate     = polarStarhighway1.construction_scene_successful_cnt / (polarStarhighway1.construction_scene_cnt + 1e-5)


    def add_polarStarUrban(polarStarUrban1, polarStarUrban2):
        """
        北极星、接管原因赋值
        """

        # Urban polarstar
        polarStarUrban1.turn_cnt                   += polarStarUrban2.turn_cnt               
        polarStarUrban1.turn_pass_cnt              += polarStarUrban2.turn_pass_cnt          
        polarStarUrban1.turn_pass_rate              = polarStarUrban1.turn_pass_cnt / (polarStarUrban1.turn_cnt + 1e-5)         
        polarStarUrban1.urban_road_coverage         = polarStarUrban2.urban_road_coverage     # TODO
        polarStarUrban1.auto_driving_efficiency     = polarStarUrban2.auto_driving_efficiency #TODO  


    def add_cityNoaInterventionReseason(cityNoaInterventionReseason1, cityNoaInterventionReseason2):
        """
        北极星、接管原因赋值
        """
        # highway CityNoaInterventionReseason
        cityNoaInterventionReseason1.exceeding_speed_limit                 += cityNoaInterventionReseason2.exceeding_speed_limit               
        cityNoaInterventionReseason1.illegal_lane_change                   += cityNoaInterventionReseason2.illegal_lane_change                 
        cityNoaInterventionReseason1.start_slowly                          += cityNoaInterventionReseason2.start_slowly                        
        cityNoaInterventionReseason1.braking_decelerating_slowly           += cityNoaInterventionReseason2.braking_decelerating_slowly         
        cityNoaInterventionReseason1.running_traffic_lights                += cityNoaInterventionReseason2.running_traffic_lights              
        cityNoaInterventionReseason1.failure_yield_pedestrians_crosswalks  += cityNoaInterventionReseason2.failure_yield_pedestrians_crosswalks
        cityNoaInterventionReseason1.failure_overtake_detour               += cityNoaInterventionReseason2.failure_overtake_detour             
        cityNoaInterventionReseason1.failure_follow_lane                   += cityNoaInterventionReseason2.failure_follow_lane                 
        cityNoaInterventionReseason1.speed_slow                            += cityNoaInterventionReseason2.speed_slow                          

        cityNoaInterventionReseason1.speed_fast                            += cityNoaInterventionReseason2.speed_fast                          
        cityNoaInterventionReseason1.driving_without_following_directions  += cityNoaInterventionReseason2.driving_without_following_directions
        cityNoaInterventionReseason1.turn_early                            += cityNoaInterventionReseason2.turn_early                          
        cityNoaInterventionReseason1.turn_late                             += cityNoaInterventionReseason2.turn_late                           
        cityNoaInterventionReseason1.others                                += cityNoaInterventionReseason2.others          


    def add_journeyStatistics(journeyStatistics1, journeyStatistics2):
        journeyStatistics1.duration += journeyStatistics2.duration
        journeyStatistics1.odometer_total += journeyStatistics2.odometer_total
        journeyStatistics1.odometer_auto += journeyStatistics2.odometer_auto
        journeyStatistics1.odometer_hmi += journeyStatistics2.odometer_hmi
        journeyStatistics1.odometer_accuracy = (
            journeyStatistics1.odometer_total / journeyStatistics1.odometer_hmi)*100

        print("*"*10 + "odometer_total:"+ str(journeyStatistics1.odometer_total) + "*"*10)
        print("*"*10 + "odometer_auto:"+ str(journeyStatistics1.odometer_auto) + "*"*10)

        add_journey(journeyStatistics1.auto, journeyStatistics2.auto)
        add_journey(journeyStatistics1.noa, journeyStatistics2.noa)
        add_journey(journeyStatistics1.lcc, journeyStatistics2.lcc)
        add_journey(journeyStatistics1.driver, journeyStatistics2.driver, is_driver=True)

        # 增加北极星等指标
        add_polarStarhighway(journeyStatistics1.polarStarhighway, journeyStatistics2.polarStarhighway)
        add_polarStarUrban(journeyStatistics1.polarStarUrban, journeyStatistics2.polarStarUrban)
        add_cityNoaInterventionReseason(journeyStatistics1.cityNoaInterventionReseason, journeyStatistics2.cityNoaInterventionReseason)
        
    def add_SceneStatistics(SceneStatistics1, SceneStatistics2):
        print("#"*10 + "sunny: " + "#"*10)
        add_scene(SceneStatistics1.sunny, SceneStatistics2.sunny)
        print("#"*10 + "rainy: " + "#"*10)
        add_scene(SceneStatistics1.rainy, SceneStatistics2.rainy)
        print("#"*10 + "highway: " + "#"*10)
        add_scene(SceneStatistics1.highway, SceneStatistics2.highway)
        print("#"*10 + "expressway: " + "#"*10)
        add_scene(SceneStatistics1.expressway, SceneStatistics2.expressway)
        print("#"*10 + "urban: " + "#"*10)
        add_scene(SceneStatistics1.urban, SceneStatistics2.urban)
        print("#"*10 + "day: " + "#"*10)
        add_scene(SceneStatistics1.day, SceneStatistics2.day)
        print("#"*10 + "day: " + "#"*10)
        add_scene(SceneStatistics1.night, SceneStatistics2.night)

    def add_scene(sub_scene1, sub_scene2):
        sub_scene1.odometer += sub_scene2.odometer
        sub_scene1.auto_odometer += sub_scene2.auto_odometer
        sub_scene1.Intervention += sub_scene2.Intervention
        sub_scene1.risk_intervention += sub_scene2.risk_intervention
        for city in sub_scene2.city_dict: 
            if city in sub_scene1.city_dict:   
                sub_scene1.city_dict[city] += sub_scene2.city_dict[city]   
            else:                                #.update(sub_scene2.city_dict)
                sub_scene1.city_dict[city] = sub_scene2.city_dict[city]   
        print("*"*10 + "odometer:"+ str(sub_scene1.odometer) + "*"*10)
        print("*"*10 + "auto_odometer:"+ str(sub_scene1.auto_odometer) + "*"*10)

        add_journeyStatistics(sub_scene1.journeyStatistics, sub_scene2.journeyStatistics)

    def cal_city_proportion(scene):
        # 计算城市占比
        scene_city = scene.city_dict
        total_gsp_point = 1e-5
        for city in scene_city:
            total_gsp_point += scene_city[city]
        
        for city in scene_city:
            scene_city[city] /= total_gsp_point

    journeyStatistics = merged_message.journeyStatistics
    sceneStatistics = merged_message.scene

    for msg in messages:

        add_journeyStatistics(journeyStatistics, msg.journeyStatistics)

        add_SceneStatistics(sceneStatistics, msg.scene)

    cal_city_proportion(sceneStatistics.sunny)
    cal_city_proportion(sceneStatistics.rainy)
    cal_city_proportion(sceneStatistics.highway)
    cal_city_proportion(sceneStatistics.expressway)
    cal_city_proportion(sceneStatistics.urban)
    cal_city_proportion(sceneStatistics.day)
    cal_city_proportion(sceneStatistics.night)
    
    # 设置MBTI 暂时服务于小程序
    if merged_message.journeyStatistics.driver.speed_average > average_speed_thre:
        merged_message.user.MBTI = MBTI_e
    else:
        merged_message.user.MBTI = MBTI_i

    if merged_message.journeyStatistics.auto.speed_average > average_speed_thre:
        merged_message.car.MBTI = MBTI_e
    else:
        merged_message.car.MBTI = MBTI_i  

    print('test_duration...',merged_message.journeyStatistics.duration)
    return merged_message




if __name__ == '__main__':

    pro_csv_list = []
    
    csvProcess = CSVProcess(pro_csv_list)
    csvProcess.process_list_csv_save_journey()

    json_str = json.dumps(csvProcess.frame_intervention_file, indent=4)
    print(json_str)

    json_str_risk = json.dumps(csvProcess.frame_intervention_risk_file, indent=4)
    print(json_str_risk)