import os
import pandas as pd
import logging
from pathlib import Path
# 包含上级目录的common_task模块
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 导入TinderOS类
from common_task.handle_tos import TinderOS

logger = logging.getLogger('common_task')

# NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
def process_and_upload_files_sync(user_id, csv_path_list, det_path_list, brand, model, hardware_config, software_config):
    """同步版本的文件处理和上传函数"""
    try:
        tinder_os = TinderOS()
        results = []
        
        files_to_process = []
        if csv_path_list and isinstance(csv_path_list, list) and len(csv_path_list) > 0:
            for csv_path in csv_path_list:
                if csv_path and Path(csv_path).exists():
                    files_to_process.append((csv_path, 'csv'))

        if det_path_list and isinstance(det_path_list, list) and len(det_path_list) > 0:   
            for det_path in det_path_list:                 
                if det_path and Path(det_path).exists():
                    files_to_process.append((det_path, 'det'))        

        # for file_path, file_type in [(csv_path, 'csv'), (det_path, 'det')]:
        for file_path, file_type in files_to_process:
            if not file_path:
                continue
                
            file_name = Path(file_path)
            model = file_name.name.split('_')[0]
            time_line = file_name.name.split('_')[-1].split('.')[0]
            # brand =  "通用模型"
            # model =  "通用模型"
            # hardware_config =  "通用模型"
            # software_config = "通用模型"
            # 获取品牌信息
            middle_model = True
            if middle_model:
                upload_path = f"app_project/{user_id}/inference_data/{brand}/{model}/{time_line.split(' ')[0]}/{time_line}/{file_name.name}"
                
                # 上传文件
                tinder_os.upload_file('chek-app', upload_path, file_path)
                

                results.append((file_type, upload_path))
                
                # 可以选择删除本地文件
                os.remove(file_path)
        
        return True, results
    except Exception as e:
        logger.error(f"处理和上传文件失败: {e}")
        return False, []


# NOTE: 同一用户&同一车机版本&同一设备5分钟间隔行程结果合并，csv det相互独立
def merge_files_sync(file_path,file_name):
    try:

        # 创建合并目录
        # 当前目录
        merged_dir = os.path.join('./')
        os.makedirs(merged_dir, exist_ok=True)


        # 处理文件名
        merged_csv_filename = None
        merged_csv_filename = file_name.split('.')[0] + '.csv'
        # 处理文件名
        merged_det_filename = None
        merged_det_filename = file_name.split('.')[0] + '.det'

        csv_merged_results = []
        det_merged_results = []

        # 读取file_path中的所有CSV和DET文件
        # 并对所有文件按顺序排序，文件名以数字序号命名
        csv_path_list = []
        det_path_list = []
        if file_path and Path(file_path).exists():
            file_path = Path(file_path)
            if file_path.is_dir():
                for file in file_path.iterdir():
                    if file.suffix.lower() == '.csv':
                        csv_path_list.append(str(file))
                    elif file.suffix.lower() == '.det':
                        det_path_list.append(str(file))
            elif file_path.is_file():
                if file_path.suffix.lower() == '.csv':
                    csv_path_list.append(str(file_path))
                elif file_path.suffix.lower() == '.det':
                    det_path_list.append(str(file_path))
        # 对列表内的文件进行排序,文件名是用数字序号命名的
        csv_path_list.sort(key=lambda x: int(Path(x).stem))
        det_path_list.sort(key=lambda x: int(Path(x).stem))
        if len(csv_path_list) > 0:
            merged_csv = pd.DataFrame()
            for chunk in csv_path_list:
                try:
                    df = pd.read_csv(chunk)
                    merged_csv = pd.concat([merged_csv, df])
                except Exception as e:
                    logger.error(f"读取CSV分片失败 : {e}")

            if not merged_csv.empty:
                # 保存合并文件
                merged_path = os.path.join(merged_dir, merged_csv_filename)
                merged_csv.to_csv(merged_path, index=False)
                csv_merged_results.append(merged_path)
                logger.info(f"合并CSV文件成功.保存到 {merged_path}")

        # 合并DET文件
        if len(det_path_list) > 0:
            merged_dir = os.path.join('./')
            os.makedirs(merged_dir, exist_ok=True)

            det_merged_path = os.path.join(merged_dir, merged_det_filename)
            with open(det_merged_path, 'wb') as outfile:
                for chunk in det_path_list:
                    try:
                        with open(chunk, 'rb') as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        logger.error(f"读取DET分片失败 : {e}")
            det_merged_results.append(det_merged_path)
            logger.info(f"合并DET文件成功.保存到 {det_merged_path}")

        return csv_merged_results, det_merged_results
        
    except Exception as e:
        logger.error(f"合并文件失败: {e}")
        return None, None
    



if __name__ == "__main__":
    # 示例调用
    # 通用模型_通用模型_通用模型_spcialPoint_2025-06-15 18-22-38.csv
    user_id = "d11a1cd1-798a-4cd3-91fb-4237f60d3e3b"
    brand =  "通用模型"
    model =  "通用模型"
    hardware_config =  "通用模型"
    software_config = "通用模型"
    file_path = "/root/project/chekappbackendnew/chunks/31bce749-ee98-4751-874c-bde401e5a513 copy"
    file_name = "通用模型_通用模型_通用模型_spcialPoint_2025-06-15 21-08-20.csv"  # 替换为实际的文件

    csv_path_list, det_path_list = merge_files_sync(file_path,file_name)
    process_and_upload_files_sync(user_id, csv_path_list, det_path_list,brand, model, hardware_config, software_config)
