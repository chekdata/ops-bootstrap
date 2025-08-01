from django.db import models
import os
import uuid
import json
from accounts.models import User,CoreUser
from datetime import  datetime
from django.utils import timezone

class analysis_data_app(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False, verbose_name='唯一标识ID')
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True, blank=True)

    updated_date = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    model = models.CharField(max_length=255,editable=False,null=True, verbose_name='用户使用车型')

    intervention = models.IntegerField(default=0, blank=True, null=True,verbose_name="接管次数")
    intervention_risk = models.IntegerField(default=0,blank=True, null=True, verbose_name="危险接管次数")
    mpi = models.FloatField(default=0.0, blank=True, null=True,verbose_name="接管里程")
    mpi_risk = models.FloatField(default=0.0,blank=True, null=True, verbose_name="危险接管里程")
    total_mile = models.FloatField(default=0.0,blank=True, null=True, verbose_name="总里程")
    noa_mile = models.FloatField(default=0.0,blank=True, null=True, verbose_name="NOA总里程")
    lcc_mile = models.FloatField(default=0.0,blank=True, null=True, verbose_name="LCC总里程")
    noa_lcc_mile = models.FloatField(default=0.0,blank=True, null=True, verbose_name="NOA LCC总里程")
    standby_mile = models.FloatField(default=0.0,blank=True, null=True, verbose_name="人类驾驶里程")

    class Meta:
        db_table = 'analysis_data_app'


class tos_csv_app(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='唯一标识ID')
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True, blank=True)

    updated_date = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    tos_file_path = models.CharField(max_length=2000, editable=False, verbose_name='tos存储路径')
    tos_file_type =  models.CharField(max_length=2000, editable=False, verbose_name='tos存储文件类型 inference/analysis')

    approved_status = models.IntegerField(default=0,verbose_name='审核状态：0 未审核， 1 审核通过 2 审核不通过')
    class Meta:
        db_table = 'tos_csv_app'


class Trip(models.Model):
    trip_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='行程id')
    user_id = models.CharField(max_length=50, blank=True, verbose_name='app用户id')
    task_id = models.CharField(max_length=50, null=True,blank=True, verbose_name='之家任务id')
    autohome_phone = models.CharField(max_length=11, null=True,blank=True, verbose_name='之家任务输入手机号')
    car_name = models.CharField(max_length=100, verbose_name='车型名')
    file_name = models.CharField(max_length=500, blank=True, verbose_name='行程文件名')
    is_completed = models.BooleanField(default=False, verbose_name='行程是否已完成合并')
    is_merging = models.BooleanField(default=False, verbose_name='行程正在合并中')
    first_update = models.DateTimeField(auto_now_add=True, verbose_name='行程第一次分片接收时间') #记录第一次生成时间，后面不做更新
    last_update = models.DateTimeField(auto_now=True, verbose_name='行程最后一次分片接收时间')
    merged_csv_path = models.CharField(max_length=255, null=True, blank=True, verbose_name='行程合并csv文件路径')
    merged_det_path = models.CharField(max_length=255, null=True, blank=True, verbose_name='行程合并det文件路径')
    hardware_version = models.CharField(max_length=64, null=True, blank=True, verbose_name='行程硬件版本')
    software_version = models.CharField(max_length=64, null=True, blank=True, verbose_name='行程软件版本')
    device_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='行程生成设备id')
    merge_into_current = models.BooleanField(default=True, verbose_name='异常行程合并到当前行程')
    set_journey_status = models.BooleanField(default=False, verbose_name='异常行程是否已设置行程状态')
    trip_status = models.CharField(max_length=50, blank=True, verbose_name='行程状态')
    reported_car_name = models.CharField(max_length=100, null=True, blank=True,verbose_name='上报模式车型名')
    reported_hardware_version = models.CharField(max_length=64, null=True, blank=True, default=None, verbose_name='上报模式行程硬件版本')
    reported_software_version = models.CharField(max_length=64, null=True, blank=True, verbose_name='上报模式行程软件版本')
    parent_trip_id = models.UUIDField(null=True, blank=True, verbose_name='父行程ID', help_text='如果是子行程，则指向父行程的ID')
    record_upload_tos_status = models.CharField(max_length=50,default=False, verbose_name='行程音频文件落库状态')
    record_audio_file_path = models.CharField(max_length=500, null=True, blank=True, verbose_name='行程音频文件路径')
    csv_chunk_count = models.IntegerField(default=0, verbose_name='行程csv分片数量')
    csv_chunk_lose = models.IntegerField(default=0, verbose_name='行程csv分片丢失数量')
    det_chunk_count = models.IntegerField(default=0, verbose_name='行程det分片数量')
    det_chunk_lose = models.IntegerField(default=0, verbose_name='行程det分片丢失数量')
    is_less_than_5min = models.BooleanField(default=False, verbose_name='行程是否小于5分钟')


    def __str__(self):
        return f"trip {self.car_name}"
    
    class Meta:
        db_table = 'trip'

class ChunkFile(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField()
    file_path = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)  # 'csv' 或 'det'
    file_name = models.CharField(max_length=500, blank=True)
    upload_time = models.DateTimeField(auto_now_add=True)
    car_name = models.CharField(max_length=100)
    hardware_version = models.CharField(max_length=64, null=True, blank=True)
    software_version = models.CharField(max_length=64, null=True, blank=True)
    device_id = models.CharField(max_length=255, null=True, blank=True)
    # chunk_status = models.CharField(max_length=50, blank=True, verbose_name='行程分片状态')

    class Meta:
        unique_together = ('trip', 'chunk_index', 'file_type')
        db_table = 'chunkfile'
        
    def __str__(self):
        return f"chunk {self.chunk_index} of {self.trip.car_name}"
    

class RecoredChunkFile(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='recored_chunks')
    chunk_index = models.IntegerField()
    file_path = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)  # 'csv' 或 'det'
    file_name = models.CharField(max_length=500, blank=True)
    upload_time = models.DateTimeField(auto_now_add=True)
    car_name = models.CharField(max_length=100)
    hardware_version = models.CharField(max_length=64, null=True, blank=True)
    software_version = models.CharField(max_length=64, null=True, blank=True)
    device_id = models.CharField(max_length=255, null=True, blank=True)
    # chunk_status = models.CharField(max_length=50, blank=True, verbose_name='行程分片状态')

    class Meta:
        unique_together = ('trip', 'chunk_index', 'file_type')
        db_table = 'RecoredChunkFile'
        
    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.trip.car_name}"


class Journey(models.Model):
    """
    车辆行程评测数据模型
    """
    id = models.AutoField(primary_key=True)
    task_id = models.CharField(max_length=50, null=True,blank=True, verbose_name='之家任务id')
    autohome_phone = models.CharField(max_length=11, null=True,blank=True, verbose_name='之家任务输入手机号')
    brand = models.CharField(max_length=64, null=True, blank=True, verbose_name='车型')
    model = models.CharField(max_length=64, null=True, blank=True, verbose_name='车型名')
    hardware_config = models.CharField(max_length=64, null=False, verbose_name='车机硬件版本编码')
    software_config = models.CharField(max_length=64, null=False, verbose_name='车机软件版本编码')
    journey_id = models.CharField(max_length=64, null=False, verbose_name='评测数据编码')
    user_uuid = models.CharField(max_length=64, null=False, verbose_name='用户在车控产品中ID')
    journey_category = models.IntegerField(null=False, verbose_name='报告类别')
    city_status_code = models.IntegerField(null=True, blank=True, verbose_name='是否是合并数据')
    city = models.CharField(max_length=255, null=True, blank=True, verbose_name='评测城市')
    scene_status_code = models.IntegerField(null=True, blank=True, verbose_name='是否是场景数据')
    scene = models.CharField(max_length=255, null=True, blank=True, verbose_name='场景说明')
    polar_star = models.JSONField(null=True, blank=True, verbose_name='车控北极星指标')
    
    # 里程相关
    auto_mileages = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾总里程')
    total_mileages = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='测试总里程')
    
    # 帧数相关
    frames = models.IntegerField(null=True, blank=True, verbose_name='测试总帧数')
    auto_frames = models.IntegerField(null=True, blank=True, verbose_name='智驾帧数')
    noa_frames = models.IntegerField(null=True, blank=True, verbose_name='noa智驾帧数')
    lcc_frames = models.IntegerField(null=True, blank=True, verbose_name='lcc智驾帧数')
    driver_frames = models.IntegerField(null=True, blank=True, verbose_name='driver驾驶帧数')
    
    # 速度相关
    auto_speed_average = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾平均车速')
    auto_max_speed = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾最大车速')
    
    # 接管相关
    invervention_risk_proportion = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='危险接管占比')
    invervention_mpi = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='接管里程')
    invervention_risk_mpi = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='危险接管里程')
    invervention_cnt = models.IntegerField(null=True, blank=True, verbose_name='接管次数')
    invervention_risk_cnt = models.IntegerField(null=True, blank=True, verbose_name='危险接管次数')
    
    # NOA相关
    noa_invervention_risk_mpi = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='noa危险接管里程')
    noa_invervention_mpi = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='noa接管里程')
    noa_invervention_risk_cnt = models.IntegerField(null=True, blank=True, verbose_name='noa危险接管次数')
    noa_auto_mileages = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='noa智驾里程')
    noa_auto_mileages_proportion = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='noa智驾里程占比')
    noa_invervention_cnt = models.IntegerField(null=True, blank=True, verbose_name='noa接管次数')
    
    # LCC相关
    lcc_invervention_risk_mpi = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='lcc危险接管里程')
    lcc_invervention_mpi = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='lcc接管里程')
    lcc_invervention_risk_cnt = models.IntegerField(null=True, blank=True, verbose_name='lcc危险接管次数')
    lcc_auto_mileages = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='lcc智驾里程')
    lcc_auto_mileages_proportion = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='lcc智驾里程占比')
    lcc_invervention_cnt = models.IntegerField(null=True, blank=True, verbose_name='lcc接管次数')
    
    # 智驾急刹相关
    auto_dcc_max = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾急刹最大加速度')
    auto_dcc_frequency = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾急刹里程')
    auto_dcc_cnt = models.IntegerField(null=True, blank=True, verbose_name='智驾急刹次数')
    auto_dcc_duration = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾急刹总时长')
    auto_dcc_average_duration = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾急刹平均时长')
    auto_dcc_average = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾急刹平均加速度')
    
    # 智驾急加速相关
    auto_acc_max = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾急加速最大加速度')
    auto_acc_frequency = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾急加速里程')
    auto_acc_cnt = models.IntegerField(null=True, blank=True, verbose_name='智驾急加速次数')
    auto_acc_duration = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾急加速总时长')
    auto_acc_average_duration = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾急加速平均时长')
    auto_acc_average = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾急加速平均加速度')
    
    # 人类驾驶相关
    driver_mileages = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='人类驾驶里程')
    driver_dcc_max = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='车主急刹最大加速度')
    driver_dcc_frequency = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='车主急刹频次')
    driver_acc_max = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='车主急加速最大加速度')
    driver_acc_frequency = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='车主急加速频次')
    driver_speed_average = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='车主平均车速')
    driver_speed_max = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='车主最高车速')
    driver_dcc_cnt = models.IntegerField(null=True, blank=True, verbose_name='车主急刹次数')
    driver_acc_cnt = models.IntegerField(null=True, blank=True, verbose_name='车主急加速次数')
    driver_acc_average =models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='车主平均急加速加速度')
    driver_dcc_average =models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='车主平均急刹车加速度')

    # 行程时间相关
    journey_start_time = models.DateTimeField(null=True, blank=True, verbose_name='行程开始时间')
    journey_end_time = models.DateTimeField(null=True, blank=True, verbose_name='行程结束时间')
    # journey_generated_time = models.DateTimeField(null=True, blank=True, verbose_name='行程落库时间')
    journey_status = models.CharField(max_length=64, null=True, blank=True, verbose_name='行程状态')
    duration = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='智驾时长')
    auto_safe_duration = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='安全智驾时长')
    lcc_safe_duration = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='lcc安全智驾时长')
    noa_safe_duration = models.DecimalField(max_length=10, decimal_places=5, null=True, blank=True, verbose_name='noa安全智驾时长')

    # 文件相关
    pdf_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='文件名称')
    pdf_path = models.CharField(max_length=255, null=True, blank=True, verbose_name='文件路径')
    auto_MBTI = models.CharField(max_length=255, null=True, blank=True, verbose_name='智驾MBTI')
    standby_MBTI = models.CharField(max_length=255, null=True, blank=True, verbose_name='人驾MBTI')

    # 行程所属关系相关
    is_sub_journey = models.BooleanField(default=False, verbose_name='是否是子行程')
    is_less_than_5min = models.BooleanField(default=False, verbose_name='行程是否小于5分钟')
    parent_trip_id = models.UUIDField(null=True, blank=True, verbose_name='父行程ID', help_text='如果是子行程，则指向父行程的ID')

    # 音频相关
    record_upload_tos_status = models.CharField(max_length=50, null=True, blank=True, verbose_name='行程音频文件落库状态')
    record_audio_file_path = models.CharField(max_length=500, null=True, blank=True, verbose_name='行程音频文件路径')

    # 长图相关
    longimg_upload_tos_status = models.CharField(max_length=50, null=True, blank=True, verbose_name='行程音频文件落库状态')
    longimg_file_path = models.CharField(max_length=500, null=True, blank=True, verbose_name='行程音频文件路径')

    # 创建信息
    # created_by = models.CharField(max_length=50, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    
    cover_image = models.CharField(max_length=255, null=True, blank=True, verbose_name='行程音频文件路径') 
    
    #文本信息
    gpt_comment = models.CharField(max_length=30, null=True, blank=True, verbose_name='gpt评价')

    class Meta:
        managed = False
        db_table = 'total_journey'
        app_label = 'core_user'     # 指定应用标签为 core_user
        verbose_name = '行程评测数据'
        verbose_name_plural = '行程评测数据'
    
    def __str__(self):
        return f"Journey {self.journey_id}"
    


class JourneyInterventionGps(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='自增ID')
    journey_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='关联的行程 ID', db_index=True)
    created_date = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    frame_id =   models.IntegerField(null=False, verbose_name='帧数id')
    gps_lon = models.DecimalField(max_length=20, decimal_places=15, null=True, blank=True, verbose_name='gps_lon')
    gps_lat = models.DecimalField(max_length=20, decimal_places=15, null=True, blank=True, verbose_name='gps_lat')
    gps_datetime = models.DateTimeField(null=True, blank=True, verbose_name='gps时间')
    type =  models.CharField(max_length=50, null=True, blank=True, verbose_name='gps点位类型')
    is_risk = models.BooleanField(default=False, verbose_name='是否危险接管')
    identification_type =  models.CharField(max_length=50, null=True, blank=True, verbose_name='gps识别类型')
    created_date = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    class Meta:
        managed = False
        db_table = 'journey_gps_intervention'
        app_label = 'core_user'     # 指定应用标签为 core_user
        verbose_name = '行程评测数据接管点位'
        verbose_name_plural = '行程评测数据接管点位'
    
    def __str__(self):
        return f"Journey {self.journey_id}"



class Reported_Journey(models.Model):
    """
    车辆行程评测数据模型
    """
    id = models.AutoField(primary_key=True)
    brand = models.CharField(max_length=64, null=True, blank=True, verbose_name='车型')
    model = models.CharField(max_length=64, null=True, blank=True, verbose_name='车型名')
    hardware_config = models.CharField(max_length=64, null=False, verbose_name='车机硬件版本编码')
    software_config = models.CharField(max_length=64, null=False, verbose_name='车机软件版本编码')
    journey_id = models.CharField(max_length=64, null=False, verbose_name='评测数据编码')
    user_uuid = models.CharField(max_length=64, null=False, verbose_name='用户在车控产品中ID')
    journey_status = models.CharField(max_length=64, null=True, blank=True, verbose_name='行程状态')
    
    # 文件相关
    csv_tos_path = models.CharField(max_length=500, null=True, blank=True, verbose_name='csv文件tos路径')
    det_tos_path = models.CharField(max_length=500, null=True, blank=True, verbose_name='det文件tos路径')

    reported_car_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='上报模式车型名')
    reported_hardware_version = models.CharField(max_length=64, null=True, blank=True, verbose_name='上报模式行程硬件版本')
    reported_software_version = models.CharField(max_length=64, null=True, blank=True, verbose_name='上报模式行程软件版本')

    # 创建信息
    # created_by = models.CharField(max_length=50, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'reported_journey'
        app_label = 'core_user'     # 指定应用标签为 core_user
        verbose_name = '行程评测数据'
        verbose_name_plural = '行程评测数据'
    
    def __str__(self):
        return f"Journey {self.journey_id}"
    



class JourneyGPS(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='唯一标识 ID')
    id = models.AutoField(primary_key=True, verbose_name='自增ID')
    journey_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='关联的行程 ID', db_index=True)
    # gps = models.CharField(max_length=255, blank=True, null=True, verbose_name='GPS 信息')
    gps = models.TextField(blank=True, null=True, verbose_name='GPS 信息')
    segment_id = models.IntegerField(null=True, verbose_name='GPS 分段 ID')
    driver_status = models.CharField(max_length=50, blank=True, null=True, verbose_name='驾驶员状态')
    road_scene = models.CharField(max_length=50, blank=True, null=True, verbose_name='道路')
    city = models.CharField(max_length=255, blank=True, null=True, verbose_name='城市')
    created_date = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'journey_gps'
        app_label = 'core_user'


class JourneyGPSTracking(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='自增ID')
    journey_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='关联的行程 ID', db_index=True)

    gps_tracking = models.JSONField(blank=True, null=True,verbose_name='手动打点数据')
    auto_gps_tracking = models.JSONField(blank=True, null=True,verbose_name='自动打点数据')
    created_date = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'journey_gps_tracking'
        app_label = 'core_user'



class HotBrandVehicle(models.Model):
    _id = models.CharField(primary_key=True, max_length=36, verbose_name='ID')
    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name='品牌')
    brand_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='品牌类型')
    cover_image = models.CharField(max_length=255, blank=True, null=True, verbose_name='封面图片')
    model = models.CharField(max_length=100, blank=True, null=True, verbose_name='车型')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    power_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='动力类型')
    vehicle_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='车辆类型')
    hardware_config_version = models.CharField(max_length=50, blank=True, null=True, verbose_name='硬件配置版本')
    market_price_max = models.FloatField(blank=True, null=True, verbose_name='市场价格最大值')
    market_price_min = models.FloatField(blank=True, null=True, verbose_name='市场价格最小值')
    created_date = models.DateTimeField(blank=True, null=True, verbose_name='创建日期')
    update_date = models.DateTimeField(blank=True, null=True, verbose_name='更新日期')

    class Meta:
        db_table = 'hot_brand_vehicle'


class JourneyRecordLongImg(models.Model):
    """
    车辆行程评测数据模型
    """
    user_id = models.CharField(max_length=50, blank=True, verbose_name='app用户id')
    journey_id = models.CharField(primary_key=True, max_length=64, null=False, verbose_name='评测数据编码')
    # 音频相关
    record_upload_tos_status = models.CharField(max_length=50, null=True, blank=True, verbose_name='行程音频文件落库状态')
    record_audio_file_path = models.CharField(max_length=500, null=True, blank=True, verbose_name='行程音频文件路径')
    record_audio_zipfile_path = models.CharField(max_length=500, null=True, blank=True, verbose_name='行程音频文件打包路径，没有子行程的是包内只有父行程音频，有子行程的包内包含子行程音频')

    # 长图相关
    longimg_upload_tos_status = models.CharField(max_length=50, null=True, blank=True, verbose_name='行程音频文件落库状态')
    longimg_file_path = models.CharField(max_length=500, null=True, blank=True, verbose_name='行程音频文件路径')

    car_name = models.CharField(max_length=100, verbose_name='车型名')
    hardware_version = models.CharField(max_length=64, null=True, blank=True, verbose_name='行程硬件版本')
    software_version = models.CharField(max_length=64, null=True, blank=True, verbose_name='行程软件版本')
    device_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='行程生成设备id')

    # 行程app存储路径
    file_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='行程本地存储路径')

    task_id = models.CharField(max_length=50, null=True,blank=True, verbose_name='之家任务id')
    autohome_phone = models.CharField(max_length=11, null=True,blank=True, verbose_name='之家任务输入手机号')
    
    # 创建信息
    # created_by = models.CharField(max_length=50, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True,null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'journey_record_longimg'
        app_label = 'core_user'     # 指定应用标签为 core_user
        verbose_name = '行程评测数据音频&长图'
        verbose_name_plural = '行程评测数据音频&长图'
    
    def __str__(self):
        return f"JourneyRecordLongImg {self.journey_id}"