import os
import pandas as pd
import logging
import asyncio
import time
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from django.db import transaction
from asgiref.sync import sync_to_async
from .models import Trip, ChunkFile

logger = logging.getLogger(__name__)

# 创建线程池执行器
executor = ThreadPoolExecutor(max_workers=4)

async def save_chunk_file(trip_id, chunk_index, file_obj, file_type):
    """保存上传的分片文件（异步版本）"""
    try:
        # 获取或创建Trip
        trip, created = await sync_to_async(Trip.objects.get_or_create, thread_sensitive=True)(id=trip_id)
        
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

async def merge_files(trip_id):
    """合并文件的后台任务（异步版本）"""
    try:
        # 使用sync_to_async包装事务操作
        @sync_to_async(thread_sensitive=True)
        def _merge_files_sync():
            with transaction.atomic():
                trip = Trip.objects.select_for_update().get(id=trip_id)
                
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
                    
                    if not merged_csv.empty:
                        # 创建合并目录
                        merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip_id))
                        os.makedirs(merged_dir, exist_ok=True)
                        
                        # 保存合并文件
                        merged_path = os.path.join(merged_dir, 'merged.csv')
                        merged_csv.to_csv(merged_path, index=False)
                        trip.merged_csv_path = merged_path
                
                # 合并DET文件
                det_chunks = chunks.filter(file_type='det')
                if det_chunks.exists():
                    merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged', str(trip_id))
                    os.makedirs(merged_dir, exist_ok=True)
                    
                    merged_path = os.path.join(merged_dir, 'merged.det')
                    with open(merged_path, 'wb') as outfile:
                        for chunk in det_chunks:
                            try:
                                with open(chunk.file_path, 'rb') as infile:
                                    outfile.write(infile.read())
                            except Exception as e:
                                logger.error(f"读取DET分片失败 {chunk.chunk_index}: {e}")
                    
                    trip.merged_det_path = merged_path
                
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
                
                # 这里可以添加数据处理和上传TOS的逻辑
                
                return True
        
        # 执行同步操作
        return await _merge_files_sync()
    except Exception as e:
        logger.error(f"合并文件失败: {e}")
        return False

async def start_merge_async(trip_id):
    """启动异步合并任务"""
    try:
        result = await merge_files(trip_id)
        logger.info(f"合并任务完成，结果: {result}")
        return result
    except Exception as e:
        logger.error(f"合并任务异常: {e}")
        return False

# 定期检查超时任务
async def check_timeout_trips():
    """检查超时的上传任务并触发合并（异步版本）"""
    from django.utils import timezone
    from datetime import timedelta
    
    while True:
        try:
            # 查找所有未完成且超过30分钟未更新的Trip
            timeout = timezone.now() - timedelta(minutes=30)
            
            # 使用sync_to_async获取超时的Trip
            trips = await sync_to_async(list, thread_sensitive=True)(
                Trip.objects.filter(is_completed=False, last_update__lt=timeout)
            )
            
            # 为每个超时的Trip创建合并任务
            tasks = []
            for trip in trips:
                logger.info(f"检测到超时Trip {trip.id}，开始异步合并")
                task = asyncio.create_task(start_merge_async(trip.id))
                tasks.append(task)
            
            # 等待所有任务完成
            if tasks:
                await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"超时检查失败: {e}")
        
        # 每5分钟检查一次
        await asyncio.sleep(300)

# 启动超时检查任务
def start_timeout_checker():
    """启动超时检查器"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(check_timeout_trips())

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
        trip = await sync_to_async(Trip.objects.get, thread_sensitive=True)(id=trip_id)
        
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

async def check_timeout_trip(trip_id):
    """检查单个行程是否超时（异步版本）"""
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # 获取Trip对象
        trip = await sync_to_async(Trip.objects.get, thread_sensitive=True)(id=trip_id)
        
        # 检查是否已经完成
        if trip.is_completed:
            return
        
        # 检查是否超时
        if timezone.now() - trip.last_update > timedelta(minutes=30):
            logger.info(f"Trip {trip_id} 上传超时，开始异步合并")
            await start_merge_async(trip_id)
    except Exception as e:
        logger.error(f"检查行程超时失败: {e}")

async def upload_chunk_file(trip_id, chunk_index, file_obj, file_type, metadata=None):
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
            if 'device_id' in metadata:
                defaults['device_id'] = metadata['device_id']
            if 'car_name' in metadata:
                defaults['car_name'] = metadata['car_name']
            if 'start_time' in metadata:
                defaults['start_time'] = metadata['start_time']
            if 'total_chunks' in metadata:
                defaults['total_chunks'] = metadata['total_chunks']
        
        trip, created = await sync_to_async(Trip.objects.get_or_create, thread_sensitive=True)(
            id=trip_id, 
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
            if 'start_time' in metadata:
                chunk_defaults['start_time'] = metadata['start_time']
            if 'end_time' in metadata:
                chunk_defaults['end_time'] = metadata['end_time']
            if 'checksum' in metadata:
                chunk_defaults['checksum'] = metadata['checksum']
        
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
        trip = await sync_to_async(Trip.objects.get, thread_sensitive=True)(id=trip_id)
        
        # 开始合并
        result = await start_merge_async(trip_id)
        
        if result:
            return True, "行程合并成功"
        else:
            return False, "行程合并失败"
    except Exception as e:
        logger.error(f"强制合并行程失败: {e}")
        return False, f"强制合并行程失败: {str(e)}"

# 使用线程启动异步循环
import threading
timeout_thread = threading.Thread(target=start_timeout_checker)
timeout_thread.daemon = True
timeout_thread.start()