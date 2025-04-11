from django.shortcuts import render
# from common_task.tasks import merge_trip_chunks , check_and_merge_trip # Import the missing task
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import  permission_classes
from adrf.decorators import api_view
from common_task.models import analysis_data_app,tos_csv_app
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.decorators import  permission_classes
from adrf.decorators import api_view
from rest_framework.response import Response
import io
import csv
import logging
import asyncio
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from accounts.models import User
from common_task.handle_tos_play_link import *

import re
import os
import json
from django.db import transaction
from asgiref.sync import sync_to_async
from django.core.files.storage import FileSystemStorage
import tempfile
from common_task.handle_tos import *
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample,inline_serializer, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from rest_framework import status,serializers
from common_task.serializers import *
from data.models import model_config
from .models import Trip, ChunkFile
#from .chek_dataprocess.cloud_process_csv.wechat_csv_process import process_csv
from .chek_dataprocess.cloud_process_csv.saas_csv_process import process_journey, async_process_journey
from .tasks import (
    upload_chunk_file, 
    check_chunks_complete, 
    start_merge_async, 
    check_timeout_trip, 
    force_merge_trip, 
    handle_merge_task,
    cleanup_background_tasks,
    background_tasks)


logger = logging.getLogger('common_task')

# 限制并发任务5
semaphore = asyncio.Semaphore(5)


# from .tasks import (
#     upload_chunk_file, 
#     check_chunks_complete, 
#     start_merge_async, 
#     check_timeout_trip,
#     force_merge_trip
# )


def is_valiad_phone_number(phone):
    
    pattern = r"^1[3-9]\d{9}$"

    if re.match(pattern, phone):
        return True
    else:
        return False

# 小程序proto1.0版本
# 没有上传中间结果
async def process_wechat_data(user, file_path):
    file_name = file_path.split('/')[-1]
    infos = file_name.split('_')
    if len(infos) > 3:
        model = infos[0]
        hardware_version = infos[1]
        software_version = infos[2]
        print(f"process user :{user.name} {file_name} journey!")

        is_phone_number = await sync_to_async(is_valiad_phone_number, thread_sensitive=True)(user.phone)

        if is_phone_number: 
            # # NOTE: 确保phone和小程序phone对应一致
            # # user_id 默认100000
            # # proto_v1.0
            # # 可处理文件列表
            # await sync_to_async(process_csv, thread_sensitive=True)(
            #                                                         [file_path], 
            #                                                         user_id=100000, 
            #                                                         user_name=user.name, 
            #                                                         phone=user.phone, 
            #                                                         car_brand =model, 
            #                                                         car_model='', 
            #                                                         car_version=software_version)


            # # proto_v1.2
            # # 每次处理一个文件
            # await sync_to_async(process_journey, thread_sensitive=True)(
            #                                                         file_path, 
            #                                                         user_id=100000, 
            #                                                         user_name=user.name, 
            #                                                         phone=user.phone, 
            #                                                         car_brand =model, 
            #                                                         car_model='', 
            #                                                         car_hardware_version=hardware_version,
            #                                                         car_software_version=software_version)
            
            await async_process_journey(file_path, 
                                        user_id=100000, 
                                        user_name=user.name, 
                                        phone=user.phone, 
                                        car_brand =model, 
                                        car_model='', 
                                        car_hardware_version=hardware_version,
                                        car_software_version=software_version)

        else:
            print(f"user phone:{user.phone} is not correct! journey not to be processed!")     
    else:
        print(f"file name:{file_name} is not correct! journey not to be processed!")
    
    
async def limited_task_wrapper(user, file_path):
    """资源限制任务包装器"""
    async with semaphore:
        """后台任务：处理微信行程数据"""
        try: 
            await process_wechat_data(user, file_path)
        except Exception as e:
            print(f"后台任务失败: {e}")

# 用于在程序关闭时等待所有后台任务完成
async def shutdown_background_tasks():
    """等待所有后台任务完成"""
    if background_tasks:
        print("等待后台任务完成...")
        await asyncio.gather(*background_tasks, return_exceptions=True)

async def prepare_upload_file_path(_id,status_tag,file_name):
    # temp/app_project/{_id}/inference_data/品牌名/车型/2024-08-25/2024-08-25 21-32-12/file
    file_name = file_name.name
    model = file_name.split('_')[0]
    time_line = file_name.split('_')[-1].split('.')[0]
    # middle_model = await sync_to_async(model_config.objects.get, thread_sensitive=True)(model=model)
    # 异步环境下获取满足条件的第一条记录
    middle_model = await sync_to_async(model_config.objects.filter(model=model).first, thread_sensitive=True)()
    brand = middle_model.brand

    if middle_model:
        upload_file_path = f"""temp/app_project/{_id}/{status_tag}/{brand}/{model}/{time_line.split(' ')[0]}/{time_line}/{file_name}"""
        return upload_file_path
    else:
        return None

# Create your views here.
@extend_schema(
    # 指定请求体的参数和类型
    request=AfterAnalysisDataSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="接收并处理CSV文件，然后上传到云存储。需要用户认证。处理成功返回200，处理异常返回500。",
    summary="上传推理CSV文件并处理",
    tags=['数据']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def process_after_inference_data(request):
    user = request.user  # 获取当前登录用户
    _id = user.id
    try:
        csv_file = request.FILES.get('file')

        if not csv_file:
            return Response({'code':500,'message': '没有接收到文件','data':{}})

        # 使用 tempfile 创建一个临时文件夹
        temp_dir = tempfile.gettempdir()

        # 创建一个 FileSystemStorage 实例，指向临时目录
        fs = FileSystemStorage(location=temp_dir)

        # 保存文件
        # upload_file_path =  prepare_upload_file_path(_id, 'inference_data', csv_file)
        # upload_file_path = await sync_to_async(prepare_upload_file_path, thread_sensitive=True)(_id, 'inference_data', csv_file)
        upload_file_path = await prepare_upload_file_path(_id, 'inference_data', csv_file)
        if not upload_file_path:
            return Response({'code': 500, 'message': '上传错误 model', 'data': {}})
        filename = await sync_to_async(fs.save, thread_sensitive=True)(csv_file.name, csv_file)
        # 获取保存后的文件的完整路径
        file_url = fs.path(filename)

        # 上传wechat格式行程
        task = asyncio.create_task(
            limited_task_wrapper(user, file_url)
        )
        # 用于管理所有后台任务的列表
        background_tasks.append(task)

        # upload_file_path = f'temp/app_project/{_id}/inference_data/{csv_file.name}'
        # 保存文件
        tinder_os = TinderOS()
        tinder_os.upload_file('chek',upload_file_path , file_url)
        # os.remove(file_url)

        data_tos_model, creat = await sync_to_async(tos_csv_app.objects.get_or_create, thread_sensitive=True)(
            user_id=user.id,
            tos_file_path=upload_file_path,
            tos_file_type='inference'
        )
        data_tos_model.user_id = user.id

        data_tos_model.tos_file_path =upload_file_path
        data_tos_model.tos_file_type = 'inference'
        # data_tos_model.save()
        await sync_to_async(data_tos_model.save, thread_sensitive=True)()

        return Response({'code':200,'message': '文件接收和上传成功','data':{}})
    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})


@extend_schema(
    # 指定请求体的参数和类型
    request=AfterAnalysisDataSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="接收并处理CSV文件，然后上传到云存储。需要用户认证。处理成功返回200，处理异常返回500。",
    summary="上传接收分析后CSV文件并处理",
    tags=['数据']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def process_after_analysis_data_csv(request):
    user = request.user  # 获取当前登录用户
    _id = user.id
    try:
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'code':500,'message': '没有接收到文件','data':{}})

        # 使用 tempfile 创建一个临时文件夹
        temp_dir = tempfile.gettempdir()

        # 创建一个 FileSystemStorage 实例，指向临时目录
        fs = FileSystemStorage(location=temp_dir)

        # 保存文件
        upload_file_path =  await prepare_upload_file_path(_id, 'analysis_data', csv_file)

        if not upload_file_path:
            return Response({'code': 500, 'message': '上传错误 model', 'data': {}})
        filename = await sync_to_async(fs.save, thread_sensitive=True)(csv_file.name, csv_file)

        # 获取保存后的文件的完整路径
        file_url = fs.path(filename)

        # upload_file_path = f'temp/app_project/{_id}/analysis_data/{csv_file.name}'
        # 保存文件
        tinder_os = TinderOS()
        tinder_os.upload_file('chek',upload_file_path , file_url)
        os.remove(file_url)

        data_tos_model,creat =await sync_to_async(tos_csv_app.objects.get_or_create, thread_sensitive=True)(
            user_id=user.id,
            tos_file_path=upload_file_path,
            tos_file_type= 'analysis'
        )
        data_tos_model.user_id = user.id

        data_tos_model.tos_file_path =upload_file_path
        data_tos_model.tos_file_type = 'analysis'
        data_tos_model.save()
        await sync_to_async(data_tos_model.save, thread_sensitive=True)()

        return Response({'code':200,'message': '文件接收和上传成功','data':{}})
    except Exception as e:
    #     print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})


@extend_schema(
    # 指定请求体的参数和类型
    request=AnalysisDataSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="根据传入的参数更新用户的分析数据，处理成功返回200，处理异常返回500。",
    summary="更新分析数据",
    tags=['数据']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def process_after_analysis_data(request):
    user = request.user
    # profile =  await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)
    user_id = user.id

    intervention = request.POST.get('intervention')
    intervention_risk = request.POST.get('intervention_risk')
    mpi = request.POST.get('mpi')
    mpi_risk = request.POST.get('mpi_risk')
    total_mile = request.POST.get('total_mile')
    noa_mile = request.POST.get('noa_mile')
    lcc_mile = request.POST.get('lcc_mile')
    noa_lcc_mile = request.POST.get('noa_lcc_mile')
    standby_mile = request.POST.get('standby_mile')

    try:
        # data_model =  analysis_data_app()
        # user_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)
        data_model,creat =await sync_to_async(analysis_data_app.objects.get_or_create, thread_sensitive=True)
        # data_model.user_id = user_id
        if intervention:
            data_model.intervention = intervention
        if intervention_risk:
            data_model.intervention_risk = intervention_risk

        if mpi:
            data_model.mpi = mpi

        if mpi_risk:
            data_model.mpi_risk = mpi_risk

        if total_mile:
            data_model.total_mile = total_mile

        if noa_mile:
            data_model.noa_mile = noa_mile

        if lcc_mile:
            data_model.lcc_mile = lcc_mile

        if noa_lcc_mile:
            data_model.noa_lcc_mile = noa_lcc_mile

        if standby_mile:
            data_model.standby_mile = standby_mile
        data_model.user_id = user_id
        # data_model.save()
        await sync_to_async(data_model.save, thread_sensitive=True)()


        return Response({'code':200,'message': 'process_after_inference_data 更新成功','data':{}})
    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})


@extend_schema(
    # 指定请求体的参数和类型
    request=InferenceDetialDetDataSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="接收并处理CSV文件，然后上传到云存储。需要用户认证。处理成功返回200，处理异常返回500。",
    summary="上传推理det文件并处理",
    tags=['数据']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def process_inference_detial_det_data(request):
    user = request.user  # 获取当前登录用户
    _id = user.id
    try:
        det_file = request.FILES.get('file')
        if not det_file:
            return Response({'code':500,'message': '没有接收到文件','data':{}})

        # 使用 tempfile 创建一个临时文件夹
        temp_dir = tempfile.gettempdir()

        # 创建一个 FileSystemStorage 实例，指向临时目录
        fs = FileSystemStorage(location=temp_dir)

        # 保存文件
        # temp/app_project/{_id}/inference_data/品牌名/车型/2024-08-25/2024-08-25 21-32-12/file
        # upload_file_path = f'temp/app_project/{_id}/inference_data/{det_file.name}'
        upload_file_path = await prepare_upload_file_path(_id,  'inference_data', det_file)
        if not upload_file_path:
            return Response({'code': 500, 'message': '上传错误 model', 'data': {}})

        filename = await sync_to_async(fs.save, thread_sensitive=True)(det_file.name, det_file)
        # 获取保存后的文件的完整路径
        file_url = fs.path(filename)

        # 保存文件
        tinder_os = TinderOS()
        tinder_os.upload_file('chek',upload_file_path , file_url)
        os.remove(file_url)

        data_tos_model, creat = await sync_to_async(tos_csv_app.objects.get_or_create, thread_sensitive=True)(
            user_id=user.id,
            tos_file_path=upload_file_path,
            tos_file_type='inference'
        )
        data_tos_model.user_id = user.id

        data_tos_model.tos_file_path =upload_file_path
        data_tos_model.tos_file_type = 'inference'
        # data_tos_model.save()
        await sync_to_async(data_tos_model.save, thread_sensitive=True)()


        return Response({'code':200,'message': '文件接收和上传成功','data':{}})
    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})

@extend_schema(
    # 指定请求体的参数和类型
    request=TosPlayLink,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="根据传入的tos路径获取点播链接，处理成功返回200，处理异常返回500。",
    summary="获取点播链接",
    tags=['点播链接']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def process_tos_play_link(request):
    try:
        tos_link = request.data.get('tos_link')

        bucket_name = tos_link.split('/')[0]
        tos_path = '/'.join(tos_link.split('/')[1:])
        if bucket_name =='chek':
            url = f'http://bytevdn.chekkk.com/{tos_path}'
            play_link_tos = test(url)
        elif bucket_name =='chek-models':
            #暂时不能使用
            url = f'http://bytevdn.chekkk.com/{tos_path}'
            play_link_tos =test(url)
        return Response({'code':200,'message': '成功','data':{'tos_play_link':play_link_tos}})
    except Exception as e:
        return Response({'code': 500, 'message': '内部服务报错','data':{}})

@extend_schema(
    # 指定请求体的参数和类型
    request=InferenceDetialDetDataSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    description="根据传入的tos路径获取点播链接，处理成功返回200，处理异常返回500。",
    summary="分片上传数据",
    tags=['数据']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def upload_chunk(request):
    """上传分片文件"""
    user = request.user  # 获取当前登录用户
    _id = user.id
    try:
        # 获取上传文件
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'code':500, 'success': False, 'message': '没有接收到文件', 'data':{}})
        
        # 获取并解析 metadata JSON
        metadata_str = request.POST.get('metadata')
        if not metadata_str:
            return JsonResponse({'code':500,'success': False, 'message': '缺少 metadata', 'data':{}})
            
        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            return JsonResponse({'code':500, 'success': False, 'message': 'metadata 格式错误', 'data':{}})
        
        # 从 metadata 中获取必要信息
        trip_id = metadata.get('trip_id')
        chunk_index = int(metadata.get('chunk_index', 0))
        file_type = metadata.get('file_type', 'csv')
        
        if not trip_id:
            return JsonResponse({'code':500,'success': False, 'message': '缺少 trip_id', 'data':{}})
        
        # 上传分片
        success, message, chunk_file = await upload_chunk_file(
            trip_id, 
            chunk_index, 
            file, 
            file_type,
            metadata
        )
        
        if not success:
            return JsonResponse({'code':500,'success': False, 'message': message, 'data':{}})
        
        # # 如果是最后一个分片，触发合并
        # if metadata.get('is_last_chunk'):
        #     asyncio.create_task(start_merge_async(_id, trip_id))
        # else:
        #     # 检查是否需要触发自动合并
        #     asyncio.create_task(check_timeout_trip(_id, trip_id))
        
        #创建后台任务
        merge_task = asyncio.create_task(
            handle_merge_task(_id,trip_id, is_last_chunk=metadata.get('is_last_chunk'))
        )
        background_tasks.append(merge_task)

        await cleanup_background_tasks()
        
        return JsonResponse({
            'code':200,
            'success': True, 
            'message': '分片上传成功',
            'data': {
                'trip_id': trip_id,
                'chunk_index': chunk_index,
                'file_type': file_type,
                'session_id': metadata.get('session_id')
            }
        })
    
    except Exception as e:
        logger.error(f"上传分片失败: {str(e)}")
        return JsonResponse({'code':500,'success': False, 'message': f'请求处理失败: {str(e)}', 'data':{}})

@csrf_exempt
@api_view(['POST'])
async def complete_upload(request):
    """完成上传，开始合并文件"""
    try:
        data = json.loads(request.body)
        trip_id = data.get('trip_id')
        total_chunks = data.get('total_chunks')  # 预期的分片总数
        force = data.get('force', False)  # 是否强制合并
        
        if not trip_id:
            return JsonResponse({'code':500,'success': False, 'message': '缺少trip_id参数', 'data':{}})
        
        # 检查分片完整性
        is_complete, missing_chunks = await check_chunks_complete(trip_id, total_chunks)
        
        if not is_complete and not force:
            return JsonResponse({
                'code':500,
                'success': False, 
                'message': '分片不完整',
                'data':{'missing_chunks': missing_chunks}
            })
        
        # 启动合并任务
        success, message = await force_merge_trip(trip_id)
        
        return JsonResponse({
            'code':200,
            'success': success, 
            'message': message,
            'data':{}
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'请求处理失败: {str(e)}','data':{}})

@api_view(['POST'])
async def check_chunks(request, trip_id):
    """检查分片状态"""
    try:
        total_chunks = request.GET.get('total_chunks')
        if total_chunks:
            total_chunks = int(total_chunks)
        
        is_complete, missing_chunks = await check_chunks_complete(trip_id, total_chunks)
        
        return JsonResponse({
            'success': True,
            'is_complete': is_complete,
            'data':{'missing_chunks': missing_chunks}
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'请求处理失败: {str(e)}','data':{}})
    
