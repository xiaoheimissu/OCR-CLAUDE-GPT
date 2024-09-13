import os
import time
import concurrent.futures
from pdf2image import convert_from_path
from math import ceil
from dependencies.pdfpreprocesser import *
from dependencies.uplaod2 import *
from dependencies.chat import *

# 文件路径和名称定义
BASE_PATH = 'D:/Files/Code/Python/tips'
RAW_PDF_NAME = '256-287.pdf'
CROPPED_PDF_PATH = "D:/Files/Code/Python/tips"
CROPPED_PDF_NAME = 'temp.pdf' 
OCR_RESULT_PATH = "D:/Files/Code/Python/tips"
OCR_RESULT_NAME = '256-287.txt'

ALIYUNOSS_BUCKET = 'oss-for-nextweb'
ALIYUNOSS_UPLOAD_URL = 'oss-cn-hongkong.aliyuncs.com'
ALIYUNOSS_DOWNLOAD_URL = 'https://*********.****'

API_KEY = "*****************"
BASE_URL = "https://***********/v1/chat/completions"

KEY_WORDS = "computer, C++, program"

PROMPT = f"""I need you to extract the content (ocr) from the image, which contains the field of {KEY_WORDS}. The requirements are as follows: 
      1. Reply using markdown format. Do not put the content in an entire code block unless the image only contains code. You should add markdown tags at specific formatting places in the text, rather than simply putting all text in ``` code blocks.
      2. Only send the extracted content and do not add any description text. Even if the image has very little content or is even a blank image, you are not allowed to add additional content. In the case of a blank image, you only need to reply with a blank character.  
      3. In the text, most of the line breaks are not needed, most line breaks are due to page width limitations. Please remove the line breaks in these places. Line breaks are not allowed in consecutive sentences. 
      4. For the headings, you should determine the heading level and add the correct number of “#” tags. Only lone lines beginning with w, w.x, w.x.y, w.x.y.z followed by a short text are headings, where w,x,y,z are numbers. Note that the beginning of the page is not necessarily the title
      """

# MODEL = "claude-3-5-sonnet-20240620"
MODEL  = "claude-3-haiku-20240307"        # THIS IS ENOUGH, CLUADE IN OCR IS BETTER THAN GPT. JUST SUPPORT GPT FORMAT

temperature = 0.0
top_p = 1.0

# TOP_MARGIN = 0  # 顶部裁剪的像素数
# BOTTOM_MARGIN = 0  # 底部裁剪的像素数



RAW_PDF_PATH = os.path.join(BASE_PATH, RAW_PDF_NAME)                    # 初始PDF路径
CROPPED_PDF_PATH = os.path.join(CROPPED_PDF_PATH, CROPPED_PDF_NAME)     # 中间处理后的PDF路径
OCR_CONTENT_DESTINATION = os.path.join(BASE_PATH, OCR_RESULT_NAME)      # 最终OCR识别结果保存的TXT路径



# 5. 主流程
def process_pdf_with_ocr_in_one(raw_pdf_path, cropped_pdf_path,  
                                output_txt_path, chat_instance, 
                                save_figure = False, output_figure_folder=None, 
                                top_margin = None, bottom_margin = None,
                                ocr_max_retries=5,  ocr_max_workers=4):
    # Step 1: 裁剪PDF转化为图像
    crop_pdf(raw_pdf_path, cropped_pdf_path, top_margin, bottom_margin)
    
    image_objects = pdf_to_images(cropped_pdf_path, output_folder = output_figure_folder, images_per_long=2, save_to_disk=save_figure)
    
    # oss_urls = oss_uplaoder.upload_files(image_paths)
    oss_urls = oss_uploader.upload_images(image_objects)
    
    # Step 4: 使用ChatGPT进行OCR（使用OCR的线程数和重试次数）
    ocr_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=ocr_max_workers) as executor:
        future_to_url = {executor.submit(ocr_with_chatgpt, PROMPT, url, chat_instance, ocr_max_retries): i for i, url in enumerate(oss_urls)}
        results_dict = {}
        for future in concurrent.futures.as_completed(future_to_url):
            index = future_to_url[future]
            result = future.result()
            results_dict[index] = result
        
        for i in range(len(oss_urls)):
            ocr_results.append(results_dict[i])

    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.writelines(f"{result}\n" for result in ocr_results)





oss_uploader = OSSUploader(
        bucket_name=ALIYUNOSS_BUCKET,
        aliyun_oss_upload_url=ALIYUNOSS_UPLOAD_URL,
        aliyun_oss_download_url=ALIYUNOSS_DOWNLOAD_URL,
        second_folder="pdf_ocr",
        max_retries=8,  # 上传重试次数
        max_workers=1   # 并发线程数
    )


chat_retry = Chat_Retry(
    api_key=API_KEY,
    model=MODEL,
    baseurl=BASE_URL,
    max_retries=5,  # 最大重试次数
    retry_delay=2   # 每次重试的延迟时间
)




# 主程序入口
process_pdf_with_ocr_in_one(
    raw_pdf_path = RAW_PDF_PATH,              # 原始PDF路径
    cropped_pdf_path = CROPPED_PDF_PATH,      # 裁剪后的PDF路径
    output_txt_path = OCR_CONTENT_DESTINATION,                    # OCR结果保存的文本路径
    chat_instance = chat_retry,               # 带重传机制的 Chat_Retry 实例
    save_figure = False,                      # 是否需要保存中间图片
    output_figure_folder=None,                # 中间图片文件目录
    # top_margin = TOP_MARGIN,                # 裁剪的上边距(一般为了裁剪页眉页脚)  未设置则自动裁剪页眉, 设置成0不裁剪
    # bottom_margin = BOTTOM_MARGIN,          # 裁剪的下边距
    ocr_max_retries=5,                        # 设置OCR的重试次数覆盖
    ocr_max_workers=2                         # 设置OCR的线程数
)
