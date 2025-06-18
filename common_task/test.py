import pandas as pd
from datetime import datetime
from handle_journey_message import *

from chek_dataprocess.cloud_process_csv.saas_csv_process import process_journey, async_process_journey
def convert_gps_time(csv_file_path):
    """
    读取 CSV 文件，并将 gps_time 转换为现实时间
    假设 gps_time 是形如 '%Y%m%d%H%M%S' 格式的字符串
    """
    df = pd.read_csv(csv_file_path)
    list_process = []
    initial_time = ''
    end_time = ''
    pre_scene = ''
    index = 1
    for _ in df.index: 
    # 假设这个数字是毫秒级时间戳
        timestamp_ms =  df.loc[_,'gps_timestamp']
        # 转换为秒级时间戳
        timestamp_s = timestamp_ms / 1000

        # 将时间戳转换为 datetime 对象
        dt = datetime.fromtimestamp(timestamp_s)
        lon = df.loc[_,'lon']
        lat = df.loc[_,'lat']
        road_scene = df.loc[_,'road_scene']
        if not initial_time:
            initial_time = dt
            pre_scene = road_scene

        if len(list_process)>=1000:
            #update
            pass
            list_process = [(lon,lat)]
            index+=1

        elif road_scene!= pre_scene:
            #update
            pass
            list_process = [(lon,lat)]
            index +=1
        else:
            list_process.append((lon,lat))
        end_time = dt
        # 输出结果
        # print("转换后的时间为:", dt)
        pre_scene = road_scene
    return df

# convert_gps_time('/root/project/chekappbackendnew/common_task/智己L7_2022款 Dynamic_IMOS 2.5.8_2025-04-21 13-51-40.csv')

def handle_message_data(total_message,trip_id,model,hardware_version,software_version):
    # try:
        parser = ChekMessageParser(total_message)
        data = parser.parse()

        # core_user_profile = Journey.objects.get(journey_id=trip_id) 
        # 使用 filter 方法筛选符合条件的对象，再用 exists 方法检查是否存在
   
        # journey_exists = Journey.objects.using('core_user').filter(journey_id=trip_id).exists()
        # if journey_exists:
            # 如果存在，可以进一步获取对象
            # core_Journey_profile = Journey.objects.using('core_user').get(journey_id=trip_id)
            # journey_update(parsed_data,trip_id,model,hardware_version,software_version,core_Journey_profile)
            # if model:
            #     core_Journey_profile.model = model
            
            # if hardware_version:
            #     core_Journey_profile.hardware_version = hardware_version

            # if software_version:
            #     core_Journey_profile.software_version = software_version
            
            # if parsed_data:
            #     for key,value in parsed_data.items():
            #         # print(key,value)
            #         # if type(value) != 'str' or value:
            #         core_Journey_profile.key = value
            #         print(key,core_Journey_profile.key)

            # if data.get('auto_mileages') or type(data.get('auto_mileages')) != 'str':
            #     core_Journey_profile.auto_mileages = data.get('auto_mileages')

            # if data.get('total_mileages') or type(data.get('total_mileages')) != 'str':
            #     core_Journey_profile.total_mileages = data.get('total_mileages')

            # if data.get('frames') or type(data.get('frames')) != 'str':
            #     core_Journey_profile.frames = data.get('frames')

            # if data.get('auto_frames') or type(data.get('auto_frames')) != 'str':
            #     core_Journey_profile.auto_frames = data.get('auto_frames')

            # if data.get('noa_frames') or type(data.get('noa_frames')) != 'str':
            #     core_Journey_profile.noa_frames = data.get('noa_frames')

            # if data.get('lcc_frames') or type(data.get('lcc_frames')) != 'str':
            #     core_Journey_profile.lcc_frames = data.get('lcc_frames')

            # if data.get('driver_frames') or type(data.get('driver_frames')) != 'str':
            #     core_Journey_profile.driver_frames = data.get('driver_frames')

            # if data.get('auto_speed_average') or type(data.get('auto_speed_average')) != 'str':
            #     core_Journey_profile.auto_speed_average = data.get('auto_speed_average')

            # if data.get('auto_max_speed') or type(data.get('auto_max_speed')) != 'str':
            #     core_Journey_profile.auto_max_speed = data.get('auto_max_speed')

            # if data.get('invervention_risk_proportion') or type(data.get('invervention_risk_proportion')) != 'str':
            #     core_Journey_profile.invervention_risk_proportion = data.get('invervention_risk_proportion')

            # if data.get('invervention_mpi') or type(data.get('invervention_mpi')) != 'str':
            #     core_Journey_profile.invervention_mpi = data.get('invervention_mpi')

            # if data.get('invervention_risk_mpi') or type(data.get('invervention_risk_mpi')) != 'str':
            #     core_Journey_profile.invervention_risk_mpi = data.get('invervention_risk_mpi')

            # if data.get('invervention_cnt') or type(data.get('invervention_cnt')) != 'str':
            #     core_Journey_profile.invervention_cnt = data.get('invervention_cnt')

            # if data.get('invervention_risk_cnt') or type(data.get('invervention_risk_cnt')) != 'str':
            #     core_Journey_profile.invervention_risk_cnt = data.get('invervention_risk_cnt')

            # if data.get('noa_invervention_risk_mpi') or type(data.get('noa_invervention_risk_mpi')) != 'str':
            #     core_Journey_profile.noa_invervention_risk_mpi = data.get('noa_invervention_risk_mpi')

            # if data.get('noa_invervention_mpi') or type(data.get('noa_invervention_mpi')) != 'str':
            #     core_Journey_profile.noa_invervention_mpi = data.get('noa_invervention_mpi')

            # if data.get('noa_invervention_risk_cnt') or type(data.get('noa_invervention_risk_cnt')) != 'str':
            #     core_Journey_profile.noa_invervention_risk_cnt = data.get('noa_invervention_risk_cnt')

            # if data.get('noa_auto_mileages') or type(data.get('noa_auto_mileages')) != 'str':
            #     core_Journey_profile.noa_auto_mileages = data.get('noa_auto_mileages')

            # if data.get('noa_auto_mileages_proportion') or type(data.get('noa_auto_mileages_proportion')) != 'str':
            #     core_Journey_profile.noa_auto_mileages_proportion = data.get('noa_auto_mileages_proportion')

            # if data.get('noa_invervention_cnt') or type(data.get('noa_invervention_cnt')) != 'str':
            #     core_Journey_profile.noa_invervention_cnt = data.get('noa_invervention_cnt')

            # if data.get('lcc_invervention_risk_mpi') or type(data.get('lcc_invervention_risk_mpi')) != 'str':
            #     core_Journey_profile.lcc_invervention_risk_mpi = data.get('lcc_invervention_risk_mpi')

            # if data.get('lcc_invervention_mpi') or type(data.get('lcc_invervention_mpi')) != 'str':
            #     core_Journey_profile.lcc_invervention_mpi = data.get('lcc_invervention_mpi')

            # if data.get('lcc_invervention_risk_cnt') or type(data.get('lcc_invervention_risk_cnt')) != 'str':
            #     core_Journey_profile.lcc_invervention_risk_cnt = data.get('lcc_invervention_risk_cnt')

            # if data.get('lcc_auto_mileages') or type(data.get('lcc_auto_mileages')) != 'str':
            #     core_Journey_profile.lcc_auto_mileages = data.get('lcc_auto_mileages')

            # if data.get('lcc_auto_mileages_proportion') or type(data.get('lcc_auto_mileages_proportion')) != 'str':
            #     core_Journey_profile.lcc_auto_mileages_proportion = data.get('lcc_auto_mileages_proportion')

            # if data.get('lcc_invervention_cnt') or type(data.get('lcc_invervention_cnt')) != 'str':
            #     core_Journey_profile.lcc_invervention_cnt = data.get('lcc_invervention_cnt')

            # if data.get('auto_dcc_max') or type(data.get('auto_dcc_max')) != 'str':
            #     core_Journey_profile.auto_dcc_max = data.get('auto_dcc_max')

            # if data.get('auto_dcc_frequency') or type(data.get('auto_dcc_frequency')) != 'str':
            #     core_Journey_profile.auto_dcc_frequency = data.get('auto_dcc_frequency')

            # if data.get('auto_dcc_cnt') or type(data.get('auto_dcc_cnt')) != 'str':
            #     core_Journey_profile.auto_dcc_cnt = data.get('auto_dcc_cnt')

            # if data.get('auto_dcc_duration') or type(data.get('auto_dcc_duration')) != 'str':
            #     core_Journey_profile.auto_dcc_duration = data.get('auto_dcc_duration')

            # if data.get('auto_dcc_average_duration') or type(data.get('auto_dcc_average_duration')) != 'str':
            #     core_Journey_profile.auto_dcc_average_duration = data.get('auto_dcc_average_duration')

            # if data.get('auto_dcc_average') or type(data.get('auto_dcc_average')) != 'str':
            #     core_Journey_profile.auto_dcc_average = data.get('auto_dcc_average')

            # if data.get('auto_acc_max') or type(data.get('auto_acc_max')) != 'str':
            #     core_Journey_profile.auto_acc_max = data.get('auto_acc_max')

            # if data.get('auto_acc_frequency') or type(data.get('auto_acc_frequency')) != 'str':
            #     core_Journey_profile.auto_acc_frequency = data.get('auto_acc_frequency')

            # if data.get('auto_acc_cnt') or type(data.get('auto_acc_cnt')) != 'str':
            #     core_Journey_profile.auto_acc_cnt = data.get('auto_acc_cnt')

            # if data.get('auto_acc_duration') or type(data.get('auto_acc_duration')) != 'str':
            #     core_Journey_profile.auto_acc_duration = data.get('auto_acc_duration')

            # if data.get('auto_acc_average_duration') or type(data.get('auto_acc_average_duration')) != 'str':
            #     core_Journey_profile.auto_acc_average_duration = data.get('auto_acc_average_duration')

            # if data.get('auto_acc_average') or type(data.get('auto_acc_average')) != 'str':
            #     core_Journey_profile.auto_acc_average = data.get('auto_acc_average')

            # if data.get('driver_mileages') or type(data.get('driver_mileages')) != 'str':
            #     core_Journey_profile.driver_mileages = data.get('driver_mileages')

            # if data.get('driver_dcc_max') or type(data.get('driver_dcc_max')) != 'str':
            #     core_Journey_profile.driver_dcc_max = data.get('driver_dcc_max')

            # if data.get('driver_dcc_frequency') or type(data.get('driver_dcc_frequency')) != 'str':
            #     core_Journey_profile.driver_dcc_frequency = data.get('driver_dcc_frequency')

            # if data.get('driver_acc_max') or type(data.get('driver_acc_max')) != 'str':
            #     core_Journey_profile.driver_acc_max = data.get('driver_acc_max')

            # if data.get('driver_acc_frequency') or type(data.get('driver_acc_frequency')) != 'str':
            #     core_Journey_profile.driver_acc_frequency = data.get('driver_acc_frequency')

            # if data.get('driver_speed_average') or type(data.get('driver_speed_average')) != 'str':
            #     core_Journey_profile.driver_speed_average = data.get('driver_speed_average')

            # if data.get('driver_speed_max') or type(data.get('driver_speed_max')) != 'str':
            #     core_Journey_profile.driver_speed_max = data.get('driver_speed_max')

            # if data.get('driver_dcc_cnt') or type(data.get('driver_dcc_cnt')) != 'str':
            #     core_Journey_profile.driver_dcc_cnt = data.get('driver_dcc_cnt')

            # if data.get('driver_acc_cnt') or type(data.get('driver_acc_cnt')) != 'str':
            #     core_Journey_profile.driver_acc_cnt = data.get('driver_acc_cnt')

            # core_Journey_profile.save()
        print(data.get('intervention_gps'))
        if data.get('intervention_gps'):
            # core_Journey_intervention_gps = Journey.objects.using('core_user').get(journey_id=trip_id)
            for _ in data.get('intervention_gps'):
                # core_Journey_intervention_gps = JourneyInterventionGps.objects.using('core_user').get(journey_id=trip_id)
                # 直接创建并保存对象
                print(trip_id,_.get('frame_id'),_.get('gps_lon'),_.get('gps_lat'),_.get('is_risk'))
                # core_Journey_intervention_gps = JourneyInterventionGps.objects.using('core_user').create(
                #     journey_id=trip_id,
                #     frame_id = _.get('frame_id'),
                #     gps_lon = _.get('gps_lon'),
                #     gps_lat = _.get('gps_lat'),
                #     gps_datetime = _.get('gps_datetime'),
                #     is_risk = _.get('is_risk'),
                #     identification_type = '自动识别',
                #     type = '识别接管'
                # )
        else:
            print(f"未找到 journey_id 为 {trip_id} 的行程记录。")
            # logger.info(f"未找到 journey_id 为 {trip_id} 的行程记录。")
    # except Exception as e:
        # print(e)
        # logger.info(f"报错 {e} ")

if __name__ == '__main__':
    file_path_list = ['/root/project/chekappbackendnew/merged/21a70f12-3210-4c94-95e7-7e0d3e881fc0/阿维塔12_2023款 700 三激光后驱奢享版_AVATR.OS 4.0.0_spcialPoint_2025-05-15 12-49-55.csv']
    trip_id = '82ef3322-8aa9-4cd2-81aa-3ef1499eca3d'
    total_message = process_journey(file_path_list, 
                                    user_id=100000, 
                                    user_name='念书人', 
                                    phone='18847801997', 
                                    car_brand ='理想', 
                                    car_model='', 
                                    car_hardware_version='2024款 Pro',
                                    car_software_version='OTA7.0'
                    )
              

    # NOTE: trip_id 关联id 落库结果数据
    
    handle_message_data(total_message,trip_id,'model','hardware_version','software_version')