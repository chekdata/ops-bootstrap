from tqdm import tqdm
import tos
from pathlib import Path
from tos import DataTransferType

class TinderOS:
    def __init__(self):
        self.access_key = 'AKLTNjI1MjlkMzNkNTRlNDczZDlhNWVkMzZlNmU2NDFiMmU'
        self.secret_key = 'TldSaVltTmpPRGN3T0RJd05EWXdPVGs0TTJJelpHVTBPV1UzWmprd01ETQ=='
        self.endpoint = "tos-cn-shanghai.volces.com"
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
            self.client.put_object_from_file(bucket, object_key, file_path, data_transfer_listener=self.percentage)
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
