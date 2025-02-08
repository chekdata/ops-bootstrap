import os
import json
import glob
import sys
import argparse
import pandas as pd
import tablib
import csv

from pathlib import Path
from pathlib import PurePath


#sys.path.append("..")

current_dir = os.path.dirname(os.path.abspath(__file__))

parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(parent_dir)
sys.path.append(grandparent_dir)

from name_mapping import *
# from chek_utils.process_files import get_all_specify_filename_files, create_folders_from_filename


def add_colunm_name_proportion(scene_name,scene1_jouney, scene2_jouney, item):
    """
    计算场景综合数据
    scene1: 晴天、高速、白天、
    scene2: 雨天、城区、黑夜、
    """
    scene1_odometer = 1e-5
    scene1_auto_odometer = 1e-5
    scene1_intervention_cnt = 1e-5
    scene1_intervention_risk_cnt = 1e-5

    scene2_odometer = 1e-5
    scene2_auto_odometer = 1e-5
    scene2_intervention_cnt = 1e-5
    scene2_intervention_risk_cnt = 1e-5

    if scene1_jouney.get('odometer'): scene1_odometer = scene1_jouney.get('odometer')
    if scene1_jouney.get('auto_odometer'): scene1_auto_odometer = scene1_jouney.get('auto_odometer')
    if scene1_jouney.get('Intervention'): scene1_intervention_cnt = scene1_jouney.get('Intervention')
    if scene1_jouney.get('risk_intervention'): scene1_intervention_risk_cnt = scene1_jouney.get('risk_intervention')


    if scene2_jouney.get('odometer'): scene2_odometer = scene2_jouney.get('odometer')
    if scene2_jouney.get('auto_odometer'): scene2_auto_odometer = scene2_jouney.get('auto_odometer')
    if scene2_jouney.get('Intervention'): scene2_intervention_cnt = scene2_jouney.get('Intervention')
    if scene2_jouney.get('risk_intervention'): scene2_intervention_risk_cnt = scene2_jouney.get('risk_intervention')

    item[f'{scene_name}_odometer_proportion'] = scene1_odometer / scene2_odometer
    item[f'{scene_name}_auto_odometer_proportion'] = scene1_auto_odometer / scene2_auto_odometer
    item[f'{scene_name}_intervention_cnt_proportion'] = scene1_intervention_cnt / scene2_intervention_cnt
    item[f'{scene_name}_intervention_risk_cnt_proportion'] = scene1_intervention_risk_cnt / scene2_intervention_risk_cnt


def add_colunm_name_proportion(scene_category,scene_name, scene_jouney,\
                               odometer_total,auto_odometer_total,intervention_cnt_total,intervention_risk_cnt_total, item):
    """
    计算场景综合数据
    scene1: 晴天、高速、白天、
    scene2: 雨天、城区、黑夜、
    """
    scene_odometer = 1e-5
    scene_auto_odometer = 1e-5
    scene_intervention_cnt = 1e-5
    scene_intervention_risk_cnt = 1e-5

    if scene_jouney.get('odometer'): scene_odometer = scene_jouney.get('odometer')
    if scene_jouney.get('auto_odometer'): scene_auto_odometer = scene_jouney.get('auto_odometer')
    if scene_jouney.get('Intervention'): scene_intervention_cnt = scene_jouney.get('Intervention')
    if scene_jouney.get('risk_intervention'): scene_intervention_risk_cnt = scene_jouney.get('risk_intervention')


    item[f'{scene_category}_{scene_name}_odometer_proportion'] = scene_odometer / odometer_total
    item[f'{scene_category}_{scene_name}_auto_odometer_proportion'] = scene_auto_odometer / auto_odometer_total
    item[f'{scene_category}_{scene_name}_intervention_cnt_proportion'] = scene_intervention_cnt / intervention_cnt_total
    item[f'{scene_category}_{scene_name}_intervention_risk_cnt_proportion'] = scene_intervention_risk_cnt / intervention_risk_cnt_total




# 将json中的key作为header, 也可以自定义header（列名）

def add_colunm_name(colunm_name,sub_jouney,item):
    item[f'{colunm_name}_odometer_total'] = sub_jouney.get('odometer') if sub_jouney.get('odometer') else 1e-5

    item[f'{colunm_name}_odometer_auto'] = sub_jouney.get('auto_odometer') if sub_jouney.get('auto_odometer') else 1e-5

    item[f'{colunm_name}_risk_intervention'] = sub_jouney.get('risk_intervention') if sub_jouney.get('risk_intervention') else 1e-5

    item[f'{colunm_name}_Intervention'] = sub_jouney.get('Intervention') if sub_jouney.get('Intervention') else 1e-5

    if sub_jouney.get('risk_intervention') and sub_jouney.get('Intervention'):
        item[f'{colunm_name}_risk_proportion'] = sub_jouney.get('risk_intervention') / (sub_jouney.get('Intervention') + 1e-5)
    else:
        item[f'{colunm_name}_risk_proportion'] = 1e-5

    if sub_jouney.get('auto_odometer') and sub_jouney.get('risk_intervention'):
        item[f'{colunm_name}_risk_mpi'] = sub_jouney.get('auto_odometer') / (sub_jouney.get('risk_intervention') + 1e-5)
    else: 
        item[f'{colunm_name}_risk_mpi'] = 1e-5

    if sub_jouney.get('auto_odometer') and sub_jouney.get('Intervention'):
        item[f'{colunm_name}_mpi'] = sub_jouney.get('auto_odometer') / (sub_jouney.get('Intervention') + 1e-5)    
    else:
        item[f'{colunm_name}_mpi'] = 1e-5


    if sub_jouney.get('journeyStatistics'):
        journeyStatistics = sub_jouney.get('journeyStatistics')
        item[f'{colunm_name}_datetime'] = journeyStatistics.get('datetime') if journeyStatistics.get('datetime') else '2023.01.01 00:00:00'

        # 暂时没有数据支持，不做输出
        # item[f'{colunm_name}_odometer_hmi'] = journeyStatistics.get('odometer_hmi') if journeyStatistics.get('odometer_hmi') else 1e-5
        #item[f'{colunm_name}_odometer_accuracy'] = journeyStatistics.get('odometer_accuracy') if journeyStatistics.get('odometer_accuracy') else 1e-5

        item[f'{colunm_name}_odometer_hmi'] = '-'
        item[f'{colunm_name}_odometer_accuracy'] = '-'

        if journeyStatistics.get('auto'):
            auto = journeyStatistics.get('auto')
            item[f'{colunm_name}_dcc_cnt_auto']= auto.get('dcc_cnt') if auto.get('dcc_cnt') else 1e-5

            item[f'{colunm_name}_dcc_frequency_auto']= auto.get('dcc_frequency') if auto.get('dcc_frequency') else 1e-5

            item[f'{colunm_name}_dcc_max_auto']= auto.get('dcc_max') if auto.get('dcc_max') else -1*1e-5

            item[f'{colunm_name}_dcc_duration_auto']= auto.get('dcc_duration') if auto.get('dcc_duration') else 1e-5

            item[f'{colunm_name}_acc_cnt_auto']= auto.get('acc_cnt') if auto.get('acc_cnt') else 1e-5

            item[f'{colunm_name}_acc_frequency_auto']= auto.get('acc_frequency') if auto.get('acc_frequency') else 1e-5

            item[f'{colunm_name}_acc_max_auto']= auto.get('acc_max') if auto.get('acc_max') else 1e-5

            item[f'{colunm_name}_acc_duration_auto']= auto.get('acc_duration') if auto.get('acc_duration') else 1e-5

            item[f'{colunm_name}_speed_average_auto']= auto.get('speed_average') if auto.get('speed_average') else 1e-5

            item[f'{colunm_name}_speed_max_auto']= auto.get('speed_max') if auto.get('speed_max') else 1e-5

            item[f'{colunm_name}_dcc_average_auto']= auto.get('dcc_average') if auto.get('dcc_average') else 1e-5

            item[f'{colunm_name}_acc_average_auto']= auto.get('acc_average') if auto.get('acc_average') else 1e-5


        if journeyStatistics.get('driver'):
            driver = journeyStatistics.get('driver')
            item[f'{colunm_name}_speed_average_driver'] = driver.get('speed_average') if driver.get('speed_average') else 1e-5

            item[f'{colunm_name}_speed_max_driver'] = driver.get('speed_max')  if driver.get('speed_max') else 1e-5

            item[f'{colunm_name}_dcc_cnt_driver'] = driver.get('dcc_cnt') if driver.get('dcc_cnt') else 1e-5

            item[f'{colunm_name}_dcc_max_driver'] = driver.get('dcc_max') if driver.get('dcc_max') else -1*1e-5

            item[f'{colunm_name}_acc_cnt_driver'] = driver.get('acc_cnt') if driver.get('acc_cnt') else 1e-5

            item[f'{colunm_name}_acc_max_driver'] = driver.get('acc_max') if driver.get('acc_max') else 1e-5



        if journeyStatistics.get('noa'):
            noa = journeyStatistics.get('noa')
            item[f'{colunm_name}_odometer_noa'] = noa.get('odometer') if noa.get('odometer') else 1e-5

            odometer_total = journeyStatistics.get('odometer_total') if journeyStatistics.get('odometer_total') else 1e-5

            item[f'{colunm_name}_odometer_rate_noa'] = noa.get('odometer') / odometer_total * 100 if noa.get('odometer') else 1e-5

            if noa.get('intervention_statistics'):
                noa_intervention = noa.get('intervention_statistics')
                item[f'{colunm_name}_intervention_cnt_noa'] = noa_intervention.get('cnt') if noa_intervention.get('cnt') else 1e-5

                item[f'{colunm_name}_intervention_risk_cnt_noa'] = noa_intervention.get('risk_cnt') if noa_intervention.get('risk_cnt') else 1e-5

                item[f'{colunm_name}_intervention_mpi_noa'] = noa_intervention.get('mpi') if noa_intervention.get('mpi') else 1e-5




        if journeyStatistics.get('lcc'):
            lcc = journeyStatistics.get('lcc')
            item[f'{colunm_name}_odometer_lcc'] = lcc.get('odometer') if lcc.get('odometer') else 1e-5

            odometer_total = journeyStatistics.get('odometer_total') if journeyStatistics.get('odometer_total') else 1e-5

            item[f'{colunm_name}_odometer_rate_lcc'] = lcc.get('odometer') / odometer_total * 100 if lcc.get('odometer') else 0

            if lcc.get('intervention_statistics'):
                lcc_intervention = lcc.get('intervention_statistics')
                item[f'{colunm_name}_intervention_cnt_lcc'] = lcc_intervention.get('cnt') if lcc_intervention.get('cnt') else 1e-5

                item[f'{colunm_name}_intervention_risk_cnt_lcc'] = lcc_intervention.get('risk_cnt') if lcc_intervention.get('risk_cnt') else 1e-5

                item[f'{colunm_name}_intervention_mpi_lcc'] = lcc_intervention.get('mpi') if lcc_intervention.get('mpi') else 1e-5           


    item[f'{colunm_name}_city_dict'] = sub_jouney.get('city_dict') if sub_jouney.get('city_dict') else {}


def split_json_data(rows, statistics_filepath, truck_avoid_filepath):
    list_res = []
    list_single_avoid = []
    item = {}

    odometer_total = 1e-5
    auto_odometer_total = 1e-5
    intervention_cnt_total = 1e-5
    intervention_risk_cnt_total = 1e-5

    if rows.get('user'):
        user = rows.get('user')
        item['id'] = user.get('id') if user.get('id') else 100000
        item['name'] = user.get('name') if user.get('name') else "张三"
        item['phone'] = user.get('phone') if user.get('phone') else "13213213212"
        item['MBTI_auto'] = user.get('MBTI') if user.get('MBTI') else "MBTI"

    if rows.get('car'):
        car = rows.get('car')
        item['brand'] = car.get('brand') if car.get('brand') else "汽车"
        item['model'] = car.get('model') if car.get('model') else "型号"
        item['version'] = car.get('version') if car.get('version') else "版本"
        item['MBTI_driver'] = car.get('MBTI') if car.get('MBTI') else "MBTI_driver"


    if rows.get('journeyStatistics'):
        # print(rows.get('JourneyStatistics').keys())
        journey =  rows.get('journeyStatistics')
        item['datetime'] = journey.get('datetime') if journey.get('datetime') else '2023.01.01 00:00:00'

        item['duration'] = journey.get('duration') if journey.get('duration') else 1e-5

        item['odometer_total'] = journey.get('odometer_total') if journey.get('odometer_total') else 1e-5
        item['odometer_auto'] = journey.get('odometer_auto') if journey.get('odometer_auto') else 1e-5

        # 用于场景计算统计数据
        odometer_total = journey.get('odometer_total') if journey.get('odometer_total') else 1e-5
        auto_odometer_total = journey.get('odometer_auto') if journey.get('odometer_auto') else 1e-5

        #item['odometer_hmi'] = journey.get('odometer_hmi') if journey.get('odometer_hmi') else 1e-5
        #item['odometer_accuracy'] = journey.get('odometer_accuracy') if journey.get('odometer_accuracy') else 1e-5

        item['odometer_hmi'] = '-'
        item['odometer_accuracy'] = '-'

        if journey.get('auto'):
            auto = journey.get('auto')
            item['dcc_cnt_auto'] = auto.get('dcc_cnt') if auto.get('dcc_cnt') else 1e-5
            item['dcc_frequency_auto'] = auto.get('dcc_frequency') if auto.get('dcc_frequency') else 1e-5
            item['dcc_max_auto'] = auto.get('dcc_max') if auto.get('dcc_max') else -1*1e-5
            item['dcc_duration_auto'] = auto.get('dcc_duration') if auto.get('dcc_duration') else 1e-5

            item['acc_cnt_auto'] = auto.get('acc_cnt') if auto.get('acc_cnt') else 1e-5

            item['acc_frequency_auto'] = auto.get('acc_frequency') if auto.get('acc_frequency') else 1e-5

            item['acc_max_auto'] = auto.get('acc_max') if auto.get('acc_max') else 1e-5

            item['acc_duration_auto'] = auto.get('acc_duration')  if auto.get('acc_duration') else 1e-5

            item['speed_average_auto'] = auto.get('speed_average') if auto.get('speed_average') else 1e-5

            item['speed_max_auto'] = auto.get('speed_max') if auto.get('speed_max') else 1e-5
            
            item['dcc_average_auto'] = auto.get('dcc_average') if auto.get('dcc_average') else 1e-5
            
            item['acc_average_auto'] = auto.get('acc_average') if auto.get('acc_average') else 1e-5

            if auto.get('intervention_statistics'):
                auto_intervention = auto.get('intervention_statistics')

                item['intervention_cnt_total'] = auto_intervention.get('cnt') if auto_intervention.get('cnt') else 1e-5

                item['intervention_risk_cnt_total'] = auto_intervention.get('risk_cnt') if auto_intervention.get('risk_cnt') else 1e-5

                # 用于场景统计数据计算
                intervention_cnt_total = auto_intervention.get('cnt') if auto_intervention.get('cnt') else 1e-5
                intervention_risk_cnt_total = auto_intervention.get('risk_cnt') if auto_intervention.get('risk_cnt') else 1e-5

                item['intervention_risk_proportion_total'] = intervention_risk_cnt_total/intervention_cnt_total*100

                item['intervention_mpi_total'] = auto_intervention.get('mpi') if auto_intervention.get('mpi') else 1e-5

                item['intervention_risk_mpi_total'] = auto_intervention.get('risk_mpi') if auto_intervention.get('risk_mpi') else 1e-5   

            if auto.get('gps_trajectories'): item['gps_trajectories'] = auto.get('gps_trajectories')

            if auto.get('truck_avoidance_statistics'):
                truck_avoidance_statistics = auto.get('truck_avoidance_statistics')
                item['average_duration_truck_avoidance'] = (truck_avoidance_statistics.get('average_duration')) \
                    if truck_avoidance_statistics.get('average_duration') else 1e-5

                item['avoid_cnt_truck_avoidance'] = (truck_avoidance_statistics.get('avoid_cnt')) \
                    if truck_avoidance_statistics.get('avoid_cnt') else 1e-5 

                item['intervention_cnt_truck_avoidance'] = ( truck_avoidance_statistics.get('intervention_cnt')) \
                    if truck_avoidance_statistics.get('intervention_cnt') else 1e-5

                item['intervention_risk_cnt_truck_avoidance'] = (truck_avoidance_statistics.get('intervention_risk_cnt')) \
                    if truck_avoidance_statistics.get('intervention_risk_cnt') else 1e-5

                item['average_min_lat_distance_truck_avoidance'] = (truck_avoidance_statistics.get('average_min_lat_distance')) \
                    if truck_avoidance_statistics.get('average_min_lat_distance') else 1e-5

                item['average_max_lat_distance_truck_avoidance'] = (truck_avoidance_statistics.get('average_max_lat_distance')) \
                    if truck_avoidance_statistics.get('average_max_lat_distance') else 1e-5

                # item['average_speed'] = (truck_avoidance_statistics.get('average_speed')) \
                #     if truck_avoidance_statistics.get('average_speed') else 1e-5

                if truck_avoidance_statistics.get('truck_avoidances'):
                    for _ in truck_avoidance_statistics.get('truck_avoidances'):
                        single_item = {}
                        list_state = []
                        if _.get('policy'): single_item['policy'] = _.get('policy')
                        if _.get('duration'): single_item['duration'] = _.get('duration')
                        if _.get('has_intervention'):
                            single_item['has_intervention'] = 'True'
                            list_state.append('noa')
                        else:
                            single_item['has_intervention'] = 'False'
                        if _.get('has_intervention_risk'):
                            single_item['has_intervention_risk'] = 'True'
                            list_state.append('lcc')
                        else:
                            single_item['has_intervention_risk'] = 'False'
                        if _.get('min_lat_distance'): single_item['min_lat_distance'] = _.get('min_lat_distance')
                        if _.get('max_lat_distance'): single_item['max_lat_distance'] = _.get('max_lat_distance')
                        if _.get('start_frame_id'): single_item['start_frame_id'] = _.get('start_frame_id')
                        if _.get('end_frame_id'): single_item['end_frame_id'] = _.get('end_frame_id')
                        if _.get('gps_position'): single_item['gps_position'] = _.get('gps_position')

                        single_item['state'] = ','.join(list_state)
                        list_single_avoid.append(single_item)
                                

                       
        
        if journey.get('driver'):
            driver = journey.get('driver')
            item['speed_average_driver'] = driver.get('speed_average') if driver.get('speed_average') else 1e-5

            item['speed_max_driver'] = driver.get('speed_max') if driver.get('speed_max') else 1e-5

            item['dcc_cnt_driver'] = driver.get('dcc_cnt') if driver.get('dcc_cnt') else 1e-5

            item['dcc_max_driver'] = driver.get('dcc_max') if driver.get('dcc_max') else -1*1e-5

            item['acc_cnt_driver'] = driver.get('acc_cnt') if driver.get('acc_cnt') else 1e-5

            item['acc_max_driver'] = driver.get('acc_max') if driver.get('acc_max') else 1e-5

            if 'gps_trajectories' in item:
                if driver.get('gps_trajectories'): item['gps_trajectories'].append(driver.get('gps_trajectories'))


        if journey.get('noa'):
            noa = journey.get('noa')
            item['odometer_noa'] = noa.get('odometer') if noa.get('odometer') else 1e-5

            odometer_total_noa = journey.get('odometer_total') if journey.get('odometer_total') else 1e-5

            item['odometer_rate_noa'] = noa.get('odometer') / odometer_total_noa * 100 if noa.get('odometer') else 1e-5

            if noa.get('intervention_statistics'):
                noa_intervention = noa.get('intervention_statistics')
                item['intervention_cnt_noa'] = noa_intervention.get('cnt') if noa_intervention.get('cnt') else 1e-5

                item['intervention_risk_cnt_noa'] = noa_intervention.get('risk_cnt') if noa_intervention.get('risk_cnt') else 1e-5

                item['intervention_mpi_noa'] = noa_intervention.get('mpi') if noa_intervention.get('mpi') else 1e-5




        if journey.get('lcc'):
            lcc = journey.get('lcc')
            item['odometer_lcc'] = lcc.get('odometer') if lcc.get('odometer') else 1e-5

            odometer_total_lcc = journey.get('odometer_total') if journey.get('odometer_total') else 1e-5

            item['odometer_rate_lcc'] = lcc.get('odometer') / odometer_total_lcc * 100 if lcc.get('odometer') else 1e-5

            if lcc.get('intervention_statistics'):
                lcc_intervention = lcc.get('intervention_statistics')
                item['intervention_cnt_lcc'] = lcc_intervention.get('cnt') if lcc_intervention.get('cnt') else 1e-5

                item['intervention_risk_cnt_lcc'] = lcc_intervention.get('risk_cnt') if lcc_intervention.get('risk_cnt') else 1e-5

                item['intervention_mpi_lcc'] = lcc_intervention.get('mpi') if lcc_intervention.get('mpi') else 1e-5       

    if rows.get('scene'):
        SceneStatistics =  rows.get('scene')

        if SceneStatistics.get('sunny'):
            add_colunm_name_proportion('weather','sunny', SceneStatistics.get('sunny'), \
                                       odometer_total,auto_odometer_total,intervention_cnt_total,intervention_risk_cnt_total, item)

        if SceneStatistics.get('rainy'):
            add_colunm_name_proportion('weather','rainy', SceneStatistics.get('rainy'), \
                                       odometer_total,auto_odometer_total,intervention_cnt_total,intervention_risk_cnt_total, item)

        # if SceneStatistics.get('expressway'):
        #     add_colunm_name_proportion('road','expressway', SceneStatistics.get('expressway'), \
        #                                odometer_total,auto_odometer_total,intervention_cnt_total,intervention_risk_cnt_total, item)

        if SceneStatistics.get('highway'):
            add_colunm_name_proportion('road','highway', SceneStatistics.get('highway'), \
                                       odometer_total,auto_odometer_total,intervention_cnt_total,intervention_risk_cnt_total, item)

        if SceneStatistics.get('urban'):
            add_colunm_name_proportion('road','urban', SceneStatistics.get('urban'), \
                                       odometer_total,auto_odometer_total,intervention_cnt_total,intervention_risk_cnt_total, item)


        if SceneStatistics.get('day'):
            add_colunm_name_proportion('light','day', SceneStatistics.get('day'), \
                                       odometer_total,auto_odometer_total,intervention_cnt_total,intervention_risk_cnt_total, item)            


        if SceneStatistics.get('night'):
            add_colunm_name_proportion('light','night', SceneStatistics.get('night'), \
                                       odometer_total,auto_odometer_total,intervention_cnt_total,intervention_risk_cnt_total, item)   
            
        
        if SceneStatistics.get('sunny'): add_colunm_name('sunny', SceneStatistics.get('sunny'), item)
        if SceneStatistics.get('rainy'): add_colunm_name('rainy', SceneStatistics.get('rainy'), item)
        #if SceneStatistics.get('expressway'): add_colunm_name('expressway', SceneStatistics.get('expressway'), item)
        if SceneStatistics.get('highway'): add_colunm_name('highway', SceneStatistics.get('highway'), item)
        if SceneStatistics.get('urban'): add_colunm_name('urban', SceneStatistics.get('urban'), item)
        if SceneStatistics.get('day'): add_colunm_name('day', SceneStatistics.get('day'), item)
        if SceneStatistics.get('night'): add_colunm_name('night', SceneStatistics.get('night'), item)

    list_res.append(item)


    df_statistics_filepath = pd.DataFrame(list_res)
    #print(list(df_statistics_filepath.keys()))
    df_name = pd.DataFrame([item_list_], index=[0],
                           columns=column_list)
    df_statistics_filepath = pd.concat([df_name, df_statistics_filepath], ignore_index=True)
    #df_statistics_filepath.transpose()
    df_statistics_filepath.transpose().to_excel(statistics_filepath)


    df_truck_avoid_filepath = pd.DataFrame(list_single_avoid)

    df_name=pd.DataFrame([['策略', '持续时间', '智驾接管', '智驾危险接管', '最小纵值距离', '最大纵值距离', '开始帧id', '结束帧id', '状态']],index=[0],columns=['policy', 'duration', 'has_intervention', 'has_intervention_risk',
       'min_lat_distance', 'max_lat_distance', 'start_frame_id',
       'end_frame_id', 'state'])
    df_truck_avoid_filepath = pd.concat([df_name, df_truck_avoid_filepath], ignore_index=True)
    df_truck_avoid_filepath.to_excel(truck_avoid_filepath)

# def get_all_files(directory):
#     file_list = []
#     for root, dirs, files in os.walk(directory):
#         for file in files:
#             file_path = os.path.join(root, file)
#             file_list.append(file_path)
#     return file_list


def get_all_specify_filename_files(directory, filename):

    csv_file_list = []
    directory = Path(directory)
    csv_path = directory / '**' / ('*'+ filename)
    csv_files = glob.glob(str(csv_path), recursive=True) 
    for file_name in csv_files:
        csv_file_list.append(file_name)
        print(file_name)
    
    print("="* 10 + "total file number is {}".format(len(csv_file_list)) + "="* 10)

    return csv_file_list

def create_folders_from_filename(output_dir, file_name, extension, start_index = 9):
    """
    根据output_dir以及file_name生成新的文件格式的所有父级目录，
    并返回修改后的文件路径及名称
    """
    file_name = PurePath(file_name)

    output_pure_path = PurePath(output_dir)

    # NOTE
    # 这里parts[7:] 要根据本地路径深度进行调整
    # 其中‘/’也占一位在0索引位置
    #new_cparts = (output_dir,) + file_name.parts[9:]
    if start_index == -1:
        new_cparts = (output_dir,) + file_name.parts[len(output_pure_path.parts):]
    else:
        new_cparts = (output_dir,) + file_name.parts[start_index:]

    new_path = file_name.__class__(*new_cparts)

    output_path = new_path.with_suffix(extension)

    output_path = Path(output_path)

    if output_path.exists():
        print(f'{output_path} exists')
    else:
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            print(f'create {output_path.parent}')
        else:
            print(f'{output_path.parent} exists')

    return str(output_path)


def process_list(json_root_path, json_name, excel_root_path, excel_name):

    time_inter = '3s'
    file_list = get_all_specify_filename_files(json_root_path, json_name)
    for file in file_list:
        print("="*10+file+"="*10)

        excel_path = create_folders_from_filename(excel_root_path, file, excel_name, start_index=-1)

    
        with open(file, 'r',encoding='utf-8',errors='ignore') as f:
            rows = json.load(f)
        split_json_data(rows, excel_path[:-5]+"statistics_"+time_inter + ".xlsx",\
                         excel_path[:-5] + "truck_avoid_" + time_inter +".xlsx")
        print(excel_path)

def process_list_not_special_dir(file_list):

    statistics_file_list = []
    truck_avoid_file_list = []
    time_inter = '3s'
    #file_list = get_all_specify_filename_files(json_root_path, json_name)
    for file in file_list:
        print("="*10+file+"="*10)

        #excel_path = create_folders_from_filename(excel_root_path, file, excel_name, start_index=-1)
        excel_path = Path(file).with_suffix('').with_suffix('.excel')

        statistics_file_path = excel_path[:-5]+"statistics_"+time_inter + ".xlsx"
        truck_avoid_file_path = excel_path[:-5] + "truck_avoid_" + time_inter +".xlsx"
    
        with open(file, 'r',encoding='utf-8',errors='ignore') as f:
            rows = json.load(f)
        # split_json_data(rows, excel_path[:-5]+"statistics_"+time_inter + ".xlsx",\
        #                  excel_path[:-5] + "truck_avoid_" + time_inter +".xlsx")
        split_json_data(rows, statistics_file_path, truck_avoid_file_path)
        print(excel_path)

    return statistics_file_list, truck_avoid_file_list


def process_list(args):

    json_root_path, json_name, excel_root_path, excel_name = args.json_path + args.car_brand,\
                                                             args.json_name,\
                                                             args.excel_path + args.car_brand,\
                                                             args.excel_name

    time_inter = '3s'
    file_list = get_all_specify_filename_files(json_root_path, json_name)
    for file in file_list:
        print("="*10+file+"="*10)

        excel_path = create_folders_from_filename(excel_root_path, file, excel_name, start_index=-1)

    
        with open(file, 'r',encoding='utf-8',errors='ignore') as f:
            rows = json.load(f)
        split_json_data(rows, excel_path[:-5]+"statistics_"+time_inter + ".xlsx",\
                         excel_path[:-5] + "truck_avoid_" + time_inter +".xlsx")
        print(excel_path)

def process_json_file_list(json_file_list):
        
        statistics_xlsx_file_list = []
        truck_avoid_xlsx_file_list = []

        for file in json_file_list:
            print("="*10+file+"="*10)

            file_parts = str(file).split('/')
            file_parts[-1] = file_parts[-1].replace('.json', '_statistics.xlsx')
            new_statistics_xlsx_file_path = '/'.join(file_parts)

            file_parts[-1] = file_parts[-1].replace('_statistics.xlsx', '_truck_avoid.xlsx')
            new_truck_avoid_xlsx_file_path = '/'.join(file_parts)
        
            with open(file, 'r',encoding='utf-8',errors='ignore') as f:
                rows = json.load(f)
            split_json_data(rows, new_statistics_xlsx_file_path,new_truck_avoid_xlsx_file_path)

            statistics_xlsx_file_list.append(new_statistics_xlsx_file_path)
            truck_avoid_xlsx_file_list.append(new_truck_avoid_xlsx_file_path)


            print(f'statistics xlsx file path: {new_statistics_xlsx_file_path}, statistics xlsx file path: {new_truck_avoid_xlsx_file_path}')

        return statistics_xlsx_file_list, truck_avoid_xlsx_file_list

if __name__ == '__main__':


    sys.argv = ['json2excel_v1_1_proto.py', '--car_brand=X9/',\
                '--json-path=/Users/chek_zjx/Desktop/chek_code/data_process/results/results_final/json/',\
                '--excel-path=/Users/chek_zjx/Desktop/chek_code/data_process/results/results_final/excel/']

    parser = argparse.ArgumentParser()

    parser.add_argument('-b', '--car_brand', 
                        default='nio',
                        type=str,
                        required=True,
                        help='car types in [nio/, IM/, xiaopeng/, AITO/, Jiyue/]')
    
    parser.add_argument('-j_p', '--json-path', 
                        default='/data_process/results/results_final/json/',
                        type=str,
                        required=True,
                        help='original csv file path')
    
    parser.add_argument('-e_p','--excel-path',
                        default='/data_process/results/results_final/excel/',
                        type=str,
                        required=True,
                        help='processed csv file path. Same length as original path')
    
    parser.add_argument('-j_n', '--json-name',
                        default='.json',
                        type=str,
                        help='the json file extension')
    
    parser.add_argument('-e_n', '--excel-name',
                        default='.excel',
                        type=str,
                        help='the excel file extension')

    args = parser.parse_args()

    process_list(args)





    # brand = 'IM/' 


    # # 创建父级文件夹的方式
    # json_name = '.json'
    # excel_name = '.excel'

    # json_root_path = '/Users/chek_zjx/Desktop/chek_code/data_process/results/results_final/json/' + brand
    # excel_root_path = '/Users/chek_zjx/Desktop/chek_code/data_process/results/results_final/excel/' + brand

    # process_list(json_root_path, json_name, excel_root_path, excel_name)