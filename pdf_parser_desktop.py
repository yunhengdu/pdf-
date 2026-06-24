"""
PDF 智能解析工具 — 桌面版（Tkinter 原生界面）
无需浏览器，双击即用
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import fitz
import os
import json
import threading
import time
from pathlib import Path

# ========== OCR 按需导入 ==========
try:
    from rapidocr_onnxruntime import RapidOCR
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class PDFParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF 智能解析工具 v1.0 — YunHengDu")
        self.root.geometry("900x700")
        self.root.minsize(700, 500)

        # 设置图标（如果有）
        try:
            self.root.iconbitmap(default="")
        except:
            pass

        # 变量
        self.pdf_path = None
        self.pdf_info = None
        self.parse_result = []
        self.current_page = 0

        # 样式
        self.setup_styles()
        self.build_ui()

        # 居中显示
        self.center_window()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")
        style.configure("Title.TLabel", font=("微软雅黑", 16, "bold"))
        style.configure("Heading.TLabel", font=("微软雅黑", 11, "bold"))
        style.configure("Info.TLabel", font=("微软雅黑", 10))
        style.configure("Success.TLabel", font=("微软雅黑", 10), foreground="#2e7d32")
        style.configure("Warning.TLabel", font=("微软雅黑", 10), foreground="#e65100")
        style.configure("Action.TButton", font=("微软雅黑", 10))
        style.configure("Primary.TButton", font=("微软雅黑", 11, "bold"))

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def build_ui(self):
        # ===== 顶部标题 =====
        header = ttk.Frame(self.root, padding=15)
        header.pack(fill="x")

        ttk.Label(header, text="📄 PDF 智能解析工具", style="Title.TLabel").pack(
            side="left"
        )
        ttk.Label(
            header,
            text="by YunHengDu | 提取文字 · OCR 识别 · 导出结构化文本",
            style="Info.TLabel",
            foreground="gray",
        ).pack(side="left", padx=15)

        # ===== 主内容区域（左右分栏） =====
        main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=10, pady=5)

        # ===== 左侧：操作面板 =====
        left_frame = ttk.Frame(main_paned, padding=10)
        main_paned.add(left_frame, weight=1)

        # 文件选择
        file_frame = ttk.LabelFrame(left_frame, text="📂 选择文件", padding=10)
        file_frame.pack(fill="x", pady=5)

        file_btn_frame = ttk.Frame(file_frame)
        file_btn_frame.pack(fill="x")

        self.file_label = ttk.Label(
            file_btn_frame, text="未选择文件", style="Info.TLabel", foreground="gray"
        )
        self.file_label.pack(side="left", fill="x", expand=True)

        ttk.Button(
            file_btn_frame,
            text="浏览...",
            command=self.select_file,
            style="Action.TButton",
        ).pack(side="right", padx=5)

        # 文件信息
        self.info_frame = ttk.LabelFrame(left_frame, text="📋 文件信息", padding=10)
        self.info_frame.pack(fill="x", pady=5)

        self.info_text = tk.StringVar(value="请先选择 PDF 文件")
        ttk.Label(
            self.info_frame, textvariable=self.info_text, style="Info.TLabel", wraplength=350
        ).pack(fill="x")

        # PDF 类型提示
        self.type_label = ttk.Label(self.info_frame, text="", style="Info.TLabel")
        self.type_label.pack(fill="x", pady=2)

        # 解析设置
        opt_frame = ttk.LabelFrame(left_frame, text="⚙️ 解析设置", padding=10)
        opt_frame.pack(fill="x", pady=5)

        # 解析方式
        method_frame = ttk.Frame(opt_frame)
        method_frame.pack(fill="x", pady=3)
        ttk.Label(method_frame, text="解析方式:", style="Heading.TLabel").pack(side="left")
        self.parse_method = tk.StringVar(value="auto")
        ttk.Radiobutton(
            method_frame, text="自动检测", variable=self.parse_method, value="auto"
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            method_frame, text="文字提取", variable=self.parse_method, value="text"
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            method_frame, text="OCR 识别", variable=self.parse_method, value="ocr"
        ).pack(side="left", padx=5)

        # OCR DPI
        dpi_frame = ttk.Frame(opt_frame)
        dpi_frame.pack(fill="x", pady=3)
        ttk.Label(dpi_frame, text="OCR 精度:", style="Heading.TLabel").pack(side="left")
        self.dpi_var = tk.IntVar(value=300)
        dpi_menu = ttk.Combobox(
            dpi_frame,
            textvariable=self.dpi_var,
            values=[150, 200, 300, 400, 600],
            width=8,
            state="readonly",
        )
        dpi_menu.pack(side="left", padx=5)
        ttk.Label(dpi_frame, text="DPI（越高越清晰越慢）", style="Info.TLabel", foreground="gray").pack(
            side="left", padx=5
        )

        # 页数限制
        page_frame = ttk.Frame(opt_frame)
        page_frame.pack(fill="x", pady=3)
        ttk.Label(page_frame, text="解析页数:", style="Heading.TLabel").pack(side="left")
        self.page_limit = tk.StringVar(value="0")
        ttk.Entry(page_frame, textvariable=self.page_limit, width=10).pack(side="left", padx=5)
        ttk.Label(page_frame, text="(0=全部)", style="Info.TLabel", foreground="gray").pack(side="left")

        # 操作按钮
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(fill="x", pady=10)

        self.parse_btn = ttk.Button(
            action_frame,
            text="🚀 开始解析",
            command=self.start_parse,
            style="Primary.TButton",
            state="disabled",
        )
        self.parse_btn.pack(fill="x", ipady=5)

        # 进度条
        self.progress = ttk.Progressbar(left_frame, mode="determinate")
        self.progress.pack(fill="x", pady=2)
        self.progress_label = ttk.Label(left_frame, text="", style="Info.TLabel")
        self.progress_label.pack(fill="x")

        # 导出按钮
        export_frame = ttk.Frame(left_frame)
        export_frame.pack(fill="x", pady=5)

        self.export_md_btn = ttk.Button(
            export_frame,
            text="📥 导出 Markdown",
            command=lambda: self.export_file("md"),
            state="disabled",
        )
        self.export_md_btn.pack(side="left", fill="x", expand=True, padx=2)

        self.export_txt_btn = ttk.Button(
            export_frame,
            text="📥 导出 TXT",
            command=lambda: self.export_file("txt"),
            state="disabled",
        )
        self.export_txt_btn.pack(side="left", fill="x", expand=True, padx=2)

        self.export_json_btn = ttk.Button(
            export_frame,
            text="📥 导出 JSON",
            command=lambda: self.export_file("json"),
            state="disabled",
        )
        self.export_json_btn.pack(side="left", fill="x", expand=True, padx=2)

        # ===== 右侧：预览面板 =====
        right_frame = ttk.Frame(main_paned, padding=10)
        main_paned.add(right_frame, weight=2)

        preview_header = ttk.Frame(right_frame)
        preview_header.pack(fill="x")

        ttk.Label(preview_header, text="📝 预览", style="Heading.TLabel").pack(side="left")

        self.page_nav_frame = ttk.Frame(preview_header)
        self.page_nav_frame.pack(side="right")

        ttk.Button(
            self.page_nav_frame, text="◀", command=self.prev_page, width=3
        ).pack(side="left", padx=1)
        self.page_indicator = ttk.Label(
            self.page_nav_frame, text="0/0", style="Info.TLabel"
        )
        self.page_indicator.pack(side="left", padx=5)
        ttk.Button(
            self.page_nav_frame, text="▶", command=self.next_page, width=3
        ).pack(side="left", padx=1)

        self.text_preview = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 10),
            state="disabled",
            bg="#fafafa",
            relief="flat",
            borderwidth=1,
        )
        self.text_preview.pack(fill="both", expand=True, pady=5)

        # 初始欢迎词（带作者标识）
        self.show_welcome()

        # 状态栏（带作者信息）
        status_frame = ttk.Frame(self.root, relief="sunken", padding=3)
        status_frame.pack(fill="x", side="bottom")

        self.status_label = ttk.Label(
            status_frame, text="就绪 | 支持文字 PDF 和扫描件 OCR", style="Info.TLabel"
        )
        self.status_label.pack(side="left")

        ttk.Label(
            status_frame, text="YunHengDu © 2026", style="Info.TLabel",
            foreground="gray",
        ).pack(side="right", padx=5)

    def show_welcome(self):
        """显示欢迎页"""
        self.text_preview.config(state="normal")
        self.text_preview.delete(1.0, tk.END)
        welcome = """
╔════════════════════════════════════╗
║     📄 PDF 智能解析工具              ║
║     by YunHengDu                    ║
╚════════════════════════════════════╝

功能介绍：
  • 上传 PDF → 自动提取文字
  • 扫描版 PDF → OCR 识别
  • 导出为 Markdown / TXT / JSON

使用步骤：
  1. 点击左侧「浏览」选择 PDF 文件
  2. 设置解析方式（默认自动检测）
  3. 点击「开始解析」
  4. 预览结果并导出

---
YunHengDu © 2026
"""
        self.text_preview.insert(1.0, welcome)
        self.text_preview.config(state="disabled")

    def select_file(self):
        path = filedialog.askopenfilename(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if not path:
            return

        self.pdf_path = path
        fname = os.path.basename(path)
        fsize = os.path.getsize(path)
        self.file_label.config(text=fname, foreground="black")

        # 读取 PDF 信息
        self.root.config(cursor="watch")
        self.root.update()

        try:
            doc = fitz.open(path)
            pages = doc.page_count
            meta = doc.metadata
            has_text = False
            for i in range(min(3, pages)):
                if doc[i].get_text().strip():
                    has_text = True
                    break
            doc.close()

            self.pdf_info = {
                "pages": pages,
                "has_text": has_text,
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "producer": meta.get("producer", ""),
            }

            title_text = meta.get("title", "无标题") or "无标题"
            info_lines = [
                f"📄 标题: {title_text}",
                f"👤 作者: {meta.get('author', '未知') or '未知'}",
                f"📎 页数: {pages} 页 | 大小: {fsize/1024:.1f} KB",
            ]
            self.info_text.set("\n".join(info_lines))

            if has_text:
                self.type_label.config(
                    text="✅ 包含文字层，可直接提取",
                    style="Success.TLabel",
                )
            else:
                self.type_label.config(
                    text="⚠️ 扫描版 PDF，需要 OCR 识别",
                    style="Warning.TLabel",
                )
                if not OCR_AVAILABLE:
                    self.type_label.config(
                        text="⚠️ 扫描版 PDF，需要安装 OCR: pip install rapidocr-onnxruntime",
                        style="Warning.TLabel",
                    )

            self.parse_btn.config(state="normal")
            self.status_label.config(text=f"已加载: {fname} ({pages} 页)")

        except Exception as e:
            messagebox.showerror("错误", f"无法读取 PDF 文件:\n{str(e)}")
            self.pdf_info = None

        self.root.config(cursor="")

    def start_parse(self):
        if not self.pdf_path or not self.pdf_info:
            return

        # 禁用按钮
        self.parse_btn.config(state="disabled", text="⏳ 解析中...")
        self.export_md_btn.config(state="disabled")
        self.export_txt_btn.config(state="disabled")
        self.export_json_btn.config(state="disabled")

        # 在新线程中运行
        thread = threading.Thread(target=self.do_parse, daemon=True)
        thread.start()

    def do_parse(self):
        try:
            doc = fitz.open(self.pdf_path)
            total = self.pdf_info["pages"]

            # 决定是否用 OCR
            method = self.parse_method.get()
            use_ocr = False
            if method == "auto":
                use_ocr = not self.pdf_info["has_text"]
            elif method == "ocr":
                use_ocr = True

            if use_ocr and not OCR_AVAILABLE:
                self.root.after(0, lambda: messagebox.showerror(
                    "OCR 不可用",
                    "RapidOCR 未安装，无法进行 OCR 识别。\n请运行: pip install rapidocr-onnxruntime",
                ))
                self.root.after(0, self.reset_buttons)
                doc.close()
                return

            # 页数限制
            limit = int(self.page_limit.get())
            max_pages = min(total, limit) if limit > 0 else total

            result = []
            engine = None
            if use_ocr:
                engine = RapidOCR()

            for i in range(max_pages):
                page = doc[i]

                if use_ocr and engine:
                    pix = page.get_pixmap(dpi=self.dpi_var.get())
                    tmp_img = os.path.join(
                        os.environ.get("TEMP", "."), f"_pdf_ocr_{i}.png"
                    )
                    pix.save(tmp_img)
                    ocr_result, _ = engine(tmp_img)
                    text = ""
                    if ocr_result:
                        text = "\n".join([line[1] for line in ocr_result])
                    try:
                        os.remove(tmp_img)
                    except:
                        pass
                else:
                    text = page.get_text().strip()

                result.append({
                    "page": i + 1,
                    "text": text,
                    "char_count": len(text),
                })

                # 更新进度
                progress = (i + 1) / max_pages * 100
                self.root.after(0, lambda p=progress, c=i+1, t=max_pages: self.update_progress(p, c, t))

            doc.close()
            self.parse_result = result

            # 更新预览
            self.current_page = 0
            self.root.after(0, self.show_page)
            self.root.after(0, self.update_stats)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("解析失败", str(e)))

        self.root.after(0, self.reset_buttons)

    def update_progress(self, progress, current, total):
        self.progress["value"] = progress
        chars = sum(c["char_count"] for c in self.parse_result) if self.parse_result else 0
        self.progress_label.config(
            text=f"⏳ 正在解析: {current}/{total} 页 | 已提取 {chars:,} 字符"
        )

    def update_stats(self):
        total_chars = sum(c["char_count"] for c in self.parse_result)
        self.status_label.config(
            text=f"✅ 解析完成: {len(self.parse_result)} 页, {total_chars:,} 字符"
        )
        self.progress_label.config(
            text=f"✅ 完成! 共 {len(self.parse_result)} 页, {total_chars:,} 字符"
        )

    def reset_buttons(self):
        self.parse_btn.config(state="normal", text="🚀 开始解析")
        if self.parse_result:
            self.export_md_btn.config(state="normal")
            self.export_txt_btn.config(state="normal")
            self.export_json_btn.config(state="normal")

    def show_page(self):
        if not self.parse_result:
            return

        page_data = self.parse_result[self.current_page]
        self.text_preview.config(state="normal")
        self.text_preview.delete(1.0, tk.END)
        header = f"══════════ 第 {page_data['page']} 页 ══════════\n"
        if page_data["char_count"] > 0:
            content = header + page_data["text"]
        else:
            content = header + "\n（此页无文字内容）"
        self.text_preview.insert(1.0, content)
        self.text_preview.config(state="disabled")

        total = len(self.parse_result)
        self.page_indicator.config(text=f"{self.current_page + 1}/{total}")

    def next_page(self):
        if self.parse_result and self.current_page < len(self.parse_result) - 1:
            self.current_page += 1
            self.show_page()

    def prev_page(self):
        if self.parse_result and self.current_page > 0:
            self.current_page -= 1
            self.show_page()

    def export_file(self, fmt):
        if not self.parse_result:
            return

        base_name = Path(self.pdf_path).stem if self.pdf_path else "output"
        default_name = {
            "md": f"{base_name}.md",
            "txt": f"{base_name}.txt",
            "json": f"{base_name}.json",
        }.get(fmt, f"{base_name}.txt")

        file_path = filedialog.asksaveasfilename(
            title="保存文件",
            defaultextension=f".{fmt}",
            filetypes={
                "md": [("Markdown", "*.md")],
                "txt": [("文本文件", "*.txt")],
                "json": [("JSON", "*.json")],
            }.get(fmt, [("所有文件", "*.*")]),
            initialfile=default_name,
        )
        if not file_path:
            return

        if fmt == "md":
            content = f"# {base_name} — 解析结果\n\n"
            for r in self.parse_result:
                if r["text"]:
                    content += f"\n## 第 {r['page']} 页\n{r['text']}\n"
        elif fmt == "txt":
            content = ""
            for r in self.parse_result:
                if r["text"]:
                    content += f"[第 {r['page']} 页]\n{r['text']}\n\n"
        elif fmt == "json":
            content = json.dumps(self.parse_result, ensure_ascii=False, indent=2)
        else:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("导出成功", f"文件已保存到:\n{file_path}")
            self.status_label.config(text=f"✅ 已导出: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))


def main():
    root = tk.Tk()
    app = PDFParserApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
