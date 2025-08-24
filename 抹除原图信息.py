import os
import sys
from PIL import Image

def clear_exif_faster(image_path, output_path=None):
    """更快速地清除图像的 Exif 信息。"""
    try:
        img = Image.open(image_path)
        image_without_exif = Image.new(img.mode, img.size)
        image_without_exif.putdata(list(img.getdata()))
        if output_path:
            image_without_exif.save(output_path)
        else:
            image_without_exif.save(image_path)
        return True
    except Exception as e:
        print(f"处理文件 {image_path} 时出错: {e}")
        return False

def generate_unique_filename(base_path, filename, suffix="-改", counter=None):
    """生成唯一的文件名，避免覆盖现有文件。"""
    name, ext = os.path.splitext(filename)
    if counter is None:
        new_filename = f"{name}{suffix}{ext}"
    else:
        new_filename = f"{name}{suffix}({counter}){ext}"

    new_path = os.path.join(base_path, new_filename)
    if os.path.exists(new_path):
        return generate_unique_filename(base_path, filename, suffix, (counter or 0) + 1)
    return new_path

def process_image(image_path, output_dir=None):
    """处理单个图像文件。"""
    dir_path = os.path.dirname(image_path)
    filename = os.path.basename(image_path)
    if output_dir:
        output_path = generate_unique_filename(output_dir, filename)
    else:
        output_path = generate_unique_filename(dir_path, filename, "-改")
    if clear_exif_faster(image_path, output_path):
        print(f"已处理: {image_path} -> {output_path}")

def process_directory(dir_path):
    """处理目录下的所有图片文件。"""
    output_base_dir = os.path.join(dir_path, "修改后的图片")
    output_dir = output_base_dir
    counter = 1
    while os.path.exists(output_dir):
        output_dir = f"{output_base_dir}({counter})"
        counter += 1
    os.makedirs(output_dir, exist_ok=True) # 使用 exist_ok=True 避免重复创建文件夹时的错误
    print(f"创建输出文件夹: {output_dir}")

    for filename in os.listdir(dir_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
            image_path = os.path.join(dir_path, filename)
            process_image(image_path, output_dir)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for input_path in sys.argv[1:]:
            if os.path.isfile(input_path) and input_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
                process_image(input_path)
            elif os.path.isdir(input_path):
                process_directory(input_path)
            else:
                print(f"不支持的文件类型或路径: {input_path}")
    else:
        print("请将图片文件或文件夹拖放到此脚本上。")

    # 移除暂停等待用户输入的代码，实现自动关闭