from django.db import models
import os
import uuid
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
    trip_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=50, blank=True)
    car_name = models.CharField(max_length=100)
    file_name = models.CharField(max_length=500, blank=True)
    is_completed = models.BooleanField(default=False)
    is_merging = models.BooleanField(default=False)
    first_update = models.DateTimeField(auto_now_add=True) #记录第一次生成时间，后面不做更新
    last_update = models.DateTimeField(auto_now=True)
    merged_csv_path = models.CharField(max_length=255, null=True, blank=True)
    merged_det_path = models.CharField(max_length=255, null=True, blank=True)
    hardware_version = models.CharField(max_length=64, null=True, blank=True)
    software_version = models.CharField(max_length=64, null=True, blank=True)
    device_id = models.CharField(max_length=255, null=True, blank=True)
    merge_into_current = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Trip {self.car_name}"
    
    class Meta:
        db_table = 'Trip'

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

    class Meta:
        unique_together = ('trip', 'chunk_index', 'file_type')
        db_table = 'ChunkFile'
        
    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.trip.car_name}"
    



# class CoreUser(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False, verbose_name='唯一标识ID')

#     app_id = models.CharField(max_length=50,blank=True, null=True)

#     mini_id = models.CharField(max_length=50,blank=True, null=True)

#     saas_id = models.CharField(max_length=50,blank=True, null=True)

#     app_phone = models.CharField(max_length=15, null=True, verbose_name='app手机号')
    
#     saas_phone = models.CharField(max_length=15, null=True, verbose_name='saas手机号')
    
#     mini_phone = models.CharField(max_length=15, null=True, verbose_name='小程序手机号')

#     class Meta:
#         managed = False
#         db_table = 'accounts_core_user'  # 替换为实际的表名
#         app_label = 'core_user'


class JourneyGPS(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='唯一标识 ID')
    id = models.AutoField(primary_key=True, verbose_name='自增ID')
    journey_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='关联的行程 ID', db_index=True)
    # gps = models.CharField(max_length=255, blank=True, null=True, verbose_name='GPS 信息')
    gps = models.TextField(blank=True, null=True, verbose_name='GPS 信息')
    segment_id = models.IntegerField(null=True, verbose_name='GPS 分段 ID')
    driver_status = models.CharField(max_length=50, blank=True, null=True, verbose_name='驾驶员状态')
    road_scene = models.CharField(max_length=50, blank=True, null=True, verbose_name='驾驶员状态')
    city = models.CharField(max_length=255, blank=True, null=True, verbose_name='城市')
    created_date = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'journey_gps'
        app_label = 'core_user'


class Journey(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='唯一标识ID')
    id = models.AutoField(primary_key=True)
    brand = models.CharField(max_length=50, blank=True, null=True)
    model = models.CharField(max_length=50, blank=True, null=True)
    software_config = models.CharField(max_length=50, blank=True, null=True)
    hardware_config =  models.CharField(max_length=50, blank=True, null=True)


    journey_id = models.CharField(max_length=50, blank=True, null=True)
    journey_name =  models.CharField(max_length=50, blank=True, null=True)
    user_uuid = models.CharField(max_length=50, blank=True, null=True)
    # user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, null=True, blank=True)
    journey_category =  models.IntegerField(null=True)
    city_status_code = models.IntegerField(null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    scene_status_code = models.CharField(max_length=50, blank=True, null=True)
    scene = models.CharField(max_length=255, blank=True, null=True)

    # polar_star 这里可以考虑用JSONField 来存储复杂结构，假设用TextField 简单存储
    polar_star = models.JSONField(blank=True, null=True)
    auto_mileages = models.FloatField(null=True)
    total_mileages = models.FloatField(null=True)
    frames = models.IntegerField(null=True)
    auto_frames = models.IntegerField(null=True)
    noa_frames = models.IntegerField(null=True)
    lcc_frames = models.IntegerField(null=True)
    driver_frames = models.IntegerField(null=True)
    auto_speed_average = models.FloatField(null=True)
    auto_max_speed = models.FloatField(null=True)
    invervention_risk_proportion = models.FloatField(null=True)
    invervention_mpi = models.FloatField(null=True)
    invervention_risk_mpi = models.FloatField(null=True)
    invervention_cnt = models.IntegerField(null=True)
    invervention_risk_cnt = models.IntegerField(null=True)
    noa_invervention_risk_mpi = models.FloatField(null=True)
    noa_invervention_mpi = models.FloatField(null=True)
    noa_invervention_risk_cnt = models.IntegerField(null=True)
    noa_auto_mileages = models.FloatField(null=True)
    noa_auto_mileages_proportion = models.FloatField(null=True)
    noa_invervention_cnt = models.IntegerField(null=True)
    lcc_invervention_risk_mpi = models.FloatField(null=True)
    lcc_invervention_mpi = models.FloatField(null=True)
    lcc_invervention_risk_cnt = models.IntegerField(null=True)
    lcc_auto_mileages = models.FloatField(null=True)
    lcc_auto_mileages_proportion = models.FloatField(null=True)
    lcc_invervention_cnt = models.IntegerField(null=True)
    auto_dcc_max = models.FloatField(null=True)
    auto_dcc_frequency = models.FloatField(null=True)
    auto_dcc_cnt = models.IntegerField(null=True)
    auto_dcc_duration = models.FloatField(null=True)
    auto_dcc_average_duration = models.FloatField(null=True)
    auto_dcc_average = models.FloatField(null=True)
    auto_acc_max = models.FloatField(null=True)
    auto_acc_frequency = models.FloatField(null=True)
    auto_acc_cnt = models.IntegerField(null=True)
    auto_acc_duration = models.FloatField(null=True)
    auto_acc_average_duration = models.FloatField(null=True)
    auto_acc_average = models.FloatField(null=True)
    driver_mileages = models.FloatField(null=True)
    driver_dcc_max = models.FloatField(null=True)
    driver_dcc_frequency = models.FloatField(null=True)
    driver_acc_max = models.FloatField(null=True)
    driver_acc_frequency = models.FloatField(null=True)
    driver_speed_average = models.FloatField(null=True)
    driver_speed_max = models.FloatField(null=True)
    driver_dcc_cnt = models.IntegerField(null=True)
    driver_acc_cnt = models.IntegerField(null=True)
    journey_start_time = models.DateTimeField(blank=True,null=True)
    journey_end_time = models.DateTimeField(blank=True,null=True)
    journey_status = models.CharField(max_length=50, blank=True, null=True)
    pdf_name = models.CharField(max_length=255, blank=True, null=True)
    pdf_path = models.CharField(max_length=255, blank=True, null=True)
    auto_MBTI = models.CharField(max_length=50, blank=True, null=True)
    standby_MBTI = models.CharField(max_length=50, blank=True, null=True)
    created_date = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'total_journey'  # 替换为实际的表名
        app_label = 'core_user'
    
