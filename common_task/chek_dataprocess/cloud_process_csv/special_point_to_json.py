
import os
import time as run_time
import json
import glob
from pathlib import Path
from pathlib import PurePath
from tinder_os import TinderOS


def special_point2_json(total_interventions, total_risk_interventions, bucket='chek'):
    """
    将视频分析中接管和危险接管点按固定格式生成json文件
    """ 
    interventions_json_list = set()
    for pro_csv_obj, intervention_frame_ids in total_interventions.items():
        path = Path(pro_csv_obj)
        new_path = Path(*path.parts[:-1], path.stem + '_visual.crop.json')
        # 检查文件是否存在
        if not new_path.is_file():
            # 如果文件不存在，创建一个具有基本结构的新字典
            data = {"crop_points": []}
            # 创建父路径
            if not new_path.parent.exists():
                new_path.parent.mkdir(parents=True, exist_ok=True)

        else:
            # 如果文件存在，读取其内容
            with open(str(new_path), 'r', encoding='utf-8') as file:
                data = json.load(file)
        for id in intervention_frame_ids:
            new_record = {
                "type": "识别",
                "frame_id": id,
                "name": "接管",
                "crop_pre_seconds": 10,
                "crop_after_seconds": 10
            }
            # 添加新的记录到'crop_points'列表
            data['crop_points'].append(new_record)
        data['crop_points'] = sorted(data['crop_points'], key=lambda x: x['frame_id'])
        # 写回修改后的数据到文件
        with open(str(new_path), 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        
        interventions_json_list.add(new_path)

    

    for pro_csv_obj, intervention_frame_ids in total_risk_interventions.items():
        path = Path(pro_csv_obj)
        new_path = Path(*path.parts[:-1], path.stem + '_visual.crop.json')
        # 检查文件是否存在
        if not new_path.is_file():
            # 如果文件不存在，创建一个具有基本结构的新字典
            data = {"crop_points": []}
                        # 创建父路径
            if not new_path.parent.exists():
                new_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # 如果文件存在，读取其内容
            with open(str(new_path), 'r', encoding='utf-8') as file:
                data = json.load(file)
        for id in intervention_frame_ids:
            new_record = {
                "type": "识别",
                "frame_id": id,
                "name": "危险接管",
                "crop_pre_seconds": 10,
                "crop_after_seconds": 10
            }
            # 添加新的记录到'crop_points'列表
            data['crop_points'].append(new_record)
        data['crop_points'] = sorted(data['crop_points'], key=lambda x: x['frame_id'])
        # 写回修改后的数据到文件
        with open(str(new_path), 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

        interventions_json_list.add(new_path)

    return list(interventions_json_list)
    # upload_json_file(list(total_interventions.keys())[0], bucket)


def upload_json_file(json_file_path, bucket='chek'):
    tinder_os = TinderOS() 
    root_path = Path(json_file_path)
    root_path = Path(*root_path.parts[:2])
    tmp = str(root_path / '**' / ('*.json'))
    json_file_list = glob.glob(str(root_path / '**' / ('*.json')), recursive=True)
    # json_file_list = glob.glob('rawData/denza/N7/**/*.json', recursive=True)

    for json in json_file_list:
        # 上传数据
        tinder_os.upload_file(bucket,json, json )
        # 删除下载的文件
        if Path(json).exists():
            os.remove(str(json))






if __name__ == '__main__':
    
    total_interventions = {
    "rawData/Aion/Hyper/Hyper_A19_AVNT_S3_240413_0443W_R/mik_3.1.0/20240627/020859a2babe_20240627_195628/020859a2babe_20240627_195628.csv": [
        2153,
        3400,
        85588,
        91255,
        92406,
        93276,
        98393,
        107202,
        109777,
        113205,
        122183,
        123140,
        123950,
        138640,
        174077,
        181143,
        210076,
        216857,
        218175,
        222748,
        228338,
        245036,
        254685,
        266848,
        291751,
        304624,
        307738,
        317288,
        323072,
        345665,
        365263,
        388034,
        405765
    ],
    "rawData/Aion/Hyper/Hyper_A19_AVNT_S3_240413_0443W_R/mik_3.1.0/20240627/020859a2babe_20240627_114805/020859a2babe_20240627_114805.csv": [
        27243,
        40405,
        46988,
        57907,
        61542,
        64824
    ],
    "rawData/Aion/Hyper/Hyper_A19_AVNT_S3_240413_0443W_R/mik_3.1.0/20240627/020859a2babe_20240627_101256/020859a2babe_20240627_101256.csv": [
        3629,
        5006,
        23795,
        26486,
        27910,
        33873,
        40381,
        56933,
        66986,
        85779,
        92354,
        93242,
        95533,
        100779,
        105939,
        109939,
        112590,
        119436,
        125215
    ],
    "rawData/Aion/Hyper/Hyper_A19_AVNT_S3_240413_0443W_R/mik_3.1.0/20240627/020859a2babe_20240627_154046/020859a2babe_20240627_154046.csv": [
        12427
    ],
    "rawData/Aion/Hyper/Hyper_A19_AVNT_S3_240413_0443W_R/mik_3.1.0/20240627/020859a2babe_20240627_164441/020859a2babe_20240627_164441.csv": [
        12489,
        13718,
        49547,
        51830,
        55280,
        58207,
        58881,
        68932,
        74731,
        75492,
        79979,
        83050,
        90388,
        94357
    ]
}
    total_risk_interventions = {
    "rawData/Aion/Hyper/Hyper_A19_AVNT_S3_240413_0443W_R/mik_3.1.0/20240627/020859a2babe_20240627_114805/020859a2babe_20240627_114805.csv": [
        45072
    ],
    "rawData/Aion/Hyper/Hyper_A19_AVNT_S3_240413_0443W_R/mik_3.1.0/20240627/020859a2babe_20240627_101256/020859a2babe_20240627_101256.csv": [
        38367
    ],
    "rawData/Aion/Hyper/Hyper_A19_AVNT_S3_240413_0443W_R/mik_3.1.0/20240627/020859a2babe_20240627_164441/020859a2babe_20240627_164441.csv": [
        18267,
        71847
    ]
}
    
    # for pro_csv_obj, intervention_frame_ids in total_interventions.items():
    #     path = Path(pro_csv_obj)
    #     new_path = "./special-point_json/" + (path.parts[-1]).split('.')[0]+ ('_visual.crop.json')
    #     # 检查文件是否存在
    #     if not os.path.exists(new_path):
    #         # 如果文件不存在，创建一个具有基本结构的新字典
    #         data = {"crop_points": []}
    #     else:
    #         # 如果文件存在，读取其内容
    #         with open(new_path, 'r', encoding='utf-8') as file:
    #             data = json.load(file)
    #     for id in intervention_frame_ids:
    #         new_record = {
    #             "type": "识别",
    #             "frame_id": id,
    #             "name": "接管",
    #             "crop_pre_seconds": 10,
    #             "crop_after_seconds": 10
    #         }
    #         # 添加新的记录到'crop_points'列表
    #         data['crop_points'].append(new_record)
    #     data['crop_points'] = sorted(data['crop_points'], key=lambda x: x['frame_id'])
    #     # 写回修改后的数据到文件
    #     with open(new_path, 'w', encoding='utf-8') as file:
    #         json.dump(data, file, ensure_ascii=False, indent=4)
    

    # for pro_csv_obj, intervention_frame_ids in total_risk_interventions.items():
    #     path = Path(pro_csv_obj)
    #     new_path = "./special-point_json/" + (path.parts[-1]).split('.')[0]+ ('_visual.crop.json')
    #     # 检查文件是否存在
    #     if not os.path.exists(new_path):
    #         # 如果文件不存在，创建一个具有基本结构的新字典
    #         data = {"crop_points": []}
    #     else:
    #         # 如果文件存在，读取其内容
    #         with open(new_path, 'r', encoding='utf-8') as file:
    #             data = json.load(file)
    #     for id in intervention_frame_ids:
    #         new_record = {
    #             "type": "识别",
    #             "frame_id": id,
    #             "name": "危险接管",
    #             "crop_pre_seconds": 10,
    #             "crop_after_seconds": 10
    #         }
    #         # 添加新的记录到'crop_points'列表
    #         data['crop_points'].append(new_record)
    #     data['crop_points'] = sorted(data['crop_points'], key=lambda x: x['frame_id'])
    #     # 写回修改后的数据到文件
    #     with open(new_path, 'w', encoding='utf-8') as file:
    #         json.dump(data, file, ensure_ascii=False, indent=4)

    special_point2_json(total_interventions, total_risk_interventions)
    upload_json_file(list(total_interventions.keys())[0])