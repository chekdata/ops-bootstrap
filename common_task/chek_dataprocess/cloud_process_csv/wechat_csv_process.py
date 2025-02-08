import os
import sys
import shutil
from pathlib import Path
import argparse
from .wechat_csv_process_detail import WeChatCSVProcess
from .csv_clean import DataProcessor
from .tinder_os import TinderOS

car_model_map = {
    'AITO' : '问界',
    'Aion' : '埃安',
    'IM' : '智己',
    'Jiyue' : '极越',
    'Aion' : '埃安',
    'Lantu' : '岚图',
    'Tesla' : '特斯拉',
    'Wuling' : '五菱',
    'avatr' : '阿维塔',
    'denza' : '腾势',
    'lixiang' : '理想',
    'nio' : '蔚来',
    'risingauto' : '飞凡',
    'wey' : '魏牌',
    'xiaopeng' : '小鹏',
    'zeeker' : '极氪',
}

def download_file_tos(bucket, prefix, suffix):
    tinder_os = TinderOS()
    # 列出待处理文件列表
    #objects = tinder_os.list_objects(args.bucket, args.prefix, suffix='.pro.csv')
    objects = tinder_os.list_objects(bucket, prefix, suffix)
    # 下载所有log文件并解析
    black_list = []  #['.pro']


    file_path_list = []

    for ob in objects:
        ob_path = Path(ob)
        if ob_path.suffixes[0] in black_list:
            print(f'{ob} is in black list')
            continue
        local_file_path = tinder_os.download_object(bucket, ob)
        file_path_list.append(local_file_path)
    print('Save csv {} items!'.format(len(file_path_list)))
    return file_path_list

def remove_file(file_path):
    if Path(file_path).exists():
        os.remove(str(file_path))
        print(f'remove file: {file_path}')

def process(args):
    # 下载csv文件
    csv_files = download_file_tos(args.bucket, args.prefix, suffix=".csv")
    
    all_pro_files = []
    if len(csv_files) == 0:
        pass
    else:
        filter_conditions = ['.pro.csv']
        for filter in filter_conditions:
            for iterm in csv_files: 
                combined_suffix = ''.join(iterm.suffixes)
                if combined_suffix == filter:
                    all_pro_files.append(str(iterm))
            
        csvProcess = WeChatCSVProcess(all_pro_files, user_id = args.user_id, user_name = args.user_name, user_phone = args.phone, 
                 car_brand = args.car_brand, car_model = args.car_model, car_version = args.car_version) 
        csvProcess.process()

        for csv in csv_files:
            if Path(csv).exists():
                print(f'删除文件: {str(csv)}')
                remove_file(csv)
    
       # 清除临时文件夹
    if os.path.exists('/tmp/rawData'):
        # 删除文件夹及其中所有文件和子文件夹
        shutil.rmtree('/tmp/rawData')
        print(f'文件夹 /tmp/rawData 及其所有子文件夹已被成功删除')


# 处理本地csv文件
def process_csv(csv_files, user_id, user_name, phone, car_brand, car_model, car_version):
    if len(csv_files) == 0:
        pass
    else:
        
        data_processor = DataProcessor()
        pro_csv_list = []
        for csv in csv_files:
            file_parts = str(csv).split('/')
            file_parts[-1] = file_parts[-1].replace('.csv', '.pro.csv')
            new_file_path = '/'.join(file_parts)
            if Path(new_file_path).exists():
                print(f'文件已存在: {str(new_file_path)}')
                pro_csv_list.append(new_file_path)
                continue

            data_processor.recover(str(csv))
            data_processor.process()
            data_processor.save(new_file_path)
            pro_csv_list.append(new_file_path)

        csvProcess = WeChatCSVProcess(pro_csv_list, user_id = user_id, user_name = user_name, user_phone = phone, 
                 car_brand = car_brand, car_model = car_model, car_version = car_version) 
        csvProcess.process()       

        for csv in pro_csv_list:
            if Path(csv).exists():
                print(f'删除文件: {str(csv)}')
                remove_file(csv)


if __name__ == "__main__":

    sys.argv = ['wechat_csv_process.py', '-p=chek/rawData/xiaopeng/P7i/XOS5.1.1.8902/', '-ph=15117929459']

    parser = argparse.ArgumentParser()

    parser.add_argument('-p', '--tos_path', 
                        default='chek/rawData/xiaopeng/P7i/XOS5.1.1.8902/',
                        type=str,
                        required=True,
                        help='sub name for bucket to load data')

    parser.add_argument('-ud', '--user_id', 
                        default=100001,
                        type=int,
                        required=False,
                        help='user id for journey')   
    
    parser.add_argument('-un', '--user_name', 
                        default='洪泽鑫',
                        type=str,
                        required=False,
                        help='user id for journey') 

    parser.add_argument('-ph', '--phone', 
                        default='15320504550',
                        type=str,
                        required=True,
                        help='user phone')
    
    parser.add_argument('-cb', '--car_brand', 
                        default='理想',
                        type=str,
                        required=False,
                        help='car brand for journey') 
    
    
    parser.add_argument('-cm', '--car_model', 
                        default='L9',
                        type=str,
                        required=False,
                        help='car model for journey') 
    
    parser.add_argument('-cv', '--car_version', 
                        default='V5.2.1',
                        type=str,
                        required=False,
                        help='car software version for journey') 
    
    args = parser.parse_args()
    path = Path(args.tos_path)
    args.bucket = path.parts[0]
    args.prefix = '/'.join(path.parts[1:])
    args.car_brand = car_model_map.get(path.parts[2], " ")
    args.car_model = path.parts[3]
    args.car_version = path.parts[4]

    process(args)