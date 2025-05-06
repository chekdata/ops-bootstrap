from django.db import models
import os
import uuid
from accounts.models import User
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