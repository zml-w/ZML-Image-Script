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

def write_text_to_image_metadata(image_filepath, text_content):
    """
    将文本内容写入到PNG图像的comfy_text_block元数据中。
    """
    base_name = os.path.basename(image_filepath)
    try:
        with Image.open(image_filepath) as img:
            if img.format != "PNG":
                print(f"❌ 内部错误: 图片 '{base_name}' 格式不是PNG，无法写入文本块。")
                return False

            pnginfo = PngImagePlugin.PngInfo()
            for k, v in img.info.items():
                if k != TEXT_BLOCK_KEY and isinstance(k, str) and isinstance(v, str): 
                    pnginfo.add_text(k, v)
            
            pnginfo.add_text(TEXT_BLOCK_KEY, text_content)
            
            img.save(image_filepath, pnginfo=pnginfo)
            # print(f"✅ 成功写入: '{base_name}' 的文本块。") # 这一步在主要循环中统一显示
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
    """
    base_name = os.path.basename(file_path)
    folder_path = os.path.dirname(file_path)
    name_without_ext = os.path.splitext(base_name)[0]
    new_filepath_base = os.path.join(folder_path, name_without_ext) # 先不加扩展名
    
    # 防止文件重名冲突：如果转换后的文件名已经存在，尝试添加后缀
    counter = 0
    final_new_filepath = new_filepath_base + TARGET_EXTENSION
    while os.path.exists(final_new_filepath) and final_new_filepath != file_path:
        counter += 1
        final_new_filepath = name_without_ext + f"_{counter}" + TARGET_EXTENSION
        final_new_filepath = os.path.join(folder_path, final_new_filepath)

    if counter > 0:
        print(f"❗ 警告: 转换后文件名 '{name_without_ext}{TARGET_EXTENSION}' 已存在，将保存为 '{os.path.basename(final_new_filepath)}'。")

    try:
        with Image.open(file_path) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")

            pnginfo_to_transfer = PngImagePlugin.PngInfo()
            if img.format == "PNG" and img.info:
                 for k, v in img.info.items():
                     if isinstance(k, str) and isinstance(v, str):
                         pnginfo_to_transfer.add_text(k, v)

            if pnginfo_to_transfer.text:
                img.save(final_new_filepath, pnginfo=pnginfo_to_transfer)
            else:
                img.save(final_new_filepath)
            
            print(f"➡️ 成功转换: '{base_name}' -> '{os.path.basename(final_new_filepath)}'")
        
        # 只有当原始文件不是同名PNG时才删除。如果是同名PNG，其实就是写入覆盖，不需删除。
        if file_path != final_new_filepath:
            os.remove(file_path)
            print(f"🗑️ 成功删除原始文件: '{base_name}'")
        return True, final_new_filepath

    except Exception as e:
        print(f"❌ 错误: 转换或删除文件 '{base_name}' 时发生错误: {e}")
        return False, None

def process_current_image(
    image_folder_path, 
    original_filename, 
    image_temp_filepath, 
    new_image_name, 
    text_blocks
):
    """
    处理当前图片的重命名和文本块写入。
    返回True表示成功处理，False表示失败。
    """
    processed_successfully = True

    # 1. 确保图片是PNG格式 (如果不是，进行转换)
    # image_temp_filepath 已经是从这里出去的唯一PNG路径，或者原始路径就是PNG
    
    # 2. 如果新名称已设定，进行重命名
    final_image_filepath = image_temp_filepath
    if new_image_name:
        final_new_name_with_ext = new_image_name + TARGET_EXTENSION
        desired_final_filepath = os.path.join(image_folder_path, final_new_name_with_ext)

        if final_image_filepath != desired_final_filepath: # 避免自己重命名自己
            if os.path.exists(desired_final_filepath):
                print(f"❌ 重命名失败：目标文件名 '{final_new_name_with_ext}' 已存在。将不对该图片重命名，并尝试写入元数据到其当前路径。")
                # 不更新 final_image_filepath，保持在当前路径进行元数据写入
                # 并标记为部分失败
                processed_successfully = False 
            else:
                try:
                    os.rename(final_image_filepath, desired_final_filepath)
                    print(f"✅ 成功重命名: '{os.path.basename(final_image_filepath)}' -> '{final_new_name_with_ext}'")
                    final_image_filepath = desired_final_filepath # 更新路径为重命名后的路径
                except Exception as e:
                    print(f"❌ 重命名文件 '{os.path.basename(final_image_filepath)}' 为 '{final_new_name_with_ext}' 失败: {e}。")
                    processed_successfully = False # 标记失败

    # 3. 写入文本块到最终路径的图片
    if text_blocks:
        # 合并所有文本块，用双换行符分隔
        combined_text_content = "\n\n".join(text_blocks)
        if write_text_to_image_metadata(final_image_filepath, combined_text_content):
            print(f"✅ 成功写入文本块到: '{os.path.basename(final_image_filepath)}'。")
        else:
            print(f"❌ 写入文本块到 '{os.path.basename(final_image_filepath)}' 失败。")
            processed_successfully = False # 标记失败
    else:
        print(f"❗ 未为图片 '{os.path.basename(final_image_filepath)}' 指定文本块，跳过写入。")

    return processed_successfully


def main():
    """
    脚本主入口。
    """
    root = tk.Tk()
    root.withdraw() # 隐藏Tkinter主窗口，只显示对话框

    messagebox.showinfo(
        "提示", 
        "这是一个交互式脚本。请先选择一个图像文件夹，然后选择一个TXT文件。\n"
        "脚本将指导您逐行处理TXT内容。\n"
        "对于TXT的每一行，您可以选择将其作为图片的新名称，或作为文本块写入。\n"
        "多个文本块会自动用双换行符隔开。\n"
        "注意：脚本将直接修改原图的文件名和元数据，**不创建备份！**"
    )

    # 1. 选择图像文件夹
    image_folder_path = select_folder("请选择一个图像文件夹 (里面的图片将被重命名和写入文本块)")
    if not image_folder_path:
        messagebox.showinfo("取消", "未选择图像文件夹，脚本退出。")
        sys.exit()

    # 2. 选择TXT文件
    txt_file_path = select_file("请选择一个TXT文本文件 (提供新文件名和文本块内容)", [("Text files", "*.txt")])
    if not txt_file_path:
        messagebox.showinfo("取消", "未选择TXT文件，脚本退出。")
        sys.exit()

    print("\n" + "="*80)
    print(f"待处理图像文件夹: {image_folder_path}")
    print(f"文本源文件 (TXT): {txt_file_path}")
    print("注意: 脚本将直接修改原图，不创建备份。请确保您已备份重要文件！")
    print("操作模式: 逐行交互式处理，每次处理一张图片。")
    print("="*80 + "\n")

    # 3. 获取并排序所有待处理的图片文件
    all_raw_image_files_sorted = sorted([f for f in os.listdir(image_folder_path) 
                                         if os.path.splitext(f)[1].lower() in READABLE_EXTENSIONS],
                                        key=lambda x: [int(s) if s.isdigit() else s.lower() for s in re.split('([0-9]+)', os.path.splitext(x)[0])])
    
    if not all_raw_image_files_sorted:
        messagebox.showerror("错误", f"所选图像文件夹中未找到任何支持的图片文件（{', '.join(READABLE_EXTENSIONS)}）。")
        sys.exit()

    num_images_to_process = len(all_raw_image_files_sorted)
    print(f"待处理文件 (按自然顺序排列): {num_images_to_process} 张。\n")


    # 4. 初始化处理状态和统计
    image_processed_count = 0
    text_processed_count = 0
    total_renamed_count = 0
    total_write_success_count = 0
    total_fail_count = 0

    # 5. 打开TXT文件准备逐行读取
    try:
        txt_file = open(txt_file_path, 'r', encoding='utf-8-sig')
    except Exception as e:
        messagebox.showerror("错误", f"无法打开TXT文件进行读取: {e}")
        sys.exit()

    # 6. 主循环：逐个处理图片
    current_txt_line = "" # 当前从TXT读取到的行
    txt_line_num = 0      # 当前TXT行号

    while image_processed_count < num_images_to_process:
        original_filename = all_raw_image_files_sorted[image_processed_count]
        original_filepath = os.path.join(image_folder_path, original_filename)
        
        print("\n" + "*"*80)
        print(f"----- 开始处理第 {image_processed_count + 1} 张图片: '{original_filename}' -----")
        print("*"*80)

        # 准备当前图片的状态变量
        # current_image_temp_filepath 转换后的PNG文件路径，或原始PNG文件路径
        current_image_temp_filepath = original_filepath 
        new_image_name_for_current_image = None
        text_blocks_for_current_image = []

        # A. 确保图片是PNG格式 (如果不是，进行转换)
        if os.path.splitext(original_filename)[1].lower() != TARGET_EXTENSION:
            print(f"  图片 '{original_filename}' 检测到非PNG格式，尝试转换为PNG...")
            success_convert, converted_filepath = convert_to_png_and_delete_original(original_filepath)
            if not success_convert:
                print(f"❌ 转换 '{original_filename}' 失败，跳过此图片。")
                total_fail_count += 1
                image_processed_count += 1 # 移动到下一张图片
                continue # 继续外层循环，处理下一张图片
            current_image_temp_filepath = converted_filepath # 更新为转换后的PNG文件路径
            print(f"  转换成功，当前图片处理路径为: '{os.path.basename(current_image_temp_filepath)}'")
        else:
            print("  图片已经是PNG格式，无需转换。")
            current_image_temp_filepath = original_filepath # 确保路径正确

        # B. 交互式处理TXT行，直到用户切换图片或TXT读完
        while True:
            # 尝试从TXT文件读取下一行，如果之前已经读过但未处理，则使用已有的行
            current_txt_line = current_txt_line if current_txt_line else txt_file.readline()
            
            if not current_txt_line: # TXT文件已读完
                print("\n❗ TXT文件已全部读取完毕。")
                break # 退出内部循环，准备处理当前图片并结束任务

            txt_line = current_txt_line.strip()
            txt_line_num += 1 # TXT行号递增

            if not txt_line: # 跳过空行
                current_txt_line = "" # 清空，以便读取下一行
                continue

            print("\n" + "-"*50)
            print(f"当前图片: '{os.path.basename(current_image_temp_filepath)}'")
            print(f"已指定新名称: '{new_image_name_for_current_image}'" if new_image_name_for_current_image else "未指定新名称")
            print(f"已收集文本块: {len(text_blocks_for_current_image)} 个")
            print("-" * 50)
            print(f"  正在审阅TXT第 {txt_line_num} 行内容: '{txt_line}'")
            print("  请选择操作：")
            print("    1 - 将此行作为图片新名称 (覆盖旧名称)")
            print("    2 - 将此行作为文本块 (添加到现有文本块后面)")
            print("    0 - 结束当前图片处理，开始处理下一张图片")
            print("    Q - 退出整个脚本")
            
            user_choice = input("  您的选择 (1/2/0/Q): ").strip().upper()
            
            if user_choice == '1':
                if new_image_name_for_current_image:
                    print(f"❗ 警告: 新图片名称将从 '{new_image_name_for_current_image}' 变更为 '{txt_line}'。")
                new_image_name_for_current_image = txt_line
                print(f"  ✔️ 已指定新图片名称: '{new_image_name_for_current_image}'")
                text_processed_count += 1
            elif user_choice == '2':
                text_blocks_for_current_image.append(txt_line)
                print(f"  ✔️ 已将此行作为文本块添加到列表。当前共 '{len(text_blocks_for_current_image)}' 个文本块。")
                text_processed_count += 1
            elif user_choice == '0':
                print("  即将结束当前图片处理，准备处理下一张图片。")
                break # 退出内部循环，执行当前图片的保存操作
            elif user_choice == 'Q':
                if messagebox.askyesno("确认退出", "您确定要退出整个脚本吗？未保存的当前图片更改将丢失。"):
                    txt_file.close()
                    sys.exit("用户选择退出。")
                else:
                    print("用户取消退出，继续处理当前图片。")
                    current_txt_line = txt_line # 恢复当前行，让用户重新选择
                    txt_line_num -= 1 # 行号回退
                    continue
            else:
                print("无效输入，请重新输入 (1, 2, 0 或 Q)。")
                current_txt_line = txt_line # 保持当前行，让用户重新选择
                txt_line_num -= 1 # 行号回退
                continue
            
            current_txt_line = "" # 当前行已处理，清空以便读取下一行

        # C. 处理当前图片（重命名和写入文本块）
        print("\n" + "="*50)
        print(f"正在保存图片 '{os.path.basename(current_image_temp_filepath)}' 的更改...")
        processed_ok = process_current_image(
            image_folder_path, 
            original_filename, # 原始文件名仅用于日志，不用于后续处理
            current_image_temp_filepath, 
            new_image_name_for_current_image, 
            text_blocks_for_current_image
        )

        if processed_ok:
            print(f"成功处理了图片 '{os.path.basename(new_image_name_for_current_image + TARGET_EXTENSION if new_image_name_for_current_image else os.path.basename(current_image_temp_filepath))}'。")
            image_processed_count += 1
            total_renamed_count += (1 if new_image_name_for_current_image else 0)
            total_write_success_count += (1 if text_blocks_for_current_image else 0)
        else:
            print(f"处理图片 '{os.path.basename(current_image_temp_filepath)}' 失败或部分失败，请查看上方日志。")
            total_fail_count += 1
            image_processed_count += 1 # 即使失败也移动到下一张图片，除非用户明确想重试

        # 如果TXT文件已读完，且所有图片也处理完毕，则退出
        if not current_txt_line and image_processed_count >= num_images_to_process:
            break

    # 7. 结束统计和清理
    txt_file.close() # 关闭TXT文件

    print("\n" + "="*80)
    print("所有图片处理完毕或TXT文件已读完！")
    print(f"总共修改了: {image_processed_count} 张图片")
    print(f"其中，成功重命名了: {total_renamed_count} 张图片")
    print(f"成功写入文本块到: {total_write_success_count} 张图片")
    print(f"处理失败 (转换/重命名/写入): {total_fail_count} 张图片")
    print("="*80)
    
    # 最终结果弹窗
    messagebox.showinfo(
        "完成", 
        f"批量处理任务已完成！\n"
        f"处理图片总数: {image_processed_count} 张\n"
        f"成功重命名: {total_renamed_count} 张图片\n"
        f"成功写入文本块: {total_write_success_count} 张图片\n"
        f"处理失败: {total_fail_count} 张图片"
    )
    
    root.destroy() 


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        print(e)
    except Exception as e:
        messagebox.showerror("程序错误", f"发生未预期的错误: {e}")
        print(f"发生未预期的错误: {e}")
    finally:
        input("\n所有操作已完成，按 Enter 键退出...")

