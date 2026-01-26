import sys
import os
from PIL import Image, PngImagePlugin # 导入 PngImagePlugin 用于存储PNG元数据
import tkinter as tk
from tkinter import filedialog, messagebox
import re # 导入 re 模块用于自然排序

# -------------------- 配置 --------------------
# ZML节点用于存储文本块的特定键名
TEXT_BLOCK_KEY = "comfy_text_block"

# 目标图片文件扩展名（所有图片最终都应该成为PNG）
TARGET_EXTENSION = '.png' 

# 所有支持读取并可能转换的图片文件扩展名
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
    从指定的TXT文件中读取所有行，并按照奇偶行规则解析。
    奇数行作为新的图片名称 (new_filename)，偶数行作为对应的文本内容 (text_content)。
    返回一个列表，其中每个元素是一个字典 {'new_filename': '...', 'text_block': '...'}.
    """
    paired_data = []
    try:
        # 使用 'utf-8-sig' 编码，可以自动处理并移除BOM字符（如你遇到的 '﻿'）
        with open(txt_filepath, 'r', encoding='utf-8-sig') as f:
            # 读取所有非空行，并去除首尾空白
            all_lines = [line.strip() for line in f if line.strip()]
        
        # 检查行数是否至少够一个配对
        if len(all_lines) < 2:
            messagebox.showerror("错误", "TXT文件内容不足以形成图片名称和文本块配对（至少需要两行）。")
            return None

        # 检查行数是否为偶数
        if len(all_lines) % 2 != 0:
            messagebox.showwarning("警告", f"TXT文件中的总行数 ({len(all_lines)} 行) 为奇数，这意味着最后一行文本（作为新图片名或文本块）没有对应的配对。脚本将跳过不成对的最后一行。")
            all_lines.pop() # 移除最后一行，确保所有数据都成对
        
        # 遍历所有行，步长为2，处理奇数行（新图片名称）和偶数行（文本内容）
        for i in range(0, len(all_lines), 2):
            new_filename = all_lines[i]   # 奇数行（txt实际行号1,3,5...）作为新图片名称
            text_block = all_lines[i + 1] # 偶数行（txt实际行号2,4,6...）作为文本块

            # 简单的验证，防止图片名或文本块为空
            if not new_filename:
                messagebox.showwarning("警告", f"TXT文件第 {i+1} 行的新图片名为空，跳过此配对。")
                continue
            if not text_block:
                messagebox.showwarning("警告", f"TXT文件第 {i+2} 行的文本块为空，图片 '{new_filename}' 将写入空文本块。")
                # 即使文本块为空，我们也可能希望处理它，所以不 'continue'

            paired_data.append({'new_filename': new_filename, 'text_block': text_block})
            
        return paired_data
        
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
            # 确保是PNG格式
            if img.format != "PNG":
                print(f"❌ 内部错误: 图片 '{base_name}' 格式不是PNG，无法写入文本块。")
                return False

            pnginfo = PngImagePlugin.PngInfo()
            
            # 遍历原始图像的info字典，保留其他元数据
            for k, v in img.info.items():
                if k != TEXT_BLOCK_KEY and isinstance(k, str) and isinstance(v, str): 
                    pnginfo.add_text(k, v)
            
            # 添加或更新comfy_text_block
            pnginfo.add_text(TEXT_BLOCK_KEY, text_content)
            
            # 保存到原始路径，覆盖原文件
            img.save(image_filepath, pnginfo=pnginfo)
            # print(f"✅ 成功写入: '{base_name}' 的文本块。") # 这一步在重命名后执行，不在控制台显示详细信息
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
    会尝试保留原始PNG的特定元数据（如comfy_text_block）。
    对于非PNG格式，通常无法保留其特有的元数据（如JPG的EXIF）。
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
            pnginfo_to_transfer = PngImagePlugin.PngInfo()
            if img.format == "PNG" and img.info:
                 for k, v in img.info.items():
                     if isinstance(k, str) and isinstance(v, str): # 确保键值都是字符串
                         pnginfo_to_transfer.add_text(k, v)

            # 保存为新的PNG文件
            if pnginfo_to_transfer.text:
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
        "请先选择一个包含图片（将被重命名和写入文本块）的文件夹，然后选择一个TXT文件。\n"
        "注意：脚本将直接修改原图的文件名和元数据，**不创建备份！**\n"
        "如果检测到非PNG图片，可选择转换为PNG并删除原图。\n\n"
        "TXT文件格式要求：\n"
        "奇数行 (1,3,5...)：将作为图片的新文件名 (不含扩展名)，例如 '深吻'\n"
        "偶数行 (2,4,6...)：将作为文本内容写入该图片，例如 '这是“深吻”的描述'"
    )

    # 1. 选择图像文件夹
    image_folder_path = select_folder("请选择一个图像文件夹 (里面的图片将被重命名并写入文本块)")
    if not image_folder_path:
        messagebox.showinfo("取消", "未选择图像文件夹，脚本退出。")
        sys.exit()

    # 2. 选择TXT文件
    txt_file_path = select_file("请选择一个TXT文本文件 (提供新文件名和文本块内容)", [("Text files", "*.txt")])
    if not txt_file_path:
        messagebox.showinfo("取消", "未选择TXT文件，脚本退出。")
        sys.exit()

    print("\n" + "="*50)
    print(f"待处理图像文件夹: {image_folder_path}")
    print(f"文本源文件 (TXT): {txt_file_path}")
    print(f"注意: 脚本将直接修改原图，不创建备份。")
    print(f"目标图像格式: {TARGET_EXTENSION.upper()}")
    print("="*50 + "\n")

    # 3. 读取TXT文件内容并解析成图片名称和文本块配对
    paired_text_data = read_text_from_file(txt_file_path)
    if not paired_text_data:
        messagebox.showerror("错误", "TXT文件内容为空或读取解析失败，脚本退出。")
        sys.exit()
    print(f"TXT文件中解析出 {len(paired_text_data)} 对 (新图片名称-文本块) 数据。")

    # 4. 扫描待处理图片文件夹，获取所有原始文件列表
    # 按照文件名进行自然排序，以确保与TXT内容的顺序一致
    all_raw_image_files_sorted = sorted([f for f in os.listdir(image_folder_path) 
                                         if os.path.splitext(f)[1].lower() in READABLE_EXTENSIONS],
                                        key=lambda x: [int(s) if s.isdigit() else s.lower() for s in re.split('([0-9]+)', os.path.splitext(x)[0])])
    
    if not all_raw_image_files_sorted:
        messagebox.showerror("错误", f"所选图像文件夹中未找到任何支持的图片文件（{', '.join(READABLE_EXTENSIONS)}）。")
        sys.exit()

    print(f"待处理文件 (按自然顺序排列): {len(all_raw_image_files_sorted)} 张。\n")
    # print("待处理文件列表:")
    # for f in all_raw_image_files_sorted:
    #     print(f" - {f}")

    # 5. 检查TX T配对数量与图片数量是否匹配
    num_txt_pairs = len(paired_text_data)
    num_images_to_process = len(all_raw_image_files_sorted)

    if num_txt_pairs == 0:
        messagebox.showerror("错误", "TXT文件中没有有效的图片名称和文本块配对，脚本退出。")
        sys.exit()

    if num_txt_pairs < num_images_to_process:
        response = messagebox.askyesno(
            "警告",
            f"TXT文件中的图片名-文本块配对数 ({num_txt_pairs}) 小于待处理图片数量 ({num_images_to_process})。\n"
            "多余的图片将不会被重命名和写入文本块。是否继续？"
        )
        if not response:
            messagebox.showinfo("取消", "用户取消操作，脚本退出。")
            sys.exit()
        # 截断图片列表，只处理与TXT配对数量相同的图片
        all_raw_image_files_sorted = all_raw_image_files_sorted[:num_txt_pairs]
        print(f"基于TXT文件配对数量，将实际处理 {len(all_raw_image_files_sorted)} 张图片。")

    elif num_txt_pairs > num_images_to_process:
        response = messagebox.askyesno(
            "警告",
            f"TXT文件中的图片名-文本块配对数 ({num_txt_pairs}) 大于待处理图片数量 ({num_images_to_process})。\n"
            "多余的TXT配对将不会有图片可以重命名和写入。是否继续？"
        )
        if not response:
            messagebox.showinfo("取消", "用户取消操作，脚本退出。")
            sys.exit()
        # 截断TXT配对数据，只处理与图片数量相同的配对
        paired_text_data = paired_text_data[:num_images_to_process]
        print(f"基于待处理图片数量，将实际使用TXT中前 {len(paired_text_data)} 个配对。")
    
    # 至此，num_txt_pairs 和 num_images_to_process 应该已协调一致
    print(f"最终将处理 {len(all_raw_image_files_sorted)} 张图片，并使用 {len(paired_text_data)} 个TXT配对。")


    # 6. 核心逻辑：遍历，转换，重命名，写入元数据
    renamed_count = 0
    write_success_count = 0
    fail_count = 0

    print("\n" + "="*50)
    print("开始批量处理图片 (转换、重命名、写入文本块)...")
    print("="*50 + "\n")

    for i in range(len(paired_text_data)):
        original_filename = all_raw_image_files_sorted[i]
        original_filepath = os.path.join(image_folder_path, original_filename)
        
        data_pair = paired_text_data[i]
        new_base_filename = data_pair['new_filename'] # 从TXT奇数行获取的新文件名（不含扩展名）
        text_content = data_pair['text_block']        # 从TXT偶数行获取的文本块

        print(f"\n===== 正在处理第 {i+1} 张图片 =====")
        print(f"  原始文件: '{original_filename}'")
        print(f"  新文件名: '{new_base_filename}{TARGET_EXTENSION}'")
        print(f"  将写入文本: '{text_content}'")

        current_filepath_to_process = original_filepath

        # A. 确保图片是PNG格式 (如果不是，进行转换)
        if os.path.splitext(original_filename)[1].lower() != TARGET_EXTENSION:
            print("  检测到非PNG格式，尝试转换为PNG...")
            success_convert, converted_filepath = convert_to_png_and_delete_original(original_filepath)
            if not success_convert:
                print(f"❌ 转换 '{original_filename}' 失败，跳过此文件。")
                fail_count += 1
                continue # 跳过当前文件，处理下一个
            current_filepath_to_process = converted_filepath # 更新为转换后的PNG文件路径
            print(f"  转换成功，临时处理文件为: '{os.path.basename(current_filepath_to_process)}'")
        else:
            print("  图片已经是PNG格式，无需转换。")

        # B. 重命名文件
        # 新的完整文件路径，使用TXT提供的新基础文件名和TARGET_EXTENSION
        final_new_filepath = os.path.join(image_folder_path, new_base_filename + TARGET_EXTENSION)
        if os.path.exists(final_new_filepath) and final_new_filepath != current_filepath_to_process:
            # 如果新文件名已经存在，并且不是当前正在处理的这个文件的路径
            messagebox.showwarning("警告", f"新文件名 '{new_base_filename}{TARGET_EXTENSION}' 已存在！\n"
                                     f"原始文件 '{os.path.basename(current_filepath_to_process)}' 将不会被重命名以避免覆盖。请手动处理冲突。")
            print(f"❌ 重命名失败：新文件名 '{new_base_filename}{TARGET_EXTENSION}' 已存在。跳过此文件重命名。")
            fail_count += 1
            # 即使重命名失败，我们仍然尝试写入元数据到原始文件（如果它是PNG）
            # 或者到转换后的文件，但这可能意味着元数据写入到不是期望的文件名。
            # 为了明确，这里我们直接跳过这一整个文件的处理。
            continue 
        
        try:
            # os.rename 会将文件移动或重命名
            os.rename(current_filepath_to_process, final_new_filepath)
            print(f"✅ 成功重命名: '{os.path.basename(current_filepath_to_process)}' -> '{new_base_filename}{TARGET_EXTENSION}'")
            renamed_count += 1
            current_filepath_to_process = final_new_filepath # 更新路径为重命名后的路径
        except Exception as e:
            print(f"❌ 重命名文件 '{os.path.basename(current_filepath_to_process)}' 为 '{new_base_filename}{TARGET_EXTENSION}' 失败: {e}。跳过此文件处理。")
            fail_count += 1
            continue # 跳过当前文件，处理下一个

        # C. 写入文本块到重命名后的图片
        # 只有在重命名成功之后，才对这个文件写入元数据
        if write_text_to_image_metadata(current_filepath_to_process, text_content):
            write_success_count += 1
        else:
            print(f"❌ 写入文本块到 '{new_base_filename}{TARGET_EXTENSION}' 失败。")
            fail_count += 1 # 写入失败也算作一个失败

    print("\n" + "="*50)
    print("所有图片处理完毕！")
    print(f"成功重命名: {renamed_count} 张图片")
    print(f"成功写入文本块: {write_success_count} 张图片")
    print(f"处理失败 (转换/重命名/写入): {fail_count} 张图片")
    print("="*50)
    
    messagebox.showinfo(
        "完成", 
        f"批量重命名和写入文本块已完成！\n"
        f"成功重命名: {renamed_count} 张图片\n"
        f"成功写入文本块: {write_success_count} 张图片\n"
        f"处理失败: {fail_count} 张图片"
    )
    
    root.destroy() 


if __name__ == "__main__":
    main()
    # 保持这个，让窗口不自动关闭
    input("\n所有操作已完成，按 Enter 键退出...")

