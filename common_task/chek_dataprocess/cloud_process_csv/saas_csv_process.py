import os
import sys
import time
import shutil
from pathlib import Path
import argparse
import asyncio
# from .csv_clean import DataProcessor
from .csv_process import CSVProcess
from .special_point_to_json import special_point2_json
from .json2excel import process_json_file_list
from .file_operater import download_file_tos, upload_files_tos

from .async_csv_clean import DataProcessor



def process(args):
    # 下载csv文件
    csv_files = download_file_tos(args.bucket, args.prefix, suffix=".csv")
    
    if len(csv_files) == 0:
        pass
    else:
        # csv->pro.csv
        # data_processor = DataProcessor()
        # pro_csv_list = []
        # for csv in csv_files:
        #     file_parts = str(csv).split('/')
        #     file_parts[-1] = file_parts[-1].replace('.csv', '.pro.csv')
        #     new_file_path = '/'.join(file_parts)
        #     if Path(new_file_path).exists():
        #         print(f'文件已存在: {str(new_file_path)}')
        #         pro_csv_list.append(new_file_path)
        #         continue

        #     data_processor.recover(str(csv))
        #     data_processor.process()
        #     data_processor.save(new_file_path)
        #     pro_csv_list.append(new_file_path)

        # csvProcess = CSVProcess(pro_csv_list) 

        # 直接pro.csv
        pro_csv_list = []
        for csv in csv_files:
            new_file_path = str(csv)
            pro_csv_list.append(new_file_path)
        csvProcess = CSVProcess(pro_csv_list) 

        frame_intervention_file, frame_intervention_risk_file, json_file_list = csvProcess.process_list_csv_save_journey()
        statistics_xlsx_file_list, truck_avoid_xlsx_file_list = process_json_file_list(json_file_list)
        special_point_json_list = special_point2_json(frame_intervention_file, frame_intervention_risk_file)

        # upload_files_tos(args.bucket,  pro_csv_list)
        upload_files_tos(args.bucket,  statistics_xlsx_file_list)
        upload_files_tos(args.bucket,  truck_avoid_xlsx_file_list)
        upload_files_tos(args.bucket,  special_point_json_list)
    
    for file in csv_files:
        if Path(file).exists():
            os.remove(str(file))
            print(f'remove file: {file}')

       # 清除临时文件夹
    # if os.path.exists('/tmp/rawData'):
    #     # 删除文件夹及其中所有文件和子文件夹
    #     shutil.rmtree('/tmp/rawData')
    #     print(f'文件夹 /tmp/rawData 及其所有子文件夹已被成功删除')



def process_journey(file_path, user_id, user_name, phone, 
                 car_brand, car_model, car_hardware_version, car_software_version):
    # csv文件
    
    if len(file_path) == 0:
        print(f'file path is empty : {file_path}')
        pass
    else:
        print(f"process data clean!")
        # csv->pro.csv
        data_processor = DataProcessor()
        pro_csv_list = []
        file_parts = str(file_path).split('/')
        file_parts[-1] = file_parts[-1].replace('.csv', '.pro.csv')
        new_file_path = '/'.join(file_parts)
        if Path(new_file_path).exists():
            print(f'文件已存在: {str(new_file_path)}')
            pro_csv_list.append(new_file_path)

        data_processor.recover(str(file_path))
        data_processor.process()
        data_processor.save(new_file_path)
        pro_csv_list.append(new_file_path)

        print(f"process data process!")
        csvProcess = CSVProcess(pro_csv_list, user_id = user_id, user_name = user_name, user_phone = phone, 
                 car_brand = car_brand, car_model = car_model, car_hardware_version = car_hardware_version, car_software_version = car_software_version) 


        # frame_intervention_file, frame_intervention_risk_file, json_file_list = csvProcess.process_list_csv_save_journey(upload_journey=True)
        frame_intervention_file, frame_intervention_risk_file, json_file_list = csvProcess.process_save_journey(upload_journey=True)
        # statistics_xlsx_file_list, truck_avoid_xlsx_file_list = process_json_file_list(json_file_list)
        # special_point_json_list = special_point2_json(frame_intervention_file, frame_intervention_risk_file)

        # upload_files_tos(args.bucket,  pro_csv_list)
        # upload_files_tos(args.bucket,  statistics_xlsx_file_list)
        # upload_files_tos(args.bucket,  truck_avoid_xlsx_file_list)
        # upload_files_tos(args.bucket,  special_point_json_list)
    
        if Path(new_file_path).exists():
            os.remove(str(new_file_path))
            print(f'remove file: {new_file_path}')
        
        for json_file in json_file_list:
            if Path(json_file).exists():
                os.remove(str(json_file))
                print(f'remove file: {json_file}')


async def async_process_journey(file_path, user_id, user_name, phone, 
                 car_brand, car_model, car_hardware_version, car_software_version):
    # csv文件
    
    if len(file_path) == 0:
        print(f'file path is empty : {file_path}')
        pass
    else:
        print(f"process data clean!")
        # if Path(file_path).exists():
        #     copy_file_path = Path(file_path).with_name(Path(file_path).name+'_copy')
        #     await asyncio.to_thread(shutil.copy,str(file_path), str(copy_file_path))
        #     file_path = copy_file_path
        #     print(f'copy file is : {file_path}')
        # csv->pro.csv
        data_processor = DataProcessor()
        pro_csv_list = []
        file_parts = str(file_path).split('/')
        file_parts[-1] = file_parts[-1].replace('.csv', '.pro.csv')
        new_file_path = '/'.join(file_parts)
        if Path(new_file_path).exists():
            print(f'文件已存在: {str(new_file_path)}')
            pro_csv_list.append(new_file_path)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))}  - process data recover!")
        await asyncio.to_thread(data_processor.recover, str(file_path))
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))}  - process data process!")
        await asyncio.to_thread(data_processor.async_process)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))} - process data save!")
        await asyncio.to_thread(data_processor.save, new_file_path)
        pro_csv_list.append(new_file_path)

        print(f"process data process!")
        csvProcess = CSVProcess(pro_csv_list, user_id = user_id, user_name = user_name, user_phone = phone, 
                 car_brand = car_brand, car_model = car_model, car_hardware_version = car_hardware_version, car_software_version = car_software_version) 


        # frame_intervention_file, frame_intervention_risk_file, json_file_list = csvProcess.process_list_csv_save_journey(upload_journey=True)
        frame_intervention_file, frame_intervention_risk_file, json_file_list = await asyncio.to_thread(csvProcess.process_save_journey,upload_journey=True)
        # statistics_xlsx_file_list, truck_avoid_xlsx_file_list = process_json_file_list(json_file_list)
        # special_point_json_list = special_point2_json(frame_intervention_file, frame_intervention_risk_file)

        # upload_files_tos(args.bucket,  pro_csv_list)
        # upload_files_tos(args.bucket,  statistics_xlsx_file_list)
        # upload_files_tos(args.bucket,  truck_avoid_xlsx_file_list)
        # upload_files_tos(args.bucket,  special_point_json_list)
    
        if Path(file_path).exists():
            await asyncio.to_thread(os.remove,str(file_path))
            print(f'remove file: {file_path}')

        if Path(new_file_path).exists():
            await asyncio.to_thread(os.remove,str(new_file_path))
            print(f'remove file: {new_file_path}')
        
        for json_file in json_file_list:
            if Path(json_file).exists():
                await asyncio.to_thread(os.remove, str(json_file))
                print(f'remove file: {json_file}')

async def main():
    from pathlib import Path
    current_path = Path(__file__).resolve()
    current_dir = current_path.parent
    await async_process_journey(
        file_path= str(current_path.with_name('b013a8dc84ad_20231113_065948.csv')),
        user_id=1001,
        user_name='赵建新',
        phone='13212728954',
        car_brand='IM',
        car_model='LS7',
        car_hardware_version='1.0',
        car_software_version='2.0'
    )





if __name__ == "__main__":

    ## sys.argv = ['saas_csv_process.py', '-p=chek/rawData/denza/N7/23.1.2.2312020.1/']

    # parser = argparse.ArgumentParser()

    # parser.add_argument('-p', '--tos_path', 
    #                     default='chek/rawData/xiaopeng/P7i/XOS5.1.1.8902/',
    #                     type=str,
    #                     required=True,
    #                     help='sub name for bucket to load data')

    # args = parser.parse_args()
    # path = Path(args.tos_path)
    # args.bucket = path.parts[0]
    # args.prefix = '/'.join(path.parts[1:])

    # process(args)

    # 运行异步主函数
    asyncio.run(main())