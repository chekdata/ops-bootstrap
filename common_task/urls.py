
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
]
