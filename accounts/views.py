from django.shortcuts import render

# Create your views here.
from rest_framework import generics
# from django.contrib.auth.models import User
from accounts.serializers import UserSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from accounts.models import User,SMSVerification,UserHistoryHardware,ProjectVersion
from django.views.decorators.http import require_POST
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import  permission_classes,authentication_classes
from adrf.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
import tempfile
from django.core.files.storage import FileSystemStorage
from accounts.handle_unionid import *
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from accounts.serializers import CustomTokenObtainPairSerializer
from accounts.tencent_sms import *
from accounts.handle_function import *
from asgiref.sync import sync_to_async
import os
from common_task.handle_tos import *


# from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
# from drf_spectacular.types import OpenApiTypes
# from rest_framework import serializers

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample,inline_serializer, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from rest_framework import status,serializers
from .serializers import *


def check_time_difference(code_create_time):
    from datetime import timedelta
    time_difference = abs(timezone.now() - code_create_time)
    if time_difference < timedelta(minutes=10):
        return True
    else:
        return False

@extend_schema(
    # 指定请求体的参数和类型
    request=UserSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    description="创建新用户",
    summary="创建用户",
    tags=['用户']
)
class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)

@extend_schema(
    # 指定请求体的参数和类型
    request=WechatCodeRequestSerializer,
    # 指定响应的信息
    responses={
        200: OpenApiResponse(response=UserInfoResponseSerializer, description="处理成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务错误")
    },
    description="根据微信code获取用户token信息，如果用户不存在，则先创建用户。处理成功返回200，处理异常返回500。",
    summary="获取或创建用户并返回token",
    tags=['用户']
)
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
async def custom_token_obtain_pair_view(request):
    code = request.data.get('code')
    unionid = get_access_token(SOCIAL_AUTH_WEIXIN_appid, SOCIAL_AUTH_WEIXIN_secret, code)
    print(unionid)
    if not unionid or 'unionid' not in unionid.keys():
        return Response({'code': 500, 'message': '请输入正确的code','data':{}})
    access_token = unionid.get('access_token')
    openid = unionid.get('openid')
    unionid = unionid.get('unionid')

    if not await sync_to_async(User.objects.filter(unionid=unionid).exists, thread_sensitive=True)():
        user_wechat_info = get_user_info(access_token, openid)
        if  user_wechat_info.get('nickname'):
            username = user_wechat_info.get('nickname')
        else:
            username = '这是一个名字'

        user = await sync_to_async(User.objects.create_user, thread_sensitive=True)(
            username=username,
            unionid=unionid
        )
        user.pic ='chek/temp/app_project/default/default_avatar_final.jpg'
        await sync_to_async(user.save, thread_sensitive=True)()

        # 如果有额外的字段需要在创建时设置，可以在这里添加
        # if user_wechat_info.get('headimgurl'):
        #     image_file = down_load_image(user_wechat_info.get('headimgurl'))
        #     # 使用 tempfile 创建一个临时文件夹
        #     temp_dir = tempfile.gettempdir()
        #
        #     # 创建一个 FileSystemStorage 实例，指向临时目录
        #     fs = FileSystemStorage(location=temp_dir)
        #
        #     # 保存文件
        #     filename = fs.save(image_file,f'{user.id}/pic.jpg' )
        #     # 获取保存后的文件的完整路径
        #     file_url = fs.path(filename)
        #     upload_file_path = f'temp/app_project/{user.id}/pic/pic.jpg'
        #     tinder_os = TinderOS()
        #     tinder_os.upload_file('chek', upload_file_path, file_url)
        #     os.remove(file_url)
        #     user.pic = upload_file_path

    serializer = CustomTokenObtainPairSerializer(unionid=unionid)
    validated_data = serializer.validate()
    # is_valid = await sync_to_async(serializer.is_valid)()
    # if not is_valid:
    #     return Response(serializer.errors, status=400)
    # validated_data = await sync_to_async(serializer.validate)(request.data)
    return Response(validated_data)

@extend_schema(
    # 方法说明
    summary="检查用户信息",
    description="获取当前登录用户的详细信息。",
    # 请求体说明（如果有）
    request=None,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=UserInfoResponseSerializer, description="用户信息存在"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="用户不存在")
    },
    # 标签，用于分类
    tags=['用户'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def check_user_info(request):
    user = request.user  # 获取当前登录用户
    user_token = request.auth
    try:
        profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)
        item = handle_user_info(profile)
        item['AccessToken'] = str(user_token)
        if item:
            return Response({'code': 200, 'message': '用户信息存在','data':item})

    except User.DoesNotExist:
        return Response({'code':500, 'message': '用户不存在','data':{}})


@extend_schema(
    # 方法说明
    summary="查看账号是否绑定手机号",
    description="查看账号是否绑定手机号",
    # 请求体说明（如果有）
    request=None,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="用户信息存在"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="用户不存在")
    },
    # 标签，用于分类
    tags=['用户'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def check_phone(request):
    user = request.user  # 获取当前登录用户

    try:
        profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)

        if profile.phone:
            return Response({'code': 200, 'has_phone_number': True,'message': '用户手机号已绑定','data':{}})
        else:
            return Response({'code': 200,'has_phone_number': False, 'message': '用户手机没有绑定','data':{}})
    except User.DoesNotExist:
        return Response({'code':500,'has_phone_number': False, 'message': '内部服务报错','data':{}})


@extend_schema(
    # 方法说明
    summary="手机号验证码发送",
    description="发送验证码到手机",
    # 请求体说明（如果有）
    request=SendSmsProcessResponseSerializer,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="发送成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务报错")
    },
    # 标签，用于分类
    tags=['用户'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def send_sms_process(request):
    user = request.user
    _id = user.id
    phone = str(request.data.get('phone'))

    if not phone:
        return Response({'code': 500, 'message': '没有提供字段 phone' ,'data':{}})

    # phone_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(phone=phone)
    # if phone_profile:
    #     return Response({'code': 500, 'message': 'phone 已存在' ,'data':{}})

    try:

        user_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)
        if user_profile.phone != phone:
            try:
                phone_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(phone=phone)
                if phone_profile:
                    return Response({'code': 500, 'message': '该手机号已被注册', 'data': {}})
            except Exception as e:
                # print(e)
                pass

        user_profile.phone = phone
        # user_profile.save()
        await sync_to_async(user_profile.save, thread_sensitive=True)()

        vericode=str(generate_verification_code())
        # smsverification= SMSVerification.objects.get_or_create(user_id=user.id)
        smsverification,creat =await sync_to_async(SMSVerification.objects.get_or_create, thread_sensitive=True)(user_id=user.id)
        smsverification.phone = phone
        smsverification.code = vericode
        smsverification.user_id = user.id
        # smsverification.save()
        await sync_to_async(smsverification.save, thread_sensitive=True)()

        send_sms(phone, vericode)
        return Response({'code': 200, 'message': 'sms 发送成功','data':{}})
    except Exception as e:
    #     print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})


@extend_schema(
    # 方法说明
    summary="验证码验证",
    description="手机短信验证码验证",
    # 请求体说明（如果有）
    request=CheckSmsProcessResponseSerializer,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=CheckSmsProcessResponseSerializer, description="成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务报错")
    },
    # 标签，用于分类
    tags=['用户'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def check_sms_process(request):
    user = request.user
    _id = user.id
    code = request.data.get('code')
    try:
        user_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)

        item = handle_user_info(user_profile)
        smsverification = await sync_to_async(SMSVerification.objects.get, thread_sensitive=True)(user_id=user.id)

        if code == smsverification.code and check_time_difference(smsverification.created_at):
            refresh = RefreshToken.for_user(user)
            item['RefreshToken'] = str(refresh)
            item['AccessToken'] = str(refresh.access_token)

            return Response( {'code': 200, 'message': '成功','data':item})
        else:
            return Response({'code': 500, 'message': '验证码错误或验证码已超时','data':{}})
    except:
        return Response({'code': 500, 'message': '内部服务报错','data':{}})



@extend_schema(
    # 方法说明
    summary="更新手机号",
    description="更新手机号",
    # 请求体说明（如果有）
    request=SendSmsProcessResponseSerializer,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务报错")
    },
    # 标签，用于分类
    tags=['用户'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def update_phone(request):
    user = request.user
    phone = request.data.get('phone')

    if not phone:
        return Response({'code': 500, 'message': '没有提供字段 phone','data':{}})

    phone_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(phone=phone)
    if phone_profile:
        return Response({'code': 500, 'message': 'phone 已存在' ,'data':{}})
    try:

        user_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)

        user_profile.phone = phone
        await sync_to_async(user_profile.save, thread_sensitive=True)()
        # user_profile.save()
        return Response({'code': 200, 'message': 'phone 更新成功.','data':{}})
    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})


@extend_schema(
    # 方法说明
    summary="更新用户名",
    description="更新用户名",
    # 请求体说明（如果有）
    request=SendSmsProcessResponseSerializer,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务报错")
    },
    # 标签，用于分类
    tags=['用户'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def update_name(request):
    user = request.user
    name = request.data.get('name')

    if not name:
        return Response({'code': 500, 'message': '没有提供字段 name','data':{}})

    try:
        # profile = User.objects.get(user=request.user)
        user_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)
        user_profile.name = name
        # user_profile.save()
        await sync_to_async(user_profile.save, thread_sensitive=True)()

        return Response({'code': 200, 'message': 'name 更新成功','data':{}})
    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})


@extend_schema(
    # 方法说明
    summary="修改签名",
    description="修改签名",
    # 请求体说明（如果有）
    request=UpdateSignatureResponseSerializer,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务报错")
    },
    # 标签，用于分类
    tags=['用户'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def update_signature(request):
    user = request.user
    desc = request.data.get('desc')

    if not desc:
        return Response({'code': 500, 'message': '没有提供字段 desc','data':{}})

    try:
        # user_profile=  User.objects.async_get(id=user.id)
        # profile = User.objects.get(user=request.user)
        user_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)
        user_profile.desc = desc
        # user_profile.save()
        await sync_to_async(user_profile.save, thread_sensitive=True)()

        return Response({'code': 200, 'message': 'desc 更新成功','data':{}})
    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错' ,'data':{}})


@extend_schema(
    # 方法说明
    summary="修改用户软件版本号的接口",
    description="修改用户版本号的接口",
    # 请求体说明（如果有）
    request=UpdateAppSoftwareVersionResponseSerializer,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务报错")
    },
    # 标签，用于分类
    tags=['车型'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def update_app_software_version(request):
    user = request.user
    app_software_config_version =  request.data.get('app_software_config_version')

    if not app_software_config_version:
        return Response({'code': 500, 'message': '没有提供字段 app_software_config_version','data':{}})

    try:
        user_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)

        user_profile.app_software_config_version = app_software_config_version
        # user_profile.save()
        await sync_to_async(user_profile.save, thread_sensitive=True)()

        return Response({'code': 200, 'message': 'app_software_config_version 更新成功','data':{}})
    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})



# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# async def update_password(request):
#     user = request.user
#
#     old_password = request.data.get('old_password')
#     new_password = request.data.get('new_password')
#
#     if not user.check_password(old_password):
#         return Response({'code': 500, 'success': 'Wrong password.'})
#
#
#     try:
#         user_profile =  User.objects.get(id=user.id)
#         user_profile.set_password(new_password)
#         # user.updated_date = timezone.now()
#         user_profile.save()
#         update_session_auth_hash(request, user)  # 保持用户登录状态
#         return Response({'code': 200, 'success': 'Password 更新成功'})
#     except Exception as e:
#         print(e)
#         return Response({'code': 500, 'success': 'internal error'})

@extend_schema(
    # 方法说明
    summary="更新用户头像",
    description="更新用户头像的接口",
    # 请求体说明（如果有）
    request=UpdatePicResponseSerializer,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务报错")
    },
    # 标签，用于分类
    tags=['用户'],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def update_pic(request):
    user = request.user
    _id = user.id
    user_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)
    try:
        if 'image' in request.FILES:
            image_file = request.FILES.get('image')
            # 使用 tempfile 创建一个临时文件夹
            temp_dir = tempfile.gettempdir()

            # 创建一个 FileSystemStorage 实例，指向临时目录
            fs = FileSystemStorage(location=temp_dir)

            # 保存文件
            # filename = fs.save(image_file.name, image_file)
            filename = await sync_to_async(fs.save, thread_sensitive=True)(image_file.name, image_file)
            # 获取保存后的文件的完整路径
            file_url = fs.path(filename)

            upload_file_path = f'temp/app_project/{_id}/pic/pic.jpg'
            tinder_os = TinderOS()
            tinder_os.upload_file('chek',upload_file_path , file_url)
            os.remove(file_url)

            user_profile.pic = f'chek/{upload_file_path}'
            # user_profile.save()
            await sync_to_async(user_profile.save, thread_sensitive=True)()

            return Response({'code': 200, 'success': 'Password 更新成功','data':{}})
        else:
            return Response({'code': 500, 'message': '没有提供图片','data':{}})
        return Response({'code': 500, 'message': '错误访问','data':{}})
    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})

@extend_schema(
    # 方法说明
    summary="修改用户版本号的接口",
    description="修改用户版本号的接口",
    # 请求体说明（如果有）
    request=ModelConfigSerializer,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务报错")
    },
    # 标签，用于分类
    tags=['车型'],
    examples=[
        OpenApiExample(
            name="Example request",
            summary="Example POST request with model configuration data",
            value={
                "model_config": {
                    "model": "Model XYZ",
                    "hardware_config_version": "v2.4",
                    "software_config_version": "v3.1"
                }
            },
            request_only=True  # Example only applies to the request
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def update_model_config(request):
    user = request.user
    model_config = request.data.get('model_config')

    if not model_config:
        return Response({'code': 500, 'message': '没有提供字段 model_config','data':{}})
    item = {}
    if model_config.get('model'):
        item['model'] = model_config.get('model')
    if model_config.get('hardware_config_version'):
        item['hardware_config_version'] = model_config.get('hardware_config_version')
    if model_config.get('software_config_version'):
        item['software_config_version'] = model_config.get('software_config_version')
    try:
        # profile = User.objects.get(user=request.user)
        user_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)
        user_profile.model_config = item
        # user_profile.save()
        await sync_to_async(user_profile.save, thread_sensitive=True)()

        return Response({'code': 200, 'message': 'model_config 更新成功','data':{}})


    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})


@extend_schema(
    # 方法说明
    summary="上传project_version",
    description="上传project_version",
    # 请求体说明（如果有）
    request=ModelConfigSerializer,  # 如果有需要接收的请求体，可以设置对应的序列化器
    parameters=[
        OpenApiParameter(name="Authorization", description="认证令牌，格式为：Bearer <token>", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.HEADER)
    ],
    # 响应体说明
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer, description="成功"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="内部服务报错")
    },
    # 标签，用于分类
    tags=['车型'],
    examples=[
        OpenApiExample(
            name="Example request",
            summary="Example POST request with model configuration data",
            value={
                "code": "T29jrie9u4hju8ej49tw",
                "project_version": "xxxx"

            },
            request_only=True  # Example only applies to the request
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def update_project_version(request):
    user = request.user
    _id = user.id
    project_version = request.data.get('project_version')
    code = request.data.get('code')

    if not code or not project_version:
        return Response({'code': 500, 'message': '没有提供字段 code or project_version','data':{}})
    
    project_version_connect, creat = await sync_to_async(ProjectVersion.objects.get_or_create, thread_sensitive=True)(
            project_version=project_version,
            code=code
        )
    project_version_connect.project_version = project_version
    project_version_connect.code =code
    # project_version_connect.save()

    user_history_hardware_connect, creat = await sync_to_async(UserHistoryHardware.objects.get_or_create, thread_sensitive=True)(
            user_id=_id,
            hardware_device_id=project_version_connect.id
        )
    user_history_hardware_connect.user_id = user.id
    user_history_hardware_connect.hardware_device_id =project_version_connect.id
    # user_history_hardware_connect.save()
    item = {}
    if project_version:
        item['project_version'] =project_version
    if code:
        item['code'] = code
  
    try:
        # profile = User.objects.get(user=request.user)
        user_profile = await sync_to_async(User.objects.get, thread_sensitive=True)(id=user.id)
        user_profile.project_version = item
        # user_profile.save()
        await sync_to_async(user_profile.save, thread_sensitive=True)()

        return Response({'code': 200, 'message': 'project_version 更新成功','data':{}})


    except Exception as e:
        print(e)
        return Response({'code': 500, 'message': '内部服务报错','data':{}})
