# 提取文本块并重命名图像.py

import os
import sys
import re
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

# -------------------- 配置 --------------------
# ZML节点用于存储文本块的特定键名
TEXT_BLOCK_KEY = "comfy_text_block"

# 支持的图片文件扩展名
SUPPORTED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']

# 文件名非法字符替换为下划线
ILLEGAL_CHARS = r'[<>"/\\|?*]'
# ----------------------------------------------

def sanitize_filename(filename):
    """
    清理文件名，移除或替换非法字符
    """
    # 更全面的非法字符列表，包括冒号、引号等
    illegal_chars = r'[<>"/\\|?*:,;=+&^%$#@!`~\[\]{}()]'
    
    # 替换非法字符为下划线
    sanitized = re.sub(illegal_chars, '_', filename)
    
    # 移除控制字符
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char == '\t' or char == '\n')
    
    # 移除多余的下划线
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # 移除文件名前后的空白和下划线
    sanitized = sanitized.strip('_ ')
    
    # 如果文件名过长，截断到250字符（Windows限制）
    if len(sanitized) > 250:
        sanitized = sanitized[:250]
    
    # 确保文件名不为空
    if not sanitized:
        sanitized = "unnamed"
    
    # 确保文件名不会只有点和下划线
    if all(c in '._' for c in sanitized):
        sanitized = "unnamed"
    
    return sanitized

def extract_text_block(image_path):
    """
    从图像中提取文本块
    """
    try:
        with Image.open(image_path) as img:
            if img.info and TEXT_BLOCK_KEY in img.info:
                return img.info[TEXT_BLOCK_KEY].strip()
    except Exception as e:
        print(f"❌ 读取图像 '{os.path.basename(image_path)}' 时出错: {e}")
    return None

def rename_images_with_text_blocks(folder_path):
    """
    从文件夹中的所有图像提取文本块并重命名
    """
    # 扫描文件夹中的所有图片文件
    image_files = [f for f in os.listdir(folder_path) 
                  if os.path.isfile(os.path.join(folder_path, f)) and 
                     os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS]
    
    if not image_files:
        messagebox.showinfo("提示", f"在文件夹 '{folder_path}' 中未找到支持的图片文件。")
        return
    
    print(f"找到 {len(image_files)} 个图像文件。")
    
    # 统计变量
    success_count = 0
    failure_count = 0
    skipped_count = 0
    renamed_files = []
    failed_files = []
    
    # 获取目标文件夹中已存在的所有文件名（用于更准确的冲突检测）
    existing_files = set(os.listdir(folder_path))
    
    # 首先扫描所有图像，收集将进行的重命名操作
    rename_operations = []
    for filename in image_files:
        image_path = os.path.join(folder_path, filename)
        original_ext = os.path.splitext(filename)[1].lower()
        
        try:
            # 提取文本块
            text_block = extract_text_block(image_path)
            
            if not text_block:
                print(f"ℹ️ 未在 '{filename}' 中找到文本块，跳过。")
                skipped_count += 1
                continue
            
            # 清理文本块作为新文件名
            new_name = sanitize_filename(text_block)
            new_filename = new_name + original_ext
            new_path = os.path.join(folder_path, new_filename)
            
            # 检查文件名冲突，使用更可靠的方法
            if new_filename != filename:
                # 检查新文件名是否已经存在
                if new_filename in existing_files or os.path.exists(new_path):
                    # 处理冲突 - 使用更可靠的编号方式
                    counter = 1
                    base_name = new_name
                    conflict_new_filename = new_filename
                    
                    # 循环直到找到一个不存在的文件名
                    while conflict_new_filename in existing_files or os.path.exists(os.path.join(folder_path, conflict_new_filename)):
                        conflict_new_filename = f"{base_name}_{counter}{original_ext}"
                        counter += 1
                        # 防止无限循环，最多尝试1000次
                        if counter > 1000:
                            print(f"❌ 警告: 为 '{filename}' 查找可用文件名时达到最大尝试次数，跳过。")
                            skipped_count += 1
                            conflict_new_filename = None
                            break
                    
                    if conflict_new_filename:
                        new_filename = conflict_new_filename
                        new_path = os.path.join(folder_path, new_filename)
                        # 将新文件名添加到已存在文件集合中，避免后续文件与这个新文件名冲突
                        existing_files.add(new_filename)
                        renamed_files.append(f"'{filename}' -> '{new_filename}' (冲突处理)")
                    else:
                        continue
                else:
                    # 将新文件名添加到已存在文件集合中，避免后续文件与这个新文件名冲突
                    existing_files.add(new_filename)
                    renamed_files.append(f"'{filename}' -> '{new_filename}'")
                
                rename_operations.append((image_path, new_path, filename, new_filename))
            else:
                print(f"ℹ️ '{filename}' 已经使用文本块命名，跳过。")
                skipped_count += 1
        except Exception as e:
            print(f"❌ 处理文件 '{filename}' 时出错: {str(e)}")
            skipped_count += 1
    
    # 确认操作
    if rename_operations:
        # 显示将要进行的重命名操作的简要信息
        print(f"\n即将重命名 {len(rename_operations)} 个文件。")
        if len(renamed_files) <= 10:
            for item in renamed_files[:10]:
                print(f"  {item}")
        else:
            for item in renamed_files[:5]:
                print(f"  {item}")
            print(f"  ... 还有 {len(renamed_files) - 5} 个文件...")
        
        confirm = messagebox.askyesno(
            "确认重命名",
            f"即将对 {len(rename_operations)} 个图像进行重命名操作。\n"
            f"跳过 {skipped_count} 个图像（无文本块、已使用文本块命名或处理出错）。\n\n"
            f"是否继续？"
        )
        
        if not confirm:
            print("操作已取消。")
            return
        
        print("\n开始执行重命名操作...")
        print("="*60)
        
        # 执行重命名
        for old_path, new_path, old_name, new_name in rename_operations:
            try:
                # 再次检查文件是否存在，以防在确认期间被其他程序修改
                if not os.path.exists(old_path):
                    print(f"❌ 失败: 源文件 '{old_name}' 不存在，跳过。")
                    failure_count += 1
                    failed_files.append(f"'{old_name}' (源文件不存在)")
                    continue
                    
                if os.path.exists(new_path):
                    # 再次处理意外的冲突
                    base_name, ext = os.path.splitext(new_name)
                    counter = 1
                    while os.path.exists(new_path):
                        new_path = os.path.join(folder_path, f"{base_name}_{counter}{ext}")
                        counter += 1
                    new_name = os.path.basename(new_path)
                    
                os.rename(old_path, new_path)
                print(f"✅ 成功: '{old_name}' -> '{new_name}'")
                success_count += 1
            except Exception as e:
                error_msg = str(e)
                if "无法创建该文件" in error_msg:
                    print(f"❌ 失败: 重命名 '{old_name}' -> '{new_name}' 时出错: 文件已存在")
                elif "语法不正确" in error_msg:
                    print(f"❌ 失败: 重命名 '{old_name}' -> '{new_name}' 时出错: 文件名包含非法字符")
                else:
                    print(f"❌ 失败: 重命名 '{old_name}' -> '{new_name}' 时出错: {error_msg}")
                failure_count += 1
                failed_files.append(f"'{old_name}' -> '{new_name}' (错误: {error_msg})")
    else:
        messagebox.showinfo("提示", "没有需要重命名的图像文件。")
        return
    
    # 显示结果摘要
    print("\n" + "="*60)
    print("操作完成！")
    print(f"成功重命名: {success_count} 个文件")
    if failure_count > 0:
        print(f"重命名失败: {failure_count} 个文件")
        # 显示前5个失败的文件信息
        if len(failed_files) <= 5:
            for item in failed_files:
                print(f"  - {item}")
        else:
            for item in failed_files[:3]:
                print(f"  - {item}")
            print(f"  ... 还有 {len(failed_files) - 3} 个失败文件...")
    if skipped_count > 0:
        print(f"跳过文件: {skipped_count} 个文件")
    print("="*60)
    
    # 准备弹窗消息
    result_msg = f"成功重命名: {success_count} 个文件\n"
    if failure_count > 0:
        result_msg += f"重命名失败: {failure_count} 个文件\n"
    result_msg += f"跳过文件: {skipped_count} 个文件"
    
    if failure_count > 0:
        messagebox.showwarning("操作完成（部分失败）", result_msg)
    else:
        messagebox.showinfo("操作完成", result_msg)

def main():
    """
    脚本主入口
    """
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 显示提示信息
    messagebox.showinfo(
        "提示", 
        "此脚本将从图像中提取文本块并使用提取的内容重命名图像。\n"
        "请选择包含图像的文件夹。"
    )
    
    # 选择文件夹
    folder_path = filedialog.askdirectory(
        title="请选择包含图像的文件夹"
    )
    
    if not folder_path:
        print("未选择文件夹，脚本已退出。")
        return
    
    print(f"已选择文件夹: {folder_path}")
    
    # 执行重命名操作
    rename_images_with_text_blocks(folder_path)

if __name__ == "__main__":
    main()
    input("\n按 Enter 键退出...")