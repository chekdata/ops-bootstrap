from dataclasses import dataclass
import pandas as pd
import numpy as np
import os
import json
import glob
import math
import pymysql
from pathlib import Path
import wgs84_to_gcj02

from tinder_os import TinderOS


def download_file_tos(bucket, prefix, suffix):
    tinder_os = TinderOS()
    # 列出待处理文件列表
    #objects = tinder_os.list_objects(args.bucket, args.prefix, suffix='.pro.csv')
    objects = tinder_os.list_objects(bucket, prefix, suffix)
    # 下载所有log文件并解析
    white_list = ['.det'] #['.pro']
    # NOTE: app roadscene normal
    # roadscene normal
    filter_list = ['.pro'] 

    # NOTE: app roadscene  not normal
    # roadscene not normal
    # filter_list = ['.propro'] 
    data_black_list = ['2025-02-26 01-58-23', '2025-02-26 18-13-06']


    file_path_list = []

    for ob in objects:
        ob_path = Path(ob)
        # 下载csv
        # NOTE: 使用黑名单过滤
        if len(ob_path.suffixes) >= 5 and (ob_path.suffixes[-5] in white_list) and (ob_path.suffixes[-2] in filter_list) and (ob_path.parts[-2] not in data_black_list):
        # if len(ob_path.suffixes) >= 5 and (ob_path.suffixes[-5] in white_list) and (ob_path.suffixes[-2] in filter_list):
        # 下载.pro.csv
            local_file_path = tinder_os.download_object(bucket, ob)
            file_path_list.append(local_file_path)
        else:
            print(f'{ob} is not in white list')
            continue
    print('Save csv {} items!'.format(len(file_path_list)))
    return file_path_list


class GPSTools:
    """
           car_code = 'fc0bab1fe14f4e31b7bd7d1f5442eb8a'  # 小鹏G6
        version_code = '444444'
        check_code = 'v100000'
        city = '上海'
    """
    def __init__(self, car_code = '856fb582039c4feba54422b531dca747', version_code = '4444443', check_code =  'v100000', report_category = 0, city = "上海市", \
                  host = '101.126.6.116', port = 3306, user = 'root', password = 'Qwer4321@',\
                  database = 'chek_backend', charset = 'utf8') -> None:
        self.car_code = car_code
        self.version_code = version_code
        self.check_code = check_code
        self.report_category = report_category
        self.city = city
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.driver_status = ["standby", "lcc", "noa"]

    def connect_mysql(self):
        args = {
            #'host':'62.234.57.136',
            'host':self.host,
            'port':self.port,
            'user':self.user,
            'password':self.password,
            #'database':'chek_cloudbackend',
            'database':self.database,
            'charset':self.charset
        }
        db = pymysql.connect(**args)
        cur = db.cursor()
        return db, cur

    def update_gps_wgs84_to_gcj02(self):
        db, cur = self.connect_mysql()
        # 查询表中所有数据并进行更新
        #query = "SELECT id, gps_lon, gps_lat FROM chek_cloudbackend.city_noa_special_points"
        query = "SELECT id, gps_lon, gps_lat FROM chek_backend.city_noa_special_points"
        cur.execute(query)
        rows = cur.fetchall()

        for row in rows:
            id = row[0]
            gps_lon = row[1]
            gps_lat = row[2]
            lat, lon = wgs84_to_gcj02.transform(gps_lat, gps_lon)
            print(lon, lat)
            #update_query = f"UPDATE chek_cloudbackend.city_noa_special_points SET gps_lon = {lon} , gps_lat = {lat} WHERE id = {id}"
            update_query = f"UPDATE chek_backend.city_noa_special_points SET gps_lon = {lon} , gps_lat = {lat} WHERE id = {id}"
            cur.execute(update_query)
            # Commit the changes to the database
            db.commit()
            #break;

        # 提交更改并关闭链接
        cur.close()
        db.close()

    # 调整
    def change_state(self, row):
        state = row.get('state')
        if not isinstance(row.get('state'), str) and np.isnan(float(row.get('state'))):
            return 'standby'
        else:
            return row.get('state')


    # 查询库中version最大值，库中是以字符串形式保存
    def get_max_check_code(self):
        db, cur = self.connect_mysql()
        query = "SELECT id, check_code FROM chek_backend.city_noa_gps_data_segment"
        # 得到versioin_code字符串中最大值
        cur.execute(query)
        rows = cur.fetchall()
        max_check_code = 0
        for row in rows:
            check_code = row[1]
            if int(check_code[1:]) > max_check_code:
                max_check_code = int(check_code[1:])
        self.check_code = 'v' + str(max_check_code + 1)
        # 提交更改并关闭链接
        cur.close() 
        db.close()
        return self.check_code 

    def set_gps_track(self, file_path, suffix, is_tos = True):
        """
        根据清洗结果csv文件完成对gps轨迹按照智驾状态切分落库
        """

        if not is_tos:
            # 本地获取
            # 获取处理结果文件详细路径
            root_dir = Path(file_path)
            files_path = root_dir / '**' / ('*' + suffix)
            files_name = glob.glob(str(files_path), recursive=True)
        else:
            path = Path(file_path)
            bucket = path.parts[0]
            prefix = '/'.join(path.parts[1:])
            files_name = download_file_tos(bucket, prefix, '.csv')

            print(files_name)


        # 查询city_noa_gps_data_segment中最大的check_code
        self.get_max_check_code()

        # 打开数据库
        db, cur = self.connect_mysql()



        # 处理数据
        segment_id = 0
        points_number_thre = 50
        for file_name in files_name:
            
            df = pd.read_csv(file_name)
            if (df.empty) or (df is None):
                continue
                # NOTE: 驾驶状态为空置位standby,后续改为auto

            df['state'] = df.apply(self.change_state, axis=1)
            
            gps_length = 1000
            pre_status = None
            pre_gps_time = '2025-03-13 22:24:35'
            gps_list = []
            for i, (frams_id, state, gps_time, lon, lat) in enumerate(zip(df['frame'],df['state'], df['gps_timestamp'], df['lon'], df['lat'])):

                if not isinstance(gps_time, str) and np.isnan(float(gps_time)):
                    gps_time = pre_gps_time

                # 状态切换 且 点位个数超过 points_number_thre
                if pre_status != None and state != pre_status and len(gps_list) > points_number_thre:
                    
                    gps_data ={'gps':gps_list}
                    sql = """
                    INSERT INTO city_noa_gps_data_segment(
                    car_code,
                    version_code,
                    check_code,
                    report_category,
                    segment_id,
                    gps,
                    driver_status,
                    city,
                    juourney_time) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                    values = (self.car_code,self.version_code,self.check_code,self.report_category,
                              segment_id,json.dumps(gps_data,ensure_ascii=False),str(pre_status),self.city,str(gps_time))
                    cur.execute(sql, values)
                    print(sql)
                    # Commit the changes to the database
                    db.commit()
                    gps_list = []
                    segment_id += 1
                if math.isnan(lat) or math.isnan(lon):
                    continue
                # # NOTE: 经纬度未进行wgs84_to_gcj02
                # lat, lon = wgs84_to_gcj02.transform(lat, lon)
                # # NOTE: app 已进行wgs84_to_gcj02转换就不用再次转换
                #gps_list.append((f'["{lon}","{lat}"]'))
                gps_list.append((f'{lon} {lat}'))
                pre_status = state
                pre_gps_time = gps_time 

        # tos下载文件清理
        if is_tos:
            for file in files_name:
                if Path(file).exists():
                    os.remove(str(file))

        # 关闭数据库
        cur.close()
        db.close()
        pass 

def connect_mysql(database):
    args = {
        #'host':'62.234.57.136',
        'host':'101.126.6.116',
        'port':3306,
        'user':'root',
        'password':'Qwer4321@',
        #'database':'chek_cloudbackend',
        'database':'chek_backend',
        'charset':'utf8'
    }
    db = pymysql.connect(**args)
    cur = db.cursor()
    return db, cur



def update_gps_wgs84_to_gcj02():
    db, cur = connect_mysql('')
    # 查询表中所有数据并进行更新
    #query = "SELECT id, gps_lon, gps_lat FROM chek_cloudbackend.city_noa_special_points"
    query = "SELECT id, gps_lon, gps_lat FROM chek_backend.city_noa_special_points"
    cur.execute(query)
    rows = cur.fetchall()

    for row in rows:
        id = row[0]
        gps_lon = row[1]
        gps_lat = row[2]
        lat, lon = wgs84_to_gcj02.transform(gps_lat, gps_lon)
        print(lon, lat)
        #update_query = f"UPDATE chek_cloudbackend.city_noa_special_points SET gps_lon = {lon} , gps_lat = {lat} WHERE id = {id}"
        update_query = f"UPDATE chek_backend.city_noa_special_points SET gps_lon = {lon} , gps_lat = {lat} WHERE id = {id}"
        cur.execute(update_query)
        # Commit the changes to the database
        db.commit()
        #break;

    # 提交更改并关闭链接
    cur.close()
    db.close()


if __name__ == "__main__":
    # update_gps_wgs84_to_gcj02()
    # 本地数据
    # suffix = '.csv'
    # root_path = '/chek/zjx/data/detect_data/highway_noa/rawData/IM/LS6/IMOS2.7.0/mik_3.1.0'
    # tos数据
    suffix = '.csv'
    root_path = 'chek/temp/for wayve/Q12025/智界S7/2025-02-26/'
    gpstools = GPSTools(car_code = '40167fca45724f68abdc6dfeaf7812aa', version_code = '4444463', check_code =  'v100005',report_category = 1, city = "芜湖市")
    gpstools.set_gps_track(root_path, suffix)


