from django.test import TestCase

# Create your tests here.
from update_mino import *

def get_mino_link(file_path,image_name,bucket_name='vehicle-control'):
    # print('test',file_path,image_name)
    # upload_image(file_path, bucket_name, image_name)
    link = mino_link(bucket_name, 'Tesla_model3.png')
    link = link.replace('http://62.234.57.136:9000/vehicle-control/','https://app.chekkk.com/assets/imgs/')
    return link

def get_mino_link(file_path, image_name, bucket_name='vehicle-control', bucket_prefix='', link_prefix=''):
    print('test', file_path, image_name)
    
    # 拼接完整的桶名：前缀 + 原始桶名
    full_bucket_name = f"{bucket_prefix}{bucket_name}"
    
    # 上传时使用完整桶名
    upload_image(file_path, full_bucket_name, image_name)
    
    # 获取预签名URL时也使用完整桶名
    link = mino_link(full_bucket_name, image_name)
    
    # 替换URL前缀（如果需要）
    if link_prefix:
        original_prefix = f'http://62.234.57.136:9000/{full_bucket_name}/'
        link = link.replace(original_prefix, link_prefix)
    
    return link
print(get_mino_link('file_path','image_name'))
print(get_mino_link(file_path, image_name, bucket_name='vehicle-control', bucket_prefix='/app_project/21a70f12-3210-4c94-95e7-7e0d3e881fc0/', link_prefix='https://app.chekkk.com/assets/imgs/'))