import sys
import os
import base64
import re
import tkinter as tk
from tkinter import filedialog

# 配置参数
SUPPORTED_IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']
EXT_TO_MIME = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'bmp': 'image/bmp',
    'webp': 'image/webp'
}
MIME_TO_EXT = {v: k for k, v in EXT_TO_MIME.items()}

def convert_image_to_html(img_path):
    """图片转HTML（无提示）"""
    try:
        file_ext = os.path.splitext(img_path)[1][1:].lower()
        if file_ext not in SUPPORTED_IMAGE_EXTS:
            return False

        with open(img_path, 'rb') as f:
            img_data = f.read()
        b64_data = base64.b64encode(img_data).decode('utf-8')
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body>
    <img src="data:{EXT_TO_MIME[file_ext]};base64,{b64_data}">
</body>
</html>'''

        output_path = os.path.splitext(img_path)[0] + '.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return True
    except:
        return False

def convert_html_to_image(html_path):
    """HTML转图片（无提示）"""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read().replace('\n', ' ')

        pattern = re.compile(
            r'src\s*=\s*["\']data:(image/\w+);base64,([^"\']+)["\']', 
            re.IGNORECASE
        )
        match = pattern.search(content)
        if not match:
            return False

        mime_type, b64_data = match.groups()
        mime_type = mime_type.lower()
        if mime_type not in MIME_TO_EXT:
            return False

        img_data = base64.b64decode(b64_data)
        base_name = os.path.splitext(html_path)[0]
        ext = MIME_TO_EXT[mime_type]
        output_path = f"{base_name}.{ext}"
        
        # 自动处理重名文件
        counter = 1
        while os.path.exists(output_path):
            output_path = f"{base_name}({counter}).{ext}"
            counter += 1

        with open(output_path, 'wb') as f:
            f.write(img_data)
        return True
    except:
        return False

def batch_convert(folder_path):
    """静默批量转换"""
    has_converted = False
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            ext = filename.split('.')[-1].lower() if '.' in filename else ''
            success = False
            
            if ext in SUPPORTED_IMAGE_EXTS:
                success = convert_image_to_html(file_path)
            elif ext == 'html':
                success = convert_html_to_image(file_path)
            
            if success:
                has_converted = True
    return has_converted

def main():
    # 批量模式（双击运行）
    if len(sys.argv) == 1:
        root = tk.Tk()
        root.withdraw()
        folder_path = filedialog.askdirectory(title="选择要转换的文件夹")
        if folder_path:
            if batch_convert(folder_path):
                print("转换成功")
            else:
                print("未找到可转换文件")
        sys.exit()
    
    # 单文件模式（拖放文件）
    for file_path in sys.argv[1:]:
        if os.path.isfile(file_path):
            base_name = os.path.basename(file_path)
            ext = base_name.split('.')[-1].lower() if '.' in base_name else ''
            
            if ext in SUPPORTED_IMAGE_EXTS:
                convert_image_to_html(file_path)
            elif ext == 'html':
                convert_html_to_image(file_path)

if __name__ == '__main__':
    main()