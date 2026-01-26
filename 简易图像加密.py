# --- drag_to_encrypt.py ---

import os
import sys
from PIL import Image
import random
import math
import ctypes # 用于隐藏Windows控制台窗口

# --- 核心图像处理辅助函数 ---

def split_image_into_blocks(image, block_size):
    """
    将图像分割成指定大小的矩形块。
    """
    img_width, img_height = image.size
    num_cols = math.ceil(img_width / block_size)
    num_rows = math.ceil(img_height / block_size)
    blocks = []
    for r in range(num_rows):
        for c in range(num_cols):
            left = c * block_size
            top = r * block_size
            right = min((c + 1) * block_size, img_width) 
            bottom = min((r + 1) * block_size, img_height) 
            block = image.crop((left, top, right, bottom))
            blocks.append(block)
    return blocks, img_width, img_height, num_rows, num_cols, block_size, block_size

def combine_blocks_into_image(blocks, img_width, img_height, num_rows, num_cols, block_width, block_height):
    """
    将一列图像块重新组合成一张完整的图像。
    """
    new_image = Image.new('RGB', (img_width, img_height))
    for i, block in enumerate(blocks):
        r = i // num_cols
        c = i % num_cols
        left = c * block_width
        top = r * block_height
        new_image.paste(block, (left, top))
    return new_image

# --- 核心加密函数 ---

def encrypt_image(image_path, password, block_size):
    """
    对图像进行块打乱加密。
    """
    try:
        original_image = Image.open(image_path).convert("RGB") 
    except FileNotFoundError:
        return None, f"错误：找不到文件 '{image_path}'。"
    except Exception as e:
        return None, f"加载图像时发生错误: {e}"

    # 调整图像尺寸，确保宽度和高度都能被block_size整除
    img_width, img_height = original_image.size
    new_width = (img_width // block_size) * block_size
    new_height = (img_height // block_size) * block_size
    
    # 如果尺寸发生变化，裁剪图像到合适大小
    if new_width != img_width or new_height != img_height:
        # 计算裁剪区域的左上角坐标，从中心裁剪
        left = (img_width - new_width) // 2
        top = (img_height - new_height) // 2
        right = left + new_width
        bottom = top + new_height
        original_image = original_image.crop((left, top, right, bottom))

    blocks, img_width, img_height, num_rows, num_cols, actual_block_width, actual_block_height = split_image_into_blocks(original_image, block_size)
    num_blocks = len(blocks)

    random.seed(password) 
    shuffled_indices = list(range(num_blocks))
    random.shuffle(shuffled_indices)
    
    # 创建打乱后的块数组
    shuffled_blocks = [None] * num_blocks
    for original_index, new_position_index in enumerate(shuffled_indices):
        shuffled_blocks[new_position_index] = blocks[original_index]

    # 重新组合图像
    encrypted_image = combine_blocks_into_image(
        shuffled_blocks, 
        img_width, img_height, 
        num_rows, num_cols, 
        actual_block_width, actual_block_height
    )
    return encrypted_image, "图像加密完成！"

def process_single_image(image_path, password, block_size):
    """处理单个图像文件的加密"""
    print(f"正在加密图像: {os.path.basename(image_path)}")
    
    # 尝试加密图像
    result_image, status_message = encrypt_image(image_path, password, block_size)

    if result_image:
        # 自动构建保存路径和文件名
        base_name, ext = os.path.splitext(os.path.basename(image_path))
        ext = ext.lower()

        # 默认保存为PNG，减少有损压缩导致的切割感
        actual_ext = '.png' if ext in ['.jpg', '.jpeg'] else ext
        
        # 完整新文件名： 原文件名_加密_块大小.后缀
        new_file_name = f"{base_name}_加密_{block_size}{actual_ext}"
        
        # 保存到原图像文件所在的目录
        output_dir = os.path.dirname(image_path)
        final_save_path = os.path.join(output_dir, new_file_name)

        try:
            result_image.save(final_save_path)
            print(f"加密成功！文件已保存到: {final_save_path}")
            return True
        except Exception as e:
            print(f"错误：保存加密图像时发生错误: {e}")
            return False
    else:
        print(f"加密失败: {status_message}")
        return False

def console_mode(password, block_size):
    """控制台交互模式"""
    print("========================================")
    print("          简易图像加密工具")
    print("========================================")
    print("请将图像文件拖拽到此窗口中，按Enter键开始加密")
    print(f"当前密码: {password}")
    print(f"当前块大小: {block_size}")
    print("========================================")
    print("\n等待图像文件...")
    
    while True:
        user_input = input().strip()
        
        # 移除路径两端的引号（Windows拖拽文件会自动添加引号）
        if user_input.startswith('"') and user_input.endswith('"'):
            user_input = user_input[1:-1]
        
        if user_input.lower() == 'exit':
            print("感谢使用，再见！")
            break
            
        if os.path.isfile(user_input):
            # 处理单个文件
            process_single_image(user_input, password, block_size)
            print("\n等待图像文件...")
        elif os.path.isdir(user_input):
            # 处理文件夹中的所有图像
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
            files_to_process = [f for f in os.listdir(user_input) 
                              if os.path.isfile(os.path.join(user_input, f)) and 
                              os.path.splitext(f)[1].lower() in image_extensions]
            
            if files_to_process:
                print(f"找到 {len(files_to_process)} 个图像文件，开始批量处理...")
                success_count = 0
                for file_name in files_to_process:
                    file_path = os.path.join(user_input, file_name)
                    if process_single_image(file_path, password, block_size):
                        success_count += 1
                print(f"批量处理完成！成功: {success_count}/{len(files_to_process)}")
                print("\n等待图像文件...")
            else:
                print("指定文件夹中没有找到支持的图像文件")
                print("\n等待图像文件...")
        else:
            print("错误：请输入有效的文件或文件夹路径")
            print("\n等待图像文件...")

# --- 隐藏控制台窗口 (仅限Windows) ---
# 只有在通过拖拽文件运行时才隐藏控制台窗口
# 如果是直接运行脚本（双击），则显示控制台窗口
hide_console = False

# --- 主逻辑 ---
if __name__ == "__main__":
    fixed_password = "在梦里w"
    fixed_block_size = 16
    
    # 判断运行模式：
    # 1. 如果有命令行参数（拖拽文件），则自动处理并隐藏控制台
    # 2. 如果没有参数，则显示控制台等待用户交互
    if len(sys.argv) > 1:
        # 获取拖拽进来的文件路径列表
        files_to_process = sys.argv[1:]
        
        # 隐藏控制台窗口（仅在Windows上）
        try:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0) # 0 = SW_HIDE
        except:
            pass # 非Windows系统会失败，忽略
        
        # 处理所有拖拽的文件
        for image_to_process in files_to_process:
            if os.path.isfile(image_to_process):
                process_single_image(image_to_process, fixed_password, fixed_block_size)
        
        # 自动退出
        sys.exit(0)
    else:
        # 控制台交互模式
        console_mode(fixed_password, fixed_block_size)
        # 等待用户按键后退出
        input("\n按任意键退出...")
