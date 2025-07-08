
from django.contrib import admin
from django.urls import path, include
from common_task import views
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.urls import path
from . import views

urlpatterns = [
    path('process_after_analysis_data', views.process_after_analysis_data),
    path('process_after_inference_data_csv', views.process_after_inference_data),
    path('process_after_analysis_data_csv', views.process_after_analysis_data_csv),
    path('process_inference_detial_det_data', views.process_inference_detial_det_data),
    path('process_tos_play_link', views.process_tos_play_link),
    path('upload_chunk', views.upload_chunk),
    path('complete_upload', views.complete_upload),  # 完成上传
    path('check_chunks/<uuid:trip_id>/', views.check_chunks),  # 检查分片状态
    path('setStartMerge', views.setStartMerge),  # 检查分片状态
    path('get_abnormal_journey', views.get_abnormal_journey),  # 获取异常退出行程
    path('set_merge_abnormal_journey', views.set_merge_abnormal_journey), # 设置异常退出行程是否会被合并到接下来的行程中
    path('get_journey_data_entrance', views.get_journey_data_entrance),
    path('get_journey_gps_data_entrance', views.get_journey_gps_data_entrance),
    path('get_user_journey_data_entrance', views.get_user_journey_data_entrance),
    path('get_single_journey_data_entrance', views.get_single_journey_data_entrance),
    path('get_journey_intervention_gps_data_entrance', views.get_journey_intervention_gps_data_entrance),
    path('get_journey_dimention_entrance', views.get_journey_dimention_entrance),
    path('get_journey_mbti_entrance', views.get_journey_mbti_entrance),
    path('set_recordUploadTosStatus', views.set_recordUploadTosStatus),
    path('update_journey_image', views.update_journey_image),
    
]

