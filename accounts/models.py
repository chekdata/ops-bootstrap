from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
import datetime
from django.db.models  import JSONField

class UserManager(BaseUserManager):
    # def create_user(self, username, password=None, **extra_fields):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(name=username, **extra_fields)
        # user.set_password(password)
        user.save(using=self._db)
        return user

    # def create_superuser(self, username, password=None, **extra_fields):
    def create_superuser(self, username, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        # return self.create_user(username, password, **extra_fields)
        return self.create_user(username, **extra_fields)

# Create your models here.
class User(AbstractBaseUser, PermissionsMixin):

    objects = UserManager()
    # 用户名 (中文)
    name = models.CharField(max_length=100,  blank=True, null=True,verbose_name='用户名')

    # 唯一标识id
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False, verbose_name='唯一标识ID')

    # 外部联系人在微信开放平台的唯一身份标识
    unionid = models.CharField(max_length=100, blank=True, null=True, verbose_name='微信开放平台ID')

    # 个人头像
    pic = models.CharField(max_length=500, blank=True, null=True, verbose_name='个人头像')

    # 手机号
    phone = models.CharField(max_length=15, null=True, verbose_name='手机号')

    # 创建时间
    created_date = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    # 更新时间
    updated_date = models.DateTimeField(auto_now=True,null=True,   verbose_name='更新时间')

    # 个人签名
    desc = models.TextField(blank=True, null=True, verbose_name='个人签名')
    signature = models.TextField(blank=True, null=True, verbose_name='个人签名')

    #性别
    gender = models.CharField(max_length=5,blank=True, null=True, verbose_name='性别')

    # 用户App版本号
    app_software_config_version = models.CharField(max_length=100, blank=True, null=True, verbose_name='App版本号')

    # password = models.CharField(max_length=128, null=True, verbose_name='账号密码')  # 加密后的密码通常需要更多的存储空间
    model_config = JSONField(blank=True, null=True, verbose_name='车型配置数据')
    project_version = JSONField(blank=True, null=True, verbose_name='硬件信息')


    nickname = models.CharField(max_length=255, blank=True, null=True, verbose_name='微信昵称')

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['unionid']

    # def set_password(self, raw_password):
    #     self.password = make_password(raw_password)

    def __str__(self):
        return self.name

    # def save(self, *args, **kwargs):
    #     self.updated_date = timezone.now()
    #     return super(User, self).save(*args, **kwargs)

    class Meta:
        managed = True
        verbose_name = '用户'
        verbose_name_plural = '用户'

class User_SMS_Verification(models.Model):
    id = models.AutoField(primary_key=True)
    phone = models.CharField(max_length=15,blank=True, null=True)
    code = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f'{self.id} {self.phone}'

    def is_valid(self):
        # 验证码有效期为 10 分钟
        return (datetime.datetime.now(datetime.timezone.utc) - self.created_at) <= datetime.timedelta(minutes=10)

    class Meta:
        db_table = 'SMS_verify_login'

class SMSVerification(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=15,blank=True, null=True)
    code = models.IntegerField(max_length=6,blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.id} {self.user}'

    def is_valid(self):
        # 验证码有效期为 10 分钟
        return (datetime.datetime.now(datetime.timezone.utc) - self.created_at) <= datetime.timedelta(minutes=10)

    class Meta:
        db_table = 'SMS_verify'

class ProjectVersion(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=30,blank=True, null=True)
    project_version = models.CharField(max_length=30,blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.id}'


    class Meta:
        db_table = 'hardware_device'


class UserHistoryHardware(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    hardware_device = models.ForeignKey(ProjectVersion, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.id}'


    class Meta:
        db_table = 'user_historical_hardware'



class CoreUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False, verbose_name='唯一标识ID')

    app_id = models.CharField(max_length=50,blank=True, null=True)

    mini_id = models.CharField(max_length=50,blank=True, null=True)

    saas_id = models.CharField(max_length=50,blank=True, null=True)

    app_phone = models.CharField(max_length=15, null=True, verbose_name='app手机号')
    
    saas_phone = models.CharField(max_length=15, null=True, verbose_name='saas手机号')
    
    mini_phone = models.CharField(max_length=15, null=True, verbose_name='小程序手机号')

    class Meta:
        managed = False
        db_table = 'accounts_core_user'  # 替换为实际的表名
        app_label = 'core_user'