from django.db import models
import uuid
# Create your models here.
from django.db import models
from accounts.models import User

class Data(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True, blank=True)
    title = models.CharField(max_length=100)
    content = models.TextField()

    def __str__(self):
        return self.title

# Create your models here.
class model_config(models.Model):

    """
         CREATE TABLE IF NOT EXISTS  model_config(
             id VARCHAR(255) PRIMARY KEY,
             model VARCHAR(255),
             hardware_config_version VARCHAR(255),
             software_config_version VARCHAR(2000)

    """
    # id = models.CharField(max_length=255, primary_key=True, verbose_name='model_config id')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False, verbose_name='唯一标识ID')
    brand = models.CharField(max_length=255, blank=True, null=True, verbose_name='model_config brand')
    model = models.CharField(max_length=255, blank=True, null=True, verbose_name='model_config model')
    hardware_config_version = models.CharField(max_length=255, blank=True, null=True, verbose_name='model_config hardware_config_version')
    software_config_version = models.CharField(max_length=2000, blank=True, null=True, verbose_name='model_config software_config_version')

    class Meta:
        db_table = 'model_config'

class version_vault(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False, verbose_name='唯一标识ID')
    package_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='package name')
    version_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='version name')
    chanel = models.CharField(max_length=255, blank=True, null=True, verbose_name='channel')
    link = models.CharField(max_length=255, blank=True, null=True, verbose_name='link')
    md5_value = models.CharField(max_length=255, blank=True, null=True, verbose_name='md5_value')
    version_code = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'version_vault'

class model_config_app_update(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True, blank=True)
    updated_date = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    created_brand = models.CharField(max_length=100,editable=False, verbose_name='新建品牌名',null=True, blank=True)
    created_model = models.CharField(max_length=100,editable=False, verbose_name='新建车型',null=True, blank=True)
    created_hardware_config_version = models.CharField(max_length=100,editable=False, verbose_name='新建硬件版本',null=True, blank=True)
    created_software_config_version = models.CharField(max_length=100,editable=False, verbose_name='新建软件版本',null=True, blank=True)
    check_status = models.CharField(max_length=100,editable=True, verbose_name='审核状态')
    check_manager = models.CharField(max_length=100,editable=True, verbose_name='审核人员')

    class Meta:
        db_table = 'model_config_app_update'

