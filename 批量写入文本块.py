import sys
import os
from PIL import Image, PngImagePlugin # 导入 PngImagePlugin 用于存储PNG元数据
import tkinter as tk
from tkinter import filedialog, messagebox
import re # 导入 re 模块用于自然排序

# -------------------- 配置 --------------------
# ZML节点用于存储文本块的特定键名
TEXT_BLOCK_KEY = "comfy_text_block"

# 仅支持的图片文件扩展名（在处理时，最终目标都是PNG）
TARGET_EXTENSION = '.png' 

# 所有支持读取并可能转换的图片文件扩展名
# 用户提供的脚本本身支持这些，所以我们在转换前也应该支持读取
READABLE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
# ----------------------------------------------


def select_folder(title="请选择一个图像文件夹"):
    """
    弹出一个对话框让用户选择一个文件夹。
    """
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title=title)
    root.destroy()
    return folder_path

def select_file(title="请选择一个TXT文本文件", filetypes=[("Text files", "*.txt")]):
    """
    弹出一个对话框让用户选择一个文件。
    """
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    return file_path

def read_text_from_file(txt_filepath):
    """
    从指定的TXT文件中读取所有行，并返回一个列表。
    """
    try:
        with open(txt_filepath, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()] 
        return lines
    except FileNotFoundError:
        messagebox.showerror("错误", f"未找到文件: {txt_filepath}")
        return None
    except Exception as e:
        messagebox.showerror("错误", f"读取TXT文件时发生错误: {e}")
        return None

def write_text_to_image_metadata(image_filepath, text_content):
    """
    将文本内容写入到PNG图像的comfy_text_block元数据中。
    """
    base_name = os.path.basename(image_filepath)
    try:
        with Image.open(image_filepath) as img:
            # 再次确认是PNG格式（经过转换后应该是）
            if img.format != "PNG":
                print(f"❌ 内部错误: 图片 '{base_name}' 格式不是PNG，无法写入文本块。")
                return False

            pnginfo = PngImagePlugin.PngInfo()
            
            # 遍历原始图像的info字典，保留其他元数据
            for k, v in img.info.items():
                if k != TEXT_BLOCK_KEY: 
                    pnginfo.add_text(k, v)
            
            # 添加或更新comfy_text_block
            pnginfo.add_text(TEXT_BLOCK_KEY, text_content)
            
            img.save(image_filepath, pnginfo=pnginfo)
            print(f"✅ 成功写入: '{base_name}' 的文本块。")
            return True

    except FileNotFoundError:
        print(f"❌ 错误: 未找到图片文件 '{base_name}'。")
        return False
    except Exception as e:
        print(f"❌ 错误: 写入图片 '{base_name}' 的文本块时发生错误: {e}")
        return False

def convert_to_png_and_delete_original(file_path):
    """
    将指定文件转换为PNG格式，然后删除原始文件。
    会尝试保留原始PNG的特定元数据（如comfy_text_block）
    但对于非PNG格式，通常无法保留其特有的元数据（如JPG的EXIF）。
    """
    base_name = os.path.basename(file_path)
    folder_path = os.path.dirname(file_path)
    name_without_ext = os.path.splitext(base_name)[0]
    new_filepath = os.path.join(folder_path, name_without_ext + TARGET_EXTENSION)

    try:
        with Image.open(file_path) as img:
            # 确保图像模式是RGB或RGBA，以避免转换问题（例如灰度图转彩色）
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA") # 转换为带透明度的RGB模式

            # 如果原图已经是PNG，且包含TEXT_BLOCK_KEY，尝试保留
            # 这是为了处理用户可能先有PNG，但有其他非PNG文件的情况
            pnginfo_to_transfer = PngImagePlugin.PngInfo()
            if img.format == "PNG" and img.info:
                 for k, v in img.info.items():
                     pnginfo_to_transfer.add_text(k, v)

            # 保存为新的PNG文件
            if pnginfo_to_transfer.width > 0: # If pnginfo_to_transfer has content
                img.save(new_filepath, pnginfo=pnginfo_to_transfer)
            else:
                img.save(new_filepath)
            
            print(f"➡️ 成功转换: '{base_name}' -> '{name_without_ext}{TARGET_EXTENSION}'")
        
        # 删除原始文件
        os.remove(file_path)
        print(f"🗑️ 成功删除原始文件: '{base_name}'")
        return True, new_filepath # 返回成功状态和新的PNG路径

    except Exception as e:
        print(f"❌ 错误: 转换或删除文件 '{base_name}' 时发生错误: {e}")
        return False, None


def main():
    """
    脚本主入口。
    """
    root = tk.Tk()
    root.withdraw() # 隐藏Tkinter主窗口，只显示对话框

    messagebox.showinfo(
        "提示", 
        "请先选择一个图像文件夹，然后选择一个TXT文件。\n"
        "注意：脚本将直接修改原图且不创建备份。\n"
        "如果检测到非PNG图片，可选择转换为PNG并删除原图。"
    )

    # 1. 选择图像文件夹
    image_folder_path = select_folder("请选择一个图像文件夹")
    if not image_folder_path:
        messagebox.showinfo("取消", "未选择图像文件夹，脚本退出。")
        sys.exit()

    # 2. 选择TXT文件
    txt_file_path = select_file("请选择一个TXT文本文件", [("Text files", "*.txt")])
    if not txt_file_path:
        messagebox.showinfo("取消", "未选择TXT文件，脚本退出。")
        sys.exit()

    print("\n" + "="*50)
    print(f"图像文件夹: {image_folder_path}")
    print(f"TXT文件: {txt_file_path}")
    print(f"注意: 脚本将直接修改原图，不创建备份。")
    print(f"目标图像格式: {TARGET_EXTENSION.upper()}")
    print("="*50 + "\n")

    # 3. 读取TXT文件内容
    text_lines = read_text_from_file(txt_file_path)
    if not text_lines:
        messagebox.showerror("错误", "TXT文件内容为空或读取失败，脚本退出。")
        sys.exit()
    print(f"TXT文件中读取到 {len(text_lines)} 行文本内容。")

    # 4. 扫描所有图片文件，区分 PNG 和非 PNG
    all_raw_image_files = [f for f in os.listdir(image_folder_path) 
                           if os.path.splitext(f)[1].lower() in READABLE_EXTENSIONS]
    
    if not all_raw_image_files:
        messagebox.showerror("错误", f"所选图像文件夹中未找到任何支持的图片文件（{', '.join(READABLE_EXTENSIONS)}）。")
        sys.exit()

    png_files = []
    other_format_files = []

    for f in all_raw_image_files:
        if os.path.splitext(f)[1].lower() == TARGET_EXTENSION:
            png_files.append(f)
        else:
            other_format_files.append(f)
    
    print(f"已发现 {len(png_files)} 张 PNG 图片。")
    print(f"已发现 {len(other_format_files)} 张其他格式图片。")

    # 5. 处理非 PNG 格式图片（询问用户）
    processed_png_files_from_conversion = []
    if other_format_files:
        response = messagebox.askyesno(
            "发现非PNG图片",
            f"在文件夹中发现 {len(other_format_files)} 张非PNG图片。\n\n"
            "选择 '是'：将这些图片批量转换为PNG格式并删除原始的非PNG图片。\n"
            "选择 '否'：跳过所有非PNG图片，仅处理已有的PNG图片。"
        )

        if response: # 用户选择转换为PNG
            print("\n开始将其他格式图片转换为PNG...")
            convert_success_count = 0
            convert_fail_count = 0
            for filename in other_format_files:
                full_path = os.path.join(image_folder_path, filename)
                success, new_path = convert_to_png_and_delete_original(full_path)
                if success:
                    convert_success_count += 1
                    # 记录新生成的PNG文件，以便后续处理
                    processed_png_files_from_conversion.append(os.path.basename(new_path))
                else:
                    convert_fail_count += 1
            print(f"图片转换完成。成功转换 {convert_success_count} 个，失败 {convert_fail_count} 个。")
        else: # 用户选择跳过
            print("用户选择跳过非PNG图片，仅处理现有PNG图片。")
            other_format_files = [] # 清空，表示不再处理这些文件

    # 6. 整合所有 PNG 图片列表，并进行自然排序
    # 原始PNG文件 + 刚刚转换生成的PNG文件
    final_png_files = png_files + processed_png_files_from_conversion
    final_png_files = sorted(final_png_files, 
                            key=lambda x: [int(s) if s.isdigit() else s.lower() for s in re.split('([0-9]+)', x)])
    
    if not final_png_files:
        messagebox.showerror("错误", "处理完成后，未找到任何可用的PNG图片。脚本退出。")
        sys.exit()

    print(f"\n最终将处理 {len(final_png_files)} 张 PNG 图片。")

    # 7. 检查文本行数与最终PNG图片数量是否匹配
    if len(text_lines) > len(final_png_files):
        response = messagebox.askyesno(
            "警告",
            f"TXT文件中的文本行数 ({len(text_lines)} 行) 大于图片数量 ({len(final_png_files)} 张)。\n"
            "多余的文本将不会被写入。是否继续？"
        )
        if not response:
            messagebox.showinfo("取消", "用户取消操作，脚本退出。")
            sys.exit()
    elif len(text_lines) < len(final_png_files):
        response = messagebox.askyesno(
            "警告",
            f"TXT文件中的文本行数 ({len(text_lines)} 行) 小于图片数量 ({len(final_png_files)} 张)。\n"
            "部分图片将不会被写入文本块。是否继续？"
        )
        if not response:
            messagebox.showinfo("取消", "用户取消操作，脚本退出。")
            sys.exit()

    # 8. 批量写入文本块
    success_write_count = 0
    failure_write_count = 0

    for i in range(min(len(text_lines), len(final_png_files))): 
        text_content = text_lines[i]
        image_filename = final_png_files[i]
        image_filepath = os.path.join(image_folder_path, image_filename)
        
        print(f"\n>>>> 正在处理图片: '{image_filename}' (第 {i+1} / {len(final_png_files)} 张)")
        print(f"     将写入文本: '{text_content}'")

        if write_text_to_image_metadata(image_filepath, text_content):
            success_write_count += 1
        else:
            failure_write_count += 1

    print("\n" + "="*50)
    print("所有图片处理完毕！")
    print(f"成功写入: {success_write_count} 张图片")
    print(f"写入失败: {failure_write_count} 张图片")
    print("="*50)
    
    messagebox.showinfo(
        "完成", 
        f"批量写入文本块已完成！\n成功修改: {success_write_count} 张图片\n修改失败: {failure_write_count} 张图片"
    )
    
    root.destroy() 


if __name__ == "__main__":
    main()
    input("\n按 Enter 键退出...")

