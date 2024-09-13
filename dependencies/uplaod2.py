import os
import time
import concurrent.futures
import oss2
from io import BytesIO
from oss2.credentials import EnvironmentVariableCredentialsProvider
from PIL import Image

class OSSUploader:
    def __init__(self, bucket_name, aliyun_oss_upload_url, aliyun_oss_download_url, second_folder=None, max_retries=8, max_workers=4):
        """
        初始化OSSUploader类。
        :param second_folder: 可选的二级目录，默认为None，表示使用根目录。
        """
        self.bucket_name = bucket_name
        self.aliyun_oss_upload_url = aliyun_oss_upload_url
        self.aliyun_oss_download_url = aliyun_oss_download_url
        self.second_folder = second_folder
        self.max_retries = max_retries
        self.max_workers = max_workers
        self.auth = oss2.ProviderAuth(EnvironmentVariableCredentialsProvider())
        self.bucket = oss2.Bucket(self.auth, self.aliyun_oss_upload_url, self.bucket_name)
    
    def _upload_single(self, object_name, data, content_type=None):
        success, retries = False, 0
        while not success and retries < self.max_retries:
            try:
                
                data.seek(0, os.SEEK_END)
                file_size = data.tell()
                data.seek(0)  

                headers = {'Content-Type': content_type} if content_type else {}
                self.bucket.put_object(object_name, data, headers=headers)

                # 校验上传后的文件大小
                oss_file_info = self.bucket.head_object(object_name)
                oss_file_size = oss_file_info.content_length

                if oss_file_size == file_size:
                    success = True
                    return f"{self.aliyun_oss_download_url}/{object_name}"
                else:
                    raise Exception(f"File size mismatch: Local size {file_size}, OSS size {oss_file_size}")

            except Exception as e:
                retries += 1
                print(f"Upload failed for {object_name}, retrying {retries}/{self.max_retries}... Error: {e}")
                time.sleep(2)

        return None

    def _get_object_name(self, file_name):
        """
        根据文件名生成OSS中的对象名称。
        如果设置了second_folder，则使用该目录作为前缀，否则使用根目录。
        """
        if self.second_folder:
            return f"{self.second_folder}/{file_name}"
        return file_name

    def upload_file(self, file_path):
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist.")
            return []
        
        file_name = os.path.basename(file_path)
        object_name = self._get_object_name(file_name)
        with open(file_path, 'rb') as f:
            data = BytesIO(f.read())  # 使用 BytesIO 确保可以重复读取
        url = self._upload_single(object_name, data)
        return [url] if url else []

    def upload_image(self, object_name, image):
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0) 
        object_name = self._get_object_name(object_name)
        url = self._upload_single(object_name, img_byte_arr, content_type='image/png')
        return [url] if url else []

    def upload_files(self, file_paths):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(self.upload_file, path): path for path in file_paths}
            urls = [future.result()[0] for future in concurrent.futures.as_completed(future_to_file) if future.result()]
        return urls

    def upload_images(self, images):
        """
        上传一组图片，确保所有图片都被上传并返回其URL。
        """
        urls = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_image = {executor.submit(self.upload_image, f"image_{i}.png", img): img for i, img in enumerate(images)}
            
            for future in concurrent.futures.as_completed(future_to_image):
                try:
                    result = future.result()
                    if result:
                        urls.extend(result)
                    else:
                        print(f"Warning: Upload returned no URL for an image.")
                except Exception as e:
                    print(f"Error during image upload: {e}")
        
        # 校验是否所有图片都上传成功
        if len(urls) < len(images):
            print(f"Warning: Only {len(urls)} out of {len(images)} images were uploaded successfully.")
        
        return urls

# if __name__ == "__main__":
#     # 初始化OSSUploader实例
#     oss_uploader = OSSUploader(
#         bucket_name="oss-for-nextweb",
#         aliyun_oss_upload_url="oss-cn-hongkong.aliyuncs.com",
#         aliyun_oss_download_url="https://******.*****.**",
#         second_folder="pdf_ocr",
#         max_retries=5,  # 上传重试次数
#         max_workers=4   # 并发线程数
#     )
    
#     # PDF文件路径
#     pdf_path = "test.pdf"

#     # 将PDF转换为图片并上传到OSS
#     images = convert_from_path(pdf_path)
#     xx = oss_uploader.upload_images(images)
#     # 打印上传结果
#     print("上传结果:", xx)
