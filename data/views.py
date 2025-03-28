from django.shortcuts import render

# Create your views here.
from data.handle_mongo import  *
from rest_framework import generics
from data.models import Data
from data.serializers import DataSerializer
from rest_framework.permissions import IsAuthenticated
from data.models import model_config,model_config_app_update
from django.views.decorators.http import require_POST
import jieba
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
import re
from rest_framework.decorators import  permission_classes,authentication_classes
from adrf.decorators import api_view
from asgiref.sync import sync_to_async
from data.process_high_way import *

from .serializers import *
from drf_spectacular.utils import OpenApiResponse
import tempfile
from common_task.handle_tos import *

import os
from django.core.files.storage import FileSystemStorage
import datetime
# class DataListCreateView(generics.ListCreateAPIView):
#     queryset = Data.objects.all()
#     serializer_class = DataSerializer
#     permission_classes = [IsAuthenticated]
#
#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)
class DataListCreateView(generics.ListCreateAPIView):
    queryset = Data.objects.all()
    serializer_class = DataSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
class DataDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Data.objects.all()
    serializer_class = DataSerializer
    permission_classes = [IsAuthenticated]

# @require_POST
# @csrf_exempt
@extend_schema(
    # 指定请求体的参数和类型
    request=HardwareSearchRequestSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=HardwareSearchResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="用model与硬件版本查询软件版本。需要用户认证。处理成功返回200，处理异常返回500。",
    summary="model与硬件版本查询软件版本",
    tags=['车型']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def search_model_hardware(request):

    try:
        # model = request.POST.get( 'model')
        # hardware_config_version = request.POST.get( 'hardware_config_version')
        model = request.data.get('model')
        hardware_config_version = request.data.get('hardware_config_version')

        if  model and hardware_config_version:
            pre_model =  model_config.objects.filter(model=model,hardware_config_version=hardware_config_version)
            # pre_model = await sync_to_async(model_config.objects.filter)(model=model,
            #                                                              hardware_config_version=hardware_config_version)
            handled_data =  handle_hardware_search(pre_model)
            return Response({'code': 200, 'message': '成功', 'data':handled_data})
        else:
            return Response({'code': 500, 'message': '未找到model字段', 'data': []})

    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错', 'data': []})

# @require_POST
# @csrf_exempt
@extend_schema(
    # 指定请求体的参数和类型
    request=FuzzySearchRequestSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=FuzzySearchResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="执行模型名称的模糊搜索，可以基于完整或部分名称。需要用户认证。处理成功返回200，处理异常返回500。",
    summary="模糊查询车型",
    tags=['车型']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def search_model_fuzzy(request):
    try:
        # model = request.POST.get( 'model')
        model = request.data.get('model')

        pre_model = None
        pre_model =  model_config.objects.filter(model=model)

        if  model and pre_model:
            return Response({'code': 200, 'message': '成功', 'data': handle_model_search(pre_model)})

        elif model:
            words = list(jieba.cut(model))
            pattern = '|'.join(map(re.escape, words))
            pre_model =  model_config.objects.filter(model__iregex=pattern)[:20]
        else:
            pre_model =   model_config.objects.all()[:20]

        if  pre_model:
            return   Response({'code': 200, 'message': '成功', 'data': handle_model_search(pre_model)})
        else:
            return Response({'code': 500, 'message': '这款车型可能还没适配', 'data': []})
    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错', 'data': []})


def handle_model_search(data):
    list_res = []
    middle_dict = {}
    for _ in data:
        model = _.model
        hardware_config_version = _.hardware_config_version
        if model not in middle_dict.keys():
            middle_dict[model] = []
            if hardware_config_version:
                middle_dict[model].append(hardware_config_version)

        else:
            if hardware_config_version:
                middle_dict[model].append(hardware_config_version)

    for k,v in middle_dict.items():
        item = {}
        item['model'] = k
        item['hardware_config_version'] = v
        if item['hardware_config_version']:
            item['hardware_config_version'].sort(reverse=False)
        list_res.append(item)
    return list_res

def handle_hardware_search(data):
    list_res = []

    for _ in data:
        model = _.model
        hardware_config_version = _.hardware_config_version
        software_config_version = _.software_config_version
        item = {}
        item['model'] = model
        if hardware_config_version:
            item['hardware_config_version'] = hardware_config_version
        if software_config_version:
            item['software_config_version'] = list(set(software_config_version.split('|')))
            if item['software_config_version']:
                item['software_config_version'].sort(reverse=True)
        list_res.append(item)
    return list_res

# @require_POST
# @csrf_exempt
@extend_schema(
    # 指定请求体的参数和类型
    request=HighwayRequestSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=HighwayResponseSerializer, description="处理成功"),
        400: OpenApiResponse(response=ErrorResponseSerializer, description="请求参数错误"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="根据经纬度判断高速道路状态，返回相应的数据。需要用户认证。处理成功返回200，处理异常返回500。",
    summary="高速道路状态判断",
    tags=['道路']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def judge_high_way_process(request):
    # try:
    #     lon = request.data.get('lon')
    #     lat = request.data.get('lat')
    #     data = await sync_to_async(judge_high_way)(lon, lat)
    #     return Response({'code': 200,  'message': '成功','data':data})
    # except Exception as e:
    #     print(e)
    #     return Response({'code': 500, 'message': '内部服务报错','data':{}})
    try:
        lon_str = request.data.get('lon')
        lat_str = request.data.get('lat')
        
        # 尝试将字符串转换为浮点数
        lon = float(lon_str) if lon_str is not None else None
        lat = float(lat_str) if lat_str is not None else None
        
        # 确保 lon 和 lat 都是有效的数值
        if lon is None or lat is None:
            return JsonResponse({'code': 400, 'message': '经纬度参数不完整', 'data': {}})
        
        # 异步调用处理函数
        data = await sync_to_async(judge_high_way)(lon, lat)
        return JsonResponse({'code': 200,  'message': '成功', 'data': data})
    except ValueError:
        # 捕获并处理由 float() 抛出的错误
        return JsonResponse({'code': 400, 'message': '无效的经纬度格式', 'data': {}})
    except Exception as e:
        print(e)
        return JsonResponse({'code': 500, 'message': '内部服务报错', 'data': {}})


# @require_POST
# @csrf_exempt
@extend_schema(
    # 指定请求体的参数和类型
    request=ModelConfigUpdateRequestSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessfulResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="接收并处理用户上传的设备配置数据。需要用户认证。处理成功返回200，处理异常返回500。",
    summary="更新设备配置数据",
    tags=['车型']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def update_model_config_app(request):
    try:
        user = request.user
        model_config_update = await sync_to_async(model_config_app_update.objects.create, thread_sensitive=True)(user_id=user.id)
        model_config_update.user_id = user.id
        if  request.data.get('created_brand'):
            model_config_update.created_brand = request.data.get('created_brand')

        if  request.data.get('created_model'):
            model_config_update.created_model = request.data.get('created_model')

        if  request.data.get('created_hardware_config_version'):
            model_config_update.created_hardware_config_version = request.data.get('created_hardware_config_version')

        if  request.data.get('created_software_config_version'):
            model_config_update.created_software_config_version = request.data.get('created_software_config_version')

        # model_config_update.save()
        await sync_to_async(model_config_update.save, thread_sensitive=True)()

        return Response({'code': 200, 'message': '数据上传成功','data':{}})

    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})

@extend_schema(
    # 指定请求体的参数和类型
    request=ModelConfigUpdateRequestSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=searchModelTosResponseSerializer, description="成功"),
        400: OpenApiResponse(response=SuccessfulResponseSerializer, description="未查询到该数据"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="接收用户上传的车型信息来查询最新的模型。需要用户认证。处理成功返回200，处理异常返回500。",
    summary="查询模型tos路径",
    tags=['模型']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def search_model_tos(request):
    try:
        user = request.user
        model = request.data.get('model')
        hardware_config_version = request.data.get('hardware_config_version')
        software_config_version = request.data.get('software_config_version')
        client, db, coll = connect_mongo('vehicle', 'model_version_repository', mongo_source_link)
        if model and hardware_config_version:
            pipeline = model_search_pipline(model, hardware_config_version,software_config_version)
            # res_data = list(coll.find({ 'model_config.model':model,'model_config.hardware_config_version':hardware_config_version},{'model_tos_link':1,'version':1}))
            res_data = list(coll.aggregate(pipeline))
            client.close()
            if res_data:
                return Response({'code': 200, 'message': '成功','data':{'model_tos_link':res_data[0].get('model_tos_link'),'md5_value':res_data[0].get('md5_value'),'model_guide':res_data[0].get('model_guide'),'screen_type':res_data[0].get('screen_type')}})

            else:
                return Response({'code': 400, 'message': '未查询到该数据','data':{}})

        elif model:
            pipeline = model_search_pipline(model, None,software_config_version)
            res_data = list(coll.aggregate(pipeline))

            # res_data = list(
            #     coll.find({'model_config.model': model},
            #               {'model_tos_link': 1,'version':1}))
            client.close()
            if res_data:
                return Response(
                    {'code': 200, 'message': '成功', 'data': {'model_tos_link': res_data[0].get('model_tos_link'),'md5_value':res_data[0].get('md5_value'),'model_guide':res_data[0].get('model_guide'),'screen_type':res_data[0].get('screen_type')}})
            else:
                return Response({'code': 400, 'message': '未查询到该数据', 'data': {}})
        else:
            client.close()
            return Response({'code': 400, 'message': '数据缺失 model', 'data': {}})
    except Exception as e:
        return Response({'code': 500, 'message': '内部服务报错', 'data': {}})

def model_search_pipline(model,hardware_config_version,software_config_version):
    from bson.son import SON
    if model and hardware_config_version and software_config_version:
        pipeline = [
            {
                "$match": {
                    "model": model,  # 保持现有的查询条件
                    "hardware_config_version": hardware_config_version,  # 保持现有的查询条件
                    "software_config_version":software_config_version,
                }
            },
            {
                "$addFields": {
                    "versionAsDate": {
                        "$dateFromString": {"dateString": "$version", "format": "%Y-%m-%d"}
                    }
                }
            },
            {
                "$sort": SON([("versionAsDate", -1)])  # 按version字段转换后的日期降序排列
            },
            {
                "$limit": 1  # 获取时间最靠后的那个文档
            },
            {
                "$project": {
                    "_id": 0,
                    "model_tos_link": 1,
                    "version": 1,
                    'md5_value': 1,
                    'model_guide':1,
                     'screen_type':1
                }
            }
        ]
    elif model and hardware_config_version:
        pipeline = [
            {
                "$match": {
                    "model": model,  # 保持现有的查询条件
                    "hardware_config_version": hardware_config_version,  # 保持现有的查询条件
                }
            },
            {
                "$addFields": {
                    "versionAsDate": {
                        "$dateFromString": {"dateString": "$version", "format": "%Y-%m-%d"}
                    }
                }
            },
            {
                "$sort": SON([("versionAsDate", -1)])  # 按version字段转换后的日期降序排列
            },
            {
                "$limit": 1  # 获取时间最靠后的那个文档
            },
            {
                "$project": {
                    "_id": 0,
                    "model_tos_link": 1,
                    "version": 1,
                    'md5_value':1,
                    'model_guide':1,
                     'screen_type':1
                }
            }
        ]
    else:
        pipeline = [
            {
                "$match": {
                    "model": model,  # 保持现有的查询条件
                }
            },
            {
                "$addFields": {
                    "versionAsDate": {
                        "$dateFromString": {"dateString": "$version", "format": "%Y-%m-%d"}
                    }
                }
            },
            {
                "$sort": SON([("versionAsDate", -1)])  # 按version字段转换后的日期降序排列
            },
            {
                "$limit": 1  # 获取时间最靠后的那个文档
            },
            {
                "$project": {
                    "_id": 0,
                    "model_tos_link": 1,
                    "version": 1,
                    'md5_value': 1,
                    'model_guide':1,
                    'screen_type':1
                }
            }
        ]
    return pipeline


@extend_schema(
    # 指定请求体的参数和类型
    request=ModelConfigUpdateModelTos,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessfulResponseSerializer, description="模型上传成功"),
        400: OpenApiResponse(response=SuccessfulResponseSerializer, description="数据缺失"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
    ],
    description="接收用户上传的模型并入库。处理成功返回200，处理异常返回500。",
    summary="上传模型",
    tags=['模型']
)
@api_view(['POST'])
@authentication_classes([])  # 清空认证类
@permission_classes([AllowAny])  # 允许任何人访问
async def update_model_tos(request):
    try:
        desc = request.data.get('desc')
        name = request.data.get('name')
        version = request.data.get('version')
        brand = request.data.get('brand')
        model_config_data = eval(request.data.get('model_config'))
        model_guide = request.data.get('model_guide')
        md5_value = request.data.get('md5_value')

        model_pt_file = request.FILES.get('file')
        if not model_pt_file:
            return Response({'code': 500, 'message': '没有接收到文件', 'data': {}})

        if not md5_value:
            return Response({'code': 400, 'message': '数据缺失 md5_value', 'data': {}})

        if not model_config:
            return Response({'code': 400, 'message': '数据缺失 model_config', 'data': {}})


        # 使用 tempfile 创建一个临时文件夹
        temp_dir = tempfile.gettempdir()

        # 创建一个 FileSystemStorage 实例，指向临时目录
        fs = FileSystemStorage(location=temp_dir)

        # 保存文件
        # filename = fs.save(csv_file.name, csv_file)
        filename = await sync_to_async(fs.save, thread_sensitive=True)(model_pt_file.name, model_pt_file)
        # 获取保存后的文件的完整路径
        file_url = fs.path(filename)

        md5_cal_value = calculate_md5_value(file_url)
        if md5_cal_value == md5_value:
            upload_file_path = f'model/{model_pt_file.name}'
            # 保存文件
            tinder_os = TinderOS()
            tinder_os.upload_file('chek', upload_file_path, file_url)
            os.remove(file_url)

            client, db, coll = connect_mongo('vehicle', 'model_version_repository', mongo_source_link)
            for _ in model_config_data:
                item ={}
                if desc:
                    item['desc'] = desc
                item['md5_value'] = md5_value
                item['model_tos_link'] = f'chek/{upload_file_path}'

                if name:
                    item['name'] = name

                if version:
                    item['version'] = version
                else:
                    client.close()
                    return Response({'code': 400, 'message': '数据缺失 version', 'data': {}})

                if brand:
                    item['brand'] = brand
                if model_guide:
                    item['model_guide'] = model_guide
                if _.get('model'):
                    item['model'] = _.get('model')
                if _.get('hardware_config_version'):
                    item['hardware_config_version'] = _.get('hardware_config_version')
                if _.get('software_config_version'):
                    item['software_config_version'] = _.get('software_config_version')
                # if model and hardware_config_version:
                #     item['model_config'] = handle_modelconfig_search(model, hardware_config_version)
                # elif model:
                #     item['model_config'] = handle_modelconfig_search(model, None)
                # else:
                #     return Response({'code': 400, 'message': '数据缺失 model', 'data': {}})
                item['created_date'] = datetime.datetime.now()
                if item.get('model') and item.get('hardware_config_version') and item.get('software_config_version'):
                    mongo_update(coll, item, item)
                else:
                    return Response({'code': 400, 'message': '缺少必要参数 model，hardware_config_version，software_config_version', 'data': {}})
            update_model_info_by_match_model(brand, model_config_data)
            client.close()
            return Response({'code': 200, 'message': '模型上传成功', 'data': {}})
        os.remove(file_url)
    except Exception as e:
    #     print(e)
        return Response({'code': 500, 'message': '内部服务报错', 'data': {}})

def handle_modelconfig_search(model,hardware_config_version):
    client, db, coll = connect_mongo('vehicle', 'hot_brand_vehicle', mongo_source_link)
    if model and hardware_config_version:
        res_data = list(
            coll.find({'model': model,'hardware_config_version':hardware_config_version},
                      {'model': 1, 'hardware_config_version': 1,'software_config_version':1}))
    elif model:
        res_data = list(
            coll.find({'model': model},
                      {'model': 1, 'hardware_config_version': 1, 'software_config_version': 1}))

    else:
        res_data = []
    client.close()
    list_res = []

    for _ in res_data:
        model = _.get('model')
        hardware_config_version = _.get('hardware_config_version')
        software_config_version = _.get('software_config_version')
        item = {}
        list_software_config_version = []
        item['model'] = model
        if hardware_config_version:
            item['hardware_config_version'] = hardware_config_version
        if software_config_version:
            for _ in software_config_version:
                if _.get('publish_code'):
                    list_software_config_version.append(_.get('publish_code'))

            item['software_config_version'] = list_software_config_version
            if item['software_config_version']:
                item['software_config_version'].sort(reverse=False)
        list_res.append(item)
    return list_res

def calculate_md5_value(file_path):
    import hashlib

    md5_hash = hashlib.md5()
    with open(file_path, "rb") as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()


@extend_schema(
    # 指定请求体的参数和类型
    request=ModelConfigSearchModelTos,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessfulResponseSerializer, description="成功"),
        400: OpenApiResponse(response=SuccessfulResponseSerializer, description="车型缺失"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
    ],
    description="允许用户从获取车型硬件版本与软件版本。处理成功返回200，处理异常返回500。",
    summary="获取车型版本",
    tags=['车型']
)
@api_view(['POST'])
@authentication_classes([])  # 清空认证类
@permission_classes([AllowAny])  # 允许任何人访问
async def search_model_info(request):
    try:
        # model = request.POST.get( 'model')
        # hardware_config_version = request.POST.get( 'hardware_config_version')
        model = request.data.get('model')
        hardware_config_version = request.data.get('hardware_config_version')
        if not model:
            return Response({'code': 400, 'message': '数据缺失 model', 'data': {}})

        client, db, coll = connect_mongo('vehicle', 'hot_brand_vehicle', mongo_source_link)
        if model and hardware_config_version:
            res_data = list(coll.find({'model':model,'hardware_config_version':hardware_config_version}, {'model': 1, 'hardware_config_version': 1, 'software_config_version.publish_code': 1}))
            client.close()
        elif model:
            res_data = list(coll.find({'model': model},
                                      {'model': 1, 'hardware_config_version': 1, 'software_config_version.publish_code': 1}))
            client.close()
        handled_data = handle_hardware_search_full_data(res_data)
        return Response({'code': 200, 'message': '成功', 'data': handled_data})


    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错', 'data': []})

def handle_hardware_search_full_data(data):
    list_res = []

    for _ in data:
        model = _.get('model')
        hardware_config_version = _.get('hardware_config_version')
        software_config_version = _.get('software_config_version')

        if model and hardware_config_version and software_config_version:
            if software_config_version:
                software_config_version_filter = [x for x in software_config_version if '年'not in x.get('publish_code') and '月' not in x.get('publish_code') and '版本' not in x.get('publish_code')]
                for i in software_config_version_filter:
                    item = {}
                    item['model'] = model
                    if hardware_config_version:
                        item['hardware_config_version'] = hardware_config_version
                    item['software_config_version'] = i.get('publish_code')
                    if item not in list_res:
                        list_res.append(item)
        elif model and hardware_config_version:
            item = {}
            item['model'] = model
            if hardware_config_version:
                item['hardware_config_version'] = hardware_config_version
            if item not in list_res:
                list_res.append(item)

        else:
            item = {}
            item['model'] = model
            if item not in list_res:
                list_res.append(item)
    return list_res
# @extend_schema(
#     # 指定请求体的参数和类型
#     request=ModelConfigUpdateModelTos,
#     # 指定响应的信息
#     responses={
#         200: OpenApiResponse(response=SuccessfulResponseSerializer, description="文件下载成功"),
#         400: OpenApiResponse(response=SuccessfulResponseSerializer, description="路径缺失"),
#         500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
#     },
#     parameters=[
#     ],
#     description="允许用户从tos下载文件。处理成功返回200，处理异常返回500。",
#     summary="下载文件",
#     tags=['模型']
# )
# @api_view(['POST'])
# @authentication_classes([])  # 清空认证类
# @permission_classes([AllowAny])  # 允许任何人访问
# async def download_file_tos(request):
#     try:
#         bucket_name = request.data.get('bucket_name')
#         url_path = request.data.get('url_path')
#
#     except Exception as e:
#         # print(e)
#         return Response({'code': 500, 'message': '内部服务报错', 'data': {}})
#

def update_model_info_by_match_model(brand,model_config_data):
    item_model={}
    for _ in model_config_data:
        model = _.get('model')
        hardware_config_version = _.get('hardware_config_version')
        software_config_version = _.get('software_config_version')
        if model not in item_model.keys():
            item_model[model] = {}
        if hardware_config_version not in item_model[model]:
            item_model[model][hardware_config_version] = []
            if software_config_version:
                item_model[model][hardware_config_version].append(software_config_version)
        else:
            if software_config_version:
                item_model[model][hardware_config_version].append(software_config_version)

    for _ in item_model.keys():
        model_new = _
        for k,v in item_model[_].items():
            hardware_config_version_new = k
            software_config_version_new = list(set(v))
            if software_config_version_new:
                pre_model, created =  model_config.objects.get_or_create(model=_,hardware_config_version=hardware_config_version_new)
                if not created:
                    old_software_config_version = str(pre_model.software_config_version).split('|')
                    for data in software_config_version_new:
                        if data not in old_software_config_version:
                            old_software_config_version.append(data)
                    if old_software_config_version != str(pre_model.software_config_version).split('|'):
                        pre_model.software_config_version =   '|'.join(old_software_config_version)
                        pre_model.save()
                else:
                    pre_model.brand = brand
                    pre_model.model = model_new
                    pre_model.hardware_config_version = k
                    pre_model.software_config_version = '|'.join(software_config_version_new)
                    if pre_model.model and pre_model.hardware_config_version and pre_model.software_config_version:
                        pre_model.save()

@extend_schema(
    # 指定请求体的参数和类型
    request=ModelConfigUpdateModelTos,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessfulResponseSerializer, description="版本号上传成功"),
        400: OpenApiResponse(response=SuccessfulResponseSerializer, description="数据缺失"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
    ],
    description="接收用户上传的版本信息并入库。处理成功返回200，处理异常返回500。",
    summary="上传版本信息",
    tags=['版本包']
)
@api_view(['POST'])
@authentication_classes([])  # 清空认证类
@permission_classes([AllowAny])  # 允许任何人访问
async def update_version_vault(request):
    try:
        package_name = request.data.get('package_name')
        version_name = request.data.get('version_name')
        chanel = request.data.get('chanel')
        link = request.data.get('link')
        md5_value = request.data.get('md5_value')
        version_code = request.data.get('version_code')

        if not package_name:
            return Response({'code': 500, 'message': '数据缺失 package_name', 'data': {}})

        # if not md5_value:
        #     return Response({'code': 400, 'message': '数据缺失 md5_value', 'data': {}})

        if not version_name:
            return Response({'code': 400, 'message': '数据缺失 version_name', 'data': {}})

        if not chanel:
            return Response({'code': 400, 'message': '数据缺失 chanel', 'data': {}})
        
        if not version_code:
            return Response({'code': 400, 'message': '数据缺失 version_code', 'data': {}})

        
    except Exception as e:
    #     print(e)
        return Response({'code': 500, 'message': '内部服务报错', 'data': {}})