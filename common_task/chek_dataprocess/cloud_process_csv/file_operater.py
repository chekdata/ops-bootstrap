import os
import sys
import glob
from pathlib import Path
from pathlib import PurePath
from .tinder_os import TinderOS

print(sys.path)
# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)

# from proto_v1_1 import chek_message_pb2 as chek
# from proto_v1_1 import chek_message_pb2_grpc as chek_grpc


from proto_v1_2 import chek_message_pb2 as chek
from proto_v1_2 import chek_message_pb2_grpc as chek_grpc

from google.protobuf.json_format import MessageToJson


def get_all_specify_filename_files(directory, filename):

    csv_file_list = []
    directory = Path(directory)
    csv_path = directory / '**' / ('*'+ filename)
    csv_files = glob.glob(str(csv_path), recursive=True) 
    for file_name in csv_files:
        csv_file_list.append(file_name)
        print(file_name)
    
    print("="* 10 + "total file number is {}".format(len(csv_file_list)) + "="* 10)

    return csv_file_list


def save_to_json(chek_message: chek.ChekMessage, json_filepath):
    # Json
    json_message_format = MessageToJson(
        chek_message, preserving_proto_field_name=True, including_default_value_fields=True)
    # json_message_format = MessageToJson(
    #     chek_message, preserving_proto_field_name=True, always_print_fields_with_no_presence = True)
    # print(json_message_format)
    with open(json_filepath, mode='w', encoding='utf-8') as f:
        f.write(json_message_format)


def create_folders_from_filename(output_dir, file_name, extension, start_index = 9):
    """
    根据output_dir以及file_name生成新的文件格式的所有父级目录，
    并返回修改后的文件路径及名称
    """
    file_name = PurePath(file_name)

    output_pure_path = PurePath(output_dir)

    # NOTE
    # 这里parts[7:] 要根据本地路径深度进行调整
    # 其中‘/’也占一位在0索引位置
    #new_cparts = (output_dir,) + file_name.parts[9:]
    if start_index == -1:
        new_cparts = (output_dir,) + file_name.parts[len(output_pure_path.parts):]
    else:
        new_cparts = (output_dir,) + file_name.parts[start_index:]

    new_path = file_name.__class__(*new_cparts)

    output_path = new_path.with_suffix(extension)

    output_path = Path(output_path)

    if output_path.exists():
        print(f'{output_path} exists')
    else:
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            print(f'create {output_path.parent}')
        else:
            print(f'{output_path.parent} exists')

    return str(output_path)


def download_file_tos(bucket, prefix, suffix):
    tinder_os = TinderOS()
    # 列出待处理文件列表
    #objects = tinder_os.list_objects(args.bucket, args.prefix, suffix='.pro.csv')
    objects = tinder_os.list_objects(bucket, prefix, suffix)
    # 下载所有log文件并解析
    black_list = ['.pro']
    # black_list = ['20240113', '20240114']

    file_path_list = []

    for ob in objects:
        ob_path = Path(ob)
        # 下载csv
        if ob_path.suffixes[0] in black_list:
        # 下载.pro.csv
        # if ob_path.suffixes[0] not in black_list:
            print(f'{ob} is in black list')
            continue
        local_file_path = tinder_os.download_object(bucket, ob)
        file_path_list.append(local_file_path)
    print('Save csv {} items!'.format(len(file_path_list)))
    return file_path_list


def upload_files_tos(bucket,  file_path_list):
    """
    upload & remove local
    """
    tinder_os = TinderOS()
    for file in file_path_list:
        file_parts = str(file).split('/')
        upload_object_key = '/'.join(file_parts[2:])
        tinder_os.upload_file(bucket, upload_object_key, file)
        print(f'upload {file} to {upload_object_key}')
        
        remove_file(file)


def remove_file(file_path):
    if Path(file_path).exists():
        os.remove(str(file_path))
        print(f'remove file: {file_path}')