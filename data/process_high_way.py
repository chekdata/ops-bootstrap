# -*- coding: utf-8 -*-
import json
import urllib
import math
# import numpy as np
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# import pandas as pd
from datetime import datetime
# import uvicorn

# app = FastAPI()

x_pi = 3.14159265358979324 * 3000.0 / 180.0
pi = 3.1415926535897932384626  # π
a = 6378245.0  # 长半轴
ee = 0.00669342162296594323  # 偏心率平方

'''
输入（经度，维度）
'''


def bd09_to_gcj02(bd_lon, bd_lat):
    """
    百度坐标系(BD-09)转火星坐标系(GCJ-02)
    百度——>谷歌、高德
    :param bd_lat:百度坐标纬度
    :param bd_lon:百度坐标经度
    :return:转换后的坐标列表形式
    """
    x = bd_lon - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)
    gg_lng = z * math.cos(theta)
    gg_lat = z * math.sin(theta)
    return [gg_lng, gg_lat]


def gcj02_to_wgs84(lng, lat):
    """
    GCJ02(火星坐标系)转GPS84
    :param lng:火星坐标系的经度
    :param lat:火星坐标系纬度
    :return:
    """
    if out_of_china(lng, lat):
        return [lng, lat]
    dlat = _transformlat(lng - 105.0, lat - 35.0)
    dlng = _transformlng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return [lng * 2 - mglng, lat * 2 - mglat]


def bd09_to_wgs84(bd_lon, bd_lat):
    lon, lat = bd09_to_gcj02(bd_lon, bd_lat)
    return gcj02_to_wgs84(lon, lat)


def bd09_to_wgs84(bd_lon, bd_lat):
    lon, lat = bd09_to_gcj02(bd_lon, bd_lat)
    return gcj02_to_wgs84(lon, lat)


def gcj02_to_bd09(lng, lat):
    """
    火星坐标系(GCJ-02)转百度坐标系(BD-09)
    谷歌、高德——>百度
    :param lng:火星坐标经度
    :param lat:火星坐标纬度
    :return:
    """
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * x_pi)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * x_pi)
    bd_lng = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return [bd_lng, bd_lat]


def wgs84_to_gcj02(lng, lat):
    """
    WGS84转GCJ02(火星坐标系)
    :param lng:WGS84坐标系的经度
    :param lat:WGS84坐标系的纬度
    :return:
    """
    if out_of_china(lng, lat):  # 判断是否在国内
        return [lng, lat]
    dlat = _transformlat(lng - 105.0, lat - 35.0)
    dlng = _transformlng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return [mglng, mglat]


def wgs84_to_bd09(lon, lat):
    lon, lat = wgs84_to_gcj02(lon, lat)
    return gcj02_to_bd09(lon, lat)


def out_of_china(lng, lat):
    """
    判断是否在国内，不在国内不做偏移
    :param lng:
    :param lat:
    :return:
    """
    return not (lng > 73.66 and lng < 135.05 and lat > 3.86 and lat < 53.55)


def _transformlng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + \
          0.1 * lng * lat + 0.1 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 *
            math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * pi) + 40.0 *
            math.sin(lng / 3.0 * pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * pi) + 300.0 *
            math.sin(lng / 30.0 * pi)) * 2.0 / 3.0
    return ret


def _transformlat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + \
          0.1 * lng * lat + 0.2 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 *
            math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * pi) + 40.0 *
            math.sin(lat / 3.0 * pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * pi) + 320 *
            math.sin(lat * pi / 30.0)) * 2.0 / 3.0
    return ret


# class _Lon_Lat_Request(BaseModel):
#     lon: str
#     lat: str



def judge_high_way(lon,lat):
    """
    :param lon: 120.9910398494324
    :param lat: 31.988758546859902
    :param sign: rd71345adb7d5d234f979f16f323910859f88
    :return:
    http://47.237.20.206:8085/road/findHighSection?location=115.696948,39.277058&sign=885adb7d5d234f979f16f323910859f23
    """

    sign = '885adb7d5d234f979f16f323910859f23'
    try:
        import requests
        # url =  """http://road.jwdou.com/road/findHighSection?location=116.451984,39.01567&sign=rd71345adb7d5d234f979f16f323910859f88"""
        # 120.9910398494324, 31.988758546859902
        #lon, lat = wgs84_to_gcj02(lon, lat)
        # url = f'http://47.237.20.206:8085/road/findHighSection?location={lon},{lat}&sign={sign}'
        # url = f'http://1.95.87.72:9065/road/findHighSection?location={lon},{lat}'
        url = f'http://1.95.87.72:9065/road/findHighSectionAsync?location={lon},{lat}'
        response = requests.get(url)
        data = response.json()
        return data.get('data',{})
    except Exception as e:
        print(e)


if __name__ == "__main__":
    print( judge_high_way(120.9910398494324, 31.988758546859902))
    pass
    # uvicorn.run(app, host="0.0.0.0", port=8000)

# import pandas as pd
# import time
# from concurrent.futures import ThreadPoolExecutor
# import concurrent
# start = time.time()
# # df =pd.read_csv('7e880f2a4873_20231113_065955.pro.csv')
# # df =pd.read_csv('gps.csv')
# df =pd.read_csv('b0e0c2fa840f_20240114_105010.pro.csv')
#
# for i in df.index:
#     lon = df.loc[i,'lon']
#     lat = df.loc[i,'lat']
#     lon, lat = wgs84_to_gcj02(lon, lat)
#     df.loc[i,'lon_trans'] = lon
#     df.loc[i,'lat_trans'] = lat
# #     df.loc[i,'highway_status'] = json_data.get('data').get('highWay')
# #     df.loc[i,'roadName'] = json_data.get('data').get('roadName')
# #     print(df.loc[i,'highway_status'],df.loc[i,'roadName'])
#
#
#
#
# # print(len(df))
# df = df[df['road_scene']=='highway']
#
# with ThreadPoolExecutor(max_workers=10) as executor:
#     futures = [executor.submit(judge_high_way, df.loc[i,'lon_trans'], df.loc[i,'lat_trans']) for i in df.index]
#     for future in concurrent.futures.as_completed(futures):
#         data=future.result()
#         print(data)
#         try:
#             df.loc[data.get('index'),'highway_status']=data.get('data').get('highWay')
#             df.loc[data.get('index'),'roadName']=data.get('data').get('roadName')
#         except Exception as e:
#             concurrent
# df.to_csv('智己_noa_48.csv')
# print(time.time()-start)
# # pd.DataFrame(data=listres).to_csv('resu.csv')



