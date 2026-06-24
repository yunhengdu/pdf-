"""
PDF 解析可视化工具 — Streamlit 版
功能：上传 PDF → 自动检测文字层/扫描版 → OCR 提取 → 导出结构化文本
"""
import streamlit as st
import fitz  # PyMuPDF
import os
import json
import time
import tempfile
import zipfile
from pathlib import Path

st.set_page_config(
    page_title="PDF 智能解析工具",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========== 侧边栏 ==========
st.sidebar.title("📄 PDF 解析工具")
st.sidebar.markdown("---")
st.sidebar.markdown("### 使用步骤")
st.sidebar.markdown("1. 上传 PDF 文件")
st.sidebar.markdown("2. 选择解析方式")
st.sidebar.markdown("3. 点击「开始解析」")
st.sidebar.markdown("4. 预览并下载结果")
st.sidebar.markdown("---")

# 解析方式选择
parse_method = st.sidebar.radio(
    "解析方式",
    ["自动检测", "文字提取（直接）", "OCR 识别（扫描版）"],
    help="自动检测：先试文字提取，无文字层则自动切换 OCR",
)

# 语言选择（OCR 模式）
ocr_lang = st.sidebar.selectbox(
    "OCR 语言",
    ["ch", "en", "ch+en"],
    index=0,
    help="ch=中文, en=英文, ch+en=中英混合",
)

# DPI 设置
ocr_dpi = st.sidebar.slider(
    "OCR 图片精度 (DPI)",
    min_value=150,
    max_value=600,
    value=300,
    step=50,
    help="DPI 越高图片越清晰，OCR 越准，但速度越慢",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 输出格式")
output_format = st.sidebar.multiselect(
    "导出格式",
    ["Markdown (.md)", "纯文本 (.txt)", "JSON 分块 (.json)"],
    default=["Markdown (.md)", "纯文本 (.txt)"],
)

st.sidebar.markdown("---")
st.sidebar.caption("v1.0 | 支持 PyMuPDF + RapidOCR")


# ========== 主界面 ==========
st.title("📄 PDF 智能解析工具")
st.markdown("上传 PDF 文件，自动提取文字或 OCR 识别，导出结构化文本。")

# 上传区域
uploaded_file = st.file_uploader(
    "选择 PDF 文件",
    type=["pdf"],
    help="支持任何标准 PDF 文件",
)

# 初始化 session state
if "parse_result" not in st.session_state:
    st.session_state.parse_result = None
if "parsed_text" not in st.session_state:
    st.session_state.parsed_text = ""
if "total_pages" not in st.session_state:
    st.session_state.total_pages = 0
if "file_name" not in st.session_state:
    st.session_state.file_name = ""


def parse_with_pymupdf(pdf_path, max_pages=None):
    """使用 PyMuPDF 直接提取文字"""
    doc = fitz.open(pdf_path)
    total = doc.page_count
    pages_to_read = min(total, max_pages) if max_pages else total

    result = []
    for i in range(pages_to_read):
        page = doc[i]
        text = page.get_text().strip()
        result.append({"page": i + 1, "text": text, "char_count": len(text)})
        yield i + 1, total, result

    doc.close()


def parse_with_ocr(pdf_path, dpi=300, max_pages=None):
    """使用 RapidOCR 识别扫描版 PDF"""
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    doc = fitz.open(pdf_path)
    total = doc.page_count
    pages_to_read = min(total, max_pages) if max_pages else total

    result = []
    for i in range(pages_to_read):
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")

        # 保存到临时文件
        tmp_path = os.path.join(tempfile.gettempdir(), f"_ocr_page_{i}.png")
        pix.save(tmp_path)

        ocr_result, _ = engine(tmp_path)
        page_text = ""
        if ocr_result:
            for line in ocr_result:
                page_text += line[1] + "\n"

        os.remove(tmp_path)
        result.append({"page": i + 1, "text": page_text.strip(), "char_count": len(page_text)})
        yield i + 1, total, result

    doc.close()


def get_pdf_info(pdf_path):
    """获取 PDF 基本信息"""
    doc = fitz.open(pdf_path)
    info = {
        "pages": doc.page_count,
        "metadata": doc.metadata,
        "has_text": False,
    }
    # 检查是否有文字层
    for i in range(min(3, doc.page_count)):
        if doc[i].get_text().strip():
            info["has_text"] = True
            break
    doc.close()
    return info


# 处理上传文件
if uploaded_file is not None:
    # 保存上传的文件到临时目录
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    file_name = uploaded_file.name
    st.session_state.file_name = file_name

    # 显示文件信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("文件名", file_name[:30] + "..." if len(file_name) > 30 else file_name)
    with col2:
        st.metric("文件大小", f"{uploaded_file.size / 1024:.1f} KB")

    # 先分析 PDF
    with st.spinner("正在分析 PDF 文件..."):
        pdf_info = get_pdf_info(tmp_path)
        st.session_state.total_pages = pdf_info["pages"]

    with col3:
        st.metric("总页数", pdf_info["pages"])

    # 显示 PDF 信息
    meta = pdf_info["metadata"]
    meta_text = f"**标题**: {meta.get('title', '无')} | **作者**: {meta.get('author', '无')}"
    st.caption(meta_text)

    # PDF 类型提示
    if pdf_info["has_text"]:
        st.success("✅ 此 PDF 包含文字层，可直接提取文本")
    else:
        st.warning("⚠️ 此 PDF 是扫描版（图片），需要 OCR 识别")

    # 预览前几页
    with st.expander("📖 预览前几页", expanded=False):
        preview_pages = st.slider("预览页数", 1, min(10, pdf_info["pages"]), 3)

        # 显示图片预览
        doc = fitz.open(tmp_path)
        preview_cols = st.columns(min(preview_pages, 3))
        for i in range(preview_pages):
            page = doc[i]
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            with preview_cols[i % 3]:
                st.image(img_data, caption=f"第 {i+1} 页", use_container_width=True)
        doc.close()

    # 解析控制
    st.markdown("---")
    parse_col1, parse_col2, parse_col3 = st.columns([1, 1, 2])

    with parse_col1:
        max_pages = st.number_input(
            "解析页数限制（0=全部）",
            min_value=0,
            max_value=pdf_info["pages"],
            value=0,
        )

    with parse_col2:
        start_btn = st.button("🚀 开始解析", type="primary", use_container_width=True)

    # 进度显示
    progress_bar = st.progress(0, text="等待开始...")
    status_text = st.empty()

    if start_btn:
        max_p = None if max_pages == 0 else max_pages

        # 决定解析方式
        use_ocr = False
        if parse_method == "自动检测":
            use_ocr = not pdf_info["has_text"]
        elif parse_method == "OCR 识别（扫描版）":
            use_ocr = True
        else:
            use_ocr = False

        result = []
        total = pdf_info["pages"]
        method_name = "OCR 识别" if use_ocr else "文字提取"

        st.info(f"📌 解析方式: **{method_name}** | 目标页数: {max_p or total}")

        try:
            if use_ocr:
                generator = parse_with_ocr(tmp_path, dpi=ocr_dpi, max_pages=max_p)
            else:
                generator = parse_with_pymupdf(tmp_path, max_pages=max_p)

            for page_num, total_pages, result in generator:
                progress = page_num / (max_p or total_pages)
                progress_bar.progress(
                    min(progress, 1.0),
                    text=f"正在解析第 {page_num}/{max_p or total_pages} 页...",
                )
                # 更新状态
                chars_so_far = sum(r["char_count"] for r in result)
                status_text.text(f"已解析 {page_num} 页 | 已提取 {chars_so_far:,} 字符")

            # 完成
            st.session_state.parse_result = result
            total_chars = sum(r["char_count"] for r in result)
            st.session_state.parsed_text = "\n\n".join(
                [f"[第 {r['page']} 页]\n{r['text']}" for r in result]
            )

            progress_bar.progress(1.0, text="✅ 解析完成！")
            status_text.text(f"✅ 完成！共解析 {len(result)} 页，提取 {total_chars:,} 字符")

            st.success(f"✅ 解析完成！共提取 **{total_chars:,}** 字符")

            # 显示统计
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            with stat_col1:
                st.metric("已解析页数", len(result))
            with stat_col2:
                st.metric("总字符数", f"{total_chars:,}")
            with stat_col3:
                avg = total_chars // max(len(result), 1)
                st.metric("平均每页", f"{avg:,} 字符")

        except Exception as e:
            progress_bar.progress(0, text="❌ 解析失败")
            st.error(f"解析出错: {str(e)}")
            if "RapidOCR" in str(e) or "rapidocr" in str(e).lower():
                st.info(
                    "💡 OCR 依赖未安装，运行: `pip install rapidocr-onnxruntime`"
                )
            elif "No module" in str(e):
                st.info("💡 缺少依赖库，请安装: `pip install pymupdf rapidocr-onnxruntime streamlit`")

    # 预览和导出
    if st.session_state.parse_result is not None and len(st.session_state.parse_result) > 0:
        st.markdown("---")
        st.subheader("📝 解析结果预览")

        preview_page = st.selectbox(
            "选择预览页面",
            options=range(1, len(st.session_state.parse_result) + 1),
            format_func=lambda x: f"第 {x} 页",
        )

        page_data = st.session_state.parse_result[preview_page - 1]
        st.text_area(
            "文本内容",
            value=page_data["text"],
            height=300,
            disabled=True,
        )

        # 导出
        st.markdown("---")
        st.subheader("📥 导出结果")

        export_col1, export_col2, export_col3 = st.columns(3)

        base_name = Path(file_name).stem

        # 生成导出文件
        export_files = {}

        if "Markdown (.md)" in output_format:
            md_content = f"# {base_name} — 解析结果\n\n"
            for r in st.session_state.parse_result:
                if r["text"]:
                    md_content += f"\n\n## 第 {r['page']} 页\n{r['text']}"
            export_files["markdown"] = ("full_text.md", md_content)

        if "纯文本 (.txt)" in output_format:
            txt_content = ""
            for r in st.session_state.parse_result:
                if r["text"]:
                    txt_content += f"[第 {r['page']} 页]\n{r['text']}\n\n"
            export_files["text"] = ("full_text.txt", txt_content)

        if "JSON 分块 (.json)" in output_format:
            json_content = json.dumps(
                st.session_state.parse_result, ensure_ascii=False, indent=2
            )
            export_files["json"] = ("chunks.json", json_content)

        # 打包下载
        if len(export_files) == 1:
            for key, (fname, content) in export_files.items():
                st.download_button(
                    label=f"📥 下载 {fname}",
                    data=content.encode("utf-8"),
                    file_name=fname,
                    mime={
                        "markdown": "text/markdown",
                        "text": "text/plain",
                        "json": "application/json",
                    }.get(key, "text/plain"),
                    use_container_width=True,
                )
        elif len(export_files) > 1:
            # 打包为 ZIP
            zip_buffer = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for key, (fname, content) in export_files.items():
                    zf.writestr(fname, content.encode("utf-8"))
            zip_buffer.close()

            with open(zip_buffer.name, "rb") as f:
                st.download_button(
                    label="📥 下载全部 (ZIP 打包)",
                    data=f.read(),
                    file_name=f"{base_name}_解析结果.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            os.unlink(zip_buffer.name)

    # 清理临时文件
    try:
        os.unlink(tmp_path)
    except:
        pass

else:
    # 未上传文件时的引导界面
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 1. 📤 上传")
        st.markdown("上传你的 PDF 文件，支持任何标准 PDF")
    with col2:
        st.markdown("### 2. ⚙️ 解析")
        st.markdown("自动检测文字层或使用 OCR 识别扫描件")
    with col3:
        st.markdown("### 3. 📥 导出")
        st.markdown("导出为 Markdown / TXT / JSON 格式")

    st.markdown("---")
    st.markdown("#### 支持的 PDF 类型")
    type_col1, type_col2 = st.columns(2)
    with type_col1:
        st.markdown("✅ **文字型 PDF** — 直接提取，速度快")
        st.markdown("✅ **扫描型 PDF** — OCR 识别，支持中文")
    with type_col2:
        st.markdown("✅ **中英文混排** — 专业术语准确识别")
        st.markdown("✅ **带表格/习题** — 保留结构信息")

    st.markdown("---")
    st.caption("💡 需要安装依赖: `pip install streamlit pymupdf rapidocr-onnxruntime`")


# ========== 底部 ==========
st.markdown("---")
st.caption("📄 PDF 智能解析工具 | PyMuPDF + RapidOCR | 运行于 Streamlit")
