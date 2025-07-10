import zipfile
from pathlib import Path
import os
import shutil
import logging

logger = logging.getLogger('common_task')

def package_files(file_paths, output_zip):
    """
    将多个文件打包成一个zip文件，先写到本地临时目录，再移动到目标路径
    """

    if not file_paths or not isinstance(file_paths, list):
        print(f"package_files: 文件路径列表不能为空或非列表类型")
        return False

    try:
        tmp_zip = '/tmp/tmp_output.zip'
        with zipfile.ZipFile(tmp_zip, 'w') as zipf:
            for file_path in file_paths:
                file_path = Path(file_path)
                if file_path.exists():
                    zipf.write(file_path, arcname=file_path.name)
                else:
                    print(f"文件不存在: {file_path}")
                    logger.info(f"文件不存在: {file_path}")    
        # 移动到目标路径（覆盖）
        shutil.move(tmp_zip, output_zip)
        print(f"已打包到: {output_zip}")
        logger.info(f"已打包到: {output_zip}") 
        return True
    except FileNotFoundError as e:
        print(f"打包失败: 文件未找到 {e}", exc_info=True)
        return False
    except zipfile.BadZipFile as e:
        print(f"打包失败: 无效的zip文件 {e}", exc_info=True)
        if os.path.exists(tmp_zip):
            os.remove(tmp_zip)
        return False
    except shutil.Error as e:
        print(f"打包失败: shutil错误 {e}", exc_info=True)
        if os.path.exists(tmp_zip):
            os.remove(tmp_zip)
        return False    



if __name__ == "__main__":
    # 示例文件路径
    files_to_zip = [
        '/tos/chek-app/app_project/cb8e3aa4-fc19-4e60-9281-939a5886694e/inference_data/通用模型/通用模型/2025-06-18/2025-06-18 20-10-09/通用模型_通用模型_通用模型_2025-06-18 20-10-09.csv',
        '/tos/chek-app/app_project/cb8e3aa4-fc19-4e60-9281-939a5886694e/inference_data/通用模型/通用模型/2025-06-18/2025-06-18 10-27-44/通用模型_通用模型_通用模型_2025-06-18 10-27-44.csv',
    ]
    output_zip_file = '/tos/chek-app/app_project/cb8e3aa4-fc19-4e60-9281-939a5886694e/inference_data/通用模型/通用模型/output.zip'
    
    # 调用打包函数
    package_files(files_to_zip, output_zip_file)