import fitz  # PyMuPDF
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image    #, ImageChops
import numpy as np
import os
from pdf2image import convert_from_path

def auto_detect_margins(input_pdf):
    doc = fitz.open(input_pdf)
    header_height = 0
    footer_height = 0

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        lines = text.split('\n')

        # 使用pdfplumber加载页面，以获取页面尺寸
        with pdfplumber.open(input_pdf) as pdf:
            pdf_page = pdf.pages[page_num]
            page_width = pdf_page.width
            page_height = pdf_page.height

        # 假设页眉和页脚的文本在页面的前几行和最后几行
        if len(lines) > 0:
            header_height = max(header_height, page.search_for(lines[0])[0].y1 if page.search_for(lines[0]) else 0)
        if len(lines) > 1:
            footer_height = max(footer_height, page.search_for(lines[-1])[0].y1 if page.search_for(lines[-1]) else 0)

    return header_height, footer_height

def crop_pdf(input_path, output_path, top_margin=None, bottom_margin=None):
    if top_margin is None or bottom_margin is None:
        top_margin, bottom_margin = auto_detect_margins(input_path)
    
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        if top_margin > 0:
            page.mediabox.upper_right = (float(page.mediabox.right), float(page.mediabox.top) - top_margin)
        if bottom_margin > 0:
            page.mediabox.lower_left = (page.mediabox.left, page.mediabox.bottom + bottom_margin)
        writer.add_page(page)

    with open(output_path, "wb") as output_file:
        writer.write(output_file)

def remove_header_footer(input_pdf, output_pdf, top_margin=None, bottom_margin=None):
    crop_pdf(input_pdf, output_pdf, top_margin, bottom_margin)
    # print(f"Saved new PDF without headers and footers to {output_pdf}")



### 按照方差裁剪空白区域
def trim_left_right(im, margin=10):
    
    gray = im.convert('L')
    
    arr = np.array(gray)
    col_variances = np.var(arr, axis=0)
    
    threshold = np.mean(col_variances) / 10  # 灰度方差阈值, 低于会被认为是空白列
    content_cols = np.where(col_variances > threshold)[0]
    
    if len(content_cols) > 0:
        left = max(0, content_cols[0] - margin)
        right = min(im.width, content_cols[-1] + margin)
        return im.crop((left, 0, right, im.height))
    return im

def trim_top_bottom(im, margin=10):
    
    gray = im.convert('L')
    
    arr = np.array(gray)
    
    
    row_variances = np.var(arr, axis=1)
    
    
    threshold = np.mean(row_variances) / 10  # 方差阈值, 低于会被认为是空白行
    content_rows = np.where(row_variances > threshold)[0]
    
    if len(content_rows) > 0:
        top = max(0, content_rows[0] - margin)
        bottom = min(im.height, content_rows[-1] + margin)
        return im.crop((0, top, im.width, bottom))
    return im


def pdf_to_images(pdf_path, output_folder, images_per_long=2):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    images = convert_from_path(pdf_path, use_cropbox=True)
    
    # 裁剪每个图像的上下空白并更新 images 列表
    for i in range(len(images)):
        images[i] = trim_top_bottom(images[i]) 
        # images[i] = trim_left_right(images[i])
        
    
    image_paths = []
    
    for i in range(0, len(images), images_per_long):
        max_width = max(img.width for img in images[i:i+images_per_long])
        total_height = sum(img.height for img in images[i:i+images_per_long])
        long_image = Image.new('RGB', (max_width, total_height))
        
        # 将指定数量的图片粘贴到长图上
        current_height = 0
        for j in range(images_per_long):
            if i + j < len(images):
                long_image.paste(images[i + j], (0, current_height))
                current_height += images[i + j].height
        
        image_path = os.path.join(output_folder, f"{os.path.splitext(os.path.basename(pdf_path))[0]}_pages_{i + 1}-{min(i + images_per_long, len(images))}.png")
        long_image.save(image_path, 'PNG')
        image_paths.append(image_path)
    
    return image_paths


def pdf_to_images(pdf_path, output_folder = None, images_per_long=1, save_to_disk=False):
    if save_to_disk and not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    images = convert_from_path(pdf_path, use_cropbox=True)
    
    # 裁剪每个图像的上下空白
    for i in range(len(images)):
        images[i] = trim_top_bottom(images[i]) 
        # images[i] = trim_left_right(images[i])
    
    long_images = []  # 用于存储长图像对象
    
    for i in range(0, len(images), images_per_long):
        max_width = max(img.width for img in images[i:i+images_per_long])
        total_height = sum(img.height for img in images[i:i+images_per_long])
        long_image = Image.new('RGB', (max_width, total_height))
        
        # 将指定数量的图片粘贴到长图上
        current_height = 0
        for j in range(images_per_long):
            if i + j < len(images):
                long_image.paste(images[i + j], (0, current_height))
                current_height += images[i + j].height
        
        # 如果需要保存到本地
        if save_to_disk:
            image_path = os.path.join(output_folder, f"{os.path.splitext(os.path.basename(pdf_path))[0]}_pages_{i + 1}-{min(i + images_per_long, len(images))}.png")
            long_image.save(image_path, 'PNG')
        long_images.append(long_image)
    
    return long_images


