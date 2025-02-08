from rest_framework import serializers

# process_after_analysis_data输入结构参数
class AnalysisDataSerializer(serializers.Serializer):
    intervention = serializers.FloatField(required=False)
    intervention_risk = serializers.FloatField(required=False)
    mpi = serializers.FloatField(required=False)
    mpi_risk = serializers.FloatField(required=False)
    total_mile = serializers.FloatField(required=False)
    noa_mile = serializers.FloatField(required=False)
    lcc_mile = serializers.FloatField(required=False)
    noa_lcc_mile = serializers.FloatField(required=False)
    standby_mile = serializers.FloatField(required=False)

class TosPlayLink(serializers.Serializer):
    tos_link = serializers.CharField(required=True, help_text="tos存储路径")

# process_after_analysis_data 输入结构参数
class AfterAnalysisDataSerializer(serializers.Serializer):
    file = serializers.FileField(help_text='上传的CSV文件')

# process_inference_detial_det_data 输入结构参数
class InferenceDetialDetDataSerializer(serializers.Serializer):
    file = serializers.FileField(help_text='上传的Det文件')

# 定义成功响应的序列化器
class SuccessResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码",default=200)
    message = serializers.CharField(help_text="响应消息")
    data = serializers.DictField(help_text="包含错误详情的字典", required=False)


# 定义错误响应的序列化器
class ErrorResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(help_text="响应代码",default=500)
    message = serializers.CharField(help_text="响应消息")
    data = serializers.DictField(help_text="包含错误详情的字典", required=False)