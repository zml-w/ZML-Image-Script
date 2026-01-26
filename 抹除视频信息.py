# -*- coding: utf-8 -*-

# 导入Python的标准模块
import sys  # 用于获取拖拽进来的文件或文件夹路径
import os   # 用于文件和路径操作，如判断类型、创建文件夹、拼接路径等
import subprocess # 用于执行FFmpeg命令行工具

# --- 全局配置 ---
# 在这里可以方便地添加你希望处理的视频文件格式
# 注意要以'.'开头，并且是小写
SUPPORTED_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.avi', '.flv', '.wmv')

def process_single_file(file_path):
    """
    处理单个视频文件的函数。
    新文件名后缀改为'_改'，并保存在原文件夹。
    """
    # 使用 os.path.splitext 来分离文件名和扩展名
    # 例如: "D:\\Videos\\test.mp4" -> ("D:\\Videos\\test", ".mp4")
    base_name, extension = os.path.splitext(file_path)

    # 检查文件的扩展名是否在我们支持的格式列表中
    if extension.lower() not in SUPPORTED_EXTENSIONS:
        print(f"-> [跳过] 非视频文件: {os.path.basename(file_path)}")
        return # 如果不是支持的视频格式，就直接跳过

    # 构建新的输出文件路径
    # 例如: "D:\\Videos\\test" + "_改" + ".mp4" -> "D:\\Videos\\test_改.mp4"
    output_path = f"{base_name}_改{extension}"
    
    print(f"-> [处理文件] {os.path.basename(file_path)}  ==>  {os.path.basename(output_path)}")
    # 调用核心的FFmpeg处理函数
    run_ffmpeg(file_path, output_path)

def process_directory(dir_path):
    """
    处理整个文件夹的函数。
    会在该文件夹内创建一个名为'清除后的文件'的子文件夹来存放结果。
    """
    print(f"--- 正在处理文件夹: {dir_path} ---")

    # 构建输出子文件夹的路径
    output_subdir = os.path.join(dir_path, "清除后的文件")
    
    # 检查并创建输出子文件夹
    # exist_ok=True 意味着如果这个文件夹已经存在，也不会报错
    os.makedirs(output_subdir, exist_ok=True)
    
    # os.walk 会遍历指定文件夹下的所有文件和子文件夹
    # 我们这里只需要遍历顶层目录，所以用 os.listdir 更简单直接
    for filename in os.listdir(dir_path):
        # 构造每个文件的完整路径
        file_path = os.path.join(dir_path, filename)
        
        # 判断当前遍历到的是否是一个文件（而不是子文件夹）
        if os.path.isfile(file_path):
            # 获取文件的扩展名，并转为小写以进行不区分大小写的比较
            _ , extension = os.path.splitext(filename)
            if extension.lower() in SUPPORTED_EXTENSIONS:
                # 如果是支持的视频格式，构建输出路径并调用FFmpeg处理
                output_path = os.path.join(output_subdir, filename)
                print(f"-> [处理文件] {filename}  ==>  {os.path.join('清除后的文件', filename)}")
                run_ffmpeg(file_path, output_path)
            else:
                 print(f"-> [跳过] 非视频文件: {filename}")


def run_ffmpeg(input_path, output_path):
    """
    这是执行FFmpeg命令的核心函数。
    """
    command = [
        'ffmpeg',
        '-i', input_path,       # 输入文件路径
        '-map_metadata', '-1',  # 移除所有元数据
        '-c', 'copy',           # 快速复制所有流（视频、音频、字幕等），不重新编码
        '-y',                   # 如果输出文件已存在，直接覆盖
        output_path             # 输出文件路径
    ]
    
    try:
        # 使用subprocess.run来执行命令。
        # stdout=subprocess.DEVNULL 和 stderr=subprocess.DEVNULL 的作用是“黑洞”。
        # 它会把FFmpeg在运行时产生的所有正常输出和错误输出都丢掉，
        # 这样命令行窗口就会非常干净，只显示我们自己print()的内容。
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   [成功] {os.path.basename(output_path)} 已生成。")

    except FileNotFoundError:
        # 这个错误只在系统找不到`ffmpeg`命令时出现
        print("!!! [严重错误] 找不到 'ffmpeg' 命令。请确保已正确安装并配置环境变量。")
    except subprocess.CalledProcessError:
        # FFmpeg执行失败（例如文件损坏）
        print(f"   [失败] 处理 {os.path.basename(input_path)} 时发生错误。")


# --- 脚本的主入口 ---
if __name__ == "__main__":
    # 检查是否有文件或文件夹被拖拽进来
    if len(sys.argv) > 1:
        # sys.argv[1] 就是拖拽进来的第一个目标的完整路径
        dragged_path = sys.argv[1]
        
        # 使用os.path来判断拖拽进来的是文件还是文件夹
        if os.path.isfile(dragged_path):
            # 如果是文件，调用文件处理函数
            process_single_file(dragged_path)
        elif os.path.isdir(dragged_path):
            # 如果是文件夹，调用文件夹处理函数
            process_directory(dragged_path)
        else:
            # 如果路径既不是文件也不是文件夹（例如快捷方式或不存在的路径）
            print(f"错误: 拖拽的目标不是有效的文件或文件夹 -> {dragged_path}")
    else:
        #如果没有拖拽任何东西，直接双击运行时
        print("--- 这是一个拖拽处理脚本 ---")
        print("请将一个视频文件或一个包含视频的文件夹拖拽到此脚本图标上。")
        # 直接双击运行时，为了让用户看到提示，我们暂停一下
        input("按回车键退出...")

    # 在所有情况下（处理完成、出错、直接双击），脚本运行到这里都会自动结束。
    # 命令行窗口会自动关闭，除非是直接双击运行的情况。
