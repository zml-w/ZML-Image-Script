# -*- coding: utf-8 -*-
"""
ComfyUI LoRA管理器
用于管理ComfyUI的LoRA文件及其相关资源文件
支持显示缩略图、移动和删除操作
"""

import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import glob
import threading
import time
import configparser

# 确保中文显示正常
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

class LoRAManager:
    def __init__(self, root):
        self.root = root
        self.root.title("ZML---LoRA管理器")
        self.root.geometry("1000x600")
        self.root.minsize(800, 500)
        
        self.lora_dir = ""  # LoRA目录路径
        self.selected_items = []  # 选中的项列表
        self.current_view = "list"  # 默认列表视图
        self.auto_refresh = False  # 确保此属性在使用前被初始化
        self.image_cache = {}  # 图片缓存
        
        # 创建GUI组件
        self.create_widgets()
        
        # 启动自动刷新定时器
        self.refresh_timer = None
    
    def create_widgets(self):
        """创建GUI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建路径设置框架
        path_frame = ttk.LabelFrame(main_frame, text="路径设置", padding="10")
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        # LoRA目录设置
        ttk.Label(path_frame, text="LoRA目录: ").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.lora_dir_var = tk.StringVar(value=self.lora_dir)
        lora_dir_entry = ttk.Entry(path_frame, textvariable=self.lora_dir_var, width=60)
        lora_dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(path_frame, text="浏览", command=self.browse_lora_dir).grid(row=0, column=2, padx=5, pady=5)
        
        # 自动刷新选项
        self.auto_refresh_var = tk.BooleanVar(value=self.auto_refresh)
        ttk.Checkbutton(path_frame, text="自动刷新 (5秒)", variable=self.auto_refresh_var, 
                       command=self.toggle_auto_refresh).grid(row=0, column=3, padx=10, pady=5)
        
        path_frame.columnconfigure(1, weight=1)
        
        # 创建操作按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="刷新列表", command=self.load_lora_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="移动选中项", command=self.move_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="移动所有项", command=self.move_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除选中项", command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除所有项", command=self.delete_all).pack(side=tk.LEFT, padx=5)
        
        # 添加视图切换按钮
        self.view_mode_var = tk.StringVar(value="list")
        ttk.Radiobutton(button_frame, text="列表视图", variable=self.view_mode_var, value="list", 
                      command=self.switch_view_mode).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(button_frame, text="缩略图视图", variable=self.view_mode_var, value="thumbnail", 
                      command=self.switch_view_mode).pack(side=tk.LEFT, padx=5)
        
        # 创建底部内容区域
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建列表视图框架
        self.list_frame = ttk.LabelFrame(content_frame, text="LoRA列表", padding="10")
        self.list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 创建列表视图 - 设置为多选模式
        columns = ("name", "size", "date_modified")
        self.tree = ttk.Treeview(self.list_frame, columns=columns, show="headings", selectmode="extended")
        
        # 设置列标题和宽度
        self.tree.heading("name", text="名称")
        self.tree.heading("size", text="大小")
        self.tree.heading("date_modified", text="修改日期")
        
        self.tree.column("name", width=200)
        self.tree.column("size", width=100, anchor=tk.CENTER)
        self.tree.column("date_modified", width=150, anchor=tk.CENTER)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # 绑定选择事件
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # 创建缩略图视图框架（初始隐藏）
        self.thumbnail_frame = ttk.LabelFrame(content_frame, text="LoRA缩略图", padding="10")
        # 不使用pack，初始隐藏
        
        # 创建缩略图网格的canvas和滚动条
        self.thumbnail_canvas = tk.Canvas(self.thumbnail_frame)
        self.thumbnail_scrollbar = ttk.Scrollbar(self.thumbnail_frame, orient="vertical", command=self.thumbnail_canvas.yview)
        self.thumbnail_scrollbar.pack(side="right", fill="y")
        self.thumbnail_canvas.pack(side="left", fill="both", expand=True)
        self.thumbnail_canvas.configure(yscrollcommand=self.thumbnail_scrollbar.set)
        
        # 创建内部框架来放置缩略图
        self.thumbnail_inner_frame = ttk.Frame(self.thumbnail_canvas)
        self.thumbnail_canvas_window = self.thumbnail_canvas.create_window((0, 0), window=self.thumbnail_inner_frame, anchor="nw")
        
        # 绑定配置事件以更新滚动区域
        self.thumbnail_inner_frame.bind("<Configure>", self.on_thumbnail_frame_configure)
        self.thumbnail_canvas.bind("<Configure>", self.on_thumbnail_canvas_configure)
        
        # 创建预览框架
        preview_frame = ttk.LabelFrame(content_frame, text="预览", padding="10", width=300)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        preview_frame.pack_propagate(False)  # 防止内容影响框架大小
        
        # 缩略图显示
        self.thumbnail_label = ttk.Label(preview_frame, text="选择一个LoRA查看预览")
        self.thumbnail_label.pack(pady=20, fill=tk.BOTH, expand=True)
        
        # 添加文件操作按钮
        buttons_frame = ttk.Frame(preview_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(buttons_frame, text="查看/编辑 TXT", command=self.view_edit_txt).pack(fill=tk.X, pady=5)
        ttk.Button(buttons_frame, text="查看/编辑 LOG", command=self.view_edit_log).pack(fill=tk.X, pady=5)
        ttk.Button(buttons_frame, text="查看图像", command=self.view_image).pack(fill=tk.X, pady=5)
    
    def browse_lora_dir(self):
        """浏览选择LoRA目录"""
        directory = filedialog.askdirectory(title="选择LoRA目录")
        if directory:
            self.lora_dir_var.set(directory)
            self.lora_dir = directory
            # 移除保存配置的调用
            self.load_lora_list()
    
    def update_preview(self, filename):
        """更新缩略图预览"""
        # 清除之前的图片
        self.thumbnail_label.config(image="")
        
        # 查找缩略图
        base_name = os.path.splitext(filename)[0]
        zml_dir = os.path.join(self.lora_dir, "zml")
        
        # 尝试找到对应的图片文件
        image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
        image_path = None
        
        for ext in image_extensions:
            potential_path = os.path.join(zml_dir, base_name + ext)
            if os.path.exists(potential_path):
                image_path = potential_path
                break
        
        # 如果有缓存，直接使用
        if image_path and image_path in self.image_cache:
            self.thumbnail_label.config(image=self.image_cache[image_path])
            return
        
        # 加载并显示图片
        if image_path and os.path.exists(image_path):
            try:
                image = Image.open(image_path)
                image.thumbnail(self.thumbnail_size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                
                # 缓存图片
                self.image_cache[image_path] = photo
                
                self.thumbnail_label.config(image=photo)
            except Exception as e:
                self.thumbnail_label.config(text=f"无法加载图片: {str(e)}")
        else:
            self.thumbnail_label.config(text="没有找到缩略图")
    
    def get_related_files(self, filename):
        """获取与LoRA文件相关的所有文件"""
        related_files = []
        
        # 添加主LoRA文件
        lora_path = os.path.join(self.lora_dir, filename)
        related_files.append(lora_path)
        
        # 查找zml目录下的相关文件
        base_name = os.path.splitext(filename)[0]
        zml_dir = os.path.join(self.lora_dir, "zml")
        
        if os.path.exists(zml_dir):
            # 查找所有同名但不同扩展名的文件
            for file in os.listdir(zml_dir):
                file_base = os.path.splitext(file)[0]
                if file_base == base_name:
                    related_files.append(os.path.join(zml_dir, file))
        
        return related_files
    
    def delete_all(self):
        """删除所有LoRA及其相关文件"""
        if not self.lora_dir:
            messagebox.showwarning("警告", "请先设置LoRA目录")
            return
        
        # 检查是否有文件可删除
        if not self.tree.get_children():
            messagebox.showinfo("提示", "没有可删除的文件")
            return
        
        # 二次确认，使用askyesnocancel提供更多选项
        answer = messagebox.askyesno("危险操作确认", 
                                   "确定要永久删除所有LoRA文件及其相关文件吗？\n此操作不可恢复！\n请再次确认！")
        
        if answer:
            # 第三次确认，非常危险的操作
            final_answer = messagebox.askyesno("最终确认", 
                                             "这是最后一次确认！所有文件将被永久删除！\n确定要继续吗？")
            
            if final_answer:
                try:
                    # 删除所有文件
                    deleted_count = 0
                    for item in self.tree.get_children():
                        filename = self.tree.item(item, "values")[0]
                        related_files = self.get_related_files(filename)
                        
                        for file_path in related_files:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        
                        deleted_count += 1
                    
                    messagebox.showinfo("成功", f"已成功删除 {deleted_count} 个LoRA文件及其相关文件")
                    self.load_lora_list()  # 重新加载列表
                except Exception as e:
                    messagebox.showerror("错误", f"删除文件时出错: {str(e)}")
    
    def move_selected(self):
        """移动选中的LoRA及其相关文件"""
        if not self.selected_items:
            messagebox.showwarning("警告", "请先选择至少一个LoRA文件")
            return
        
        # 选择目标目录
        target_dir = filedialog.askdirectory(title="选择目标目录")
        if not target_dir:
            return
        
        # 确保目标目录存在
        os.makedirs(target_dir, exist_ok=True)
        
        # 确保目标zml目录存在
        target_zml_dir = os.path.join(target_dir, "zml")
        os.makedirs(target_zml_dir, exist_ok=True)
        
        # 获取选中的文件名列表
        filenames = [self.tree.item(item, "values")[0] for item in self.selected_items]
        file_count = len(filenames)
        
        # 确认操作
        answer = messagebox.askyesno("确认操作", 
                                   f"确定要移动这 {file_count} 个LoRA文件及其相关文件到目标目录吗？")
        if answer:
            try:
                # 移动文件
                moved_count = 0
                for filename in filenames:
                    related_files = self.get_related_files(filename)
                    
                    for file_path in related_files:
                        if os.path.exists(file_path):
                            # 确定目标路径
                            if "zml" in file_path:
                                # 是zml目录下的文件
                                rel_path = os.path.basename(file_path)
                                dest_path = os.path.join(target_zml_dir, rel_path)
                            else:
                                # 是主LoRA文件
                                rel_path = os.path.basename(file_path)
                                dest_path = os.path.join(target_dir, rel_path)
                            
                            # 如果目标文件已存在，询问是否覆盖
                            if os.path.exists(dest_path):
                                overwrite = messagebox.askyesno("文件已存在", 
                                                              f"文件 {rel_path} 已存在于目标目录。是否覆盖？")
                                if not overwrite:
                                    continue
                            
                            # 移动文件
                            shutil.move(file_path, dest_path)
                    
                    moved_count += 1
                
                messagebox.showinfo("成功", f"已成功移动 {moved_count} 个LoRA文件及其相关文件")
                self.load_lora_list()  # 重新加载列表
            except Exception as e:
                messagebox.showerror("错误", f"移动文件时出错: {str(e)}")
    
    def move_all(self):
        """移动所有LoRA及其相关文件"""
        if not self.lora_dir:
            messagebox.showwarning("警告", "请先设置LoRA目录")
            return
        
        # 检查是否有文件可移动
        if not self.tree.get_children():
            messagebox.showinfo("提示", "没有可移动的文件")
            return
        
        # 选择目标目录
        target_dir = filedialog.askdirectory(title="选择目标目录")
        if not target_dir:
            return
        
        # 确保目标目录不是当前LoRA目录
        if os.path.normpath(target_dir) == os.path.normpath(self.lora_dir):
            messagebox.showwarning("警告", "目标目录不能是当前LoRA目录")
            return
        
        # 确保目标目录存在
        os.makedirs(target_dir, exist_ok=True)
        
        # 确保目标zml目录存在
        target_zml_dir = os.path.join(target_dir, "zml")
        os.makedirs(target_zml_dir, exist_ok=True)
        
        # 确认操作
        answer = messagebox.askyesno("确认操作", 
                                   "确定要移动所有LoRA文件及其相关文件到目标目录吗？")
        if answer:
            try:
                # 移动所有文件
                moved_count = 0
                for item in self.tree.get_children():
                    filename = self.tree.item(item, "values")[0]
                    related_files = self.get_related_files(filename)
                    
                    for file_path in related_files:
                        if os.path.exists(file_path):
                            # 确定目标路径
                            if "zml" in file_path:
                                # 是zml目录下的文件
                                rel_path = os.path.basename(file_path)
                                dest_path = os.path.join(target_zml_dir, rel_path)
                            else:
                                # 是主LoRA文件
                                rel_path = os.path.basename(file_path)
                                dest_path = os.path.join(target_dir, rel_path)
                            
                            # 如果目标文件已存在，询问是否覆盖
                            if os.path.exists(dest_path):
                                overwrite = messagebox.askyesno("文件已存在", 
                                                              f"文件 {rel_path} 已存在于目标目录。是否覆盖？")
                                if not overwrite:
                                    continue
                            
                            # 移动文件
                            shutil.move(file_path, dest_path)
                    
                    moved_count += 1
                
                messagebox.showinfo("成功", f"已成功移动 {moved_count} 个LoRA文件及其相关文件")
                self.load_lora_list()  # 重新加载列表
            except Exception as e:
                messagebox.showerror("错误", f"移动文件时出错: {str(e)}")
    
    def toggle_auto_refresh(self):
        """切换自动刷新功能"""
        self.auto_refresh = self.auto_refresh_var.get()
        if self.auto_refresh:
            self.start_auto_refresh()
        else:
            self.stop_auto_refresh()
    
    def start_auto_refresh(self):
        """启动自动刷新定时器"""
        self.stop_auto_refresh()  # 先停止之前的定时器
        self.refresh_timer = threading.Timer(5.0, self.auto_refresh_list)
        self.refresh_timer.daemon = True
        self.refresh_timer.start()
    
    def stop_auto_refresh(self):
        """停止自动刷新定时器"""
        if self.refresh_timer:
            self.refresh_timer.cancel()
            self.refresh_timer = None
    
    def auto_refresh_list(self):
        """自动刷新LoRA列表"""
        if self.auto_refresh and self.lora_dir:
            self.load_lora_list()
            self.start_auto_refresh()  # 重新启动定时器
    
    def switch_view_mode(self):
        """切换列表视图和缩略图视图"""
        mode = self.view_mode_var.get()
        if mode == "list":
            # 显示列表视图，隐藏缩略图视图
            self.thumbnail_frame.pack_forget()
            self.list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        else:
            # 显示缩略图视图，隐藏列表视图
            self.list_frame.pack_forget()
            self.thumbnail_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
            # 加载缩略图视图
            self.load_thumbnail_view()
    
    def on_thumbnail_frame_configure(self, event):
        """当缩略图内部框架配置变化时更新canvas滚动区域"""
        self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all"))
    
    def on_thumbnail_canvas_configure(self, event):
        """当canvas配置变化时调整内部窗口宽度"""
        width = event.width
        self.thumbnail_canvas.itemconfig(self.thumbnail_canvas_window, width=width)
    
    def load_thumbnail_view(self):
        """加载并显示缩略图视图"""
        # 清空缩略图框架中的内容
        for widget in self.thumbnail_inner_frame.winfo_children():
            widget.destroy()
        
        if not self.lora_dir:
            return
        
        # 获取所有.lora和.safetensors文件
        lora_extensions = ['*.lora', '*.safetensors']
        lora_files = []
        
        for ext in lora_extensions:
            lora_files.extend(glob.glob(os.path.join(self.lora_dir, ext)))
        
        # 按文件名排序
        lora_files.sort(key=lambda x: os.path.basename(x).lower())
        
        # 创建缩略图网格（每行显示4个）
        cols = 4
        thumbnail_size = (120, 120)
        
        for i, lora_file in enumerate(lora_files):
            filename = os.path.basename(lora_file)
            base_name = os.path.splitext(filename)[0]
            
            # 创建缩略图容器
            item_frame = ttk.Frame(self.thumbnail_inner_frame, padding=5)
            row = i // cols
            col = i % cols
            item_frame.grid(row=row, column=col, padx=10, pady=10)
            
            # 创建缩略图按钮（可点击选择）
            thumb_button = ttk.Button(item_frame)
            thumb_button.pack(pady=(0, 5))
            
            # 加载缩略图
            zml_dir = os.path.join(self.lora_dir, "zml")
            image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
            image_path = None
            
            for ext in image_extensions:
                potential_path = os.path.join(zml_dir, base_name + ext)
                if os.path.exists(potential_path):
                    image_path = potential_path
                    break
            
            if image_path and os.path.exists(image_path):
                try:
                    image = Image.open(image_path)
                    image.thumbnail(thumbnail_size, Image.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    thumb_button.config(image=photo)
                    thumb_button.image = photo  # 保持引用
                except Exception:
                    # 显示默认图标或占位文本
                    thumb_button.config(text="无缩略图")
            else:
                thumb_button.config(text="无缩略图")
            
            # 添加文件名标签（显示部分文件名）
            display_name = self._truncate_text(base_name, 15)
            name_label = ttk.Label(item_frame, text=display_name, wraplength=120)
            name_label.pack()
            
            # 绑定点击事件
            thumb_button.bind("<Button-1>", lambda e, f=filename: self.on_thumbnail_click(f))
            name_label.bind("<Button-1>", lambda e, f=filename: self.on_thumbnail_click(f))
            item_frame.bind("<Button-1>", lambda e, f=filename: self.on_thumbnail_click(f))
    
    def _truncate_text(self, text, max_length):
        """截断文本，过长时添加省略号"""
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text
    
    def on_thumbnail_click(self, filename):
        """处理缩略图点击事件"""
        # 查找对应的treeview项并选中
        for item in self.tree.get_children():
            if self.tree.item(item, "values")[0] == filename:
                # 先清除所有选择
                self.tree.selection_remove(self.tree.selection())
                # 选中当前项
                self.tree.selection_add(item)
                # 滚动到可见位置
                self.tree.see(item)
                # 更新selected_items
                self.selected_items = [item]
                # 更新预览
                self.update_preview(filename)
                break
    
    def load_lora_list(self):
        """加载LoRA文件列表"""
        if not self.lora_dir:
            messagebox.showwarning("警告", "请先设置LoRA目录")
            return
        
        # 清空当前列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 清空缓存
        self.image_cache.clear()
        
        # 获取所有.lora和.safetensors文件
        lora_extensions = ['*.lora', '*.safetensors']
        lora_files = []
        
        for ext in lora_extensions:
            lora_files.extend(glob.glob(os.path.join(self.lora_dir, ext)))
        
        # 按文件名排序
        lora_files.sort(key=lambda x: os.path.basename(x).lower())
        
        # 添加到列表视图
        for lora_file in lora_files:
            filename = os.path.basename(lora_file)
            size = os.path.getsize(lora_file)
            size_str = self.format_size(size)
            mtime = os.path.getmtime(lora_file)
            date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
            
            self.tree.insert("", tk.END, values=(filename, size_str, date_str))
        
        # 如果当前是缩略图视图，重新加载缩略图
        if self.view_mode_var.get() == "thumbnail":
            self.load_thumbnail_view()
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def on_select(self, event):
        """处理选择事件 - 支持多选"""
        selection = self.tree.selection()
        if not selection:
            return
        
        self.selected_items = selection
        
        # 对于预览，只使用第一个选中项
        if self.selected_items:
            filename = self.tree.item(self.selected_items[0], "values")[0]
            # 更新预览
            self.update_preview(filename)
    
    def view_edit_txt(self):
        """查看/编辑TXT文件"""
        if not self.selected_items:
            messagebox.showwarning("警告", "请先选择一个LoRA文件")
            return
        
        # 只处理第一个选中的文件
        filename = self.tree.item(self.selected_items[0], "values")[0]
        base_name = os.path.splitext(filename)[0]
        zml_dir = os.path.join(self.lora_dir, "zml")
        txt_path = os.path.join(zml_dir, base_name + ".txt")
        
        # 检查文件是否存在，如果不存在则创建
        if not os.path.exists(txt_path):
            if not os.path.exists(zml_dir):
                os.makedirs(zml_dir)
            open(txt_path, 'w', encoding='utf-8').close()
        
        # 打开编辑窗口
        self.open_text_editor(txt_path, "编辑TXT文件")
    
    def view_edit_log(self):
        """查看/编辑LOG文件"""
        if not self.selected_items:
            messagebox.showwarning("警告", "请先选择一个LoRA文件")
            return
        
        # 只处理第一个选中的文件
        filename = self.tree.item(self.selected_items[0], "values")[0]
        base_name = os.path.splitext(filename)[0]
        zml_dir = os.path.join(self.lora_dir, "zml")
        log_path = os.path.join(zml_dir, base_name + ".log")
        
        # 检查文件是否存在，如果不存在则创建
        if not os.path.exists(log_path):
            if not os.path.exists(zml_dir):
                os.makedirs(zml_dir)
            open(log_path, 'w', encoding='utf-8').close()
        
        # 打开编辑窗口
        self.open_text_editor(log_path, "编辑LOG文件")
    
    def view_image(self):
        """查看图像文件"""
        if not self.selected_items:
            messagebox.showwarning("警告", "请先选择一个LoRA文件")
            return
        
        # 只处理第一个选中的文件
        filename = self.tree.item(self.selected_items[0], "values")[0]
        base_name = os.path.splitext(filename)[0]
        zml_dir = os.path.join(self.lora_dir, "zml")
        
        # 查找图像文件
        image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
        image_path = None
        
        for ext in image_extensions:
            potential_path = os.path.join(zml_dir, base_name + ext)
            if os.path.exists(potential_path):
                image_path = potential_path
                break
        
        if not image_path:
            messagebox.showinfo("提示", "没有找到相关图像文件")
            return
        
        # 打开图像查看窗口
        self.open_image_viewer(image_path)
    
    def open_text_editor(self, file_path, title):
        """打开文本编辑窗口"""
        editor_window = tk.Toplevel(self.root)
        editor_window.title(title)
        editor_window.geometry("600x400")
        editor_window.transient(self.root)  # 设置为主窗口的子窗口
        editor_window.grab_set()  # 模态窗口
        
        # 创建文本编辑区域
        text_widget = tk.Text(editor_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(text_widget, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        # 加载文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                text_widget.insert(tk.END, content)
        except Exception as e:
            messagebox.showerror("错误", f"读取文件时出错: {str(e)}")
        
        # 创建按钮框架
        button_frame = ttk.Frame(editor_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_file():
            """保存文件"""
            try:
                content = text_widget.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                editor_window.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时出错: {str(e)}")
        
        ttk.Button(button_frame, text="保存", command=save_file).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=editor_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def open_image_viewer(self, image_path):
        """打开图像查看窗口"""
        viewer_window = tk.Toplevel(self.root)
        viewer_window.title("查看图像")
        viewer_window.transient(self.root)  # 设置为主窗口的子窗口
        
        try:
            # 加载图像
            image = Image.open(image_path)
            
            # 调整窗口大小以适应图像，但不超过屏幕
            screen_width = self.root.winfo_screenwidth() - 100
            screen_height = self.root.winfo_screenheight() - 100
            
            # 如果图像太大，调整大小
            img_width, img_height = image.size
            if img_width > screen_width or img_height > screen_height:
                ratio = min(screen_width / img_width, screen_height / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                image = image.resize((new_width, new_height), Image.LANCZOS)
            
            # 转换为Tkinter可用的格式
            photo = ImageTk.PhotoImage(image)
            
            # 显示图像
            image_label = ttk.Label(viewer_window, image=photo)
            image_label.image = photo  # 保持引用以防止被垃圾回收
            image_label.pack(padx=10, pady=10)
            
            # 设置窗口大小
            viewer_window.geometry(f"{image.width}x{image.height + 50}")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载图像时出错: {str(e)}")
            viewer_window.destroy()
    
    def delete_selected(self):
        """删除选中的LoRA及其相关文件 - 支持多选"""
        if not self.selected_items:
            messagebox.showwarning("警告", "请先选择至少一个LoRA文件")
            return
        
        # 获取选中的文件名列表
        filenames = [self.tree.item(item, "values")[0] for item in self.selected_items]
        file_count = len(filenames)
        
        # 确认操作
        answer = messagebox.askyesno("危险操作确认", 
                                   f"确定要永久删除这 {file_count} 个LoRA文件及其相关文件吗？\n此操作不可恢复！")
        if answer:
            try:
                # 删除文件
                deleted_count = 0
                for filename in filenames:
                    related_files = self.get_related_files(filename)
                    
                    for file_path in related_files:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    
                    deleted_count += 1
                
                messagebox.showinfo("成功", f"已成功删除 {deleted_count} 个LoRA文件及其相关文件")
                self.load_lora_list()  # 重新加载列表
            except Exception as e:
                messagebox.showerror("错误", f"删除文件时出错: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LoRAManager(root)
    
    # 处理窗口关闭事件
    def on_closing():
        app.stop_auto_refresh()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    root.mainloop()