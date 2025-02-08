from django.urls import path
from accounts.views import UserCreateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# from accounts.views import CustomTokenObtainPairView
from accounts import views
urlpatterns = [
    path('register', UserCreateView.as_view(), name='register'),
    # path('login', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login', views.custom_token_obtain_pair_view, name='token_obtain_pair'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('check_phone',views.check_phone),
    path('update_phone',views.update_phone),
    path('update_app_software_version',views.update_app_software_version),
    # path('update_password/',views.update_password),
    path('update_signature',views.update_signature),
    path('update_name',views.update_name),
    path('check_user_info',views.check_user_info),
    path('send_sms_process',views.send_sms_process),
    path('check_sms_process',views.check_sms_process),
    path('update_pic',views.update_pic),
    path('update_model_config',views.update_model_config),
    path('update_project_version',views.update_project_version),
]
