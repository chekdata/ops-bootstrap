from django.urls import path
from data import views

urlpatterns = [
    # path('data/', views.DataListCreateView.as_view(), name='data-list-create'),
    # path('data/<int:pk>/', views.DataDetailView.as_view(), name='data-detail'),
    path('search_model_hardware',views.search_model_hardware),
    path('search_model_fuzzy',views.search_model_fuzzy),
    path('search_model_tos',views.search_model_tos),
    path('update_model_tos',views.update_model_tos),
    path('search_model_info',views.search_model_info),
    # path('download_file_tos',views.download_file_tos),
    path('judge_high_way_process',views.judge_high_way_process),
    path('update_model_config_app',views.update_model_config_app),
]
