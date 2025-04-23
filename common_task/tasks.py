import os
import re
import pandas as pd
import logging
import asyncio
import time
from pathlib import Path
from django.db import transaction, DatabaseError
from functools import partial
from django.db import connections
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from django.db import transaction
from asgiref.sync import sync_to_async
from .models import Trip, ChunkFile
from django.utils import timezone
from data.models import model_config
from common_task.models import analysis_data_app,tos_csv_app
from common_task.handle_tos import TinderOS

from multiprocessing import Pool, cpu_count
from functools import partial

from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from accounts.models import User
from .db_utils import db_retry, ensure_connection
# from .chek_dataprocess.cloud_process_csv.saas_csv_process import process_journey, async_process_journey
from .chek_dataprocess.cloud_process_csv.wechat_csv_process import process_csv

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
# # NOTE: 单个行程合并版本
# # 定期检查超时任务
# async def check_timeout_trips():
#     """检查超时的上传任务并触发合并（异步版本）"""
#     from django.utils import timezone
#     from datetime import timedelta
    
#     global timeout_checker_running

#     while timeout_checker_running:
#         try:
#             # 查找所有未完成且超过5分钟未更新的Trip
#             timeout = timezone.now() - timedelta(minutes=5)
            
#             # 使用正确的异步查询方法组合
#             trips = await sync_to_async(list, thread_sensitive=True)(
#                 Trip.objects.filter(
#                     is_completed=False, 
#                     last_update__lt=timeout
#                 ).values('trip_id', 'user_id')  # 只获取trip_id字段
#             )
            
#             # 为每个超时的Trip创建合并任务
#             tasks = []
#             for trip in trips:
#                 logger.info(f"检测到超时Trip {trip['trip_id']}，用户ID: {trip['user_id']}  开始异步合并")
#                 # task = asyncio.create_task(start_merge_async(trip['user_id'],trip['trip_id']))
#                 task = asyncio.create_task(
#                     handle_merge_task(
#                         trip['user_id'],
#                         trip['trip_id'], 
#                         is_last_chunk=True  # 模拟最后一个分片
#                     )
#                 )
#                 tasks.append(task)
            
#             # 等待所有任务完成
#             if tasks:
#                 await asyncio.gather(*tasks)
            
#         except Exception as e:
#             logger.error(f"超时检查失败: {str(e)}")
#             await asyncio.sleep(60)  # 发生错误时等待1分钟再重试
#             continue
        
#         # 每5分钟检查一次
#         # await asyncio.sleep(300)
#         # 每5分钟检查一次
#         for _ in range(30):  # 分成30次等待，便于及时响应停止信号
#             if not timeout_checker_running:
#                 break
#             await asyncio.sleep(10)


# NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
# 定期检查超时任务
async def check_timeout_trips():
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
                                is_last_chunk=True  # 模拟最后一个分片
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
        # await asyncio.sleep(300)
        # 每5分钟检查一次
        for _ in range(18):  # 分成18次等待，便于及时响应停止信号
            if not timeout_checker_running:
                break
            await asyncio.sleep(10)


# 启动超时检查任务
# def start_timeout_checker():
#     """启动超时检查器"""
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(check_timeout_trips())

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
            'last_update': timezone.now()
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
        # 当第一次写入时，写入first_update
        trip_exists = await sync_to_async(Trip.objects.filter(trip_id=trip_id).exists, thread_sensitive=True)()
        if not trip_exists:
            defaults['first_update'] = timezone.now()
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

# # 使用线程启动异步循环
# import threading
# timeout_thread = threading.Thread(target=start_timeout_checker, name="TimeoutChecker")
# timeout_thread.daemon = True
# timeout_thread.start()


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
        # upload_file_path =  prepare_upload_file_path(_id, 'inference_data', csv_file)
        # upload_file_path = await sync_to_async(prepare_upload_file_path, thread_sensitive=True)(_id, 'inference_data', csv_file)
        upload_file_path = await prepare_upload_tos_file_path(_id, 'inference_data', file_name)

        # # 上传wechat格式行程
        # task = asyncio.create_task(
        #     limited_task_wrapper(user, file_url)
        # )
        # # 用于管理所有后台任务的列表
        # background_tasks.append(task)

        # upload_file_path = f'temp/app_project/{_id}/inference_data/{csv_file.name}'
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


# async def handle_merge_task(user_id, trip_id, is_last_chunk):
#     """
#     处理合并任务后台函数(异步)
#     """
#     try:
#         # 如果是最后一个分片，触发合并
#         if is_last_chunk:
#             await start_merge_async(user_id, trip_id)
#         else:
#             # 检查是否需要触发自动合并
#             await check_timeout_trip(user_id, trip_id)
#     except Exception as e:
#         logger.error(f"后台合并任务失败：{user_id}, {trip_id}, error: {e}")


# async def handle_merge_task(_id, trip_id, is_last_chunk=False):
#     """处理合并任务"""
#     try:
#         if is_last_chunk:
#             # 使用进程池执行合并操作
#             loop = asyncio.get_event_loop()
#             await loop.run_in_executor(
#                 process_executor,
#                 partial(merge_files, _id, trip_id)
#             )
#         else:
#             # 检查是否需要触发自动合并
#             await check_timeout_trip(_id, trip_id)
            
#     except Exception as e:
#         logger.error(f"合并任务处理失败: {e}")
#     finally:
#         await cleanup_background_tasks()



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
# cleanup_thread = threading.Thread(target=start_background_cleanup)
# cleanup_thread.daemon = True
# cleanup_thread.start()

# cleanup_task_started = False

# def init_background_tasks():
#     """初始化后台任务"""
#     global cleanup_task_started
#     try:
#         if cleanup_task_started:
#             logger.info("定期清理任务已启动，跳过初始化")
#             return None
#         # 创建并启动清理线程
#         cleanup_thread = threading.Thread(
#             target=start_background_cleanup,
#             name="BackgroundCleanup"
#         )
#         cleanup_thread.daemon = True
#         cleanup_thread.start()
        
#         cleanup_task_started = True

#         logger.info(f"后台清理线程已启动: {cleanup_thread.name}")
#         return cleanup_thread
        
#     except Exception as e:
#         logger.error(f"启动后台任务失败: {e}")
#         return None

# cleanup_thread = init_background_tasks()



# async def cleanup_resources():
#     """清理资源"""
#     try:
#         # 关闭进程池
#         executor.shutdown(wait=True)
#         # 清理后台任务
#         await cleanup_background_tasks()
#         # 停止定期清理线程
#         if cleanup_thread.is_alive():
#             cleanup_thread._stop()
#         # 停止超时检查线程    
#         if timeout_thread.is_alive():
#             timeout_thread._stop()
            
#         logger.info("成功清理所有资源")
#     except Exception as e:
#         logger.error(f"清理资源时发生错误: {e}")



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





# NOTE: 单个行程合并版本
# def merge_files_sync(user_id, trip_id):
#     """同步版本的合并文件函数，用于进程池执行"""
#     try:
#         logger.info(f"开始合并文件, 用户ID: {user_id}, 行程ID: {trip_id}")
#         with transaction.atomic():
#             # trip = Trip.objects.select_for_update().get(trip_id=trip_id)
            
#             try:
#                 trip = Trip.objects.select_for_update(nowait=True).get(trip_id=trip_id)

#                 # 检查是否正在合并或已完成
#                 if trip.is_completed:
#                     logger.info(f"行程 {trip_id} 已完成合并，跳过处理")
#                     return None, None
                
#                 if getattr(trip, 'is_merging', False):
#                     logger.info(f"行程 {trip_id} 正在合并中，跳过处理")
#                     return None, None
                
#                 # 标记正在合并
#                 trip.is_merging = True
#                 # trip.save()
#                 trip.save(update_fields=['is_merging'])

#             except DatabaseError:
#                 logger.info(f"行程 {trip_id} 正在被其他进程处理，跳过")
#                 return None, None

#             # # 检查是否已经完成
#             # if trip.is_completed:
#             #     logger.info(f"行程 {trip_id} 已完成合并，返回已存在的文件路径")
#             #     return True, None, None
#             logger.info(f"用户ID: {user_id}, 行程ID: {trip_id} 未完成合并，开始进行合并处理！")

#             try:  
#                 # 获取所有分片
#                 chunks = ChunkFile.objects.filter(trip=trip).order_by('chunk_index')
#                 merged_results = {'csv': None, 'det': None}
                
#                 # 合并CSV文件
#                 csv_chunks = chunks.filter(file_type='csv')
#                 logger.info(f"CSV分片数量: {csv_chunks.count()} !")
#                 if csv_chunks.exists():
#                     merged_csv = pd.DataFrame()
#                     for chunk in csv_chunks:
#                         try:
#                             df = pd.read_csv(chunk.file_path)
#                             merged_csv = pd.concat([merged_csv, df])
#                         except Exception as e:
#                             logger.error(f"读取CSV分片失败 {chunk.chunk_index}: {e}")

#                     if not merged_csv.empty:
#                         # 处理文件名
#                         merged_csv_filename = None
#                         for chunk in chunks:
#                             if 'spcialPoint' in chunk.file_name:
#                                 merged_csv_filename = chunk.file_name.split('/')[-1]
#                                 break
#                         if not merged_csv_filename:
#                             merged_csv_filename = trip.file_name.split('/')[-1] if trip.file_name else f"merged_{trip_id}.csv"

#                         # 创建合并目录
#                         merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip_id))
#                         os.makedirs(merged_dir, exist_ok=True)
                        
#                         # 保存合并文件
#                         merged_path = os.path.join(merged_dir, merged_csv_filename)
#                         merged_csv.to_csv(merged_path, index=False)
#                         trip.merged_csv_path = merged_path
#                         merged_results['csv'] = merged_path
#                         logger.info(f"合并CSV文件成功.保存到 {merged_path}")
                
#                 # 合并DET文件
#                 det_chunks = chunks.filter(file_type='det')
#                 logger.info(f"DET分片数量: {det_chunks.count()} !")
#                 if det_chunks.exists():
#                     merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip_id))
#                     os.makedirs(merged_dir, exist_ok=True)
                    
#                     # 处理文件名
#                     merged_det_filename = None
#                     for chunk in det_chunks:
#                         if 'spcialPoint' in chunk.file_name:
#                             merged_det_filename = chunk.file_name.split('/')[-1]
#                             break
#                     if not merged_det_filename:
#                         merged_det_filename = trip.file_name.split('/')[-1][:-4] + '.det' if trip.file_name else f"merged_{trip_id}.det"

#                     det_merged_path = os.path.join(merged_dir, merged_det_filename)
#                     with open(det_merged_path, 'wb') as outfile:
#                         for chunk in det_chunks:
#                             try:
#                                 with open(chunk.file_path, 'rb') as infile:
#                                     outfile.write(infile.read())
#                             except Exception as e:
#                                 logger.error(f"读取DET分片失败 {chunk.chunk_index}: {e}")
                    
#                     trip.merged_det_path = det_merged_path
#                     merged_results['det'] = det_merged_path
#                     logger.info(f"合并DET文件成功.保存到 {det_merged_path}")
                
#                 try:
#                     # 更新状态
#                     trip.refresh_from_db()
#                     if not trip.is_completed:
#                         trip.is_completed = True
#                         trip.is_merging = False
#                         # trip.save()
#                         update_fields = ['is_merging']
#                         update_fields.append('is_completed')
#                         if merged_results['csv']:
#                             trip.merged_csv_path = merged_results['csv']
#                             update_fields.append('merged_csv_path')
#                         if merged_results['det']:
#                             trip.merged_det_path = merged_results['det']
#                             update_fields.append('merged_det_path')

#                         trip.save(update_fields=update_fields)

#                         logger.info(
#                             f"行程 {trip_id} 更新完成:\n"
#                             f"- 完成状态: {trip.is_completed}\n"
#                             f"- 合并状态: {trip.is_merging}\n"
#                             f"- CSV路径: {trip.merged_csv_path}\n"
#                             f"- DET路径: {trip.merged_det_path}"
#                         )
#                 except Exception as e:
#                     logger.error(f"更新行程状态失败: {e}")
#                     # 发生错误时回滚事务
#                     transaction.set_rollback(True)

#                 chunks = ChunkFile.objects.filter(trip=trip).order_by('chunk_index')
#                 # 清理分片文件
#                 for chunk in chunks:
#                     try:
#                         if os.path.exists(chunk.file_path):
#                             os.remove(chunk.file_path)
#                         chunk.delete()
#                     except Exception as e:
#                         logger.error(f"清理分片文件失败 {chunk.chunk_index}: {e}")
#                 csv_merged_results = merged_results['csv'] if merged_results['csv'] else None
#                 det_merged_results = merged_results['det'] if merged_results['det'] else None
#                 return csv_merged_results, det_merged_results
#             except Exception as e:
#                 # 发生错误时重置合并状态
#                 trip.is_merging = False
#                 trip.save()
#                 logger.error(f"合并文件失败: {e}")
#                 return None, None
            
#     except Exception as e:
#         logger.error(f"合并文件失败: {e}")
#         return None, None

# NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
def merge_files_sync(user_id, trip_id):
    """同步版本的合并文件函数，用于进程池执行"""
    
    time_interval_thre = 300
    try:
        logger.info(f"开始合并文件, 用户ID: {user_id}, 行程ID: {trip_id}")
        with transaction.atomic():
            # trip = Trip.objects.select_for_update().get(trip_id=trip_id)
            
            try:
                main_trip = Trip.objects.select_for_update(nowait=True).get(trip_id=trip_id)

                # 检查是否正在合并或已完成
                if main_trip.is_completed:
                    logger.info(f"行程 {main_trip.trip_id} 已完成合并，跳过处理")
                    return None, None
                
                if getattr(main_trip, 'is_merging', False):
                    logger.info(f"行程 {main_trip.trip_id} 正在合并中，跳过处理")
                    return None, None
                
                # # 标记正在合并
                # main_trip.is_merging = True
                # # trip.save()
                # main_trip.save(update_fields=['is_merging'])

            except DatabaseError:
                logger.info(f"行程 {main_trip.trip_id} 正在被其他进程处理，跳过")
                return None, None

            # # 检查是否已经完成
            # if trip.is_completed:
            #     logger.info(f"行程 {trip_id} 已完成合并，返回已存在的文件路径")
            #     return True, None, None
            logger.info(f"用户ID: {user_id}, 行程ID: {main_trip.trip_id} 未完成合并，开始进行合并处理！")
            # 找到所有和trip相同的carname hardware_version software_version device_id相同的trip,确保数据不会在进程间产生竞争
            try:
                # 首先获取所有符合基本条件的行程，按照last_update排序（降序，从新到旧）
                all_similar_trips = Trip.objects.filter(
                    is_completed=False,
                    user_id=user_id,
                    device_id=main_trip.device_id,
                    car_name=main_trip.car_name,
                    hardware_version=main_trip.hardware_version,
                    software_version=main_trip.software_version,
                ).order_by('-last_update')  # 降序排列，从最新到最旧

                # 筛选出需要合并的行程
                trips_to_merge = []
                prev_trip = None

                for trip in all_similar_trips:
                    if not prev_trip:  # 第一个行程（最新的行程）
                        trips_to_merge.append(trip)
                        prev_trip = trip
                        continue
                    
                    # 计算当前行程与前一个行程的时间间隔（秒）
                    # 注意：由于是降序排列，所以是prev_trip.first_update - trip.last_update
                    time_diff = (prev_trip.first_update - trip.last_update).total_seconds()
                    
                    if time_diff <= time_interval_thre:  # 5分钟 = 300秒
                        # 如果间隔小于等于5分钟，则添加到合并行程列表
                        trips_to_merge.append(trip)
                        prev_trip = trip
                    else:
                        # 找到了间隔超过5分钟的行程，停止查找
                        logger.info(f"找到间隔超过5分钟的行程，停止查找。行程ID: {trip.trip_id}, 时间间隔: {time_diff}秒")
                        break

                # 按照时间升序排序（从旧到新），便于处理
                trips_to_merge.sort(key=lambda x: x.last_update)

                logger.info(f"找到 {len(trips_to_merge)} 个需要合并的行程，时间范围: {trips_to_merge[0].last_update} 到 {trips_to_merge[-1].last_update}")
                trips = trips_to_merge


                # 记录锁定的行程数量
                trips_count = len(trips) if isinstance(trips, list) else trips.count()
                logger.info(f"已锁定 {trips_count} 个相关行程记录")

                csv_merged_results = []
                det_merged_results = []

                for trip in trips:
                    try:
                        # 检查是否正在合并或生成
                        if trip.is_completed:
                            logger.info(f"行程 {trip.trip_id} 已完成合并，跳过处理")
                            continue
                        
                        if getattr(trip, 'is_merging', False):
                            logger.info(f"行程 {trip.trip_id} 正在合并中，跳过处理")
                            continue
                        
                        logger.info(f"行程 {trip.trip_id} 马上开始合并处理！")
                        # 标记正在合并
                        trip.is_merging = True
                        # trip.save()
                        trip.save(update_fields=['is_merging'])


                        logger.info(f"用户Id {user_id}, 行程 {trip.trip_id}  正在合并中...")
                        # 获取所有分片
                        chunks = ChunkFile.objects.filter(trip=trip).order_by('chunk_index')
                        merged_results = {'csv': None, 'det': None}

                        # 合并CSV文件
                        csv_chunks = chunks.filter(file_type='csv')
                        logger.info(f"行程 {trip.trip_id} CSV分片数量: {csv_chunks.count()} !")
                        if csv_chunks.exists():
                            merged_csv = pd.DataFrame()
                            for chunk in csv_chunks:
                                try:
                                    df = pd.read_csv(chunk.file_path)
                                    merged_csv = pd.concat([merged_csv, df])
                                except Exception as e:
                                    logger.error(f"读取CSV分片失败 {chunk.chunk_index}: {e}")

                            if not merged_csv.empty:
                                # 处理文件名
                                merged_csv_filename = None
                                for chunk in chunks:
                                    if hasattr(chunk, 'file_name') and chunk.file_name and 'spcialPoint' in chunk.file_name:
                                        merged_csv_filename = chunk.file_name.split('/')[-1]
                                        break
                                if not merged_csv_filename:
                                    merged_csv_filename = trip.file_name.split('/')[-1] if trip.file_name else f"merged_{trip.trip_id}.csv"

                                # 创建合并目录
                                merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip.trip_id))
                                os.makedirs(merged_dir, exist_ok=True)

                                # 保存合并文件
                                merged_path = os.path.join(merged_dir, merged_csv_filename)
                                merged_csv.to_csv(merged_path, index=False)
                                trip.merged_csv_path = merged_path
                                merged_results['csv'] = merged_path
                                logger.info(f"合并CSV文件成功.保存到 {merged_path}")

                        # 合并DET文件
                        det_chunks = chunks.filter(file_type='det')
                        logger.info(f"行程 {trip.trip_id} DET分片数量: {det_chunks.count()} !")
                        if det_chunks.exists():
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
                                        logger.error(f"读取DET分片失败 {chunk.chunk_index}: {e}")

                            trip.merged_det_path = det_merged_path
                            merged_results['det'] = det_merged_path
                            logger.info(f"合并DET文件成功.保存到 {det_merged_path}")

                        if merged_results['csv'] is not None and Path(merged_results['csv']).exists():
                            csv_merged_results.append(merged_results['csv'])
                        if merged_results['det'] is not None and Path(merged_results['det']).exists():
                            det_merged_results.append(merged_results['det'])


                        chunks = ChunkFile.objects.filter(trip=trip).order_by('chunk_index')
                        # 清理分片文件
                        for chunk in chunks:
                            try:
                                if os.path.exists(chunk.file_path):
                                    os.remove(chunk.file_path)
                                chunk.delete()
                            except Exception as e:
                                logger.error(f"清理分片文件失败 {chunk.chunk_index}: {e}")


                        try:
                            # 更新状态
                            trip.refresh_from_db()
                            if not trip.is_completed:
                                trip.is_completed = True
                                trip.is_merging = False
                                # trip.save()
                                update_fields = ['is_merging']
                                update_fields.append('is_completed')
                                if merged_results['csv']:
                                    trip.merged_csv_path = merged_results['csv']
                                    update_fields.append('merged_csv_path')
                                if merged_results['det']:
                                    trip.merged_det_path = merged_results['det']
                                    update_fields.append('merged_det_path')

                                trip.save(update_fields=update_fields)

                                logger.info(
                                    f"行程 {trip_id} 更新完成:\n"
                                    f"- 完成状态: {trip.is_completed}\n"
                                    f"- 合并状态: {trip.is_merging}\n"
                                    f"- CSV路径: {trip.merged_csv_path}\n"
                                    f"- DET路径: {trip.merged_det_path}"
                                )
                        except Exception as e:
                            logger.error(f"更新行程状态失败: {e}")
                            # 发生错误时回滚事务
                            transaction.set_rollback(True)

                    except Exception as e:
                        # 发生错误时重置合并状态
                        trip.is_merging = False
                        trip.save()
                        logger.error(f"合并文件失败: {e}")
                        return None, None

                return csv_merged_results, det_merged_results

            except DatabaseError as e:
                # 如果无法获取锁（其他进程正在处理），记录并跳过
                logger.warning(f"无法锁定相关行程记录，可能有其他进程正在处理: {e}")
                # 可以选择稍后重试或跳过
                return None, None
            
    except Exception as e:
        logger.error(f"合并文件失败: {e}")
        return None, None


# # NOTE: 单个行程合并版本
# def process_and_upload_files_sync(user_id, csv_path, det_path):
#     """同步版本的文件处理和上传函数"""
#     try:
#         tinder_os = TinderOS()
#         results = []
        
#         files_to_process = []
#         if csv_path and Path(csv_path).exists():
#             files_to_process.append((csv_path, 'csv'))
#         if det_path and Path(det_path).exists():
#             files_to_process.append((det_path, 'det'))        

#         # for file_path, file_type in [(csv_path, 'csv'), (det_path, 'det')]:
#         for file_path, file_type in files_to_process:
#             if not file_path:
#                 continue
                
#             file_name = Path(file_path)
#             model = file_name.name.split('_')[0]
#             time_line = file_name.name.split('_')[-1].split('.')[0]
            
#             # 获取品牌信息
#             middle_model = model_config.objects.filter(model=model).first()
#             if middle_model:
#                 brand = middle_model.brand
#                 upload_path = f"app_project/{user_id}/inference_data/{brand}/{model}/{time_line.split(' ')[0]}/{time_line}/{file_name.name}"
                
#                 # 上传文件
#                 tinder_os.upload_file('chek-app', upload_path, file_path)
                
#                 # 记录到数据库
#                 data_tos_model = tos_csv_app.objects.create(
#                     user_id=user_id,
#                     tos_file_path=upload_path,
#                     tos_file_type='inference'
#                 )

#                 data_tos_model.user_id = user_id
#                 data_tos_model.tos_file_path =upload_path
#                 data_tos_model.tos_file_type = 'inference'
#                 data_tos_model.save()

#                 results.append((file_type, upload_path))
                
#                 # # 可以选择删除本地文件
#                 # os.remove(file_path)
        
#         return True, results
#     except Exception as e:
#         logger.error(f"处理和上传文件失败: {e}")
#         return False, []




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




# # NOTE: 单个行程合并版本
# # 修改合并任务处理函数
# async def handle_merge_task(_id, trip_id, is_last_chunk=False):
#     """处理合并任务"""
#     try:
#         if is_last_chunk:
#             # 检查进程池状态
#             stats = get_process_pool_stats()
#             if stats and stats['available_workers'] <= 1:
#                 logger.warning(f"进程池资源紧张: 活跃进程{stats['active_processes']}/{stats['max_workers']}")
#                 await asyncio.sleep(0.5)

#             # 使用进程池执行合并操作
#             # trip = await sync_to_async(Trip.objects.select_for_update().get, thread_sensitive=True)(trip_id=trip_id)
#             # if trip.is_completed:
#             #     logger.info(f"行程 {trip_id} 已完成，跳过合并处理")
#             #     return 
            
#             # # 使用事务和select_for_update检查状态
#             # @sync_to_async(thread_sensitive=True)
#             # def check_trip_status():
#             #     with transaction.atomic():
#             #         trip = Trip.objects.select_for_update(nowait=True).get(trip_id=trip_id)
#             #         return trip.is_completed

#             # # 检查任务是否已完成
#             # if await check_trip_status():
#             #     logger.info(f"行程 {trip_id} 已完成，跳过合并处理")
#             #     return 


#             loop = asyncio.get_event_loop()
#             csv_path, det_path = await loop.run_in_executor(
#                 process_executor,
#                 merge_files_sync,
#                 _id,
#                 trip_id
#             )
            
#             is_valid_interval = False
#             if csv_path:
#                 is_valid_interval = await loop.run_in_executor(
#                         process_executor,
#                         get_csv_time_interval,
#                         csv_path
#                 )

#             if (csv_path or det_path) and is_valid_interval:
#                 # 在进程池中执行文件处理和上传
#                 success, results = await loop.run_in_executor(
#                     process_executor,
#                     process_and_upload_files_sync,
#                     _id,
#                     csv_path,
#                     det_path
#                 )
                
#                 if success:
#                     logger.info(f"文件处理和上传成功: {results}")
#                 else:
#                     logger.error("文件处理和上传失败")

#             if csv_path:
#                 # 使用_id查询account models中用户信息
#                 user = await loop.run_in_executor(
#                     process_executor,
#                     get_user_sync,
#                     _id
#                 )
#                 if user and is_valid_interval:
#                     # 处理行程数据
#                     success, message = await loop.run_in_executor(
#                         process_executor,
#                         process_wechat_data_sync,
#                         user,
#                         csv_path
#                     )
#                     if success:
#                         logger.info(f"进程池处理行程数据成功，{message}")
#                     else:
#                         logger.error(f"进程池处理数据失败，用户: {user.name}, 错误信息: {message}")
#                 else:
#                     logger.error(f"用户 {_id} 不存在, 无法处理行程数据 {csv_path}.")

#                 if not is_valid_interval:    
#                     logger.warning(f"CSV文件 {csv_path} 时间间隔小于300秒，跳过处理")
#                 else:
#                     logger.info(f"CSV文件 {csv_path} 时间间隔大于300秒，正常处理")

#             if (csv_path is not None) and Path(csv_path).exists():
#                 os.remove(str(csv_path))
#                 logger.info(f'删除合并csv文件: {csv_path}')

#             if (det_path is not None) and Path(det_path).exists():
#                 os.remove(str(det_path))
#                 logger.info(f'删除合并det文件: {det_path}')

#         else:
#             # 检查是否需要触发自动合并
#             await check_timeout_trip(_id, trip_id)
            
#     except Exception as e:
#         logger.error(f"合并任务处理失败: {e}")


# 
async def handle_merge_task(_id, trip_id, is_last_chunk=False):
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
                trip_id
            )

            # csv_path_list, det_path_list = await loop.run_in_executor(
            #     process_executor,
            #     merge_files_sync,
            #     _id,
            #     trip_id
            # )
            
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
                    process_and_upload_files_sync,
                    _id,
                    csv_path_list,
                    det_path_list
                )
                
                if success:
                    logger.info(f"文件处理和上传成功: {results}")
                else:
                    logger.error("文件处理和上传失败")

            if (csv_path_list and isinstance(csv_path_list, list) and len(csv_path_list) > 0):
                # 使用_id查询account models中用户信息
                user = await loop.run_in_executor(
                    process_executor,
                    get_user_sync,
                    _id
                )
                if user and is_valid_interval:
                    # 处理行程数据
                    success, message = await loop.run_in_executor(
                        process_executor,
                        process_wechat_data_sync,
                        user,
                        csv_path_list
                    )
                    if success:
                        logger.info(f"进程池处理行程数据成功，{message}")
                    else:
                        logger.error(f"进程池处理数据失败，用户: {user.name}, 错误信息: {message}")
                else:
                    logger.error(f"用户 {_id} 不存在, 或行程持续时间小于300s. 无法处理行程数据 {csv_path_list}.")

                if not is_valid_interval:    
                    logger.warning(f"CSV文件 {csv_path_list} 时间间隔小于300秒，跳过处理")
                else:
                    logger.info(f"CSV文件 {csv_path_list} 时间间隔大于300秒，正常处理")

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
def ensure_db_connection_and_merge(user_id, trip_id):
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
            return merge_files_sync(user_id, trip_id)
        except Exception as e:
            logger.error(f"数据库连接检查失败 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                # 关闭所有连接并等待重试
                from django.db import connections
                connections.close_all()
                time.sleep(retry_delay * (attempt + 1))
            else:
                # 最后一次尝试也失败
                logger.error(f"数据库连接在{max_retries}次尝试后仍然失败")
                return None, None


def is_valiad_phone_number_sync(phone):
    
    pattern = r"^1[3-9]\d{9}$"

    if re.match(pattern, phone):
        return True
    else:
        return False

# # NOTE: 单个行程合并版本
# # 小程序proto1.0版本
# # 没有上传中间结果
# def process_wechat_data_sync(user, file_path):
#     try:
#         if file_path is None or not os.path.exists(file_path):
#             logger.error(f"process_wechat_data_sync 文件不存在: {file_path}")
#             return False, "文件不存在"
        
#         file_name = file_path.split('/')[-1]
#         infos = file_name.split('_')
#         if len(infos) > 3:
#             model = infos[0]
#             hardware_version = infos[1]
#             software_version = infos[2]
#             logger.info(f"开始处理用户 {user.name} 的行程数据: {file_name}")

#             if is_valiad_phone_number_sync(user.phone):
#                 # # NOTE: 确保phone和小程序phone对应一致
                
#                 process_journey(file_path, 
#                                 user_id=100000, 
#                                 user_name=user.name, 
#                                 phone=user.phone, 
#                                 car_brand =model, 
#                                 car_model='', 
#                                 car_hardware_version=hardware_version,
#                                 car_software_version=software_version
#                 )
#                 return True, f"数据处理成功. 用户名: {user.name}, 行程数据: {file_name}"
#             else:
#                 logger.warning(f"用户手机号 {user.phone} 格式不正确, 行程未处理！")
#                 return False, "手机号格式不正确"    
#         else:
#             logger.warning(f"file name:{file_name} 格式不正确, 行程未处理！")
#             return False, "文件名格式不正确"
#     except Exception as e:
#         logger.error(f"处理app数据失败: {e}")
#         return False, str(e)


# NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
# 小程序proto1.0版本
# 没有上传中间结果
def process_wechat_data_sync(user, file_path_list):
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
                
                # # saas 协议
                # process_journey(file_path_list, 
                #                 user_id=100000, 
                #                 user_name=user.name, 
                #                 phone=user.phone, 
                #                 car_brand =model, 
                #                 car_model='', 
                #                 car_hardware_version=hardware_version,
                #                 car_software_version=software_version
                # )

                # 小程序协议
                process_csv(file_path_list, 
                                user_id=100000, 
                                user_name=user.name, 
                                phone=user.phone, 
                                car_brand =model, 
                                car_model='', 
                                car_version=software_version
                )

                return True, f"数据处理成功. 用户名: {user.name}, 行程数据: {file_name}"
            else:
                logger.warning(f"用户手机号 {user.phone} 格式不正确, 行程未处理！")
                return False, "手机号格式不正确"    
        else:
            logger.warning(f"file name:{file_name} 格式不正确, 行程未处理！")
            return False, "文件名格式不正确"
    except Exception as e:
        logger.error(f"处理app数据失败: {e}")
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
    
# #NOTE: 单个行程合并版本
# def get_csv_time_interval(csv_path):
#     """
#     获取CSV文件时间间隔
#     """
#     try:
#         if csv_path is None or not os.path.exists(csv_path):
#             logger.error(f"CSV文件不存在: {csv_path}")
#             return False
        
#         df = pd.read_csv(csv_path)
#         if 'time' in df.columns:
#             min_time = df['time'].min()
#             max_time = df['time'].max()
#             time_interval = max((max_time - min_time), 0)
#             return time_interval > 300
#         else:
#             logger.error(f"CSV文件中没有time列")
#             return False
        
#     except Exception as e:
#         logger.error(f"获取时间间隔失败: {e}")
#         return False


# NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
def get_csv_time_interval(csv_path_list):
    """
    获取CSV文件时间间隔
    """
    try:
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
        if total_time > 300:
            logger.info(f"CSV文件 {csv_path} 时间间隔大于300秒，正常处理")
            return True
        else:
            logger.warning(f"CSV文件 {csv_path} 时间间隔小于300秒，不做处理")
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
            logger.error(f"数据库连接检查失败: {e}")
            # 关闭连接以便重新建立
            try:
                connections['default'].close()
            except:
                pass
        finally:
            time.sleep(60)  # 每60秒检查一次