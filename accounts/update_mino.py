from minio import Minio
import os
# 创建MinIO的客户端实例
minioClient = Minio('62.234.57.136:9000',
                    access_key='vehicle',
                    secret_key='Qwer4321@',
                    secure=False)
# http://62.234.57.136:30726/

def upload_image(file_path,bucket_name,image_name):
    # 打开图片文件
    with open(file_path, 'rb') as file_data:
        file_stat = os.stat(file_path)
        # 上传图片到MinIO
        minioClient.put_object(bucket_name,
                               image_name,
                               file_data,
                               file_stat.st_size,
                               content_type='image/png')

def mino_link(bucket_name,image_name):
    url = minioClient.presigned_get_object(bucket_name, image_name)
    # url = url.replace("http://62.234.57.136:30726/aigc-lezhen/", "https://aigc.chekkk.com/data/")
    return url

def get_mino_link(file_path,image_name,_id,bucket_name='vehicle-control'):
    print('test',file_path,image_name)
    upload_image(file_path, bucket_name, image_name)
    # link = mino_link(bucket_name, image_name)
    # link = link.replace('http://62.234.57.136:9000/vehicle-control/','https://app.chekkk.com/assets/imgs/')
    return f'https://app.chekkk.com/assets/imgs/{image_name}'



async def prepare_upload_file_path_mino(_id,file_name):
    file_name = file_name.name
    upload_file_path = f"""app_project/{_id}/{file_name}"""
    return upload_file_path

if __name__ == '__main__':
    file_path = './data/炼狱.png'
    image_name ='app_project/炼狱.png'
    bucket_name ='vehicle-control'
    upload_image(file_path, bucket_name, image_name)
    get_mino_link(bucket_name, image_name)