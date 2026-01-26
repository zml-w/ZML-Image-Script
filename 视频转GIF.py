import sys
import os
import cv2
import numpy as np
import time
from PIL import Image
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from sklearn.cluster import MiniBatchKMeans

# 修改默认配置
DEFAULT_SETTINGS = {
    'frame_step': 1,
    'color_optim': False,
    'scale_factor': 0.5,
    'vector_quantization': False,
    'vector_colors': 16,
    'dynamic_framerate': False,
    'motion_threshold': 10,
    'processing_order': 'efficiency',  # 'efficiency'或'quality'
    'time_logging': True
}

def show_settings_dialog():
    """显示完整设置弹窗（包含处理顺序选项和时间记录）"""
    root = tk.Tk()
    root.title("GIF转换设置")
    root.geometry("550x550")
    
    # 变量初始化
    var_step = tk.IntVar(value=DEFAULT_SETTINGS['frame_step'])
    var_color = tk.BooleanVar(value=DEFAULT_SETTINGS['color_optim'])
    var_scale = tk.DoubleVar(value=DEFAULT_SETTINGS['scale_factor'])
    var_vector = tk.BooleanVar(value=DEFAULT_SETTINGS['vector_quantization'])
    var_vector_colors = tk.IntVar(value=DEFAULT_SETTINGS['vector_colors'])
    var_dynamic = tk.BooleanVar(value=DEFAULT_SETTINGS['dynamic_framerate'])
    var_threshold = tk.IntVar(value=DEFAULT_SETTINGS['motion_threshold'])
    var_order = tk.StringVar(value=DEFAULT_SETTINGS['processing_order'])
    var_time_log = tk.BooleanVar(value=DEFAULT_SETTINGS['time_logging'])
    
    # 创建带滚动条的画布
    canvas = tk.Canvas(root)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # 基本设置区域
    ttk.Label(scrollable_frame, text="基本设置", font=("Arial", 10, "bold")).pack(pady=(10,5), anchor='w', padx=10)
    
    # 缩放选项
    frame_scale = ttk.Frame(scrollable_frame)
    frame_scale.pack(fill='x', padx=10, pady=5)
    ttk.Label(frame_scale, text="缩放比例:").grid(row=0, column=0, sticky='w')
    ttk.Combobox(frame_scale, textvariable=var_scale, 
                values=[1.0, 0.75, 0.5, 0.33, 0.25], 
                width=6).grid(row=0, column=1, padx=5, sticky='w')
    
    # 跳帧选项
    frame_step = ttk.Frame(scrollable_frame)
    frame_step.pack(fill='x', padx=10, pady=5)
    ttk.Label(frame_step, text="跳帧步长:").grid(row=0, column=0, sticky='w')
    ttk.Combobox(frame_step, textvariable=var_step, 
                values=[1, 2, 3, 4, 5], 
                width=6).grid(row=0, column=1, padx=5, sticky='w')
    
    # 颜色优化
    frame_color = ttk.Frame(scrollable_frame)
    frame_color.pack(fill='x', padx=10, pady=5)
    ttk.Checkbutton(frame_color, text="启用32色优化", variable=var_color).grid(row=0, column=0, sticky='w')
    
    # 高级压缩选项区域
    ttk.Label(scrollable_frame, text="高级压缩选项", font=("Arial", 10, "bold")).pack(pady=(15,5), anchor='w', padx=10)
    
    # 矢量量化选项
    frame_vector = ttk.Frame(scrollable_frame)
    frame_vector.pack(fill='x', padx=10, pady=5)
    ttk.Checkbutton(frame_vector, text="启用矢量量化 (更小文件)", variable=var_vector).grid(row=0, column=0, sticky='w')
    ttk.Label(frame_vector, text="颜色数量:").grid(row=0, column=1, padx=5, sticky='w')
    ttk.Combobox(frame_vector, textvariable=var_vector_colors, 
                values=[256, 128, 64, 32, 16, 8], 
                width=4).grid(row=0, column=2, sticky='w')
    
    # 动态帧率选项
    frame_dynamic = ttk.Frame(scrollable_frame)
    frame_dynamic.pack(fill='x', padx=10, pady=5)
    ttk.Checkbutton(frame_dynamic, text="启用动态帧率 (智能跳帧)", variable=var_dynamic).grid(row=0, column=0, sticky='w')
    ttk.Label(frame_dynamic, text="运动阈值:").grid(row=0, column=1, padx=5, sticky='w')
    ttk.Scale(frame_dynamic, from_=1, to=50, variable=var_threshold, 
             orient="horizontal", length=150).grid(row=0, column=2, padx=5)
    ttk.Label(frame_dynamic, textvariable=var_threshold).grid(row=0, column=3, padx=5)
    
    # 处理顺序选项
    frame_order = ttk.Frame(scrollable_frame)
    frame_order.pack(fill='x', padx=10, pady=10)
    ttk.Label(frame_order, text="处理顺序:").grid(row=0, column=0, sticky='w')
    ttk.Radiobutton(frame_order, text="效率优先 (先缩放和跳帧)", 
                   variable=var_order, value='efficiency').grid(row=0, column=1, padx=5, sticky='w')
    ttk.Radiobutton(frame_order, text="质量优先 (先矢量量化)", 
                   variable=var_order, value='quality').grid(row=1, column=1, padx=5, sticky='w')
    
    # 时间记录选项
    frame_time = ttk.Frame(scrollable_frame)
    frame_time.pack(fill='x', padx=10, pady=5)
    ttk.Label(frame_time, text="时间记录:").grid(row=0, column=0, sticky='w')
    ttk.Checkbutton(frame_time, text="在控制台显示详细处理时间", variable=var_time_log).grid(row=0, column=1, sticky='w')
    
    # 说明标签
    ttk.Label(scrollable_frame, 
             text="注意：高级选项需要额外依赖(scikit-learn)，首次使用请安装: pip install scikit-learn", 
             foreground="blue", font=("Arial", 9)).pack(pady=(10,5), anchor='w', padx=10)
    
    # 按钮
    btn_frame = ttk.Frame(scrollable_frame)
    btn_frame.pack(pady=15)
    ttk.Button(btn_frame, text="开始转换", command=lambda: on_confirm(), width=15).pack()
    
    def on_confirm():
        root.settings = {
            'frame_step': var_step.get(),
            'color_optim': var_color.get(),
            'scale_factor': var_scale.get(),
            'vector_quantization': var_vector.get(),
            'vector_colors': var_vector_colors.get(),
            'dynamic_framerate': var_dynamic.get(),
            'motion_threshold': var_threshold.get(),
            'processing_order': var_order.get(),
            'time_logging': var_time_log.get()
        }
        root.destroy()
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    root.mainloop()
    return getattr(root, 'settings', None)

def apply_vector_quantization(img, colors=16):
    """应用矢量量化减少颜色数量"""
    try:
        start_time = time.perf_counter()
        
        img_np = np.array(img)
        h, w, c = img_np.shape
        
        pixels = img_np.reshape((-1, 3))
        kmeans = MiniBatchKMeans(n_clusters=colors, random_state=0, batch_size=1024)
        kmeans.fit(pixels)
        new_pixels = kmeans.cluster_centers_[kmeans.labels_]
        quantized_img = new_pixels.reshape(h, w, c).astype(np.uint8)
        
        process_time = time.perf_counter() - start_time
        return Image.fromarray(quantized_img), process_time
    except Exception as e:
        print(f"矢量量化失败: {str(e)}")
        return img, 0

def frame_difference(prev_frame, curr_frame):
    """计算两帧之间的差异（均方误差）"""
    start_time = time.perf_counter()
    
    if prev_frame is None:
        return float('inf'), 0
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(prev_gray, curr_gray)
    mse = np.mean(diff ** 2)
    
    process_time = time.perf_counter() - start_time
    return mse, process_time

def generate_output_path(input_path, settings):
    """生成输出路径，处理重名文件"""
    dir_name = os.path.dirname(input_path)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    base_output = f"动图-{base_name}.gif"
    output_path = os.path.join(dir_name, base_output)
    
    # 检查文件是否存在
    counter = 1
    while os.path.exists(output_path):
        # 弹出对话框让用户选择
        choice = messagebox.askyesnocancel(
            "文件已存在",
            f"文件 '{base_output}' 已存在。\n\n"
            "是否要替换现有文件？\n"
            "点击 '是' 替换，'否' 创建新文件，'取消' 中止操作。"
        )
        
        if choice is None:  # 取消
            return None
        elif choice:  # 是 - 替换
            return output_path
        else:  # 否 - 创建新文件
            new_name = f"动图-{base_name}（{counter}）.gif"
            output_path = os.path.join(dir_name, new_name)
            counter += 1
    
    return output_path

def process_video(input_path, settings):
    input_path = input_path.strip('"')
    
    # 初始化时间记录
    time_stats = {
        'total': 0,
        'read': 0,
        'resize': 0,
        'dynamic_framerate': 0,
        'vector_quant': 0,
        'color_optim': 0,
        'save': 0,
        'frame_count': 0,
        'processed_frames': 0
    }
    
    # 开始总计时
    total_start_time = time.perf_counter()
    
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError("无法打开视频文件")
    
    # 获取视频信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 计算缩放尺寸
    scaled_width = int(original_width * settings['scale_factor']) // 2 * 2
    scaled_height = int(original_height * settings['scale_factor']) // 2 * 2
    
    frames = []
    frame_count = 0
    prev_frame = None
    last_processed_frame = None
    
    # 处理每一帧
    while True:
        # 读取帧并计时
        read_start = time.perf_counter()
        ret, frame = cap.read()
        if not ret:
            break
        time_stats['read'] += time.perf_counter() - read_start
        time_stats['frame_count'] += 1
        frame_count += 1
        
        # 动态帧率处理
        dynamic_time = 0
        skip_frame = False
        if settings['dynamic_framerate']:
            dyn_start = time.perf_counter()
            if last_processed_frame is not None:
                motion, motion_time = frame_difference(last_processed_frame, frame)
                dynamic_time += motion_time
                if motion < settings['motion_threshold']:
                    skip_frame = True
            time_stats['dynamic_framerate'] += time.perf_counter() - dyn_start
        
        if skip_frame:
            continue
        
        # 固定跳帧处理
        if not settings['dynamic_framerate'] and frame_count % settings['frame_step'] != 0:
            continue
        
        # 更新最后处理的帧
        if settings['dynamic_framerate']:
            last_processed_frame = frame.copy()
        
        # 处理顺序：质量优先（先矢量量化）
        if settings['processing_order'] == 'quality' and settings['vector_quantization']:
            vq_start = time.perf_counter()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img, vq_time = apply_vector_quantization(img, settings['vector_colors'])
            time_stats['vector_quant'] += vq_time + (time.perf_counter() - vq_start)
        
        # 缩放处理
        resize_start = time.perf_counter()
        if settings['scale_factor'] != 1.0:
            frame = cv2.resize(frame, (scaled_width, scaled_height), interpolation=cv2.INTER_AREA)
        time_stats['resize'] += time.perf_counter() - resize_start
        
        # 处理顺序：效率优先（后矢量量化）
        if settings['processing_order'] == 'efficiency' and settings['vector_quantization']:
            vq_start = time.perf_counter()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img, vq_time = apply_vector_quantization(img, settings['vector_colors'])
            time_stats['vector_quant'] += vq_time + (time.perf_counter() - vq_start)
        else:
            # 转换为PIL图像
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
        
        # 颜色优化处理
        color_start = time.perf_counter()
        if not settings['vector_quantization']:
            if settings['color_optim']:
                img = img.quantize(colors=32, method=Image.FASTOCTREE)
            else:
                img = img.convert("P", palette=Image.ADAPTIVE)
        time_stats['color_optim'] += time.perf_counter() - color_start
        
        frames.append(img)
        time_stats['processed_frames'] += 1
    
    cap.release()
    
    if not frames:
        raise ValueError("未提取到有效帧")
    
    # 计算实际帧率
    actual_fps = fps / settings['frame_step'] if not settings['dynamic_framerate'] and settings['frame_step'] > 1 else fps
    duration = int(1000 / actual_fps) if actual_fps > 0 else 100
    
    # 结束总计时
    time_stats['total'] = time.perf_counter() - total_start_time
    
    return frames, duration, time_stats

def format_time(seconds):
    """格式化时间显示"""
    if seconds < 0.001:
        return f"{seconds*1000000:.0f}μs"
    elif seconds < 1:
        return f"{seconds*1000:.1f}ms"
    return f"{seconds:.2f}s"

def print_success_message(output_path, total_time):
    """在控制台打印成功信息"""
    print(f"\n=== 转换成功! ===")
    print(f"输出文件: {output_path}")
    print(f"总耗时: {format_time(total_time)}\n")

def print_time_report(time_stats, settings):
    """在控制台打印时间报告（无优化建议）"""
    print(f"\n=== 详细处理时间报告 ===")
    print(f"总帧数: {time_stats['frame_count']}")
    print(f"处理帧数: {time_stats['processed_frames']}")
    print(f"处理顺序: {'效率优先' if settings['processing_order'] == 'efficiency' else '质量优先'}")
    
    print(f"\n--- 时间统计 ---")
    print(f"总耗时: {format_time(time_stats['total'])}")
    print(f"读取视频: {format_time(time_stats['read'])} ({time_stats['read']/time_stats['total']*100:.1f}%)")
    print(f"缩放处理: {format_time(time_stats['resize'])} ({time_stats['resize']/time_stats['total']*100:.1f}%)")
    
    if settings['dynamic_framerate']:
        print(f"动态帧率: {format_time(time_stats['dynamic_framerate'])} ({time_stats['dynamic_framerate']/time_stats['total']*100:.1f}%)")
    
    if settings['vector_quantization']:
        print(f"矢量量化: {format_time(time_stats['vector_quant'])} ({time_stats['vector_quant']/time_stats['total']*100:.1f}%)")
        avg_vq = time_stats['vector_quant'] / time_stats['processed_frames'] if time_stats['processed_frames'] else 0
        print(f"  - 平均每帧: {format_time(avg_vq)}")
    
    print(f"颜色优化: {format_time(time_stats['color_optim'])} ({time_stats['color_optim']/time_stats['total']*100:.1f}%)")
    print(f"保存GIF: {format_time(time_stats['save'])} ({time_stats['save']/time_stats['total']*100:.1f}%)")
    
    print(f"\n--- 性能指标 ---")
    if time_stats['processed_frames'] > 0:
        fps = time_stats['processed_frames'] / time_stats['total']
        print(f"处理速度: {fps:.1f} FPS")
        print(f"每帧耗时: {format_time(time_stats['total']/time_stats['processed_frames'])}")
    
    print("="*40)

def save_gif(frames, duration, output_path):
    """保存GIF文件并计时"""
    save_start = time.perf_counter()
    
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        optimize=True
    )
    
    return time.perf_counter() - save_start

def wait_for_user():
    """等待用户按键（仅用于交互模式）"""
    print("\n处理已完成，按回车键退出程序...")
    try:
        input()
    except:
        # 备用方案
        import msvcrt
        print("请按任意键继续...")
        msvcrt.getch()

def main():
    # 拖放模式（使用默认设置）
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        try:
            # 生成输出路径（处理重名文件）
            output_path = generate_output_path(input_path, DEFAULT_SETTINGS)
            if output_path is None:
                return  # 用户取消，静默退出
            
            # 处理视频
            start_time = time.perf_counter()
            frames, duration, time_stats = process_video(input_path, DEFAULT_SETTINGS)
            
            # 保存GIF
            save_time = save_gif(frames, duration, output_path)
            
            # 拖放模式静默退出，不显示任何信息
            return
        except Exception as e:
            # 错误时显示弹窗
            messagebox.showerror("错误", str(e))
            return
    # 交互模式
    settings = show_settings_dialog()
    if not settings:
        return
    
    input_path = filedialog.askopenfilename(
        title="选择MP4文件",
        filetypes=[("MP4视频", "*.mp4"), ("所有文件", "*.*")]
    )
    if not input_path:
        return
    
    try:
        # 合并设置
        combined_settings = {**DEFAULT_SETTINGS, **settings}
        
        # 生成输出路径（处理重名文件）
        output_path = generate_output_path(input_path, combined_settings)
        if output_path is None:
            print("操作已取消")
            wait_for_user()
            return
        
        # 处理视频
        frames, duration, time_stats = process_video(input_path, combined_settings)
        
        # 保存GIF
        save_time = save_gif(frames, duration, output_path)
        time_stats['save'] = save_time
        
        # 在控制台显示成功信息
        total_time = time_stats['total'] + time_stats['save']
        print_success_message(output_path, total_time)
        
        # 在控制台显示时间报告
        if combined_settings['time_logging']:
            print_time_report(time_stats, combined_settings)
            
        # 等待用户按键
        wait_for_user()
    except Exception as e:
        if "MiniBatchKMeans" in str(e):
            error_msg = "矢量量化需要scikit-learn库\n请安装: pip install scikit-learn"
            messagebox.showerror("依赖缺失", error_msg)
        else:
            messagebox.showerror("错误", str(e))
        print(f"\n错误: {str(e)}")
        wait_for_user()

if __name__ == "__main__":
    main()