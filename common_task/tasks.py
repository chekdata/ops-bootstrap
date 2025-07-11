# 设置protobuf兼容性
import os

####################################################################
# # NOTE: python 文件调试增加内容
# os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# # Django设置
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# # 添加项目根目录到Python路径
# import sys
# project_root = '/chekkk/code/chekappbackendnew'
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

# # 初始化Django
# import django
# from django.conf import settings as django_settings
# if not django_settings.configured:
#     django.setup()
######################################################################

import re
import pandas as pd
import logging
import asyncio
import time
import shutil
from pathlib import Path
from django.db import transaction, DatabaseError
from django.db.models import Q
from functools import partial
from django.db import connections
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from django.db import transaction
from asgiref.sync import sync_to_async, async_to_sync
from common_task.models import Trip, ChunkFile, Journey, Reported_Journey
from django.utils import timezone
from data.models import model_config
from accounts.models import CoreUser
from common_task.models import analysis_data_app,tos_csv_app,Journey,JourneyGPS,JourneyInterventionGps,HotBrandVehicle,JourneyRecordLongImg
from common_task.handle_tos import TinderOS
from common_task.handle_journey_message import *
from multiprocessing import Pool, cpu_count
from functools import partial
import pandas as pd
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from accounts.models import User,CoreUser
from common_task.db_utils import db_retry, ensure_connection
from common_task.chek_dataprocess.cloud_process_csv.saas_csv_process import process_journey, async_process_journey
from django.db import close_old_connections
from tmp_tools.monitor import *
from common_task.handle_chatgpt import get_chat_response
from tmp_tools.zip import package_files
from common_task.external_request import reports_successful_audio_generation
from django.db.models import Max, Min

# 创建进程池，数量为CPU核心数
process_pool = Pool(processes=cpu_count())


logger = logging.getLogger('common_task')


# 添加线程停止标志
cleanup_running = True
timeout_checker_running = True


# 创建线程池执行器
executor = ThreadPoolExecutor(max_workers=10)

MAX_WORKERS = min(multiprocessing.cpu_count(), 4)
# 创建进程池执行器
process_executor = ProcessPoolExecutor(max_workers=MAX_WORKERS)


# 用于管理所有后台任务的列表
background_tasks = []

def get_process_pool_stats():
    """
    获取进程池状态信息
    """
    if hasattr(process_executor, '_processes'):
        active_count = len(process_executor._processes)
        return {
            'active_processes': active_count,
            'max_workers': process_executor._max_workers,
            'available_workers': process_executor._max_workers - active_count
        }
    return None

async def save_chunk_file(trip_id, chunk_index, file_obj, file_type):
    """保存上传的分片文件（异步版本）"""
    try:
        # 获取或创建Trip
        trip, created = await sync_to_async(Trip.objects.get_or_create, thread_sensitive=True)(trip_id=trip_id)
        
        # 创建目录
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'chunks', str(trip_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(upload_dir, f"{chunk_index}.{file_type}")
        
        # 使用线程池处理文件IO操作
        def write_file():
            with open(file_path, 'wb+') as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)
        
        await asyncio.to_thread(write_file)
        
        # 记录到数据库
        await sync_to_async(ChunkFile.objects.update_or_create, thread_sensitive=True)(
            trip=trip,
            chunk_index=chunk_index,
            file_type=file_type,
            defaults={'file_path': file_path}
        )
        
        return True, "分片上传成功"
    except Exception as e:
        logger.error(f"保存分片文件失败: {e}")
        return False, f"保存分片文件失败: {str(e)}"

async def merge_files(user_id, trip_id):
    """合并文件的后台任务（异步版本）"""
    try:
        # 使用sync_to_async包装事务操作
        @sync_to_async(thread_sensitive=True)
        def _merge_files_sync():
            logger.info(f"开始合并文件, 用户ID: {user_id}, 行程ID: {trip_id}")
            with transaction.atomic():
                trip = Trip.objects.select_for_update().get(trip_id=trip_id)
                
                # 检查是否已经完成
                if trip.is_completed:
                    return True
                
                # 获取所有分片
                chunks = ChunkFile.objects.filter(trip=trip).order_by('chunk_index')
                
                # 合并CSV文件
                csv_chunks = chunks.filter(file_type='csv')
                if csv_chunks.exists():
                    merged_csv = pd.DataFrame()
                    for chunk in csv_chunks:
                        try:
                            df = pd.read_csv(chunk.file_path)
                            merged_csv = pd.concat([merged_csv, df])
                        except Exception as e:
                            logger.error(f"读取CSV分片失败 {chunk.chunk_index}: {e}")
                    
                    merged_csv_filename = None
                    for chunk in chunks:
                        if 'spcialPoint' in chunk.file_name:
                            merged_csv_filename = chunk.file_name.split('/')[-1]
                            break
                    if not merged_csv_filename:
                        merged_csv_filename = trip.file_name.split('/')[-1] if trip.file_name else f"merged_{trip_id}"

                    if not merged_csv.empty:
                        # 创建合并目录
                        merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip_id))
                        os.makedirs(merged_dir, exist_ok=True)
                        
                        # 保存合并文件
                        merged_path = os.path.join(merged_dir, merged_csv_filename)
                        merged_csv.to_csv(merged_path, index=False)
                        trip.merged_csv_path = merged_path

                        logger.info(f"合并CSV文件成功.保存到 {merged_path}")
                
                # 合并DET文件
                det_chunks = chunks.filter(file_type='det')
                if det_chunks.exists():
                    merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip_id))
                    os.makedirs(merged_dir, exist_ok=True)
                    
                    merged_det_filename = None
                    for chunk in det_chunks:
                        # logger.info(f"chunk.file_name: {chunk.file_name}")
                        if 'spcialPoint' in chunk.file_name:
                            merged_det_filename = chunk.file_name.split('/')[-1]
                            break
                    # NOTE: 非打点det文件重命名，取csv文件名，后缀改为det
                    if not merged_det_filename:
                        merged_det_filename = trip.file_name.split('/')[-1][:-4] + '.det' if trip.file_name else f"merged_{trip_id}"

                    det_merged_path = os.path.join(merged_dir, merged_det_filename)
                    with open(det_merged_path, 'wb') as outfile:
                        for chunk in det_chunks:
                            try:
                                with open(chunk.file_path, 'rb') as infile:
                                    outfile.write(infile.read())
                            except Exception as e:
                                logger.error(f"读取DET分片失败 {chunk.chunk_index}: {e}")
                    logging.info(f"合并DET文件成功.保存到 {det_merged_path}")

                    trip.merged_det_path = det_merged_path
                
                # 更新状态
                trip.is_completed = True
                trip.save()
                
                # 清理分片文件
                for chunk in chunks:
                    try:
                        if os.path.exists(chunk.file_path):
                            os.remove(chunk.file_path)
                        chunk.delete()
                    except Exception as e:
                        logger.error(f"清理分片文件失败 {chunk.chunk_index}: {e}")
                
                return trip.merged_csv_path, trip.merged_det_path
        
        # merged_csv_path, merged_det_path = await _merge_files_sync()
        # 执行异步操作     
        return await _merge_files_sync()
    except Exception as e:
        logger.error(f"合并文件失败: {e}")
        return None, None

async def start_merge_async(user_id,trip_id):
    """启动异步合并任务"""
    try:
        merged_csv_path, merged_det_path = await merge_files(user_id, trip_id)

        # 这里可以添加数据处理和上传TOS的逻辑
        if merged_csv_path:
            # 上传合并后的csv文件
            file_path = merged_csv_path
            await inference_file_upload_tos(user_id, file_path)

        if merged_det_path:
            # 上传合并后的csv文件
            file_path = merged_det_path
            await inference_file_upload_tos(user_id, file_path, file_type = 'det')

        logger.info(f"合并任务完成，结果: {merged_csv_path}, {merged_det_path}")
        return True
    except Exception as e:
        logger.error(f"用户:{user_id}, 行程: {trip_id}. 合并任务异常: {e}")
        return False

# NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
# 定期检查超时任务 并触发分组合并
async def check_timeout_trips_merge():
    """检查超时的上传任务并触发合并（异步版本）"""
    from django.utils import timezone
    from datetime import timedelta
    
    global timeout_checker_running

    time_interval_thre = 300
    while timeout_checker_running:
        try:
            # 查找所有未完成且超过5分钟未更新的Trip
            timeout = timezone.now() - timedelta(minutes=5)
            
            # 使用正确的异步查询方法组合
            # 查找所有还未进行合并的行程
            trips = await sync_to_async(list, thread_sensitive=True)(
                Trip.objects.filter(
                    is_completed=False, 
                ).values('trip_id', 'user_id', 
                         'car_name', 'device_id', 
                         'hardware_version', 
                         'software_version', 
                         'first_update',
                         'last_update')  # 只获取trip_id字段
            )

            if not trips:
                logger.info("没有找到超时的行程")
            else:
                logger.info(f"找到 {len(trips)} 个超时行程")
                # 按照相同特征分组
                trip_groups = {}
                for trip in trips:
                    # 创建分组键
                    group_key = (
                        trip['user_id'],
                        trip['car_name'],
                        trip['device_id'],
                        trip['hardware_version'],
                        trip['software_version']
                    )       

                    # 将行程添加到对应的组
                    if group_key not in trip_groups:
                        trip_groups[group_key] = []
                    trip_groups[group_key].append(trip)                
                        
                    
            
                # 为每个超时的Trip创建合并任务
                tasks = []
                for group_key, group_trips in trip_groups.items():
                    user_id, car_name, device_id, hw_version, sw_version = group_key
                    
                    # 按最后更新时间排序
                    sorted_trips = sorted(group_trips, key=lambda x: x['last_update'])
                    
                    # 找出每个与下一个行程间隔大于5分钟的行程
                    trips_to_merge = []
                    for i in range(len(sorted_trips) - 1):
                        current_trip = sorted_trips[i]
                        next_trip = sorted_trips[i + 1]
                        
                        # 计算当前行程与下一个行程的时间间隔（秒）
                        time_diff = (next_trip['first_update'] - current_trip['last_update']).total_seconds()
                        
                        # 找到时间间隔大于5分钟的行程，且最后一个行程和当前时间间隔5分钟以上
                        if time_diff > time_interval_thre and current_trip['last_update'] < timeout:  # 5分钟 = 300秒
                            # 如果间隔大于5分钟，则当前行程是一个需要合并的行程
                            trips_to_merge.append(current_trip)
                            logger.info(f"找到间隔大于5分钟的行程: 用户ID {user_id}, 设备ID {device_id}, "
                                       f"行程ID {current_trip['trip_id']}, 与下一行程间隔: {time_diff}秒")
                    
                    # 最后一个行程也需要检查是否超时
                    if sorted_trips and sorted_trips[-1]['last_update'] < timeout:
                        trips_to_merge.append(sorted_trips[-1])
                        logger.info(f"添加最后一个超时行程: 用户ID {user_id}, 设备ID {device_id}, "
                                   f"行程ID {sorted_trips[-1]['trip_id']}, 最后更新时间: {sorted_trips[-1]['last_update']}")
                    
                    # 为每个需要合并的行程创建任务
                    for trip_to_merge in trips_to_merge:
                        task = asyncio.create_task(
                            handle_merge_task(
                                user_id, 
                                trip_to_merge['trip_id'], 
                                is_last_chunk=True,  # 模拟最后一个分片
                                is_timeout=True,    # 标记为超时
                            )
                        )
                        tasks.append(task)
                
                # 等待所有任务完成
                if tasks:
                    logger.info(f"开始执行 {len(tasks)} 个合并任务")
                    await asyncio.gather(*tasks)
                else:
                    logger.info("没有找到需要合并的行程")
            
        except Exception as e:
            logger.error(f"超时检查失败: {str(e)}")
            await asyncio.sleep(60)  # 发生错误时等待1分钟再重试
            continue
        
        # 每5分钟检查一次
        for _ in range(18):  # 分成18次等待，便于及时响应停止信号
            if not timeout_checker_running:
                break
            await asyncio.sleep(10)



# 定期检查超时任务 并触发trip_id落库
async def check_timeout_trips():
    """检查超时的上传任务并触发合并（异步版本）"""
    from django.utils import timezone
    from datetime import timedelta
    
    global timeout_checker_running


    while timeout_checker_running:
        try:
            # 查找所有未完成且超过2分钟未更新的Trip
            # 设置2min时间阈值，对于没有新分片更新行程，判定为异常结束
            timeout = timezone.now() - timedelta(minutes=2)
            
            # 使用正确的异步查询方法组合
            # 查找所有还未进行合并的行程
            trips = await sync_to_async(list, thread_sensitive=True)(
                Trip.objects.filter(
                    is_completed=False, 
                    set_journey_status=False,
                    last_update__lt=timeout,
                ).values('trip_id', 'user_id', 
                         'car_name', 'device_id', 
                         'hardware_version', 
                         'software_version', 
                         'first_update',
                         'last_update')  # 只获取trip_id字段
            )

            for trip in trips:
                await ensure_db_connection_and_set_journey_status(trip_id=trip['trip_id'], status="异常退出待确认")

            if not trips:
                logger.info("没有找到异常结束超时的行程")
            else:
                logger.info(f"找到 {len(trips)} 个超时行程")
                # 按照相同特征分组
                trip_groups = {}
                for trip in trips:
                    # NOTE: 直接对数据进行落行程库
                    k = 0
            
        except Exception as e:
            logger.error(f"超时检查失败: {str(e)}")
            await asyncio.sleep(60)  # 发生错误时等待1分钟再重试
            continue
        
        # 每5分钟检查一次
        for _ in range(18):  # 分成18次等待，便于及时响应停止信号
            if not timeout_checker_running:
                break
            await asyncio.sleep(10)


def start_timeout_checker():
    """启动超时检查器"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        global timeout_checker_running
        timeout_checker_running = True
        
        try:
            loop.run_until_complete(check_timeout_trips())
        except Exception as e:
            logger.error(f"超时检查器运行异常: {e}")
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"启动超时检查器失败: {e}")


async def check_chunks_complete(trip_id, expected_total=None):
    """
    检查分片是否完整（异步版本）
    
    参数:
    - trip_id: 行程ID
    - expected_total: 预期的分片总数，如果为None则不检查总数
    
    返回:
    - is_complete: 是否完整
    - missing_chunks: 缺失的分片索引列表
    """
    try:
        # 获取Trip对象
        trip = await sync_to_async(Trip.objects.get, thread_sensitive=True)(trip_id=trip_id)
        
        # 获取已上传的分片
        csv_chunks = await sync_to_async(list, thread_sensitive=True)(
            ChunkFile.objects.filter(trip=trip, file_type='csv').values_list('chunk_index', flat=True)
        )
        
        det_chunks = await sync_to_async(list, thread_sensitive=True)(
            ChunkFile.objects.filter(trip=trip, file_type='det').values_list('chunk_index', flat=True)
        )
        
        # 如果没有预期总数，则假设已完成
        if expected_total is None:
            return True, []
        
        # 检查CSV分片
        csv_missing = []
        if csv_chunks:
            max_csv = max(csv_chunks) if csv_chunks else -1
            for i in range(max_csv + 1):
                if i not in csv_chunks:
                    csv_missing.append(i)
        
        # 检查DET分片
        det_missing = []
        if det_chunks:
            max_det = max(det_chunks) if det_chunks else -1
            for i in range(max_det + 1):
                if i not in det_chunks:
                    det_missing.append(i)
        
        # 合并缺失列表
        missing_chunks = list(set(csv_missing + det_missing))
        
        # 判断是否完整
        is_complete = len(missing_chunks) == 0
        
        return is_complete, missing_chunks
    
    except Exception as e:
        logger.error(f"检查分片完整性失败: {e}")
        return False, []

async def check_timeout_trip(user_id,trip_id):
    """检查单个行程是否超时（异步版本）"""
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # 获取Trip对象
        trip = await sync_to_async(Trip.objects.get, thread_sensitive=True)(trip_id=trip_id)
        
        # 检查是否已经完成
        if trip.is_completed:
            return
        
        # 检查是否超时
        if timezone.now() - trip.last_update > timedelta(minutes=30):
            logger.info(f"Trip {trip_id} 上传超时，开始异步合并")
            await start_merge_async(user_id,trip_id)
    except Exception as e:
        logger.error(f"检查行程超时失败: {e}")

# 使用对应的时区
from django.conf import settings
from django.utils import timezone

def get_current_timezone_time():
    """获取当前时区的时间"""
    try:
        # # 使用系统设置的时区，并确保应用上海时区
        # from django.utils.timezone import localtime, now
        # from pytz import timezone as pytz_timezone
        
        # # 直接使用上海时区
        # shanghai_tz = pytz_timezone('Asia/Shanghai')
        # return now().astimezone(shanghai_tz)

        return datetime.now() 

    except Exception as e:
        logger.error(f"获取时区时间失败: {e}")
        # 如果失败则返回 UTC 时间
        return timezone.now()

async def upload_chunk_file(user_id, trip_id, chunk_index, file_obj, file_type, metadata=None):
    """
    上传分片文件（异步版本）
    
    参数:
    - trip_id: 行程ID
    - chunk_index: 分片索引
    - file_obj: 文件对象
    - file_type: 文件类型（csv或det）
    - metadata: 元数据字典
    
    返回:
    - success: 是否成功
    - message: 消息
    - chunk_file: 创建的ChunkFile对象
    """
    try:
        # 获取或创建Trip
        defaults = {
            'is_completed': False,
            'last_update': get_current_timezone_time()  # 使用时区时间
        }
        # 添加元数据
        if metadata:
            # if 'device_id' in metadata:
            #     defaults['device_id'] = metadata['device_id']
            if 'car_name' in metadata:
                defaults['car_name'] = metadata['car_name']
            # if 'start_time' in metadata:
            #     defaults['start_time'] = metadata['start_time']
            # if 'total_chunks' in metadata:
            #     defaults['total_chunks'] = metadata['total_chunks']
            if 'file_name' in metadata:
                defaults['file_name'] = metadata['file_name']
            if 'hardware_version' in metadata:
                defaults['hardware_version'] = metadata['hardware_version']
            if 'software_version' in metadata:
                defaults['software_version'] = metadata['software_version']
            if 'device_id' in metadata:
                defaults['device_id'] = metadata['device_id']
            # if 'trip_status' in metadata:
            #     defaults['trip_status'] = metadata['trip_status']

        # 增加音频和长图信息落库
        journey_record_longImg_exists = await sync_to_async(JourneyRecordLongImg.objects.using("core_user").filter(journey_id=trip_id).exists, thread_sensitive=True)()

        if not journey_record_longImg_exists:
            keys_to_copy = ['car_name', 'file_name', 'hardware_version', 'software_version', 'device_id']
            journey_record_longImg_defaults = {key: defaults[key] for key in keys_to_copy}
            journey_record_longImg, created = await sync_to_async(JourneyRecordLongImg.objects.using("core_user").get_or_create, thread_sensitive=True)(
                            user_id = user_id,
                            journey_id=trip_id,
                            record_upload_tos_status = settings.RECORD_UPLOAD_TOS_ING, 
                            defaults=journey_record_longImg_defaults
                        )
            logger.info(f"=============创建新行程音频长图记录: {trip_id}====================")

        # 当第一次写入时，写入first_update
        trip_exists = await sync_to_async(Trip.objects.filter(trip_id=trip_id).exists, thread_sensitive=True)()
        if not trip_exists:
            defaults['first_update'] = get_current_timezone_time()  # 使用时区时间
            logger.info(f"创建新行程记录: {trip_id}, 设置首次更新时间: {defaults['first_update']}")
        else:
            # 如果记录已存在，确保不更新first_update字段
            if 'first_update' in defaults:
                del defaults['first_update']
                logger.debug(f"行程记录 {trip_id} 已存在，不更新首次更新时间")

        trip, created = await sync_to_async(Trip.objects.get_or_create, thread_sensitive=True)(
            user_id = user_id,
            trip_id=trip_id, 
            defaults=defaults
        )

        if metadata:
            update_fields = {}

             # 检查 trip_status
            if 'trip_status' in metadata:
                update_fields['trip_status'] = metadata['trip_status']

            # 检查 reported_car_name
            if 'reported_car_name' in metadata:
                update_fields['reported_car_name'] = metadata['reported_car_name']
            
            # 检查 reported_hardware_version
            if 'reported_hardware_version' in metadata:
                update_fields['reported_hardware_version'] = metadata['reported_hardware_version']
            
            # 检查 reported_software_version
            if 'reported_software_version' in metadata:
                update_fields['reported_software_version'] = metadata['reported_software_version']
            
            # 如果有需要更新的字段，执行更新
            if update_fields:
                trip.trip_status = update_fields['trip_status']
                trip.reported_car_name = update_fields['reported_car_name']
                trip.reported_hardware_version = update_fields['reported_hardware_version']
                trip.reported_software_version = update_fields['reported_software_version']
                logger.info(f"条件更新 Trip {trip_id} 的字段: {[f'{key}={update_fields[key]}' for key in update_fields.keys()]}")

        
        # 创建目录
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'chunks', str(trip_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(upload_dir, f"{chunk_index}.{file_type}")
        
        # 使用线程池处理文件IO操作
        def write_file():
            with open(file_path, 'wb+') as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)
        
        await asyncio.to_thread(write_file)
        
        # 记录到数据库
        chunk_defaults = {
            'file_path': file_path,
            'upload_time': timezone.now()
        }
        
        # 添加元数据
        if metadata:
            # if 'start_time' in metadata:
            #     chunk_defaults['start_time'] = metadata['start_time']
            # if 'end_time' in metadata:
            #     chunk_defaults['end_time'] = metadata['end_time']
            # if 'checksum' in metadata:
            #     chunk_defaults['checksum'] = metadata['checksum']
            if 'file_name' in metadata:
                chunk_defaults['file_name'] = metadata['file_name']

            if 'car_name' in metadata:
                chunk_defaults['car_name'] = metadata['car_name']

            if 'hardware_version' in metadata:
                chunk_defaults['hardware_version'] = metadata['hardware_version']
            if 'software_version' in metadata:
                chunk_defaults['software_version'] = metadata['software_version']
            if 'device_id' in metadata:
                chunk_defaults['device_id'] = metadata['device_id']

        
        chunk_file, created = await sync_to_async(ChunkFile.objects.update_or_create, thread_sensitive=True)(
            trip=trip,
            chunk_index=chunk_index,
            file_type=file_type,
            defaults=chunk_defaults
        )
        
        # 更新Trip的最后更新时间
        trip.last_update = timezone.now()
        await sync_to_async(trip.save, thread_sensitive=True)()
        await sync_to_async(close_old_connections)()
        return True, "分片上传成功", chunk_file
    except Exception as e:
        logger.error(f"保存分片文件失败: {e}")
        return False, f"保存分片文件失败: {str(e)}", None

async def force_merge_trip(trip_id):
    """
    强制合并行程（异步版本）
    
    参数:
    - trip_id: 行程ID
    
    返回:
    - success: 是否成功
    - message: 消息
    """
    try:
        # 获取Trip对象
        trip = await sync_to_async(Trip.objects.get, thread_sensitive=True)(trip_id=trip_id)
        
        # 开始合并
        result = await start_merge_async(trip.user_id, trip_id)
        
        if result:
            return True, "行程合并成功"
        else:
            return False, "行程合并失败"
    except Exception as e:
        logger.error(f"强制合并行程失败: {e}")
        return False, f"强制合并行程失败: {str(e)}"

# 准备上传tos路径
async def prepare_upload_tos_file_path(_id,status_tag,file_name):
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
    
# 上传文件
async def inference_file_upload_tos(_id, file_path, file_type = 'csv'):
    try:
        file_name = Path(file_path)
        # 保存文件
        upload_file_path = await prepare_upload_tos_file_path(_id, 'inference_data', file_name)

        # 保存文件
        tinder_os = TinderOS()
        tinder_os.upload_file('chek',upload_file_path , file_path)
        # os.remove(file_url)

        data_tos_model, creat = await sync_to_async(tos_csv_app.objects.get_or_create, thread_sensitive=True)(
            user_id=_id,
            tos_file_path=upload_file_path,
            tos_file_type='inference'
        )
        data_tos_model.user_id = _id

        data_tos_model.tos_file_path =upload_file_path
        data_tos_model.tos_file_type = 'inference'
        # data_tos_model.save()
        await sync_to_async(data_tos_model.save, thread_sensitive=True)()
        logger.info(f"inference_file_upload_tos upload path : {upload_file_path}")
    except Exception as e:
        logger.error(f"inference_file_upload_tos error: {e}")



async def cleanup_background_tasks():
    """
    清理已完成的后台任务
    """

    global background_tasks
    active_tasks = []
    for task in background_tasks:
        if task.done():
            try:
                if task.exception():
                    logger.error(f"后台任务执行失败: {task.exception()}")
                await task
            except Exception as e:
                logger.error(f"清理后台任务失败: {e}")
        else:
            active_tasks.append(task)
    background_tasks = active_tasks
    logger.info(f"清理后台任务完成，剩余任务数量: {len(background_tasks)}")

async def periodic_cleanup():
    """
    定期清理后台任务
    """
    global cleanup_running
    logger.info("定期清理任务开始运行")
    while cleanup_running:
        start_time = time.time()
        try:

            # 使用列表推导式一次性更新任务列表
            global background_tasks

            # start_time = time.time()
            # 获取当前任务数
            total_tasks = len(background_tasks)

            current_tasks = background_tasks[:]
            background_tasks = [t for t in current_tasks if not t.done()]

            # 处理已完成的任务
            done_tasks = [t for t in current_tasks if t.done()]
            error_count = 0

            for task in done_tasks:
                try:
                    if task.exception():
                        error_count += 1
                        logger.error(f"后台任务异常: {task.exception()}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"获取任务异常失败: {e}")                    
            
            if done_tasks or total_tasks > 0:
                #  logger.info(f"定期清理后台任务完成. 清理了{len(done_tasks)} 个已完成任务，当前剩余任务数: {len(background_tasks)} 个任务")
                logger.info(
                    f"清理任务执行完成:\n"
                    f"- 原有任务数: {total_tasks}\n"
                    f"- 清理任务数: {len(done_tasks)}\n"
                    f"- 错误任务数: {error_count}\n"
                    f"- 剩余任务数: {len(background_tasks)}\n"
                    f"- 耗时: {time.time() - start_time:.2f}秒"
                )
           
        except Exception as e:
            logger.error(f"定期清理任务失败: {e}")
            if not cleanup_running:
                break

        finally:
            # 计算需要等待的时间，确保每分钟执行一次
            elapsed = time.time() - start_time
            wait_time = max(60 - elapsed, 0)  # 确保等待时间不为负
            logger.debug(f"清理任务等待 {wait_time:.1f} 秒后继续执行")
            # 分段等待，便于及时响应停止信号
            for _ in range(int(wait_time)):
                if not cleanup_running:
                    break
                await asyncio.sleep(1)
            # await asyncio.sleep(wait_time)
        # await asyncio.sleep(60) # 每10分钟清理一次

def start_background_cleanup():
    """
    启动定期清理任务
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        cleanup_task = loop.create_task(periodic_cleanup())
        def cleanup_done(future):
            try:
                result = future.result()
                logger.info("清理任务完成")
            except Exception as e:
                logger.error(f"清理任务异常： {e}")
        cleanup_task.add_done_callback(cleanup_done)

        logger.info("定期清理任务启动成功")
        try:
            loop.run_forever()
        except Exception as e:
            logger.error(f"定期清理任务时间循环运行异常: {e}")
        finally:
            try:
                loop.stop()
                loop.close()
                logger.info("定期清理任务时间循环关闭成功")
            except Exception as e:
                logger.error(f"定期清理任务时间循环关闭失败: {e}")
    except Exception as e:
        logger.error(f"启动定期清理任务失败: {e}")


# 使用线程启动异步循环
import threading


async def cleanup_resources():
    """清理所有资源"""
    global process_executor, executor, background_tasks
    try:
        logger.info("开始清理资源...")
        

        # 1. 等待线程完全停止
        try:
            from django.apps import apps
            app_config = apps.get_app_config('common_task')
            
            if hasattr(app_config, 'cleanup_thread'):
                if app_config.cleanup_thread.is_alive():
                    logger.info("等待清理线程结束...")
                    app_config.cleanup_thread.join(timeout=2)
                    
            if hasattr(app_config, 'timeout_thread'):
                if app_config.timeout_thread.is_alive():
                    logger.info("等待超时检查线程结束...")
                    app_config.timeout_thread.join(timeout=2)
        except Exception as e:
            logger.error(f"等待线程结束失败: {e}")

        # 2. 清理进程池
        try:
            if process_executor:
                process_executor.shutdown(wait=True)
                logger.info("进程池已关闭")
        except Exception as e:
            logger.error(f"关闭进程池失败: {e}")

        # 23. 清理线程池
        try:
            if executor:
                executor.shutdown(wait=True)
                logger.info("线程池已关闭")
        except Exception as e:
            logger.error(f"关闭线程池失败: {e}")

        # 3. 清理后台任务
        try:
            await cleanup_background_tasks()
            logger.info("后台任务已清理")
        except Exception as e:
            logger.error(f"清理后台任务失败: {e}")

        # # 4. 清理临时文件
        # try:
        #     temp_dirs = ['chunks', 'merged']
        #     for dir_name in temp_dirs:
        #         dir_path = os.path.join(settings.MEDIA_ROOT, dir_name)
        #         if os.path.exists(dir_path):
        #             import shutil
        #             shutil.rmtree(dir_path)
        #             logger.info(f"临时目录已清理: {dir_path}")
        # except Exception as e:
        #     logger.error(f"清理临时文件失败: {e}")

        # # 5. 重置全局变量
        # try:
        #     global background_tasks
        #     background_tasks = []
        #     logger.info("全局变量已重置")
        # except Exception as e:
        #     logger.error(f"重置全局变量失败: {e}")

        logger.info("所有资源清理完成")
        
    except Exception as e:
        logger.error(f"清理资源时发生错误: {e}")
    finally:
        # 确保所有资源引用被释放
        process_executor = None
        executor = None
        background_tasks = []


# # NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
# def merge_files_sync(user_id, trip_id, is_timeout=False):
#     """同步版本的合并文件函数，用于进程池执行"""
#     normal_trip_status = "正常"
#     time_interval_thre = 300
#     try:
#         logger.info(f"开始合并文件, 用户ID: {user_id}, 行程ID: {trip_id}")
#         with transaction.atomic():
#             # trip = Trip.objects.select_for_update().get(trip_id=trip_id)
            
#             try:
#                 main_trip = Trip.objects.select_for_update(nowait=True).get(trip_id=trip_id)

#                 # 检查是否正在合并或已完成
#                 if main_trip.is_completed:
#                     logger.info(f"行程 {main_trip.trip_id} 已完成合并，跳过处理")
#                     return None, None
                
#                 if getattr(main_trip, 'is_merging', False):
#                     logger.info(f"行程 {main_trip.trip_id} 正在合并中，跳过处理")
#                     return None, None
                

#             except DatabaseError:
#                 logger.info(f"行程 {main_trip.trip_id} 正在被其他进程处理，跳过")
#                 return None, None

#             logger.info(f"用户ID: {user_id}, 行程ID: {main_trip.trip_id} 未完成合并，开始进行合并处理！")
#             # 找到所有和trip相同的carname hardware_version software_version device_id相同的trip,确保数据不会在进程间产生竞争
#             try:
#                 # # 正常退出
#                 # if not is_timeout:
#                 #     # 首先获取所有符合基本条件的行程，按照last_update排序（降序，从新到旧）
#                 #     all_similar_trips = Trip.objects.filter(
#                 #         is_completed=False,
#                 #         user_id=user_id,
#                 #         device_id=main_trip.device_id,
#                 #         car_name=main_trip.car_name,
#                 #         hardware_version=main_trip.hardware_version,
#                 #         software_version=main_trip.software_version,
#                 #         merge_into_current=True,
#                 #         trip_status = main_trip.trip_status,
#                 #     ).order_by('-last_update')  # 降序排列，从最新到最旧
#                 # else:
#                 #     # 首先获取所有符合基本条件的行程，按照last_update排序（降序，从新到旧）
#                 #     # 超时行程不处理merge_into_current
#                 #     # 超时行程(异常行程)只合并自己的行程
#                 #     all_similar_trips = Trip.objects.filter(
#                 #         trip_id=trip_id,
#                 #         is_completed=False,
#                 #         user_id=user_id,
#                 #         device_id=main_trip.device_id,
#                 #         car_name=main_trip.car_name,
#                 #         hardware_version=main_trip.hardware_version,
#                 #         software_version=main_trip.software_version,
#                 #         merge_into_current=True,
#                 #         trip_status = main_trip.trip_status,
#                 #     ).order_by('-last_update')  # 降序排列，从最新到最旧     

#                 # # 正常退出
#                 # 首先获取所有符合基本条件的行程，按照last_update排序（降序，从新到旧）
#                 all_similar_trips = Trip.objects.filter(
#                     is_completed=False,
#                     user_id=user_id,
#                     device_id=main_trip.device_id,
#                     car_name=main_trip.car_name,
#                     hardware_version=main_trip.hardware_version,
#                     software_version=main_trip.software_version,
#                     merge_into_current=True,
#                     trip_status = main_trip.trip_status,
#                 ).order_by('-last_update')  # 降序排列，从最新到最旧

#                 # 筛选出需要合并的行程
#                 trips_to_merge = []
#                 prev_trip = None

#                 for trip in all_similar_trips:
#                     if not prev_trip:  # 第一个行程（最新的行程）
#                         trips_to_merge.append(trip)
#                         prev_trip = trip
#                         continue
                    
#                     # 计算当前行程与前一个行程的时间间隔（秒）
#                     # 注意：由于是降序排列，所以是prev_trip.first_update - trip.last_update
#                     time_diff = (prev_trip.first_update - trip.last_update).total_seconds()

#                     # 正常退出
#                     # if not is_timeout:                    
#                     #     if time_diff <= time_interval_thre:  # 5分钟 = 300秒
#                     #         # 如果间隔小于等于5分钟，则添加到合并行程列表
#                     #         trips_to_merge.append(trip)
#                     #         prev_trip = trip
#                     #     else:
#                     #         # 找到了间隔超过5分钟的行程，停止查找
#                     #         logger.info(f"找到间隔超过5分钟的行程，停止查找。行程ID: {trip.trip_id}, 时间间隔: {time_diff}秒")
#                     #         break
#                     # else:
#                     #         # 如果正常退出，选择所有之前没处理的数据进行合并，不区分间隔小于等于5分钟，则添加到合并行程列表
#                     #         trips_to_merge.append(trip)

#                     # NOTE: 无论是异常行程单独合并还是正常行程合并上一次异常行程
#                     # 最多只有两个行程合并，因为app在每一次跑分前必须让行程上一次异常行程合并
#                     # 所以这里当前行程合并上一次行程不用考虑时间间隔
#                     trips_to_merge.append(trip)

#                 # 按照时间升序排序（从旧到新），便于处理
#                 trips_to_merge.sort(key=lambda x: x.last_update)

#                 logger.info(f"找到 {len(trips_to_merge)} 个需要合并的行程，时间范围: {trips_to_merge[0].first_update} 到 {trips_to_merge[-1].last_update}")
#                 trips = trips_to_merge


#                 # 记录锁定的行程数量
#                 trips_count = len(trips) if isinstance(trips, list) else trips.count()
#                 logger.info(f"已锁定 {trips_count} 个相关行程记录")

#                 csv_merged_results = []
#                 det_merged_results = []

#                 for trip in trips:
#                     try:
#                         # 检查是否正在合并或生成
#                         if trip.is_completed:
#                             logger.info(f"行程 {trip.trip_id} 已完成合并，跳过处理")
#                             continue
                        
#                         if getattr(trip, 'is_merging', False):
#                             logger.info(f"行程 {trip.trip_id} 正在合并中，跳过处理")
#                             continue
                        
#                         logger.info(f"行程 {trip.trip_id} 马上开始合并处理！")
#                         # 标记正在合并
#                         trip.is_merging = True
#                         # trip.save()
#                         trip.save(update_fields=['is_merging'])


#                         logger.info(f"用户Id {user_id}, 行程 {trip.trip_id}  正在合并中...")
#                         # 获取所有分片
#                         chunks = ChunkFile.objects.filter(trip=trip).order_by('chunk_index')
#                         merged_results = {'csv': None, 'det': None}

#                         # 合并CSV文件
#                         csv_chunks = chunks.filter(file_type='csv')
                        
#                         logger.info(f"行程 {trip.trip_id} CSV分片数量: {csv_chunks.count()} !")
#                         if csv_chunks.exists():
#                             # 统计csv_chunks数量
#                             trip.csv_chunk_count = csv_chunks.count()
#                             logger.info(f"行程 {trip.trip_id} CSV分片数量: {csv_chunks.count()} !")
#                             csv_indexes = list(csv_chunks.values_list('chunk_index', flat=True))
#                             if csv_indexes:
#                                 min_index = min(csv_indexes)
#                                 max_index = max(csv_indexes)
#                                 # 生成完整的索引集合
#                                 full_indexes = set(range(min_index, max_index + 1))
#                                 # 找出缺失的索引
#                                 missing_indexes = full_indexes - set(csv_indexes)
#                                 missing_count = len(missing_indexes)
#                             else:
#                                 missing_count = 0
#                             trip.csv_chunk_lose = missing_count
#                             logger.info(f"行程 {trip.trip_id} 中间缺少CSV分片数量: {missing_count}")
#                             update_fields = ['csv_chunk_count']
#                             update_fields.append('csv_chunk_lose')
#                             trip.save(update_fields=update_fields)

#                             merged_csv = pd.DataFrame()
#                             for chunk in csv_chunks:
#                                 try:
#                                     df = pd.read_csv(chunk.file_path)
#                                     merged_csv = pd.concat([merged_csv, df])
#                                 except Exception as e:
#                                     logger.error(f"读取CSV分片失败 {chunk.chunk_index}: {e}")

#                             if not merged_csv.empty:
#                                 # 处理文件名
#                                 merged_csv_filename = None
#                                 for chunk in csv_chunks:
#                                     if hasattr(chunk, 'file_name') and chunk.file_name and 'spcialPoint' in chunk.file_name:
#                                         merged_csv_filename = chunk.file_name.split('/')[-1]
#                                         break
#                                 if not merged_csv_filename:
#                                     merged_csv_filename = trip.file_name.split('/')[-1] if trip.file_name else f"merged_{trip.trip_id}.csv"

#                                 # 创建合并目录
#                                 merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip.trip_id))
#                                 os.makedirs(merged_dir, exist_ok=True)

#                                 # 保存合并文件
#                                 merged_path = os.path.join(merged_dir, merged_csv_filename)
#                                 merged_csv.to_csv(merged_path, index=False)
#                                 trip.merged_csv_path = merged_path
#                                 merged_results['csv'] = merged_path
#                                 logger.info(f"合并CSV文件成功.保存到 {merged_path}")

#                         # 合并DET文件
#                         det_chunks = chunks.filter(file_type='det')
#                         logger.info(f"行程 {trip.trip_id} DET分片数量: {det_chunks.count()} !")
#                         if det_chunks.exists():

#                             # 统计csv_chunks数量
#                             trip.det_chunk_count = det_chunks.count()
#                             logger.info(f"行程 {trip.trip_id} DET分片数量: {det_chunks.count()} !")
#                             det_indexes = list(det_chunks.values_list('chunk_index', flat=True))
#                             if det_indexes:
#                                 min_index = min(det_indexes)
#                                 max_index = max(det_indexes)
#                                 # 生成完整的索引集合
#                                 full_indexes = set(range(min_index, max_index + 1))
#                                 # 找出缺失的索引
#                                 missing_indexes = full_indexes - set(det_indexes)
#                                 missing_count = len(missing_indexes)
#                             else:
#                                 missing_count = 0
#                             trip.det_chunk_lose = missing_count
#                             logger.info(f"行程 {trip.trip_id} 中间缺少det分片数量: {missing_count}")
#                             update_fields = ['det_chunk_count']
#                             update_fields.append('det_chunk_lose')
#                             trip.save(update_fields=update_fields)


#                             merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip.trip_id))
#                             os.makedirs(merged_dir, exist_ok=True)

#                             # 处理文件名
#                             merged_det_filename = None
#                             for chunk in det_chunks:
#                                 if hasattr(chunk, 'file_name') and chunk.file_name and 'spcialPoint' in chunk.file_name:
#                                     merged_det_filename = chunk.file_name.split('/')[-1]
#                                     break
#                             if not merged_det_filename:
#                                 merged_det_filename = trip.file_name.split('/')[-1][:-4] + '.det' if trip.file_name else f"merged_{trip.trip_id}.det"

#                             det_merged_path = os.path.join(merged_dir, merged_det_filename)
#                             with open(det_merged_path, 'wb') as outfile:
#                                 for chunk in det_chunks:
#                                     try:
#                                         with open(chunk.file_path, 'rb') as infile:
#                                             outfile.write(infile.read())
#                                     except Exception as e:
#                                         logger.error(f"读取DET分片失败 {chunk.chunk_index}: {e}")

#                             trip.merged_det_path = det_merged_path
#                             merged_results['det'] = det_merged_path
#                             logger.info(f"合并DET文件成功.保存到 {det_merged_path}")

#                         if merged_results['csv'] is not None and Path(merged_results['csv']).exists():
#                             csv_merged_results.append(merged_results['csv'])
#                         if merged_results['det'] is not None and Path(merged_results['det']).exists():
#                             det_merged_results.append(merged_results['det'])


#                         chunks = ChunkFile.objects.filter(trip=trip).order_by('chunk_index')
#                         trip_chunk_dir = ''
#                         if chunks:
#                             # 分片文件夹路径
#                             trip_chunk_dir = os.path.dirname(chunks[0].file_path)
#                             logger.info(f"行程 {trip.trip_id} 的分片文件夹: {trip_chunk_dir}")

#                         # 清理分片文件
#                         for chunk in chunks:
#                             try:
#                                 if os.path.exists(chunk.file_path):
#                                     os.remove(chunk.file_path)
#                                 chunk.delete()
#                             except Exception as e:
#                                 logger.error(f"清理分片文件失败 {chunk.chunk_index}: {e}")
#                         # 清理分片文件夹
#                         if os.path.exists(trip_chunk_dir):
#                             try:
#                                 shutil.rmtree(trip_chunk_dir)
#                                 logger.info(f"清理行程 {trip.trip_id} 的分片文件夹: {trip_chunk_dir}")
#                             except Exception as e:
#                                 logger.error(f"清理行程 {trip.trip_id} 的分片文件夹失败: {e}")
#                         logger.info(f"完成清理行程 {trip.trip_id} 的分片文件")


#                         try:
#                             # 更新状态
#                             trip.refresh_from_db()
#                             if not trip.is_completed:
#                                 trip.is_completed = True
#                                 trip.is_merging = False
#                                 # trip.save()
#                                 update_fields = ['is_merging']
#                                 update_fields.append('is_completed')
#                                 if merged_results['csv']:
#                                     trip.merged_csv_path = merged_results['csv']
#                                     update_fields.append('merged_csv_path')
#                                 if merged_results['det']:
#                                     trip.merged_det_path = merged_results['det']
#                                     update_fields.append('merged_det_path')

#                                 trip.save(update_fields=update_fields)

#                                 logger.info(
#                                     f"行程 {trip_id} 更新完成:\n"
#                                     f"- 完成状态: {trip.is_completed}\n"
#                                     f"- 合并状态: {trip.is_merging}\n"
#                                     f"- CSV路径: {trip.merged_csv_path}\n"
#                                     f"- DET路径: {trip.merged_det_path}"
#                                 )
#                         except Exception as e:
#                             logger.error(f"更新行程状态失败: {e}",exc_info=True)
#                             # 发生错误时回滚事务
#                             transaction.set_rollback(True)
                        
#                         # 更新行程的状态，对于已合并行程
#                         try:
#                             if str(trip.trip_id) != trip_id:
#                                 # 设置非主行程为子行程
#                                 ensure_db_connection_and_set_sub_journey_sync(trip.trip_id)
#                         except Exception as e:
#                             logger.error(f"设置行程为子行程失败: {e}")

#                     except Exception as e:
#                         # 发生错误时重置合并状态
#                         trip.is_merging = False
#                         trip.save()
#                         logger.error(f"合并文件失败: {e}")
#                         return None, None

#                 return csv_merged_results, det_merged_results

#             except DatabaseError as e:
#                 # 如果无法获取锁（其他进程正在处理），记录并跳过
#                 logger.warning(f"无法锁定相关行程记录，可能有其他进程正在处理: {e}")
#                 # 可以选择稍后重试或跳过
#                 return None, None
            
#     except Exception as e:
#         logger.error(f"合并文件失败: {e}")
#         return None, None


# 调整数据库访问atomic使用时机
def merge_files_sync(user_id, trip_id, is_timeout=False):
    """同步版本的合并文件函数，用于进程池执行"""
    normal_trip_status = "正常"
    time_interval_thre = 300
    try:
        logger.info(f"开始合并文件, 用户ID: {user_id}, 行程ID: {trip_id}")
        
        # --------------------------
        # 1. 先获取主行程并加锁（关键数据库操作，需事务）
        # --------------------------
        main_trip = None
        with transaction.atomic():
            try:
                # 锁定主行程，防止并发修改
                main_trip = Trip.objects.select_for_update(nowait=True).get(trip_id=trip_id)
                
                # 检查状态，避免重复处理
                if main_trip.is_completed:
                    logger.info(f"行程 {main_trip.trip_id} 已完成合并，跳过处理")
                    return None, None
                if getattr(main_trip, 'is_merging', False):
                    logger.info(f"行程 {main_trip.trip_id} 正在合并中，跳过处理")
                    return None, None
            except DatabaseError:
                logger.info(f"行程 {trip_id} 正在被其他进程处理，跳过")
                return None, None

        if not main_trip:
            logger.error(f"未找到主行程 {trip_id}")
            return None, None

        logger.info(f"用户ID: {user_id}, 行程ID: {main_trip.trip_id} 开始合并处理！")

        # --------------------------
        # 2. 查询需要合并的行程（非锁定查询，事务外执行）
        # --------------------------
        all_similar_trips = Trip.objects.filter(
            is_completed=False,
            user_id=user_id,
            device_id=main_trip.device_id,
            car_name=main_trip.car_name,
            hardware_version=main_trip.hardware_version,
            software_version=main_trip.software_version,
            merge_into_current=True,
            trip_status=main_trip.trip_status,
        ).order_by('last_update')  # 升序：从旧到新

        trips_to_merge = []
        parent_trip = None
        if all_similar_trips.exists():
            parent_trip = all_similar_trips.first()  # 最早的行程作为父行程
            logger.info(f"父行程: {parent_trip.trip_id}, 时间范围: {parent_trip.first_update} 到 {parent_trip.last_update}")
            trips_to_merge = list(all_similar_trips)  # 所有符合条件的行程
        else:
            logger.info("没有找到符合条件的行程，直接返回")
            return None, None

        trips_to_merge.sort(key=lambda x: x.last_update)  # 确保顺序
        logger.info(f"找到 {len(trips_to_merge)} 个需要合并的行程")

        csv_merged_results = []
        det_merged_results = []

        # --------------------------
        # 3. 循环处理每个行程（分离数据库和IO操作）
        # --------------------------
        for trip in trips_to_merge:
            # 跳过已完成或正在合并的行程
            if trip.is_completed or getattr(trip, 'is_merging', False):
                logger.info(f"行程 {trip.trip_id} 已完成或正在合并，跳过")
                continue

            logger.info(f"行程 {trip.trip_id} 开始处理！")

            # --------------------------
            # 3.1 标记“正在合并”（数据库操作，需事务）
            # --------------------------
            try:
                with transaction.atomic():
                    # 重新加锁获取最新状态（防止并发修改）
                    trip_locked = Trip.objects.select_for_update().get(trip_id=trip.trip_id)
                    if trip_locked.is_completed or trip_locked.is_merging:
                        logger.info(f"行程 {trip.trip_id} 已被其他进程处理，跳过")
                        continue
                    trip_locked.is_merging = True
                    trip_locked.save(update_fields=['is_merging'])
                    trip = trip_locked  # 用锁定后的对象后续操作
            except Exception as e:
                logger.error(f"标记行程 {trip.trip_id} 为合并中失败: {e}")
                continue  # 处理下一个行程，不影响整体

            # --------------------------
            # 3.2 合并文件（IO操作，事务外执行）
            # --------------------------
            merged_results = {'csv': None, 'det': None}
            try:
                # 合并CSV
                csv_chunks = ChunkFile.objects.filter(trip=trip, file_type='csv').order_by('chunk_index')
                logger.info(f"行程 {trip.trip_id} CSV分片数量: {csv_chunks.count()}")
                if csv_chunks.exists():
                    # 统计分片数量和缺失情况（数据库操作，单独事务）
                    with transaction.atomic():
                        trip.csv_chunk_count = csv_chunks.count()
                        logger.info(f"行程 {trip.trip_id} CSV分片数量: {csv_chunks.count()} !")
                        csv_indexes = list(csv_chunks.values_list('chunk_index', flat=True))
                        missing_count = len(set(range(min(csv_indexes), max(csv_indexes)+1)) - set(csv_indexes)) if csv_indexes else 0
                        trip.csv_chunk_lose = missing_count
                        logger.info(f"行程 {trip.trip_id} 中间缺少CSV分片数量: {missing_count}")
                        trip.save(update_fields=['csv_chunk_count', 'csv_chunk_lose'])

                    # 合并CSV（IO操作）
                    merged_csv = pd.DataFrame()
                    for chunk in csv_chunks:
                        try:
                            df = pd.read_csv(chunk.file_path)
                            merged_csv = pd.concat([merged_csv, df])
                        except Exception as e:
                            logger.error(f"读取CSV分片 {chunk.chunk_index} 失败: {e}")

                    if not merged_csv.empty:
                        # 保存合并后的CSV

                        # 处理文件名
                        merged_csv_filename = None
                        for chunk in csv_chunks:
                            if hasattr(chunk, 'file_name') and chunk.file_name and 'spcialPoint' in chunk.file_name:
                                merged_csv_filename = chunk.file_name.split('/')[-1]
                                break
                        if not merged_csv_filename:
                            merged_csv_filename = trip.file_name.split('/')[-1] if trip.file_name else f"merged_{trip.trip_id}.csv"

                        merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip.trip_id))
                        os.makedirs(merged_dir, exist_ok=True)
                        # 保存合并文件
                        merged_path = os.path.join(merged_dir, merged_csv_filename)
                        merged_csv.to_csv(merged_path, index=False)
                        # trip.merged_csv_path = merged_path
                        merged_results['csv'] = merged_path
                        logger.info(f"合并CSV文件成功.保存到 {merged_path}")

                # 合并DET（类似CSV处理）
                det_chunks = ChunkFile.objects.filter(trip=trip, file_type='det').order_by('chunk_index')
                logger.info(f"行程 {trip.trip_id} DET分片数量: {det_chunks.count()}")
                if det_chunks.exists():
                    # 统计分片信息（数据库操作）
                    with transaction.atomic():
                        trip.det_chunk_count = det_chunks.count()
                        logger.info(f"行程 {trip.trip_id} DET分片数量: {det_chunks.count()} !")
                        det_indexes = list(det_chunks.values_list('chunk_index', flat=True))
                        missing_count = len(set(range(min(det_indexes), max(det_indexes)+1)) - set(det_indexes)) if det_indexes else 0
                        trip.det_chunk_lose = missing_count
                        logger.info(f"行程 {trip.trip_id} 中间缺少det分片数量: {missing_count}")
                        trip.save(update_fields=['det_chunk_count', 'det_chunk_lose'])

                    # 合并DET（IO操作）
                    merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip.trip_id))
                    os.makedirs(merged_dir, exist_ok=True)
                    # 处理文件名
                    merged_det_filename = None
                    for chunk in det_chunks:
                        if hasattr(chunk, 'file_name') and chunk.file_name and 'spcialPoint' in chunk.file_name:
                            merged_det_filename = chunk.file_name.split('/')[-1]
                            break
                    if not merged_det_filename:
                        merged_det_filename = trip.file_name.split('/')[-1][:-4] + '.det' if trip.file_name else f"merged_{trip.trip_id}.det"
                    det_merged_path = os.path.join(merged_dir, merged_det_filename)
                    with open(det_merged_path, 'wb') as outfile:
                        for chunk in det_chunks:
                            try:
                                with open(chunk.file_path, 'rb') as infile:
                                    outfile.write(infile.read())
                            except Exception as e:
                                logger.error(f"读取DET分片 {chunk.chunk_index} 失败: {e}")
                    # trip.merged_det_path = det_merged_path
                    merged_results['det'] = det_merged_path
                    logger.info(f"行程 {trip.trip_id} DET合并完成: {det_merged_path}")

            except Exception as e:
                logger.error(f"合并行程 {trip.trip_id} 文件失败: {e}")
                # 出错后重置“正在合并”状态（数据库操作）
                with transaction.atomic():
                    trip.is_merging = False
                    trip.save(update_fields=['is_merging'])
                continue  # 处理下一个行程

            # --------------------------
            # 3.3 清理分片文件（IO操作，事务外）
            # --------------------------
            try:
                chunks = ChunkFile.objects.filter(trip=trip)
                trip_chunk_dir = ''
                if chunks:
                    # 分片文件夹路径
                    trip_chunk_dir = os.path.dirname(chunks[0].file_path)
                    logger.info(f"行程 {trip.trip_id} 的分片文件夹: {trip_chunk_dir}")
                # 删除分片文件和记录
                for chunk in chunks:
                    if os.path.exists(chunk.file_path):
                        os.remove(chunk.file_path)
                    chunk.delete()  # 数据库删除，单独事务（或批量删除）
                # 删除文件夹
                if trip_chunk_dir and os.path.exists(trip_chunk_dir):
                    shutil.rmtree(trip_chunk_dir)
                logger.info(f"行程 {trip.trip_id} 分片清理完成")
            except Exception as e:
                logger.error(f"清理行程 {trip.trip_id} 分片失败: {e}")
                # 清理失败不影响合并结果，继续执行

            # --------------------------
            # 3.4 更新行程状态（数据库操作，事务）
            # --------------------------
            try:
                with transaction.atomic():
                    trip_locked = Trip.objects.select_for_update().get(trip_id=trip.trip_id)
                    trip_locked.is_merging = False
                    trip_locked.is_completed = True
                    update_fields = ['is_merging', 'is_completed']
                    if merged_results['csv']:
                        trip_locked.merged_csv_path = merged_results['csv']
                        update_fields.append('merged_csv_path')
                    if merged_results['det']:
                        trip_locked.merged_det_path = merged_results['det']
                        update_fields.append('merged_det_path')
                    trip_locked.save(update_fields=update_fields)
                    logger.info(f"行程 {trip.trip_id} 处理完成")


                    logger.info(
                        f"行程 {trip_locked.trip_id} 更新完成:\n"
                        f"- 完成状态: {trip_locked.is_completed}\n"
                        f"- 合并状态: {trip_locked.is_merging}\n"
                        f"- CSV路径: {trip_locked.merged_csv_path}\n"
                        f"- DET路径: {trip_locked.merged_det_path}"
                    )

                # 记录结果
                if merged_results['csv']:
                    csv_merged_results.append(merged_results['csv'])
                if merged_results['det']:
                    det_merged_results.append(merged_results['det'])
            except Exception as e:
                logger.error(f"更新行程 {trip.trip_id} 状态失败: {e}")

            # --------------------------
            # 3.5 设置父子关系（数据库操作，事务）
            # --------------------------
            if parent_trip and str(trip.trip_id) != str(parent_trip.trip_id):
                try:
                    with transaction.atomic():
                        ensure_db_connection_and_set_sub_journey_sync(trip.trip_id, parent_trip.trip_id)
                        ensure_db_connection_and_set_sub_journey_parent_id_sync(trip.trip_id, parent_trip.trip_id)
                except Exception as e:
                    logger.error(f"设置行程 {trip.trip_id} 父子关系失败: {e}")

        # 更新父行程状态
        if parent_trip:
            try:
                ensure_db_connection_and_update_parent_journey_status_sync(parent_trip.trip_id)
            except Exception as e:
                logger.error(f"更新父行程 {parent_trip.trip_id} 状态失败: {e}")

        return csv_merged_results, det_merged_results

    except Exception as e:
        logger.error(f"合并文件总失败: {e}", exc_info=True)
        return None, None



# NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
def process_and_upload_files_sync(user_id, csv_path_list, det_path_list):
    """同步版本的文件处理和上传函数"""
    try:
        tinder_os = TinderOS()
        results = []
        
        files_to_process = []
        if csv_path_list and isinstance(csv_path_list, list) and len(csv_path_list) > 0:
            for csv_path in csv_path_list:
                if csv_path and Path(csv_path).exists():
                    files_to_process.append((csv_path, 'csv'))

        if det_path_list and isinstance(det_path_list, list) and len(det_path_list) > 0:   
            for det_path in det_path_list:                 
                if det_path and Path(det_path).exists():
                    files_to_process.append((det_path, 'det'))        

        # for file_path, file_type in [(csv_path, 'csv'), (det_path, 'det')]:
        for file_path, file_type in files_to_process:
            if not file_path:
                continue
                
            file_name = Path(file_path)
            model = file_name.name.split('_')[0]
            time_line = file_name.name.split('_')[-1].split('.')[0]
            
            # 获取品牌信息
            middle_model = model_config.objects.filter(model=model).first()
            if middle_model:
                brand = middle_model.brand
                upload_path = f"app_project/{user_id}/inference_data/{brand}/{model}/{time_line.split(' ')[0]}/{time_line}/{file_name.name}"
                
                # 上传文件
                tinder_os.upload_file('chek-app', upload_path, file_path)
                
                # 记录到数据库
                data_tos_model = tos_csv_app.objects.create(
                    user_id=user_id,
                    tos_file_path=upload_path,
                    tos_file_type='inference'
                )

                data_tos_model.user_id = user_id
                data_tos_model.tos_file_path =upload_path
                data_tos_model.tos_file_type = 'inference'
                data_tos_model.save()

                results.append((file_type, upload_path))
                
                # # 可以选择删除本地文件
                # os.remove(file_path)
        
        return True, results
    except Exception as e:
        logger.error(f"处理和上传文件失败: {e}")
        return False, []


# 
async def handle_merge_task(_id, trip_id, is_last_chunk=False, is_timeout=False):
    """处理合并任务"""
    try:
       
        if is_last_chunk:
            # 检查进程池状态
            stats = get_process_pool_stats()
            if stats and stats['available_workers'] <= 1:
                logger.warning(f"进程池资源紧张: 活跃进程{stats['active_processes']}/{stats['max_workers']}")
                await asyncio.sleep(0.5)

            loop = asyncio.get_event_loop()


                # 使用外部定义的函数，传递参数
            csv_path_list, det_path_list = await loop.run_in_executor(
                process_executor,
                ensure_db_connection_and_merge,
                _id,
                trip_id,
                is_timeout
            )
            
            is_valid_interval = False
            if csv_path_list and isinstance(csv_path_list, list) and len(csv_path_list) > 0:
                is_valid_interval = await loop.run_in_executor(
                        process_executor,
                        get_csv_time_interval,
                        csv_path_list
                )

            if ((csv_path_list and isinstance(csv_path_list, list) and len(csv_path_list) > 0) or \
                (det_path_list and isinstance(det_path_list, list) and len(det_path_list) > 0)) :

                # 在进程池中执行文件处理和上传
                success, results = await loop.run_in_executor(
                    process_executor,
                    ensure_db_connection_and_process_and_upload_files_sync,
                    _id,
                    csv_path_list,
                    det_path_list
                )

                if success:
                    await loop.run_in_executor(
                        process_executor,
                        ensure_db_connection_and_set_tos_path_sync,
                        trip_id,
                        results
                    )
                    logger.info(f"文件处理和上传成功: {results}")
                else:
                    logger.error("文件处理和上传失败")

            if (csv_path_list and isinstance(csv_path_list, list) and len(csv_path_list) > 0):

                user = await loop.run_in_executor(
                    process_executor,
                    ensure_db_connection_and_get_user,
                    _id
                )

                if user and is_valid_interval:
                    # 处理行程数据
                    success, message = await loop.run_in_executor(
                        process_executor,
                        ensure_db_connection,
                        trip_id,
                        user,
                        csv_path_list
                    )
                    if success:
                        logger.info(f"进程池处理行程数据成功，{message}")
                    else:
                        logger.error(f"进程池处理数据失败，用户: {user.name}, 错误信息: {message}")
                else:
                    logger.error(f"用户 {_id} 不存在, 或行程持续时间小于{settings.TIME_THRE}s. 无法处理行程数据 {csv_path_list}.")

                if not is_valid_interval: 
                    ensure_db_connection_and_set_journey_less_than_timethre_sync(trip_id)
                    logger.warning(f"CSV文件 {csv_path_list} 时间间隔小于{settings.TIME_THRE}秒，跳过处理")
                else:
                    logger.info(f"CSV文件 {csv_path_list} 时间间隔大于{settings.TIME_THRE}秒，正常处理")

            if csv_path_list and isinstance(csv_path_list, list) and len(csv_path_list) > 0:
                for csv_path in csv_path_list:
                    if Path(csv_path).exists():
                        os.remove(str(csv_path))
                        logger.info(f'删除合并csv文件: {csv_path}')

            if det_path_list and isinstance(det_path_list, list) and len(det_path_list) > 0:
                for det_path in det_path_list:
                    if Path(det_path).exists():
                        os.remove(str(det_path))
                        logger.info(f'删除合并det文件: {det_path}')

        else:
            # 检查是否需要触发自动合并
            await check_timeout_trip(_id, trip_id)
                
    except Exception as e:
        logger.error(f"合并任务处理失败: {e}")



# 将嵌套函数移到外部作为独立函数
def ensure_db_connection_and_merge(user_id, trip_id, is_timeout=False):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行合并操作")
            # 连接正常，执行合并操作
            return merge_files_sync(user_id, trip_id, is_timeout)
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return None, None

# 将嵌套函数移到外部作为独立函数
def ensure_db_connection_and_process_and_upload_files_sync(user_id, csv_path_list, det_path_list):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行数据上传操作")
            # 连接正常，执行合并操作
            return process_and_upload_files_sync(user_id, csv_path_list, det_path_list)
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return False, []


# 将嵌套函数移到外部作为独立函数
def ensure_db_connection_and_get_user(user_id):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行获取用户信息操作")
            # 连接正常，执行合并操作
            return get_user_sync(user_id)
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return None


def is_valiad_phone_number_sync(phone):
    
    pattern = r"^1[3-9]\d{9}$"

    if re.match(pattern, phone):
        return True
    else:
        return False


def journey_update(total_message,trip_id,model,hardware_version,software_version,core_Journey_profile):
    if model:
        core_Journey_profile.model = model
    
    if hardware_version:
        core_Journey_profile.hardware_version = hardware_version

    if software_version:
        core_Journey_profile.software_version = software_version
    
    if total_message:
        for key,value in total_message.items():
            # print(key,value)
            # if type(value) != 'str' or value:
            core_Journey_profile.key = value
    core_Journey_profile.save()


def mbti_judge(auto_speed_average,auto_acc_average,auto_dcc_average,driver_speed_average,driver_acc_average,driver_dcc_average):
    human_MBTI_text = '内敛小i人'
    car_MBTI_text = '内敛小i人'
    if auto_speed_average>30 and (auto_dcc_average<-4 or auto_acc_average>4):
        car_MBTI_text = '狂飙小e人'
    elif  auto_speed_average<=30 and (auto_dcc_average<-4 or auto_acc_average>4):
        car_MBTI_text = '苦苦装e小i人'
    elif auto_speed_average>30 and (auto_dcc_average>=-4 or auto_acc_average<=4):
        car_MBTI_text = '快乐小e人'
    elif auto_speed_average<=30 and (auto_dcc_average>=-4 or auto_acc_average<=4):
        car_MBTI_text = '内敛小i人'

    if driver_speed_average>30 and (driver_acc_average<-4 or driver_acc_average>4):
        human_MBTI_text = '狂飙小e人'
    elif  driver_speed_average<=30 and (driver_acc_average<-4 or driver_acc_average>4):
        human_MBTI_text = '苦苦装e小i人'
    elif driver_speed_average>30 and (driver_acc_average>=-4 or driver_acc_average<=4):
        human_MBTI_text = '快乐小e人'
    elif driver_speed_average<=30 and (driver_acc_average>=-4 or driver_acc_average<=4):
        human_MBTI_text = '内敛小i人'
    return car_MBTI_text,human_MBTI_text


def handle_message_data(total_message,trip_id,model,hardware_version,software_version):
    try:
        parser = ChekMessageParser(total_message)
        data = parser.parse()

        # core_user_profile = Journey.objects.get(journey_id=trip_id) 
        # 使用 filter 方法筛选符合条件的对象，再用 exists 方法检查是否存在
   
        journey_exists = Journey.objects.using('core_user').filter(journey_id=trip_id).exists()
        
        if journey_exists:
            cover_image = ''
            cover_image_profile = HotBrandVehicle.objects.filter(model=model).first()
            if cover_image_profile:
                cover_image = cover_image_profile.cover_image
            # 如果存在，可以进一步获取对象
            core_Journey_profile = Journey.objects.using('core_user').get(journey_id=trip_id)
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
            if data.get('auto_safe_duration') or type(data.get('auto_safe_duration')) != 'str':
                core_Journey_profile.auto_safe_duration = data.get('auto_safe_duration')
            
            if data.get('lcc_safe_duration') or type(data.get('lcc_safe_duration')) != 'str':
                core_Journey_profile.lcc_safe_duration = data.get('lcc_safe_duration')

            if data.get('noa_safe_duration') or type(data.get('noa_safe_duration')) != 'str':
                core_Journey_profile.noa_safe_duration = data.get('noa_safe_duration')
               
            if data.get('duration') or type(data.get('duration')) != 'str':
                core_Journey_profile.duration = data.get('duration')

            if data.get('driver_acc_average') or type(data.get('duration')) != 'str':
                core_Journey_profile.driver_acc_average = data.get('driver_acc_average')

            if data.get('driver_dcc_average') or type(data.get('driver_dcc_average')) != 'str':
                core_Journey_profile.driver_dcc_average = data.get('driver_dcc_average')

            if data.get('auto_mileages') or type(data.get('auto_mileages')) != 'str':
                core_Journey_profile.auto_mileages = data.get('auto_mileages')

            if data.get('total_mileages') or type(data.get('total_mileages')) != 'str':
                core_Journey_profile.total_mileages = data.get('total_mileages')

            if data.get('frames') or type(data.get('frames')) != 'str':
                core_Journey_profile.frames = data.get('frames')

            if data.get('auto_frames') or type(data.get('auto_frames')) != 'str':
                core_Journey_profile.auto_frames = data.get('auto_frames')

            if data.get('noa_frames') or type(data.get('noa_frames')) != 'str':
                core_Journey_profile.noa_frames = data.get('noa_frames')

            if data.get('lcc_frames') or type(data.get('lcc_frames')) != 'str':
                core_Journey_profile.lcc_frames = data.get('lcc_frames')

            if data.get('driver_frames') or type(data.get('driver_frames')) != 'str':
                core_Journey_profile.driver_frames = data.get('driver_frames')

            if data.get('auto_speed_average') or type(data.get('auto_speed_average')) != 'str':
                core_Journey_profile.auto_speed_average = data.get('auto_speed_average')

            if data.get('auto_max_speed') or type(data.get('auto_max_speed')) != 'str':
                core_Journey_profile.auto_max_speed = data.get('auto_max_speed')

            if data.get('invervention_risk_proportion') or type(data.get('invervention_risk_proportion')) != 'str':
                core_Journey_profile.invervention_risk_proportion = data.get('invervention_risk_proportion')

            if data.get('invervention_mpi') or type(data.get('invervention_mpi')) != 'str':
                core_Journey_profile.invervention_mpi = data.get('invervention_mpi')

            if data.get('invervention_risk_mpi') or type(data.get('invervention_risk_mpi')) != 'str':
                core_Journey_profile.invervention_risk_mpi = data.get('invervention_risk_mpi')

            if data.get('invervention_cnt') or type(data.get('invervention_cnt')) != 'str':
                core_Journey_profile.invervention_cnt = data.get('invervention_cnt')

            if data.get('invervention_risk_cnt') or type(data.get('invervention_risk_cnt')) != 'str':
                core_Journey_profile.invervention_risk_cnt = data.get('invervention_risk_cnt')

            if data.get('noa_invervention_risk_mpi') or type(data.get('noa_invervention_risk_mpi')) != 'str':
                core_Journey_profile.noa_invervention_risk_mpi = data.get('noa_invervention_risk_mpi')

            if data.get('noa_invervention_mpi') or type(data.get('noa_invervention_mpi')) != 'str':
                core_Journey_profile.noa_invervention_mpi = data.get('noa_invervention_mpi')

            if data.get('noa_invervention_risk_cnt') or type(data.get('noa_invervention_risk_cnt')) != 'str':
                core_Journey_profile.noa_invervention_risk_cnt = data.get('noa_invervention_risk_cnt')

            if data.get('noa_auto_mileages') or type(data.get('noa_auto_mileages')) != 'str':
                core_Journey_profile.noa_auto_mileages = data.get('noa_auto_mileages')

            if data.get('noa_auto_mileages_proportion') or type(data.get('noa_auto_mileages_proportion')) != 'str':
                core_Journey_profile.noa_auto_mileages_proportion = data.get('noa_auto_mileages_proportion')

            if data.get('noa_invervention_cnt') or type(data.get('noa_invervention_cnt')) != 'str':
                core_Journey_profile.noa_invervention_cnt = data.get('noa_invervention_cnt')

            if data.get('lcc_invervention_risk_mpi') or type(data.get('lcc_invervention_risk_mpi')) != 'str':
                core_Journey_profile.lcc_invervention_risk_mpi = data.get('lcc_invervention_risk_mpi')

            if data.get('lcc_invervention_mpi') or type(data.get('lcc_invervention_mpi')) != 'str':
                core_Journey_profile.lcc_invervention_mpi = data.get('lcc_invervention_mpi')

            if data.get('lcc_invervention_risk_cnt') or type(data.get('lcc_invervention_risk_cnt')) != 'str':
                core_Journey_profile.lcc_invervention_risk_cnt = data.get('lcc_invervention_risk_cnt')

            if data.get('lcc_auto_mileages') or type(data.get('lcc_auto_mileages')) != 'str':
                core_Journey_profile.lcc_auto_mileages = data.get('lcc_auto_mileages')

            if data.get('lcc_auto_mileages_proportion') or type(data.get('lcc_auto_mileages_proportion')) != 'str':
                core_Journey_profile.lcc_auto_mileages_proportion = data.get('lcc_auto_mileages_proportion')

            if data.get('lcc_invervention_cnt') or type(data.get('lcc_invervention_cnt')) != 'str':
                core_Journey_profile.lcc_invervention_cnt = data.get('lcc_invervention_cnt')

            if data.get('auto_dcc_max') or type(data.get('auto_dcc_max')) != 'str':
                core_Journey_profile.auto_dcc_max = data.get('auto_dcc_max')

            if data.get('auto_dcc_frequency') or type(data.get('auto_dcc_frequency')) != 'str':
                core_Journey_profile.auto_dcc_frequency = data.get('auto_dcc_frequency')

            if data.get('auto_dcc_cnt') or type(data.get('auto_dcc_cnt')) != 'str':
                core_Journey_profile.auto_dcc_cnt = data.get('auto_dcc_cnt')

            if data.get('auto_dcc_duration') or type(data.get('auto_dcc_duration')) != 'str':
                core_Journey_profile.auto_dcc_duration = data.get('auto_dcc_duration')

            if data.get('auto_dcc_average_duration') or type(data.get('auto_dcc_average_duration')) != 'str':
                core_Journey_profile.auto_dcc_average_duration = data.get('auto_dcc_average_duration')

            if data.get('auto_dcc_average') or type(data.get('auto_dcc_average')) != 'str':
                core_Journey_profile.auto_dcc_average = data.get('auto_dcc_average')

            if data.get('auto_acc_max') or type(data.get('auto_acc_max')) != 'str':
                core_Journey_profile.auto_acc_max = data.get('auto_acc_max')

            if data.get('auto_acc_frequency') or type(data.get('auto_acc_frequency')) != 'str':
                core_Journey_profile.auto_acc_frequency = data.get('auto_acc_frequency')

            if data.get('auto_acc_cnt') or type(data.get('auto_acc_cnt')) != 'str':
                core_Journey_profile.auto_acc_cnt = data.get('auto_acc_cnt')

            if data.get('auto_acc_duration') or type(data.get('auto_acc_duration')) != 'str':
                core_Journey_profile.auto_acc_duration = data.get('auto_acc_duration')

            if data.get('auto_acc_average_duration') or type(data.get('auto_acc_average_duration')) != 'str':
                core_Journey_profile.auto_acc_average_duration = data.get('auto_acc_average_duration')

            if data.get('auto_acc_average') or type(data.get('auto_acc_average')) != 'str':
                core_Journey_profile.auto_acc_average = data.get('auto_acc_average')

            if data.get('driver_mileages') or type(data.get('driver_mileages')) != 'str':
                core_Journey_profile.driver_mileages = data.get('driver_mileages')

            if data.get('driver_dcc_max') or type(data.get('driver_dcc_max')) != 'str':
                core_Journey_profile.driver_dcc_max = data.get('driver_dcc_max')

            if data.get('driver_dcc_frequency') or type(data.get('driver_dcc_frequency')) != 'str':
                core_Journey_profile.driver_dcc_frequency = data.get('driver_dcc_frequency')

            if data.get('driver_acc_max') or type(data.get('driver_acc_max')) != 'str':
                core_Journey_profile.driver_acc_max = data.get('driver_acc_max')

            if data.get('driver_acc_frequency') or type(data.get('driver_acc_frequency')) != 'str':
                core_Journey_profile.driver_acc_frequency = data.get('driver_acc_frequency')

            if data.get('driver_speed_average') or type(data.get('driver_speed_average')) != 'str':
                core_Journey_profile.driver_speed_average = data.get('driver_speed_average')

            if data.get('driver_speed_max') or type(data.get('driver_speed_max')) != 'str':
                core_Journey_profile.driver_speed_max = data.get('driver_speed_max')

            if data.get('driver_dcc_cnt') or type(data.get('driver_dcc_cnt')) != 'str':
                core_Journey_profile.driver_dcc_cnt = data.get('driver_dcc_cnt')

            if data.get('driver_acc_cnt') or type(data.get('driver_acc_cnt')) != 'str':
                core_Journey_profile.driver_acc_cnt = data.get('driver_acc_cnt')
            if cover_image:
                core_Journey_profile.cover_image = cover_image
            car_MBTI_text,human_MBTI_text = mbti_judge(core_Journey_profile.auto_speed_average,core_Journey_profile.auto_acc_average,
                                                    core_Journey_profile.auto_dcc_average,core_Journey_profile.driver_speed_average,
                                                    core_Journey_profile.driver_acc_average,core_Journey_profile.driver_dcc_average)
            car_dict = {
            "user_style": human_MBTI_text,
            "user_features": {
                "avg_speed_kmh": core_Journey_profile.driver_speed_average,
                "max_speed_kmh": core_Journey_profile.driver_speed_max,
                "accel_mps2": core_Journey_profile.driver_acc_average,
                "turn_mps2": None
            },
            "car_style": car_MBTI_text,
            "car_features": {
                "accel_100_kmh_sec": 8.8,
                "torque_nm": None,
                "accel_mps2": core_Journey_profile.auto_acc_average,
                "turn_mps2": None
            }
            }
            gpt_res = get_chat_response(car_dict)
            
            
            # if gpt_res :
            #     core_Journey_profile.gpt_comment =gpt_res 
            # core_Journey_profile.save()

            # trip = Trip.objects.get(trip_id=trip_id)
            # file_name = trip.file_name.split('_')[-1].replace('.csv','')
            # file_path = f'video-on-demand/app_project/{trip.user_id}/inference_data/{trip.car_name}/{file_name[0:10]}/{file_name}/'
            # user_id = trip.user_id
            # profile = User.objects.get(id=user.id)
            # pic = profile.pic
            # name = profile.name
            # longimg_file_path = real_test()
            # core_Journey_profile.longimg_file_path = longimg_file_path
            # core_Journey_profile.save()

            if data.get('intervention_gps'):
                # core_Journey_intervention_gps = Journey.objects.using('core_user').get(journey_id=trip_id)
                for _ in data.get('intervention_gps'):
                    # core_Journey_intervention_gps = JourneyInterventionGps.objects.using('core_user').get(journey_id=trip_id)
                    # 直接创建并保存对象
                    core_Journey_intervention_gps = JourneyInterventionGps.objects.using('core_user').create(
                        journey_id=trip_id,
                        frame_id = _.get('frame_id'),
                        gps_lon = _.get('gps_lon'),
                        gps_lat = _.get('gps_lat'),
                        gps_datetime = _.get('gps_datetime'),
                        is_risk = _.get('is_risk'),
                        identification_type = '自动识别',
                        type = '识别接管'
                    )
        else:
            # print(f"未找到 journey_id 为 {trip_id} 的行程记录。")
            logger.info(f"未找到 journey_id 为 {trip_id} 的行程记录。")
    except Exception as e:
        # print(e)
        logger.info(f"报错 {e} ", exc_info=True)

def convert_gps_time(csv_file_path,trip_id):
    """
    读取 CSV 文件，并将 gps_time 转换为现实时间
    假设 gps_time 是形如 '%Y%m%d%H%M%S' 格式的字符串
    """
    df = pd.read_csv(csv_file_path)
    list_process = []
    initial_time = ''
    end_time = ''
    pre_driver = ''
    index = 1
    road_scene = ''
    last_index = df.index[-1]
    for _ in df.index: 
    # 假设这个数字是毫秒级时间戳
        timestamp_ms =  df.loc[_,'gps_timestamp']
        # 转换为秒级时间戳
        timestamp_s = timestamp_ms / 1000

        # 将时间戳转换为 datetime 对象
        dt = datetime.fromtimestamp(timestamp_s)
        lon = df.loc[_,'lon']
        lat = df.loc[_,'lat']
        if df.loc[_,'road_scene']:
            road_scene = df.loc[_,'road_scene']

        if df.loc[_,'auto_icon'] == 'noa' or df.loc[_,'auto_car'] == 'noa':
            driver_status = 'noa'
        elif df.loc[_,'auto_icon'] =='lcc' or  df.loc[_,'auto_car'] == 'lcc':
            driver_status = 'lcc'
        else:
            driver_status = 'standby'

        if not initial_time:
            initial_time = dt
            pre_driver = driver_status

        if len(list_process)>=1000:
            #update
            # pass
            
            # JourneyGPS_profile = JourneyGPS.objects.using('core_user').get()
            journey_gps = JourneyGPS.objects.using('core_user').create(
            journey_id=trip_id,
            gps=str(list_process),
            segment_id=index,
            road_scene=road_scene,
            driver_status = driver_status
            )

            list_process = [(lon,lat)]
            index+=1
            journey_gps.save()
        elif driver_status!= pre_driver:
            #update
            # pass
            journey_gps = JourneyGPS.objects.using('core_user').create(
            journey_id=trip_id,
            gps=str(list_process),
            segment_id=index,
            road_scene=road_scene,
            driver_status = driver_status
            )
            list_process = [(lon,lat)]
            index +=1
            journey_gps.save()
        elif _ == last_index:
            journey_gps = JourneyGPS.objects.using('core_user').create(
            journey_id=trip_id,
            gps=str(list_process),
            segment_id=index,
            road_scene=road_scene,
            driver_status = driver_status
            )
            list_process = [(lon,lat)]
            index +=1
            journey_gps.save()
        else:
            list_process.append((lon,lat))
        end_time = dt
        # 输出结果
        # print("转换后的时间为:", dt)
        pre_driver = driver_status
    return initial_time,end_time


def handle_message_gps_data(file_path_list,trip_id):
    journey_exists = Journey.objects.using('core_user').filter(journey_id=trip_id).exists()
    if journey_exists:
        # 如果存在，可以进一步获取对象
        core_Journey_profile = Journey.objects.using('core_user').get(journey_id=trip_id)
        _id = core_Journey_profile.id
        initial_time,end_time = convert_gps_time(file_path_list[0],trip_id)
        core_Journey_profile.journey_start_time = initial_time
        core_Journey_profile.journey_end_time = end_time
        core_Journey_profile.save()
    else:
        # print(f"未找到 journey_id 为 {trip_id} 的行程记录。")
        logger.info(f"未找到 journey_id 为 {trip_id} 的行程记录。")



# NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
# 小程序proto1.0版本
# 没有上传中间结果
@monitor
def process_wechat_data_sync(trip_id,user, file_path_list):
    try:
        if not (file_path_list and isinstance(file_path_list, list) and len(file_path_list) > 0):
            logger.error(f"process_wechat_data_sync 文件不存在,文件列表为空! ")
            return False, "文件不存在"
        

        file_path = file_path_list[0]
        file_name = file_path.split('/')[-1]
        infos = file_name.split('_')
        if len(infos) > 3:
            model = infos[0]
            hardware_version = infos[1]
            software_version = infos[2]
            logger.info(f"开始处理用户 {user.name} 的行程数据: {file_name}")

            if is_valiad_phone_number_sync(user.phone):
                # # NOTE: 确保phone和小程序phone对应一致
                logger.info(f"开始处理用户 {user.name} , 手机号 {user.phone} 的行程数据: {file_name}, file_path_list: {file_path_list}")
                # saas 协议
                total_message = process_journey(file_path_list, 
                                user_id=100000, 
                                user_name=user.name, 
                                phone=user.phone, 
                                car_brand =model, 
                                car_model='', 
                                car_hardware_version=hardware_version,
                                car_software_version=software_version
                )

                # 父行程认为是历史第一个行程
                # 根据合并行程文件找到所有行程
                current_trip = Trip.objects.get(trip_id=trip_id)
                trips = Trip.objects.filter(
                    user_id=user.id,
                    device_id=current_trip.device_id,
                    car_name=current_trip.car_name,
                    hardware_version=current_trip.hardware_version,
                    software_version=current_trip.software_version,
                    merged_csv_path__in=file_path_list  # 添加 merged_csv_path 在列表中的筛选条件
                ).order_by('-last_update')
                # 获取父行程，更新父行程数据
                trip = trips.last()

                if not trip:
                    logger.warning(f"没有找到该行程的父行程！")
                    return False, "没有找到该行程的父行程！" 

                trip_id = trip.trip_id
                # trip_id = 'ee1a65b673504d13b9c4d5c7e39d8737'
                # NOTE: gps处理     
          
                handle_message_gps_data(file_path_list,trip_id)
                # NOTE: trip_id 关联id 落库结果数据
             
                
                handle_message_data(total_message,trip_id,model,hardware_version,software_version)

                # # 小程序协议
                # process_csv(file_path_list, 
                #                 user_id=100000, 
                #                 user_name=user.name, 
                #                 phone=user.phone, 
                #                 car_brand =model, 
                #                 car_model='', 
                #                 car_version=software_version
                # )




                # 使用聚合函数获取 last_update 最晚时间和 first_update 最早时间
                time_range = trips.aggregate(
                    latest_last_update=Max('last_update'),  # 最晚的 last_update
                    earliest_first_update=Min('first_update')  # 最早的 first_update
                )

                # 提取结果
                latest_last_update = time_range['latest_last_update']
                earliest_first_update = time_range['earliest_first_update']
                # 行程状态更新

                async_to_sync(ensure_db_connection_and_set_journey_status)(trip_id, status=trip.trip_status, 
                                                                           total_journey_start = earliest_first_update, total_journey_end = latest_last_update)  



                for file_path in file_path_list:
                    if Path(file_path).exists():
                        os.remove(str(file_path))
                        print(f'remove file: {file_path}')

                        # 获取父文件夹路径
                        parent_dir = os.path.dirname(file_path)
                        
                        # 删除父文件夹及其所有内容
                        if os.path.exists(parent_dir):
                            shutil.rmtree(parent_dir)
                            print(f'已删除文件夹: {parent_dir}')

                return True, f"数据处理成功. 用户名: {user.name}, 行程数据: {file_name}"
            else:
                logger.warning(f"用户手机号 {user.phone} 格式不正确, 行程未处理！")
                return False, "手机号格式不正确"    
        else:
            logger.warning(f"file name:{file_name} 格式不正确, 行程未处理！")
            return False, "文件名格式不正确"
    except Exception as e:
        logger.error(f"处理app数据失败: {e}",exc_info=True)
        return False, str(e)



 
def get_user_sync(_id):
    """同步获取用户信息"""
    try:
        from django.db import connection
        if connection.connection and not connection.is_usable():
            connection.close()
        # _id去掉中间横线
        
        # user_id = _id.hex

        # 处理用户ID
        if hasattr(_id, 'hex'):
            user_id = _id.hex
        elif isinstance(_id, str):
            # 如果是字符串,去掉横线
            user_id = _id.replace('-', '')
        else:
            logger.error(f"无效的用户ID格式: {_id}, 类型: {type(_id)}")
            return None

        user = User.objects.get(id=user_id)
        if user:
            return user
        else:
            logger.error(f"用户 {_id} 不存在！")
            return None

    except User.DoesNotExist:
        logger.error(f"用户 {_id} 不存在！")
        return None
    except Exception as e:
        logger.error(f"获取用户信息失败： {e}")
        return None


# NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
def get_csv_time_interval(csv_path_list):
    """
    获取CSV文件时间间隔
    """
    try:
        # time_interval_thre = 240   # csv时间间隔4分钟,低于该阈值不做行程不做上传小程序处理
        time_interval_thre = settings.TIME_THRE
        if not (csv_path_list and isinstance(csv_path_list, list) and len(csv_path_list) > 0):
            logger.error(f"CSV文件列表为空!")
            return False

        total_time = 0

        for csv_path in csv_path_list:
            if not Path(csv_path).exists():
                logger.info(f"csv文件不存在： {csv_path}")
                continue
            df = pd.read_csv(csv_path)
            if 'time' in df.columns:
                min_time = df['time'].min()
                max_time = df['time'].max()
                time_interval = max((max_time - min_time), 0)
                logger.info(f"CSV文件 {csv_path} 时间间隔: {time_interval} 秒")
                total_time +=  time_interval
            else:
                logger.error(f"CSV文件{csv_path}中没有time列")
                continue
        if total_time > time_interval_thre:
            logger.info(f"CSV文件 {csv_path} 时间间隔大于{time_interval_thre}秒，正常处理")
            return True
        else:
            logger.warning(f"CSV文件 {csv_path} 时间间隔小于{time_interval_thre}秒，不做处理")
            return False
        
    except Exception as e:
        logger.error(f"获取时间间隔失败: {e}")
        return False



db_checker_running = True

def start_db_connection_checker():
    """
    启动数据库连接检查任务
    """
    while db_checker_running:
        logger.info(f"开始数据库连接检查!")
        try:
            connections['default'].ensure_connection()
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}", exc_info=True)
            # 关闭连接以便重新建立
            try:
                connections['default'].close()
            except:
                pass
        finally:
            time.sleep(60)  # 每60秒检查一次





# 将嵌套函数移到外部作为独立函数
async def ensure_db_connection_and_get_abnormal_journey(user_id,
                                                        device_id,
                                                        car_name,
                                                        hardware_version, 
                                                        software_version, 
                                                        time):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行获取所有异常退出行程操作")
            
            trips = await sync_to_async(
            list,
            thread_sensitive=True)(
                Trip.objects.filter(user_id=user_id, 
                                    is_completed=False,
                                    device_id=device_id,
                                    car_name=car_name,
                                    hardware_version=hardware_version,
                                    software_version=software_version,
                                    trip_status='正常',
                                    last_update__lt=time
                                    ).order_by('-last_update').values_list('trip_id',flat=True)
            )

            file_names = await sync_to_async(
                list,
                thread_sensitive=True
            )(
                Trip.objects.filter(
                    user_id=user_id,
                    is_completed=False,
                    device_id=device_id,
                    car_name=car_name,
                    hardware_version=hardware_version,
                    software_version=software_version,
                    trip_status='正常',
                    last_update__lt=time
                ).order_by('-last_update').values_list('file_name', flat=True)
            )

            # 获取trips列表中last_update - first_update的时间差和
            last_update = await sync_to_async(
                lambda: sum(
                    (trip.last_update - trip.first_update).total_seconds() 
                    for trip in Trip.objects.filter(trip_id__in=trips)
                )
            )()
            logger.info(f"获取到 {len(trips)} 个异常退出行程，时间间隔总和: {last_update} 秒")
            total_time = last_update
            return trips, total_time, file_names
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return []
            


# 将嵌套函数移到外部作为独立函数
async def ensure_db_connection_and_set_merge_abnormal_journey(trips):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行设置合并到当前行程操作")
            @sync_to_async(thread_sensitive=True)
            def update_trips():
                with transaction.atomic():
                    for trip_id in trips:
                        try:
                            trip = Trip.objects.select_for_update().get(trip_id=trip_id)
                            trip.merge_into_current = False
                            trip.save()
                            logger.info(f"已将行程 {trip_id} 的 Merge_into_current 字段设置为 0")
                        except Trip.DoesNotExist:
                            logger.error(f"行程 {trip_id} 不存在")
                        except Exception as e:
                            logger.error(f"更新行程 {trip_id} merge_into_current 失败: {e}",exc_info=True)
            # 执行更新操作
            await update_trips()
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return False



# 将嵌套函数移到外部作为独立函数
async def ensure_db_connection_and_set_journey_status(trip_id, status="行程生成中", total_journey_start = None, total_journey_end = None):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行设置操作totol_journey表中行程状态操作")
            @sync_to_async(thread_sensitive=True)
            def update_trips():
                with transaction.atomic():
                    try:
                        trip = Trip.objects.get(trip_id=trip_id)
                        user_id = trip.user_id
                        trip.set_journey_status = True
                        # 处理用户ID
                        # if hasattr(trip.user_id, 'hex'):
                        #     user_id = trip.user_id.hex
                        # elif isinstance(trip.user_id, str):
                        #     # 如果是字符串,去掉横线
                        #     user_id = trip.user_id.replace('-', '')
                        logger.info(f" set_journey_status: 的 user_id: {user_id}")
                        core_user_profile = CoreUser.objects.using("core_user").get(app_id=user_id)
                        journey, created = Journey.objects.using("core_user").update_or_create(
                            # 查询条件（用于定位对象）
                            journey_id=trip.trip_id,
                            # 默认值或更新值
                            defaults={
                                'brand': trip.car_name,
                                'model': trip.car_name,
                                'hardware_config': trip.hardware_version,
                                'software_config': trip.software_version,
                                'user_uuid': core_user_profile.id,
                                'journey_status': status,
                            }
                        ) 
                        # "异常退出待确认"行程状态更新journey_start_time，journey_end_time
                        # 确保行程筛选时正常
                        # 然后根据状态和是否新创建来更新时间字段
                        if status == "异常退出待确认" or status == "行程生成中":
                            journey.journey_start_time = trip.first_update
                            journey.journey_end_time = trip.last_update
                        elif not created:
                            # 如果是更新现有记录，保持原有的时间字段不变
                            journey.journey_start_time = total_journey_start
                            journey.journey_end_time = total_journey_end
                            pass
                        else:
                            # 如果是新创建的记录，时间字段保持为 None（默认值）
                            journey.journey_start_time = None
                            journey.journey_end_time = None
                        trip.save()                      
                        journey.save(using="core_user")
                        logger.info(f"已将行程 {trip_id} 的 jouney_status 字段设置为: {status}")
                        logger.info(f"已将行程 {trip_id} 的 默认字段设置为: brand: {trip.car_name}, model: {trip.car_name}, hardware_config: {trip.hardware_version}, software_config: {trip.software_version}, user_uuid: {core_user_profile.id}")

                        if status == "异常退出待确认" or status == "行程生成中":
                            log_journey_start_time = trip.first_update
                            log_journey_end_time = trip.last_update
                        elif not created:
                            log_journey_start_time = total_journey_start
                            log_journey_end_time = total_journey_end
                        else:
                            log_journey_start_time = None
                            log_journey_end_time = None
                        logger.info(f"已将行程 {trip_id} 的 默认字段设置为: journey_start_time: {log_journey_start_time}, journey_end_time: {log_journey_end_time}")
                    except Trip.DoesNotExist:
                        logger.error(f"行程 {trip_id} 不存在")
                    except Exception as e:
                        logger.error(f"更新行程 {trip_id} jouney_status, brand, journey_start_time 失败: {e}", exc_info=True)
            # 执行更新操作
            await update_trips()
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return False


# 将嵌套函数移到外部作为独立函数
def ensure_db_connection( trip_id,user,csv_path_list):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            success, message = process_wechat_data_sync(trip_id,user,csv_path_list)
            return success, message 
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return False,f"数据库连接在{max_retries}次尝试后仍然失败"



# 将嵌套函数移到外部作为独立函数
def ensure_db_connection_and_set_tos_path_sync(trip_id, results):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行csv,det在tos数据路径落库操作")
            try:
                trip = Trip.objects.get(trip_id=trip_id)
                # # 处理用户ID
                # if hasattr(trip.user_id, 'hex'):
                #     user_id = trip.user_id.hex
                # elif isinstance(trip.user_id, str):
                #     # 如果是字符串,去掉横线
                #     user_id = trip.user_id.replace('-', '')
                user_id = trip.user_id
                file_paths = {file_type: file_path for file_type, file_path in results}
                csv_path = file_paths.get('csv')
                det_path = file_paths.get('det')
                core_user_profile = CoreUser.objects.using("core_user").get(app_id=user_id)
                reported_Journey, created = Reported_Journey.objects.using("core_user").get_or_create(
                    brand = trip.car_name,
                    model = trip.car_name,
                    hardware_config = trip.hardware_version,
                    software_config = trip.software_version,
                    journey_id = trip.trip_id,
                    user_uuid = core_user_profile.id,
                    csv_tos_path = csv_path,
                    det_tos_path = det_path,
                    journey_status = trip.trip_status,
                    reported_car_name = trip.reported_car_name,
                    reported_hardware_version = trip.reported_hardware_version,
                    reported_software_version = trip.reported_software_version,
                    created_date = get_current_timezone_time(),
                )  
                trip.save()                      
                reported_Journey.save(using="core_user")
                logger.info(f"已将行程 {trip_id} 的 csv det在tos路径落库. csv: {csv_path}, det: {det_path}, status: {trip.trip_status}, reported_car_name: {trip.reported_car_name}, reported_hardware_version: {trip.reported_hardware_version}, reported_software_version: {trip.reported_software_version}")
            except Trip.DoesNotExist:
                logger.error(f"行程 {trip_id} 不存在")
            except Exception as e:
                logger.error(f"更新行程 {trip_id} Reported_Journey 失败: {e}", exc_info=True)
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return False


# 将trip_id行程设置为子行程，不在行程返回列表
def ensure_db_connection_and_set_sub_journey_sync(trip_id, parent_trip_id=None):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行设置当前行程{trip_id}:为子行程操作")
            try:
                trip = Trip.objects.get(trip_id=trip_id)
                try:
                    journey = Journey.objects.using("core_user").get(journey_id=trip_id)
                    journey.is_sub_journey = True
                    journey.parent_trip_id = parent_trip_id
                    # 更新其他字段
                    journey.save()
                except Journey.DoesNotExist:
                    # 处理对象不存在的情况
                    journey = Journey.objects.using("core_user").create(
                        journey_id=trip_id,
                        is_sub_journey=True,
                        parent_trip_id = parent_trip_id,
                        # 其他字段
                    )
                logger.info(f"已将行程 {trip_id} 设置为子行程")
            except Trip.DoesNotExist:
                logger.error(f"行程 {trip_id} 不存在")
            except Exception as e:
                logger.error(f"更新行程 {trip_id}  is_sub_journey 失败: {e}",exc_info=True)
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return False

# 将trip_id行程设置为子行程，不在行程返回列表
def ensure_db_connection_and_set_sub_journey_parent_id_sync(trip_id, parent_trip_id=None):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行设置当前行程{trip_id}:父行程操作")
            try:
                trip = Trip.objects.get(trip_id=trip_id)
                if parent_trip_id:
                    trip.parent_trip_id = parent_trip_id
                else:
                    # 如果没有提供parent_trip_id，则设置为None
                    trip.parent_trip_id = None
                    # 更新其他字段
                trip.save()
                logger.info(f"已将行程 {trip_id} 的父行程设为 {parent_trip_id}")
            except Trip.DoesNotExist:
                logger.error(f"行程 {trip_id} 不存在")
            except Exception as e:
                logger.error(f"更新行程 {trip_id}  的父行程id 失败: {e}",exc_info=True)
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return False

# 将trip_id行程设置为子行程，不在行程返回列表
def ensure_db_connection_and_update_parent_journey_status_sync(parent_trip_id):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行设置当前行程{parent_trip_id}:父行程操作")
            try:
                journey = Journey.objects.using("core_user").get(journey_id=parent_trip_id)
                journey.journey_status = settings.JOURNEY_STATUS_SUCCESS
                # 更新其他字段
                journey.save()
                logger.info(f"行程: {parent_trip_id} 的journey_status更新为 {journey.journey_status}")
            except Journey.DoesNotExist:
                # 处理对象不存在的情况
                logger.info(f"没有查到行程: {parent_trip_id} ")
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}", exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return False


# 将trip_id行程设置为子行程，不在行程返回列表
def ensure_db_connection_and_set_journey_less_than_timethre_sync(trip_id):
    """确保数据库连接并执行合并操作"""
    # 最大重试次数
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 确保数据库连接有效
            ensure_connection()
            # 测试连接是否正常
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logger.info(f"数据库连接正常，开始执行设置当前行程{trip_id}:行程时长低于限定阈值操作")
            try:
                trip = Trip.objects.get(trip_id=trip_id)
                try:
                    journey = Journey.objects.using("core_user").get(journey_id=trip_id)
                    journey.is_less_than_5min = True
                    # 更新其他字段
                    journey.save()
                    logger.info(f"已将行程 {trip_id} 设置为行程时长低于限定阈值")
                except Journey.DoesNotExist:
                    # 处理对象不存在的情况
                    logger.info(f"行程 {trip_id} 还没有写入Journey数据库,无需新建数据并设置")
            except Trip.DoesNotExist:
                logger.error(f"行程 {trip_id} 不存在")
            except Exception as e:
                logger.error(f"更新行程 {trip_id}  less_than_timethre 失败: {e}",exc_info=True)
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}",exc_info=True)
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return False


async def clear_less_5min_journey(_id, trip_id_list, is_last_chunk=False):
    """处理行程低于5分钟正常退出行程数据"""
    try:
        if is_last_chunk:
            # 检查进程池状态
            stats = get_process_pool_stats()
            if stats and stats['available_workers'] <= 1:
                logger.warning(f"进程池资源紧张: 活跃进程{stats['active_processes']}/{stats['max_workers']}")
                await asyncio.sleep(0.5)

            logger.info(f"开始处理行程低于5分钟正常退出行程数据, 用户ID: {_id}, 行程ID: {trip_id_list}")
            with transaction.atomic():

                logger.info(f"用户ID: {_id}, 行程ID: {trip_id_list} 不足5分钟, 开始进行清理处理！")
                # 找到所有和trip相同的carname hardware_version software_version device_id相同的trip,确保数据不会在进程间产生竞争
                try:  # 降序排列，从最新到最旧  

                    for trip in trip_id_list:
                        # 获取所有分片
                        logger.info(f"开始清理行程 {trip} 的分片文件")
                        # 确保分片文件存在
                        chunks = ChunkFile.objects.filter(trip=trip).order_by('chunk_index')
                        trip_chunk_dir = ''
                        if chunks:
                            # 分片文件夹路径
                            trip_chunk_dir = os.path.dirname(chunks[0].file_path)
                            logger.info(f"行程 {trip} 的分片文件夹路径: {trip_chunk_dir}")
                        # 清理分片文件
                        for chunk in chunks:
                            try:
                                if os.path.exists(chunk.file_path):
                                    os.remove(chunk.file_path)
                                logger.info(f"开始清理行程行程: {chunk.trip_id}, 分片id:{chunk.chunk_index} 的分片文件")
                                chunk.delete()
                            except Exception as e:
                                logger.error(f"清理分片文件失败 {chunk.chunk_index}: {e}")
                        # 清理分片文件夹
                        if os.path.exists(trip_chunk_dir):
                            try:
                                shutil.rmtree(trip_chunk_dir)
                                logger.info(f"清理行程 {trip} 的分片文件夹: {trip_chunk_dir}")
                            except Exception as e:
                                logger.error(f"清理行程 {trip} 的分片文件夹失败: {e}")
                        logger.info(f"完成清理行程 {trip} 的分片文件")
                        # 找到对应trip_id的行程数据
                        # 数据库里删除
                        try:
                            # 查找行程
                            trip_journey = Trip.objects.get(
                                trip_id=trip,
                            ).order_by('-last_update')  # 降序排列，从最新到最旧

                            logger.info(f"行程 {trip} 开始删除")
                            trip_id = trip
                            trip_journey.is_less_than_5min = True
                            trip_journey.is_completed = True
                            trip_journey.save()
                            logger.info(f"行程 {trip_id} 已成功删除")
                        except Exception as e:
                            logger.error(f"删除行程 {trip} 失败: {e}")

                        try:
                            # 查找行程
                            journey = Journey.objects.using('core_user').filter(
                                journey_id=trip)

                            if not journey:
                                logger.info(f"journey 行程 {trip} 开始删除")
                                trip_id = trip
                                journey.delete()
                                logger.info(f"journey 行程 {trip_id} 已成功删除")
                            else:
                                logger.info(f"journey 行程 {trip} 不存在, 无需删除")
                        except Exception as e:
                            logger.error(f"删除journey行程 {trip} 失败: {e}")

                except DatabaseError as e:
                    # 如果无法获取锁（其他进程正在处理），记录并跳过
                    logger.warning(f"无法锁定相关行程记录，可能有其他进程正在处理: {e}")
                    # 可以选择稍后重试或跳过
                    return None, None     
                
    except Exception as e:
        logger.error(f"清理文件失败: {e}")
        return None, None


# NOTE: 
async def process_record_zip_async(journey_record_longimg_id):
    """
        根据上传成功信息找到当前journey_record_longimg_id，
        在trip行程中定位是父行程还是子行程
        父行程就直接打包pcm文件到当前音频目录
        子行程当父行程处理完&所有子行程音频上传完进行打包，
        音频打包文件放在父行程目录下
    """
    try:
        if journey_record_longimg_id is None:
            return 

        stats = get_process_pool_stats()
        if stats and stats['available_workers'] <= 1:
            logger.warning(f"进程池资源紧张: 活跃进程{stats['active_processes']}/{stats['max_workers']}")
            await asyncio.sleep(0.5)

        logger.info(f"开始处理音频文件打包, 行程ID: {journey_record_longimg_id}")

        trip_id = journey_record_longimg_id
        with transaction.atomic():

            trip = await sync_to_async(Trip.objects.filter(trip_id=trip_id).first, thread_sensitive=True)()
            # 行程未处理完
            if trip.is_completed is False:
                return 
            # 行程处理完
            file_paths = []
            output_zip = settings.VIDEO_ON_DEMAND
            if trip.parent_trip_id is None:
                # 自己是父行程
                logger.info(f"当前行程是父行程, 行程ID: {trip_id}")
                journeyRecord = await sync_to_async(JourneyRecordLongImg.objects.using("core_user").get,
                                                    thread_sensitive=True
                                                )(journey_id=journey_record_longimg_id)

                file_paths.append(settings.VIDEO_ON_DEMAND+journeyRecord.record_audio_file_path)
                output_zip += str(Path(journeyRecord.record_audio_file_path).with_suffix(".zip"))

                if (journeyRecord.record_upload_tos_status == settings.RECORD_UPLOAD_TOS_SUCCESS) and (package_files(file_paths, output_zip)):
                    logger.info(f"当前行程完成打包, 行程ID: {trip_id}, zip包路径: {output_zip}")
                    journeyRecord.record_audio_zipfile_path = output_zip
                    journeyRecord.save()
                else:
                    logger.info(f"当前行程打包未完成或者音频文件丢失, 行程ID: {trip_id}")
            else:
                # 自己是子行程
                logger.info(f"当前行程是子行程,  行程ID: {trip_id}")
                # 查找父行程
                parement_trip = await sync_to_async(Trip.objects.filter(trip_id=trip.parent_trip_id).first, thread_sensitive=True)()
                if parement_trip.is_completed is False:
                    # 父行程处理未结束
                    return 
                else:
                    # 父行程处理结束
                    # 查找父行程
                    parement_journeyRecord = await sync_to_async(JourneyRecordLongImg.objects.using("core_user").filter(journey_id=trip.parent_trip_id).first, thread_sensitive=True)()
                    # 查找所有子行程
                    trip_ids = await sync_to_async(
                                    list,
                                    thread_sensitive=True
                                )(
                                    Trip.objects.filter(parent_trip_id=trip.parent_trip_id).values_list('trip_id', flat=True)
                                )
                    
                    journeyRecord_ids = [trip_id for trip_id in trip_ids]

                    logger.info(f"所有子行程,  行程列表: {journeyRecord_ids}")

                    record_audio_file_paths = await sync_to_async(
                                                list,
                                                thread_sensitive=True
                                            )(
                                                JourneyRecordLongImg.objects.using("core_user")
                                                .filter(
                                                    journey_id__in=journeyRecord_ids
                                                )
                                                .filter(
                                                    Q(record_upload_tos_status=settings.RECORD_UPLOAD_TOS_SUCCESS) |
                                                    Q(record_upload_tos_status=settings.RECORD_UPLOAD_TOS_FILE_MISSING)
                                                )
                                                .values_list('record_audio_file_path', flat=True)
                                            )
                    # 全部上传完成
                    if (len(trip_ids) == len(record_audio_file_paths)
                        and ((parement_journeyRecord.record_upload_tos_status == settings.RECORD_UPLOAD_TOS_SUCCESS)
                            or (parement_journeyRecord.record_upload_tos_status == settings.RECORD_UPLOAD_TOS_FILE_MISSING))):
                        # 查找父行程 journeyRecord
                        logger.info(f"开始准备父行程和子行程路径,  准备打包")
                        file_paths = [settings.VIDEO_ON_DEMAND + audio_file_path
                                      for audio_file_path in record_audio_file_paths]
                        parement_record_path = settings.VIDEO_ON_DEMAND + parement_journeyRecord.record_audio_file_path
                        # 打包文件里增加父行程音频
                        file_paths.append(parement_record_path)

                        output_zip = str(Path(parement_record_path).with_suffix(".zip"))

                        if(package_files(file_paths, output_zip)):
                            logger.info(f"当前行程完成打包, 行程ID: {trip_id}, zip包路径: {output_zip}")
                            parement_journeyRecord.record_audio_zipfile_path = output_zip
                            parement_journeyRecord.save()
                            # TODO:
                            # 请求数据分发通知
                            # 本行程音频处理完成
                            await reports_successful_audio_generation(parement_trip.trip_id, parement_trip.task_id)
                        else:
                            logger.info(f"当前行程打包未完成, 行程ID: {trip_id}")
        
        return True
    except Exception as e:
        logger.error(f"处理和上传文件失败: {e}", exc_info=True)
        return False, []


if __name__ == '__main__':
    # file_path_list = ['tos://chek/temp/for 汽车之家/25.5.15-成都重庆测试/阿维塔06/det_csv/2025-05-16/2025-05-16 10-11-23/阿维塔12_2023款 700 三激光后驱奢享版_AVATR.OS 4.0.0_spcialPoint_2025-05-16 10-11-23.csv','tos://chek/temp/for 汽车之家/25.5.15-成都重庆测试/阿维塔06/det_csv/2025-05-16/2025-05-16 10-11-23/阿维塔12_2023款 700 三激光后驱奢享版_AVATR.OS 4.0.0_spcialPoint_2025-05-16 10-11-23.det']
    # trip_id = '82ef3322-8aa9-4cd2-81aa-3ef1499eca3d'

    file_path_list = ['/tos/chek-app/app_project/6ab29710-9254-4e73-b6b6-15546a781be7/inference_data/蔚来/全新蔚来ES6/2025-07-06/2025-07-06 14-44-11/全新蔚来ES6_2023款 75kWh_Banyan 3.0.0_spcialPoint_2025-07-06 14-44-11.csv']
    trip_id = 'bfa597d1-1dd4-40ae-97cb-ff7735aea676'

    total_message = process_journey(file_path_list, 
                                    user_id=100000, 
                                    user_name='念书人', 
                                    phone='18847801997', 
                                    car_brand ='理想', 
                                    car_model='', 
                                    car_hardware_version='2024款 Pro',
                                    car_software_version='OTA7.0'
                    )
              
    # trip_id = 'ee1a65b673504d13b9c4d5c7e39d8737'
    # NOTE: gps处理

    handle_message_gps_data(file_path_list,trip_id)
    # NOTE: trip_id 关联id 落库结果数据
    
    handle_message_data(total_message,trip_id,'model','hardware_version','software_version')