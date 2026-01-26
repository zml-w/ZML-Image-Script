import os
from PIL import Image
import random
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --- 核心图像处理辅助函数 ---

def split_image_into_blocks(image, block_size):
    """
    将图像分割成指定大小的矩形块。

    参数:
    image (PIL.Image.Image): 要分割的PIL图像对象。
    block_size (int): 每个块的边长（假设为正方形块）。

    返回:
    tuple: 包含以下元素的元组
        - list: 图像块的列表 (PIL.Image.Image对象)。
        - int: 图像的宽度。
        - int: 图像的高度。
        - int: 块的行数 (实际可容纳的块行数)。
        - int: 块的列数 (实际可容纳的块列数)。
        - int: 单个块的宽度 (通常等于 block_size)。
        - int: 单个块的高度 (通常等于 block_size)。
    """
    img_width, img_height = image.size
    
    # 计算块的行数和列数
    # math.ceil 用于向上取整，确保即使图像边缘不足一个完整块，也能被包含进来。
    # 这样可以处理非完美整除的图像尺寸。
    num_cols = math.ceil(img_width / block_size)
    num_rows = math.ceil(img_height / block_size)

    # 存储所有图像块的列表
    blocks = []
    
    # 遍历每一行和每一列的块
    for r in range(num_rows):
        for c in range(num_cols):
            # 计算当前块的左上角和右下角坐标
            left = c * block_size
            top = r * block_size
            
            # 使用 min 确保裁剪区域不会超出图像的实际边界
            right = min((c + 1) * block_size, img_width) 
            bottom = min((r + 1) * block_size, img_height) 
            
            # 使用 crop 方法裁剪图像块
            block = image.crop((left, top, right, bottom))
            blocks.append(block)
            
    # 返回所有块，以及原始图像尺寸和块的布局信息
    return blocks, img_width, img_height, num_rows, num_cols, block_size, block_size

def combine_blocks_into_image(blocks, img_width, img_height, num_rows, num_cols, block_width, block_height):
    """
    将一列图像块重新组合成一张完整的图像。

    参数:
    blocks (list): 图像块的列表 (PIL.Image.Image对象)。
    img_width (int): 原始图像的宽度。
    img_height (int): 原始图像的高度。
    num_rows (int): 块的行数。
    num_cols (int): 块的列数。
    block_width (int): 每个块的宽度。
    block_height (int): 每个块的高度。

    返回:
    PIL.Image.Image: 重新组合后的完整图像。
    """
    # 创建一个空白的新图像，大小与原始图像相同
    # 'RGB' 模式表示彩色图像。我们确保所有图像在加载时都转换为RGB，这样这里就统一了。
    new_image = Image.new('RGB', (img_width, img_height))
    
    # 遍历每个块，并将其粘贴到新图像的正确位置
    for i, block in enumerate(blocks):
        # 计算当前块在新图像中的行和列索引
        r = i // num_cols # 整数除法，计算行索引
        c = i % num_cols  # 取模运算，计算列索引
        
        # 计算块的左上角粘贴位置
        left = c * block_width
        top = r * block_height
        
        # 将块粘贴到新图像上
        new_image.paste(block, (left, top))
        
    return new_image

# --- 核心加密和解密函数 ---

def encrypt_image(image_path, password, block_size):
    """
    对图像进行块打乱加密。

    参数:
    image_path (str): 原始图像文件的路径。
    password (str): 用于加密的密码，作为随机数种子（可以是中文）。
    block_size (int): 每个图像块的边长 (像素)。

    返回:
    PIL.Image.Image or str, str: 加密后的PIL图像对象和状态消息。如果失败则返回 None 和错误信息。
    """
    status_text = ""
    try:
        # 1. 加载图像并确保为RGB模式。
        # .convert("RGB") 确保图像在处理前都是一致的颜色模式，避免PNG/JPEG等模式差异。
        original_image = Image.open(image_path).convert("RGB") 
    except FileNotFoundError:
        status_text = f"错误：找不到文件 '{image_path}'。请检查路径是否正确。"
        return None, status_text
    except Exception as e:
        status_text = f"加载图像时发生错误: {e}"
        return None, status_text

    # 2. 将图像分割成块
    blocks, img_width, img_height, num_rows, num_cols, actual_block_width, actual_block_height = split_image_into_blocks(original_image, block_size)
    num_blocks = len(blocks)
    status_text += f"\n图像已被分割成 {num_rows} 行，{num_cols} 列，共 {num_blocks} 个块。"

    # 3. 生成打乱顺序
    # 使用密码作为随机数种子，确保相同的密码始终生成相同的打乱顺序。
    # 这里密码可以是任何可哈希的Python对象，包括中文字符串。
    random.seed(password) 
    
    # 创建一个从0到 num_blocks-1 的索引列表
    shuffled_indices = list(range(num_blocks))
    
    # 随机打乱这个索引列表。
    # 打乱后，shuffled_indices 的每个元素是一个“目标位置”，
    # 原始的 block[i] 会被移动到 shuffled_indices[i] 处。
    random.shuffle(shuffled_indices)
    
    # 创建一个列表来存储打乱后的块，预先分配空间（None），提高效率。
    encrypted_blocks = [None] * num_blocks 

    # 根据打乱顺序排列块
    # 逻辑: 将原始块列表 `blocks` 中的 `blocks[original_index]` 移动到 `encrypted_blocks` 的
    # `new_position_index` 处，其中 `new_position_index` 是由 `shuffled_indices` 提供的。
    for original_index in range(num_blocks):
        new_position_index = shuffled_indices[original_index]
        encrypted_blocks[new_position_index] = blocks[original_index]

    # 4. 将打乱后的块重新组合成新图像
    encrypted_image = combine_blocks_into_image(
        encrypted_blocks, 
        img_width, img_height, 
        num_rows, num_cols, 
        actual_block_width, actual_block_height
    )
    status_text += "\n图像加密完成！"
    return encrypted_image, status_text

def decrypt_image(image_path, password, block_size):
    """
    对图像进行块打乱解密。

    参数:
    image_path (str): 加密图像文件的路径。
    password (str): 用于解密的密码，必须与加密时使用的密码相同（可以是中文）。
    block_size (int): 每个图像块的边长 (像素)，必须与加密时使用的块大小相同。

    返回:
    PIL.Image.Image or str, str: 解密后的PIL图像对象和状态消息。如果失败则返回 None 和错误信息。
    """
    status_text = ""
    try:
        # 1. 加载加密图像并确保为RGB模式
        encrypted_image = Image.open(image_path).convert("RGB")
    except FileNotFoundError:
        status_text = f"错误：找不到文件 '{image_path}'。请检查路径是否正确。"
        return None, status_text
    except Exception as e:
        status_text = f"加载图像时发生错误: {e}"
        return None, status_text

    # 2. 将加密图像分割成块
    blocks, img_width, img_height, num_rows, num_cols, actual_block_width, actual_block_height = split_image_into_blocks(encrypted_image, block_size)
    num_blocks = len(blocks)
    status_text += f"\n图像已被分割成 {num_rows} 行，{num_cols} 列，共 {num_blocks} 个块。"

    # 3. 重新生成加密时的打乱顺序
    # 这一步至关重要：使用完全相同的密码作为随机数种子，这将生成与加密时完全相同的 shuffled_indices 列表，
    # 使得我们可以“反转”打乱操作。
    random.seed(password)
    
    shuffled_indices = list(range(num_blocks))
    random.shuffle(shuffled_indices)

    # 4. 计算逆映射 (`inverse_mapping`)
    # `shuffled_indices` 告诉我们原始块 `original_index` 移动到了 `new_position_index` (`shuffled_indices[original_index]`)。
    # 为了解密，我们需要知道在加密后的图像中，位于 `current_encrypted_position` 的块，它原本在原始图像的 `original_position` 是多少。
    # `inverse_mapping[new_position_index] = original_index` 
    inverse_mapping = [0] * num_blocks
    for original_index, new_position_index in enumerate(shuffled_indices):
        inverse_mapping[new_position_index] = original_index
    
    # 创建一个列表来存储解密后的块
    decrypted_blocks = [None] * num_blocks

    # 根据逆映射将块恢复原位
    # 逻辑：对于加密后的图像中的每个块 `blocks[current_encrypted_position]`，
    # 根据 `inverse_mapping`，它应该被粘贴到解密后图像的 `original_position` (`inverse_mapping[current_encrypted_position]`)。
    for current_encrypted_position in range(num_blocks):
        original_position = inverse_mapping[current_encrypted_position]
        decrypted_blocks[original_position] = blocks[current_encrypted_position]

    # 5. 将解密后的块重新组合成图像
    decrypted_image = combine_blocks_into_image(
        decrypted_blocks, 
        img_width, img_height, 
        num_rows, num_cols, 
        actual_block_width, actual_block_height
    )
    status_text += "\n图像解密完成！"
    return decrypted_image, status_text

# --- Tkinter GUI 界面 ---

class ImageCryptoApp:
    def __init__(self, master):
        self.master = master
        master.title("图像加密/解密工具")
        master.geometry("600x480") # 设置窗口初始大小
        master.resizable(False, False) # 不允许改变窗口大小

        # --- 设置 ttk 组件的样式 ---
        self.style = ttk.Style()
        
        # 定义字体样式
        self.font_large = ('Helvetica', 12, 'bold')
        self.font_normal = ('Helvetica', 10)
        self.font_status = ('Consolas', 9)

        # 配置ttk组件的字体
        self.style.configure('.', font=self.font_normal) # 全局设置默认字体为 normal
        self.style.configure('TLabel', font=self.font_normal)
        self.style.configure('TRadiobutton', font=self.font_normal)
        self.style.configure('TButton', font=self.font_normal)
        self.style.configure('TEntry', font=self.font_normal)
        self.style.configure('TSpinbox', font=self.font_normal)
        self.style.configure('TLabelframe.Label', font=self.font_large) # LabelFrame的标题字体
        self.style.configure('Status.TLabel', font=self.font_status) # 状态标签的特殊字体

        # 存储当前选择的图像路径
        self.image_path = "" 

        # --- 第一部分：文件选择 ---
        file_frame = ttk.LabelFrame(master, text="1. 选择图像文件", padding="10 10")
        file_frame.pack(padx=10, pady=5, fill="x")

        self.path_label = ttk.Label(file_frame, text="未选择图像文件", wraplength=450)
        self.path_label.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        browse_button = ttk.Button(file_frame, text="浏览...", command=self.select_image_file)
        browse_button.pack(side="right", padx=5, pady=5)

        # --- 第二部分：选择操作 (加密/解密) ---
        operation_frame = ttk.LabelFrame(master, text="2. 选择操作", padding="10 10")
        operation_frame.pack(padx=10, pady=5, fill="x")

        self.operation_var = tk.StringVar(value="encrypt") # 默认选择加密
        encrypt_radio = ttk.Radiobutton(operation_frame, text="加密图像 (Encrypt Image)", variable=self.operation_var, value="encrypt")
        encrypt_radio.pack(anchor="w", pady=2)
        decrypt_radio = ttk.Radiobutton(operation_frame, text="解密图像 (Decrypt Image)", variable=self.operation_var, value="decrypt")
        decrypt_radio.pack(anchor="w", pady=2)

        # --- 第三部分：输入密码和块数量 ---
        settings_frame = ttk.LabelFrame(master, text="3. 输入密码和块数量", padding="10 10")
        settings_frame.pack(padx=10, pady=5, fill="x")

        # 密码输入
        passwd_label = ttk.Label(settings_frame, text="密码 (Password):")
        passwd_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        # 移除了 show="*"，密码将明文显示
        self.password_entry = ttk.Entry(settings_frame, width=30) 
        self.password_entry.grid(row=0, column=1, sticky="we", padx=5, pady=5)

        # 块数量输入
        block_label = ttk.Label(settings_frame, text="块大小 (Block Size):")
        block_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        # Spinbox 限制输入范围，且方便修改
        self.block_size_spinbox = ttk.Spinbox(settings_frame, from_=8, to=256, increment=8, width=10)
        self.block_size_spinbox.set(32) # 默认块大小
        self.block_size_spinbox.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # 将第1列设置为可扩展，使Entry填充满可用空间
        settings_frame.grid_columnconfigure(1, weight=1)

        # --- 第四部分：执行操作 ---
        action_frame = ttk.Frame(master, padding="10 0")
        action_frame.pack(padx=10, pady=5, fill="x")

        execute_button = ttk.Button(action_frame, text="执行操作", command=self.execute_operation)
        execute_button.pack(pady=10) # 底部按钮

        # --- 状态显示区 ---
        ttk.Separator(master, orient="horizontal").pack(fill="x", padx=10, pady=5)

        status_frame = ttk.LabelFrame(master, text="状态/输出", padding="10 10")
        status_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.status_text_var = tk.StringVar(value="等待用户操作...\n结果将被自动保存到原图像所在目录。")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_text_var, anchor="nw", justify="left", wraplength=550, style='Status.TLabel')
        self.status_label.pack(fill="both", expand=True)
        self.status_label.config(foreground="black")


    def select_image_file(self):
        """
        打开文件选择对话框，让用户选择图像文件。
        """
        filetypes = [
            ("图像文件", "*.png *.jpg *.jpeg *.bmp *.gif"),
            ("PNG文件", "*.png"),
            ("JPEG文件", "*.jpg *.jpeg"),
            ("所有文件", "*.*")
        ]
        chosen_path = filedialog.askopenfilename(
            title="选择要处理的图像",
            filetypes=filetypes
        )
        if chosen_path:
            self.image_path = chosen_path
            # 更新路径显示，只显示文件名和父文件夹，避免过长
            display_path = os.path.basename(chosen_path)
            parent_dir = os.path.basename(os.path.dirname(chosen_path))
            self.path_label.config(text=f"{parent_dir}/{display_path}")
            self.update_status(f"已选择文件: {parent_dir}/{display_path}", "black")
        else:
            self.update_status("未选择任何文件。", "red")

    def update_status(self, message, color="black"):
        """
        更新状态显示区域的文本和颜色。
        """
        self.status_text_var.set(message)
        self.status_label.config(foreground=color)
        self.master.update_idletasks() # 强制更新GUI，让状态即使在长时间操作前也能显示

    def execute_operation(self):
        """
        根据用户选择执行加密或解密操作。
        """
        if not self.image_path:
            messagebox.showwarning("警告", "请先选择一个图像文件！")
            return

        password = self.password_entry.get()
        if not password:
            messagebox.showwarning("警告", "请输入密码！")
            return

        try:
            block_size = int(self.block_size_spinbox.get())
            if block_size < 8: # 块大小太小可能效果不佳或出错
                messagebox.showwarning("警告", "块大小不能小于8像素。")
                return
            
            # 临时打开图像以获取尺寸，但不保持打开状态
            with Image.open(self.image_path) as temp_img:
                img_width, img_height = temp_img.size
            
            if block_size > min(img_width, img_height):
                messagebox.showwarning("警告", f"块大小 ({block_size}px) 不能大于图像的最小边长 ({min(img_width, img_height)}px)。请选择一个更小的块大小。")
                # 尝试设置一个合理的最大值，这里取图像最小边长的最大因子（例如，如果最小边长是100，最大可能到96）
                # 确保不会超出256，并且是8的倍数
                suggested_max_block_size = min(256, (min(img_width, img_height) // 8) * 8) 
                self.block_size_spinbox.set(max(8, suggested_max_block_size)) # 确保至少是8
                return

        except ValueError:
            messagebox.showwarning("警告", "块大小必须是一个整数！")
            return
        except Exception as e:
            messagebox.showwarning("错误", f"检查块大小时发生错误: {e}")
            return

        # 获取当前选择的操作类型 (encrypt/decrypt)
        operation = self.operation_var.get() 
        result_image = None
        
        # 解析原始文件路径信息
        base_name_with_ext = os.path.basename(self.image_path) # 例如 "my_image.jpg"
        base_name, ext = os.path.splitext(base_name_with_ext) # "my_image", ".jpg"
        ext = ext.lower() # 确保后缀是小写
        output_dir = os.path.dirname(self.image_path) or os.getcwd() # 若无目录则保存到当前工作目录

        if operation == "encrypt":
            self.update_status(f"正在加密图像 '{self.image_path}'...", "blue")
            result_image, status_message = encrypt_image(self.image_path, password, block_size)
            operation_text = "加密" # 用于文件名
        else: # decrypt
            self.update_status(f"正在解密图像 '{self.image_path}'...", "blue")
            result_image, status_message = decrypt_image(self.image_path, password, block_size)
            operation_text = "解密" # 用于文件名
        
        self.update_status(status_message) # 显示加密/解密过程中的详细状态

        if result_image:
            # --- 构建新的文件名，符合用户要求：原图像名称_加密/解密_分块数量.后缀 ---
            # 默认建议保存为PNG，减少有损压缩带来的切割感
            actual_ext = '.png' if ext in ['.jpg', '.jpeg'] else ext
            
            # 新文件名格式： base_name_operation_blocksize.ext
            new_file_name = f"{base_name}_{operation_text}_{block_size}{actual_ext}"
            
            # 完整的保存路径
            final_save_path = os.path.join(output_dir, new_file_name)

            # 更新状态提示
            status_update_message = f"温馨提示：结果将自动保存为 **{actual_ext.lstrip('.').upper()}** 格式。\n文件名为: {new_file_name}\n保存路径: {output_dir}"
            self.update_status(status_update_message, "darkgreen")
            
            try:
                # 尝试保存图像
                result_image.save(final_save_path)
                final_message = f"操作成功！结果已自动保存到:\n{final_save_path}"
                self.update_status(f"操作成功！结果已保存到:\n{final_save_path}", "green")
                messagebox.showinfo("成功", final_message)
            except Exception as e:
                # 保存过程中发生错误
                error_message = f"保存图像时发生错误: {e}"
                self.update_status(error_message, "red")
                messagebox.showerror("错误", error_message)
        else:
            # 加密/解密操作本身失败
            self.update_status(f"操作失败: {status_message}", "red")
            messagebox.showerror("失败", f"操作失败: {status_message}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCryptoApp(root)
    root.mainloop() # 启动Tkinter事件循环
