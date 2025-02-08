from rest_framework import serializers
from .models import Data

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers

class DataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Data
        fields = '__all__'


# search_model_hardware 请求参数序列化
class HardwareSearchRequestSerializer(serializers.Serializer):
    model = serializers.CharField(help_text="模型名称")
    hardware_config_version = serializers.CharField(help_text="硬件配置版本")
# search_model_fuzzy
class FuzzySearchRequestSerializer(serializers.Serializer):
    model = serializers.CharField(required=True, help_text="模型名称或关键词进行模糊匹配")

# judge_high_way_process
class HighwayRequestSerializer(serializers.Serializer):
    lon = serializers.CharField(required=True, help_text="经度")
    lat = serializers.CharField(required=True, help_text="纬度")

# update_model_config_app
class ModelConfigUpdateRequestSerializer(serializers.Serializer):
    created_brand = serializers.CharField(required=False, help_text="创建的品牌")
    created_model = serializers.CharField(required=False, help_text="创建的模型")
    created_hardware_config_version = serializers.CharField(required=False, help_text="创建的硬件配置版本")
    created_software_config_version = serializers.CharField(required=False, help_text="创建的软件配置版本")

# search_model_tos
class ModelConfigSearchModelTos(serializers.Serializer):
    model = serializers.CharField(required=True, help_text="车型")
    hardware_config_version = serializers.CharField(required=False, help_text="车型硬件版本")

# update_model_tos
class ModelConfigUpdateModelTos(serializers.Serializer):
    # model = serializers.CharField(required=False, help_text="车型")
    # hardware_config_version = serializers.CharField(required=False, help_text="车型硬件版本")
    # model_config = serializers.CharField(required=True, help_text="车型配置信息")
    model_config = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        required=True,
        help_text="车型配置信息"
    )
    desc = serializers.CharField(required=False, help_text="模型描述")
    name = serializers.CharField(required=True, help_text="模型名称")
    version = serializers.CharField(required=True, help_text="模型版本")
    brand = serializers.CharField(required=False, help_text="车品牌")
    md5_value = serializers.CharField(required=True, help_text="模型md5值")
    file = serializers.FileField(help_text='上传的pt模型文件')


# update_model_config_app 响应
class SuccessfulResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码")
    message = serializers.CharField(help_text="响应消息")
    data = serializers.DictField(help_text="返回的具体数据", required=False, default={})

class HighwayResultResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码")
    roadName = serializers.CharField(help_text="道路名称")
    highWay = serializers.BooleanField(help_text="是否高速")

# judge_high_way_process响应
class HighwayResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码")
    message = serializers.CharField(help_text="响应消息")
    data = HighwayResultResponseSerializer(help_text="返回的具体数据", required=False)

class FuzzySearchModelResponseSerializer(serializers.Serializer):
    model = serializers.CharField(help_text="车型名")
    hardware_config_version = serializers.CharField(help_text="硬件版本")

# search_model_fuzzy响应消息
class FuzzySearchResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码")
    message = serializers.CharField(help_text="响应消息")
    data = serializers.ListField(        
        child=FuzzySearchModelResponseSerializer(),  # 这里指定列表的子元素为ModelResponseSerializer实例
        help_text="包含车型和配置版本的列表")

class ModelResponseSerializer(serializers.Serializer):
    model = serializers.CharField(help_text="车型名")
    hardware_config_version = serializers.CharField(help_text="硬件版本")
    software_config_version = serializers.CharField(help_text="软件版本")

# 响应序列化器
class HardwareSearchResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码",default=200)
    message = serializers.CharField(help_text="响应消息")
    data = serializers.ListField(        
        child=ModelResponseSerializer(),  # 这里指定列表的子元素为ModelResponseSerializer实例
        help_text="包含车型和配置版本的列表")

class ModelTosResponseSerializer(serializers.Serializer):
    model_tos_link = serializers.CharField(help_text="模型存储地址")
    md5_value = serializers.CharField(help_text="MD5值")

# search_model_tos
class searchModelTosResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码",default=200)
    message = serializers.CharField(help_text="响应消息")
    data = ModelTosResponseSerializer( help_text="包含模型tos路径和MD5")  # 这里指定列表的子元素为ModelResponseSerializer实例

# 错误响应序列化器
class ErrorResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="错误代码")
    message = serializers.CharField(help_text="错误消息")
    data = serializers.ListField(child=serializers.DictField(), help_text="错误数据详情")    