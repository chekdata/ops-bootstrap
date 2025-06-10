from tqdm import tqdm
import tos 
from pathlib import Path
from tos import DataTransferType

class TinderOS:
    def __init__(self):
        self.access_key = 'AKLTNjI1MjlkMzNkNTRlNDczZDlhNWVkMzZlNmU2NDFiMmU'
        self.secret_key = 'TldSaVltTmpPRGN3T0RJd05EWXdPVGs0TTJJelpHVTBPV1UzWmprd01ETQ=='
        # 走内网
        # self.endpoint = "tos-cn-shanghai.ivolces.com"
        self.endpoint = ""
        self.region = "cn-shanghai"
        self.client = tos.TosClientV2(self.access_key, self.secret_key, self.endpoint, self.region)
        self.pbar = None

    def list_objects(self, bucket, prefix = None, suffix = None):
        try:
            all_files = []
            # 列举指定桶下特定前缀所有对象
            truncated = True
            continuation_token = ''
            while truncated:
                result = self.client.list_objects_type2(bucket=bucket, prefix=prefix, continuation_token=continuation_token)
                for iterm in result.contents:
                    if Path(iterm.key).name.startswith('.'):
                        continue
                    if suffix:
                        if iterm.key.endswith(suffix):
                            all_files.append(iterm.key)
                    else:
                        all_files.append(iterm.key)
                truncated = result.is_truncated
                continuation_token = result.next_continuation_token
            print('--------------')
            print('Found objects in Volcano Engine Server')
            for ob in all_files:
                print(ob)
            print('--------------')
            return all_files
        except tos.exceptions.TosClientError as e:
            # 操作失败，捕获客户端异常，一般情况为非法请求参数或网络异常。
            print('fail with client error, message:{}, cause: {}'.format(e.message, e.cause))
        except tos.exceptions.TosServerError as e:
            # 操作失败，捕获服务端异常，可从返回信息中获取详细错误信息。
            print('fail with server error, code: {}'.format(e.code))
            # request id 可定位具体问题，强烈建议日志中保存。
            print('error with request id: {}'.format(e.request_id))
            print('error with message: {}'.format(e.message))
            print('error with http code: {}'.format(e.status_code))
            print('error with ec: {}'.format(e.ec))
            print('error with request url: {}'.format(e.request_url))
        except Exception as e:
            print('fail with unknown error: {}'.format(e))

    def download_object(self, bucket, object_key, dest_dir='/tmp'):
        try:
            tmp_file = Path(dest_dir).absolute() / object_key
            print(f'下载 {object_key} 到 {str(tmp_file)}')
            tmp_file.parent.mkdir(parents=True, exist_ok=True)
            if tmp_file.exists():
                print('文件已存在')
                return tmp_file
            # zjx
            self.task = '下载中'
            self.client.get_object_to_file(bucket, object_key, file_path=tmp_file, data_transfer_listener=self.percentage)
            return tmp_file
        except tos.exceptions.TosClientError as e:
            # 操作失败，捕获客户端异常，一般情况为非法请求参数或网络异常。
            print('fail with client error, message:{}, cause: {}'.format(e.message, e.cause))
        except tos.exceptions.TosServerError as e:
            # 操作失败，捕获服务端异常，可从返回信息中获取详细错误信息。
            print('fail with server error, code: {}'.format(e.code))
            # request id 可定位具体问题，强烈建议日志中保存。
            print('error with request id: {}'.format(e.request_id))
            print('error with message: {}'.format(e.message))
            print('error with http code: {}'.format(e.status_code))
            print('error with ec: {}'.format(e.ec))
            print('error with request url: {}'.format(e.request_url))
        except Exception as e:
            print('fail with unknown error: {}'.format(e))

    def upload_file(self, bucket, object_key, file_path):
        try:
            print(f'上传文件: {file_path}')
            self.task = '上传中'
            # zjx
            #self.client.put_object_from_file(bucket, object_key, file_path, data_transfer_listener=self.percentage)
            result = self.client.put_object_from_file(bucket, object_key, file_path, data_transfer_listener=self.percentage)
            print('http status code:{}'.format(result.status_code))
            # 请求ID。请求ID是本次请求的唯一标识，建议在日志中添加此参数
            print('request_id: {}'.format(result.request_id))
            # hash_crc64_ecma 表示该对象的64位CRC值, 可用于验证上传对象的完整性
            print('crc64: {}'.format(result.hash_crc64_ecma))
            print(f'成功上传至存储桶位置: {object_key}')
        except tos.exceptions.TosClientError as e:
            # 操作失败，捕获客户端异常，一般情况为非法请求参数或网络异常。
            print('fail with client error, message:{}, cause: {}'.format(e.message, e.cause))
        except tos.exceptions.TosServerError as e:
            # 操作失败，捕获服务端异常，可从返回信息中获取详细错误信息。
            print('fail with server error, code: {}'.format(e.code))
            # request id 可定位具体问题，强烈建议日志中保存。
            print('error with request id: {}'.format(e.request_id))
            print('error with message: {}'.format(e.message))
            print('error with http code: {}'.format(e.status_code))
            print('error with ec: {}'.format(e.ec))
            print('error with request url: {}'.format(e.request_url))
        except Exception as e:
            print('fail with unknown error: {}'.format(e))
    
    def upload_file_by_multipart(self, bucket, object_key, file_path):
        import os

        import tos
        from tos import DataTransferType
        from tos.utils import SizeAdapter, MergeProcess

        total_size = os.path.getsize(file_path)
        part_size = 10 * 1024 * 1024
        try:
            def percentage(consumed_bytes: int, total_bytes: int, rw_once_bytes: int, type: DataTransferType):
                if total_bytes:
                    rate = int(100 * float(consumed_bytes) / float(total_bytes))
                    print("rate:{}, consumed_bytes:{},total_bytes{}, rw_once_bytes:{}, type:{}".format(rate,
                                                                                                       consumed_bytes,
                                                                                                       total_bytes,
                                                                                                       rw_once_bytes,
                                                                                                       type))
            # 配置进度条，与普通上传不同的是需将分片上传的进度聚合
            data_transfer_listener = MergeProcess(percentage, total_size, (total_size + part_size - 1) // part_size, 0)
            # 初始化上传任务
            # 若需在初始化分片时设置对象的存储类型，可通过storage_class字段设置
            # 若需在初始化分片时设置对象ACL，可通过acl、grant_full_control等字段设置
            multi_result =  self.client.create_multipart_upload(bucket, object_key, acl=tos.ACLType.ACL_Public_Read,
                                                          storage_class=tos.StorageClassType.Storage_Class_Standard)

            upload_id = multi_result.upload_id
            parts = []

            # 上传分片数据
            with open(file_path, 'rb') as f:
                part_number = 1
                offset = 0
                while offset < total_size:
                    num_to_upload = min(part_size, total_size - offset)
                    out =  self.client.upload_part(bucket, object_key, upload_id, part_number,
                                             content=SizeAdapter(f, num_to_upload, init_offset=offset),
                                             data_transfer_listener=data_transfer_listener)
                    parts.append(out)
                    offset += num_to_upload
                    part_number += 1

            # 完成分片上传任务
            self.client.complete_multipart_upload(bucket, object_key, upload_id, parts)
        except tos.exceptions.TosClientError as e:
            # 操作失败，捕获客户端异常，一般情况为非法请求参数或网络异常
            print('fail with client error, message:{}, cause: {}'.format(e.message, e.cause))
        except tos.exceptions.TosServerError as e:
            # 操作失败，捕获服务端异常，可从返回信息中获取详细错误信息
            print('fail with server error, code: {}'.format(e.code))
            # request id 可定位具体问题，强烈建议日志中保存
            print('error with request id: {}'.format(e.request_id))
            print('error with message: {}'.format(e.message))
            print('error with http code: {}'.format(e.status_code))
            print('error with ec: {}'.format(e.ec))
            print('error with request url: {}'.format(e.request_url))
        except Exception as e:
            print('fail with unknown error: {}'.format(e))

    def copy_object(self, src_bucket, src_object_key, dest_bucket, dest_object_key):
        try:
            # 拷贝 src_bucket_name 桶中 src_object_key 对象到 bucket_name 桶中，并设置对象 key 为 object_key
            self.client.copy_object(dest_bucket, dest_object_key, src_bucket, src_object_key,
                               # 通过可选字段acl设置拷贝对象的acl权限
                            #    acl=tos.ACLType.ACL_Private,
                               # 通过可选字段设置拷贝对象的存储类型
                               storage_class=tos.StorageClassType.Storage_Class_Standard,
                               # 设置metadata_directive=MetadataDirectiveType.Metadata_Directive_Copy从元对象复制元数据
                               metadata_directive=tos.MetadataDirectiveType.Metadata_Directive_Copy)
        except tos.exceptions.TosClientError as e:
            # 操作失败，捕获客户端异常，一般情况为非法请求参数或网络异常
            print('fail with client error, message:{}, cause: {}'.format(e.message, e.cause))
        except tos.exceptions.TosServerError as e:
            # 操作失败，捕获服务端异常，可从返回信息中获取详细错误信息
            print('fail with server error, code: {}'.format(e.code))
            # request id 可定位具体问题，强烈建议日志中保存
            print('error with request id: {}'.format(e.request_id))
            print('error with message: {}'.format(e.message))
            print('error with http code: {}'.format(e.status_code))
            print('error with ec: {}'.format(e.ec))
            print('error with request url: {}'.format(e.request_url))
        except Exception as e:
            print('fail with unknown error: {}'.format(e))

    def exists(self, bucket, object_key):
        try:
            # 获取对象元数据
            result = self.client.head_object(bucket, object_key)
            return True
        except tos.exceptions.TosClientError as e:
            # 操作失败，捕获客户端异常，一般情况为非法请求参数或网络异常
            print('fail with client error, message:{}, cause: {}'.format(e.message, e.cause))
        except tos.exceptions.TosServerError as e:
            if e.status_code == 404:
                print(f"Not exists {object_key}")
            else:
                # 操作失败，捕获服务端异常，可从返回信息中获取详细错误信息
                print('fail with server error, code: {}'.format(e.code))
                # request id 可定位具体问题，强烈建议日志中保存
                print('error with request id: {}'.format(e.request_id))
                print('error with message: {}'.format(e.message))
                print('error with http code: {}'.format(e.status_code))
                print('error with ec: {}'.format(e.ec))
                print('error with request url: {}'.format(e.request_url))
            return False
        except Exception as e:
            print('fail with unknown error: {}'.format(e))
            return False

    def percentage(self, consumed_bytes, total_bytes, rw_once_bytes, type: DataTransferType):
        if total_bytes:
            if self.pbar is None:
                self.last_consumed_bytes = 0
                self.pbar = tqdm(total=total_bytes)
            self.pbar.update(consumed_bytes - self.last_consumed_bytes)
            self.pbar.set_description(desc=f'{self.task} {self._bytes_readable(consumed_bytes)}/{self._bytes_readable(total_bytes)}')
            self.last_consumed_bytes = consumed_bytes
            if consumed_bytes >= total_bytes:
                self.pbar.close()
                self.pbar = None

    def _bytes_readable(self, bytes)->str:
        readable_str = f'{bytes}b'
        if bytes > 1024:
            bytes /= 1024
            readable_str = f'{bytes:.2f}Kb'
            if bytes > 1024:
                bytes /= 1024
                readable_str = f'{bytes:.2f}Mb'
                if bytes > 1024:
                    bytes /= 1024
                    readable_str = f'{bytes:.2f}Gb'
        return readable_str

    
