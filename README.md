# PDF 智能解析工具

开箱即用的 PDF 文字提取与 OCR 识别桌面工具。

## 功能

- 自动检测 PDF 类型（文字版 / 扫描版）
- 扫描版 PDF 中文 OCR 识别
- 导出 Markdown / TXT / JSON 格式
- 页面预览与翻页导航

## 文件说明

| 文件 | 说明 |
|------|------|
| `pdf_parser_desktop.py` | 桌面版主程序（Tkinter 界面） |
| `pdf_parser_app.py` | Streamlit Web 版（备选） |
| `build_spec.py` | 打包为 EXE 的脚本（推荐） |
| `使用说明.md` | 详细操作手册 |
| `README.md` | 本文件 |

## 技术栈

PyMuPDF + RapidOCR + Tkinter + PyInstaller

---

MIT License | YunHengDu © 2026
