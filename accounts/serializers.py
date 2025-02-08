from rest_framework import serializers
# from django.contrib.auth.models import User
from rest_framework.validators import UniqueValidator
from accounts.models import User
from accounts.handle_unionid import  *
from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from accounts.handle_function import  *
from asgiref.sync import sync_to_async
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers




class UserSerializer(serializers.ModelSerializer):
    # unionid = serializers.CharField(
    #     validators=[UniqueValidator(queryset=User.objects.all())]
    # )
    code = serializers.CharField(write_only=True)

    def create(self, validated_data):
        code = validated_data.get('code')
        unionid = get_access_token(SOCIAL_AUTH_WEIXIN_appid, SOCIAL_AUTH_WEIXIN_secret, code)

        if not unionid or 'unionid' not in unionid.keys():
            raise serializers.ValidationError({'code': 500, 'message': '请输入正确的code'})

        unionid = unionid.get('unionid')
        if not User.objects.filter(unionid=unionid).exists():
            user = User.objects.create_user(
                username=validated_data.get('name', '这是一个名字'),
                unionid=unionid,  # 确保这里的键与模型的字段匹配
            )
            # 如果有额外的字段需要在创建时设置，可以在这里添加
            user.phone = validated_data.get('phone', None)
            user.save()
            return user
        else:
            raise serializers.ValidationError({'code': 500, 'message': '该微信用户已注册'})

    class Meta:
        model = User
        # fields = ['id']
        fields = ['id', 'code',]
        extra_kwargs = {
            'id': {'read_only': True},
            'phone': {'required': False},
            'pic': {'required': False}
        }


# @sync_to_async
def user_exists(unionid):
    return User.objects.filter(unionid=unionid).exists()

# @sync_to_async
def create_user_process(unionid):
    user = User.objects.create_user(
        username='这是一个名字',
        unionid=unionid,
    )
    user.save()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    id = None  # 注意，这可能不会直接工作，但意在表明我们不使用这个字段
    password = None  # 注意，这可能不会直接工作，但意在表明我们不使用这个字段
    code = serializers.CharField()

    def __init__(self,unionid, *args, **kwargs):
        super(TokenObtainSerializer, self).__init__(*args, **kwargs)
        # super().__init__(*args, **kwargs)
        # 移除 username 和 password 字段
        self.fields.pop('username', None)
        self.fields.pop('password', None)

        # 添加 code 字段
        self.fields['code'] = serializers.CharField()
        self.unionid = unionid


    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)

    def validate(self ):
        # try:
        #     code = attrs.get('code')
        #     unionid = get_access_token(SOCIAL_AUTH_WEIXIN_appid, SOCIAL_AUTH_WEIXIN_secret, code)

            # if not unionid or 'unionid' not in unionid.keys():
            #     raise serializers.ValidationError({'code': 500, 'message': '请输入正确的code'})
            #
            # unionid = unionid.get('unionid')
            union_id = self.unionid

            # if await sync_to_async(User.objects.filter(unionid=unionid).exists, thread_sensitive=True)():
            #     # user = User.objects.create_user(
            #     #     username='这是一个名字',
            #     #     unionid=unionid,  # 确保这里的键与模型的字段匹配
            #     # )
            #     user = await sync_to_async(User.objects.create_user, thread_sensitive=True)(
            #         username='这是一个名字',
            #         unionid=unionid
            #     )
            #     # 如果有额外的字段需要在创建时设置，可以在这里添加
            #     user.save()

            try:
                user = User.objects.get(unionid=union_id)
                # user = await sync_to_async(User.objects.get, thread_sensitive=True)(unionid=unionid)
                # user =  sync_to_async(User.objects.get, thread_sensitive=True)(unionid=unionid)
            except User.DoesNotExist:
                raise serializers.ValidationError({'code': 500, 'message': '无效user id'})

            item = handle_user_info(user)
            refresh = self.get_token(user)

            item['RefreshToken'] = str(refresh)
            item['AccessToken'] = str(refresh.access_token)

            return {'code': 200, 'message': '成功','data':item}
        # except User.DoesNotExist:
        #     raise serializers.ValidationError({'code': 500, 'message': '无效user id'})
        # except Exception as e:
        #     raise serializers.ValidationError(str(e))

    class Meta:
        model = User
        # fields = ['id']
        fields = ['code']

# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     id = None
#     password = None
#     code = serializers.CharField()
#
#     def __init__(self, *args, **kwargs):
#         # super().__init__(*args, **kwargs)
#         super(TokenObtainSerializer, self).__init__(*args, **kwargs)
#         # 移除 username 和 password 字段
#         self.fields.pop('username', None)
#         self.fields.pop('password', None)
#         self.fields.pop('id', None)
#         # 添加 code 字段
#         self.fields['code'] = serializers.CharField()
#
#     @classmethod
#     def get_token(cls, user):
#         return RefreshToken.for_user(user)
#
#     async def validate(self, attrs):
#         code = attrs.get('code')
#         unionid = await get_access_token(SOCIAL_AUTH_WEIXIN_appid, SOCIAL_AUTH_WEIXIN_secret, code)  # 确保这是异步执行的
#
#         if not unionid:
#             raise serializers.ValidationError({'code': 500, 'message': '请输入正确的code'})
#
#         unionid = unionid.get('unionid', None)
#         exists = await sync_to_async(User.objects.filter(unionid=unionid).exists, thread_sensitive=True)()
#
#         if not exists:
#             user = await sync_to_async(User.objects.create_user, thread_sensitive=True)(
#                 username='这是一个名字',
#                 unionid=unionid
#             )
#             await sync_to_async(user.save)()
#
#         try:
#             user = await sync_to_async(User.objects.get, thread_sensitive=True)(unionid=unionid)
#         except User.DoesNotExist:
#             raise serializers.ValidationError({'code': 500, 'message': '无效user id'})
#
#         item = handle_user_info(user)
#         refresh = self.get_token(user)
#
#         data = {
#             'refresh': str(refresh),
#             'access': str(refresh.access_token),
#             'data': item
#         }
#         return {'code': 200, 'message': '成功', 'data': data}
#
#     class Meta:
#         model = User
#         fields = ['code']

# custom_token_obtain_pair_view 输入参数
class WechatCodeRequestSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, help_text="微信授权码")


# custom_token_obtain_pair_view
class UserInfoResponseSerializer(serializers.Serializer):
    name = serializers.CharField(help_text="用户名")
    id   = serializers.CharField(help_text="用户id")
    RefreshToken  = serializers.CharField(help_text="更新的token", allow_null=True, required=False)
    AccessToken   = serializers.CharField(help_text="登录token")
    pic = serializers.CharField(help_text="用户图片链接", allow_null=True, required=False)
    phone = serializers.CharField(help_text="用户电话号码", allow_null=True, required=False)
    desc = serializers.CharField(help_text="用户描述", allow_null=True, required=False)
    app_software_config_version = serializers.CharField(help_text="软件配置版本", allow_null=True, required=False)
    model_config = serializers.CharField(help_text="模型配置信息", allow_null=True, required=False)

# send_sms_process 
class SendSmsProcessResponseSerializer(serializers.Serializer):
    phone = serializers.CharField(help_text="用户手机号")

# check_sms_process
class CheckSmsProcessResponseSerializer(serializers.Serializer):
    code = serializers.CharField(help_text="用户code")

# update_name
class UpdateNameResponseSerializer(serializers.Serializer):
    name = serializers.CharField(help_text="用户名")

# update_signature
class UpdateSignatureResponseSerializer(serializers.Serializer):
    desc = serializers.CharField(help_text="用户签名")

# update_app_software_version
class UpdateAppSoftwareVersionResponseSerializer(serializers.Serializer):
    app_software_config_version = serializers.CharField(help_text="用户车型软件版本")

# update_pic 输入结构参数
class UpdatePicResponseSerializer(serializers.Serializer):
    image = serializers.FileField(help_text='用户头像', required=True)

class ModelConfigSerializer(serializers.Serializer):
    model = serializers.CharField(help_text="Model of the device", required=False)
    hardware_config_version = serializers.CharField(help_text="Hardware configuration version", required=False)
    software_config_version = serializers.CharField(help_text="Software configuration version", required=False)


# 定义成功响应的序列化器
class SuccessResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码",default=200)
    message = serializers.CharField(help_text="响应消息")
    data = serializers.DictField(help_text="包含错误详情的字典", required=False, default={})


# 定义错误响应的序列化器
class ErrorResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码",default=500)
    message = serializers.CharField(help_text="响应消息")
    data = serializers.DictField(help_text="包含错误详情的字典", required=False, default={})


# check_sms_process
class CheckSmsProcessResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码",default=200)
    message = serializers.CharField(help_text="响应消息")
    data = UserInfoResponseSerializer(help_text="用户信息", required=False)