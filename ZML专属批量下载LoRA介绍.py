#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LoRA模型介绍批量下载工具
功能：读取LoRA文件，计算哈希值，查询Civitai，下载预览图和描述信息
"""

import os
import sys
import hashlib
import json
import requests
from tqdm import tqdm
import concurrent.futures
import argparse
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import queue

# 设置请求头，模拟浏览器请求
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 不再使用缓存功能


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ZML专属LoRA模型介绍批量下载工具")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        self.root.minsize(500, 400)
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(self.main_frame, text="ZML专属LoRA模型介绍批量下载工具", font=('SimHei', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 路径输入区域
        path_frame = ttk.LabelFrame(self.main_frame, text="LoRA模型文件夹")
        path_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        browse_btn = ttk.Button(path_frame, text="浏览", command=self.browse_folder)
        browse_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 文件选项区域
        options_frame = ttk.LabelFrame(self.main_frame, text="下载选项")
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.download_txt = tk.BooleanVar(value=True)
        self.download_log = tk.BooleanVar(value=True)
        self.download_image = tk.BooleanVar(value=True)
        
        txt_check = ttk.Checkbutton(options_frame, text="触发词文件 (.txt)", variable=self.download_txt)
        txt_check.pack(anchor="w", padx=10, pady=3)
        
        log_check = ttk.Checkbutton(options_frame, text="描述信息文件 (.log)", variable=self.download_log)
        log_check.pack(anchor="w", padx=10, pady=3)
        
        image_check = ttk.Checkbutton(options_frame, text="预览图像", variable=self.download_image)
        image_check.pack(anchor="w", padx=10, pady=3)
        
        # 提示文本
        tip_label = ttk.Label(self.main_frame, text="下载的文件将保存在所选LoRA文件夹的'zml'子文件夹中", font=('SimHei', 10), foreground="#666666")
        tip_label.pack(pady=(0, 15), anchor="w")
        
        # 按钮区域 - 将扫描和下载按钮放在下载选项的下面
        btn_frame_top = ttk.Frame(self.main_frame)
        btn_frame_top.pack(fill=tk.X, pady=(0, 15))
        
        scan_btn = ttk.Button(btn_frame_top, text="扫描文件", command=self.scan_files)
        scan_btn.pack(side=tk.LEFT, padx=5)
        
        self.download_btn = ttk.Button(btn_frame_top, text="开始下载", command=self.start_download, width=15)
        self.download_btn.pack(side=tk.RIGHT, padx=5)
        
        # 文件列表区域
        list_frame = ttk.LabelFrame(self.main_frame, text="LoRA文件列表")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 文件列表树状视图
        self.file_tree = ttk.Treeview(list_frame, columns=('name', 'size'), show='headings', yscrollcommand=scrollbar.set)
        self.file_tree.heading('name', text='文件名')
        self.file_tree.heading('size', text='大小')
        self.file_tree.column('name', width=400, anchor='w')
        self.file_tree.column('size', width=100, anchor='e')
        self.file_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar.config(command=self.file_tree.yview)
        
        # 统计信息
        self.stats_label = ttk.Label(self.main_frame, text="未发现LoRA文件", font=('SimHei', 10))
        self.stats_label.pack(pady=(0, 10), anchor="w")
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 工作线程和队列
        self.result_queue = queue.Queue()
        self.root.after(100, self.process_queue)
        self.lora_files_info = []  # 存储文件信息
    
    def scan_files(self):
        folder_path = self.path_var.get().strip()
        if not folder_path:
            messagebox.showwarning("警告", "请输入或选择LoRA文件夹路径")
            return
        
        if not os.path.isdir(folder_path):
            messagebox.showerror("错误", "无效的文件夹路径")
            return
        
        # 清空文件列表
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 扫描文件
        self.status_var.set("正在扫描文件...")
        
        def scan_task():
            try:
                self.lora_files_info = []
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith('.safetensors'):
                            file_path = os.path.join(root, file)
                            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                            self.lora_files_info.append((file, f"{file_size:.2f} MB", file_path))
                
                # 排序并添加到队列
                self.lora_files_info.sort(key=lambda x: x[0])
                self.result_queue.put(("scan_result", self.lora_files_info))
            except Exception as e:
                self.result_queue.put(("error", str(e)))
        
        # 在后台线程中扫描
        threading.Thread(target=scan_task, daemon=True).start()
    
    def browse_folder(self):
        folder_path = filedialog.askdirectory(title="选择LoRA模型文件夹")
        if folder_path:
            self.path_var.set(folder_path)
            self.scan_files()
    
    def process_queue(self):
        try:
            item = self.result_queue.get_nowait()
            
            if item[0] == "scan_result":
                lora_files = item[1]
                # 更新文件列表
                for file_name, file_size, _ in lora_files:
                    self.file_tree.insert('', tk.END, values=(file_name, file_size))
                
                # 更新统计信息
                self.stats_label.config(text=f"发现 {len(lora_files)} 个LoRA文件")
                self.status_var.set("就绪")
            
            elif item[0] == "download_progress":
                self.status_var.set(item[1])
            
            elif item[0] == "download_complete":
                self.status_var.set("下载完成")
                messagebox.showinfo("完成", f"下载完成！成功: {item[1]}, 失败: {item[2]}")
            
            elif item[0] == "error":
                self.status_var.set("就绪")
                messagebox.showerror("错误", item[1])
                
        except queue.Empty:
            pass
        
        # 继续监听队列
        self.root.after(100, self.process_queue)
    
    def start_download(self):
        folder_path = self.path_var.get().strip()
        if not folder_path:
            messagebox.showwarning("警告", "请输入或选择LoRA文件夹路径")
            return
        
        if not os.path.isdir(folder_path):
            messagebox.showerror("错误", "无效的文件夹路径")
            return
        
        if not hasattr(self, 'lora_files_info') or not self.lora_files_info:
            messagebox.showwarning("警告", "请先扫描文件")
            return
        
        # 检查至少选择了一个下载选项
        if not (self.download_txt.get() or self.download_log.get() or self.download_image.get()):
            messagebox.showwarning("警告", "请至少选择一个下载选项")
            return
        
        # 获取设置
        settings = {
            'download_txt': self.download_txt.get(),
            'download_log': self.download_log.get(),
            'download_image': self.download_image.get(),
            'folder_path': folder_path
        }
        
        # 在后台线程中执行下载
        self.status_var.set("开始准备下载...")
        threading.Thread(target=self.download_task, args=(settings,), daemon=True).start()
    
    def download_task(self, settings):
        try:
            total_files = len(self.lora_files_info)
            success_count = 0
            fail_count = 0
            
            # 开始下载
            for i, (_, _, file_path) in enumerate(self.lora_files_info):
                file_name = os.path.basename(file_path)
                self.result_queue.put(("download_progress", f"正在处理 {i+1}/{total_files}: {file_name}"))
                
                # 处理文件 - 确保下载到zml子文件夹
                # 计算zml文件夹路径：在LoRA文件所在目录创建zml子文件夹
                lora_dir = os.path.dirname(file_path)
                zml_dir = os.path.join(lora_dir, "zml")
                
                result = process_lora_file(
                    file_path, 
                    output_dir=zml_dir,
                    download_txt=settings['download_txt'],
                    download_log=settings['download_log'],
                    download_image=settings['download_image']
                )
                
                if result:
                    success_count += 1
                else:
                    fail_count += 1
            
            # 完成
            self.result_queue.put(("download_complete", success_count, fail_count))
            
        except Exception as e:
            self.result_queue.put(("error", str(e)))


# 移除缓存相关函数


def calculate_file_hash(file_path, hash_type='sha256', chunk_size=8192):
    """计算文件哈希值"""
    hash_obj = hashlib.new(hash_type)
    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        print(f"❌ 计算文件 {os.path.basename(file_path)} 哈希值失败: {e}")
        return None


def fetch_civitai_data_by_hash(short_hash):
    """通过哈希值查询Civitai数据"""
    # 构建API请求URL
    url = f"https://civitai.com/api/v1/model-versions/by-hash/{short_hash}"
    
    try:
        # 发送请求获取版本信息
        print(f"🔍 查询Civitai: {short_hash}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ 查询失败: HTTP {response.status_code}")
            return None
        
        data = response.json()
        
        # 获取模型信息
        model_id = data.get('modelId')
        if model_id:
            model_url = f"https://civitai.com/api/v1/models/{model_id}"
            model_response = requests.get(model_url, headers=headers, timeout=30)
            
            if model_response.status_code == 200:
                model_data = model_response.json()
                data['model'] = model_data
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求错误: {e}")
        return None
    except json.JSONDecodeError:
        print("❌ 解析响应失败")
        return None


def download_file(url, save_path):
    """下载文件并显示进度"""
    import urllib.request
    import shutil
    
    # 确保目录存在
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    try:
        print(f"📥 开始下载: {os.path.basename(save_path)}")
        print(f"   URL: {url}")
        
        # 创建请求
        req = urllib.request.Request(url, headers=headers)
        
        # 使用tqdm显示进度
        with urllib.request.urlopen(req, timeout=30) as response, open(save_path, 'wb') as out_file:
            # 获取文件大小
            content_length = response.getheader('Content-Length')
            if content_length:
                total_size = int(content_length)
                
                # 使用tqdm显示进度
                with tqdm.tqdm(
                    desc=os.path.basename(save_path),
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                    # 分块下载
                    chunk_size = 8192
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        bar.update(len(chunk))
            else:
                # 如果没有Content-Length，直接复制
                shutil.copyfileobj(response, out_file)
        
        print(f"✅ 下载成功: {os.path.basename(save_path)}")
        return True
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP错误 {e.code}: {e.reason} - {url}")
        if os.path.exists(save_path):
            os.remove(save_path)
        return False
    except urllib.error.URLError as e:
        print(f"❌ 网络错误: {e.reason} - {url}")
        if os.path.exists(save_path):
            os.remove(save_path)
        return False
    except Exception as e:
        print(f"❌ 下载失败 {save_path}: {type(e).__name__} - {str(e)}")
        if os.path.exists(save_path):
            os.remove(save_path)
        return False


def process_lora_file(file_path, output_dir=None, download_txt=True, download_log=True, download_image=True):
    """处理单个LoRA文件"""
    file_name = os.path.basename(file_path)
    base_name = os.path.splitext(file_name)[0]
    
    # 如果没有指定输出目录，使用zml子目录
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(file_path), 'zml')
    
    print(f"\n🔍 开始处理: {file_name}")
    
    # 计算文件哈希
    full_hash = calculate_file_hash(file_path)
    if not full_hash:
        return False
    
    short_hash = full_hash[:10]
    print(f"✅ 计算哈希完成: {short_hash}")
    
    # 查询Civitai数据
    civitai_data = fetch_civitai_data_by_hash(short_hash)
    if not civitai_data:
        print(f"❌ 未找到 {file_name} 的Civitai数据")
        return False
    
    # 下载触发词
    if download_txt:
        trained_words = civitai_data.get('trainedWords', [])
        if trained_words:
            txt_content = ', '.join(trained_words)
            txt_path = os.path.join(output_dir, f"{base_name}.txt")
            try:
                os.makedirs(output_dir, exist_ok=True)
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(txt_content)
                print(f"✅ 触发词已保存: {base_name}.txt")
            except Exception as e:
                print(f"❌ 保存触发词失败: {e}")
        else:
            # 创建空的txt文件
            txt_path = os.path.join(output_dir, f"{base_name}.txt")
            os.makedirs(output_dir, exist_ok=True)
            open(txt_path, 'a').close()
            print(f"✅ 已创建空触发词文件: {base_name}.txt")
    
    # 下载描述信息
    if download_log:
        model_desc = civitai_data.get('model', {}).get('description', '无')
        version_desc = civitai_data.get('description', '无')
        
        log_content = f"--- 模型介绍 ---\n\n{model_desc}\n\n--- 版本信息 ---\n\n{version_desc}"
        
        log_path = os.path.join(output_dir, f"{base_name}.log")
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            print(f"✅ 描述信息已保存: {base_name}.log")
        except Exception as e:
            print(f"❌ 保存描述信息失败: {e}")
    
    # 下载预览图
    if download_image:
        images = civitai_data.get('images', [])
        if images:
            # 获取第一张图片
            image_url = images[0].get('url')
            if image_url:
                # 确定文件扩展名
                extension = '.jpg'
                if image_url.lower().endswith('.png'):
                    extension = '.png'
                elif image_url.lower().endswith('.webp'):
                    extension = '.webp'
                elif image_url.lower().endswith('.gif'):
                    extension = '.gif'
                
                image_path = os.path.join(output_dir, f"{base_name}{extension}")
                success = download_file(image_url, image_path)
                if success:
                    print(f"✅ 预览图已下载: {base_name}{extension}")
    
    return True

def main_gui():
    """启动GUI界面"""
    root = tk.Tk()
    app = App(root)
    root.mainloop()

def main():
    """主函数"""
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 命令行模式
        parser = argparse.ArgumentParser(description='LoRA模型介绍批量下载工具')
        parser.add_argument('path', help='包含LoRA文件的文件夹路径')
        parser.add_argument('-o', '--output', help='输出文件夹路径（可选，默认在LoRA文件夹的zml子目录）')
        parser.add_argument('-w', '--workers', type=int, default=5, help='并发工作线程数（默认5）')
        
        args = parser.parse_args()
        
        # 检查路径是否存在
        if not os.path.exists(args.path):
            print(f"❌ 路径不存在: {args.path}")
            return
        
        # 检查是否为文件夹
        if not os.path.isdir(args.path):
            # 如果是单个文件，处理单个文件
            if args.path.lower().endswith('.safetensors'):
                # 确保输出到zml子目录
                output_dir = os.path.join(os.path.dirname(args.path), 'zml')
                process_lora_file(args.path, output_dir)
            else:
                print("❌ 请提供文件夹路径或.safetensors文件")
        else:
            # 批量处理文件夹
            # 获取所有safetensors文件
            lora_files = []
            for root, _, files in os.walk(args.path):
                for file in files:
                    if file.lower().endswith('.safetensors'):
                        lora_files.append(os.path.join(root, file))
            
            if not lora_files:
                print("❌ 未找到.safetensors文件")
                return
            
            print(f"✅ 找到 {len(lora_files)} 个LoRA文件")
            
            # 处理文件
            results = []
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                # 提交任务
                future_to_file = {}
                for file in lora_files:
                    # 确保输出到zml子目录
                    output_dir = os.path.join(os.path.dirname(file), 'zml')
                    future_to_file[executor.submit(process_lora_file, file, output_dir)] = file
                
                # 获取结果
                for future in concurrent.futures.as_completed(future_to_file):
                    file = future_to_file[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        print(f"❌ 处理文件时出错 {os.path.basename(file)}: {e}")
                        results.append(False)
            
            # 显示统计信息
            success_count = sum(results)
            print(f"\n📊 处理完成: 成功 {success_count}/{len(lora_files)}")
    else:
        # GUI模式
        main_gui()


if __name__ == '__main__':
    print("====================================")
    print("  ZML专属LoRA模型介绍批量下载工具")
    print("====================================\n")
    
    # 检查必要的依赖
    try:
        import tqdm
    except ImportError:
        print("⚠️  缺少必要的依赖，正在安装...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'tqdm', 'requests'])
            print("✅ 依赖安装完成")
        except:
            print("❌ 依赖安装失败，请手动运行: pip install tqdm requests")
            sys.exit(1)
    
    # 运行主函数
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
    
    print("\n👋 程序已结束")