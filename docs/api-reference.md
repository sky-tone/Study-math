# 模块 API 参考

---

## knowledge_base.py

核心知识点数据库，包含知识体系结构、概念讲解和练习题。启动时自动合并 `data/imported_exercises.json`。

**代码行数**：2003行

### 数据结构

#### `KNOWLEDGE_TREE: dict`
知识体系树，4章 → 14小节 → 54知识点。

```python
KNOWLEDGE_TREE = {
    "1": {
        "title": "数与代数",
        "sections": {
            "1.1": {
                "title": "数的认识",
                "topics": ["数的分类", "数的组成（大数读写改写）", ...]
            },
            ...
        }
    },
    ...
}
```

#### `CONCEPTS: dict[str, dict]`
概念讲解字典，key 为知识点名称。

```python
CONCEPTS["数的分类"] = {
    "explanation": "## 数的分类\n...",   # Markdown/LaTeX 格式
    "key_points": ["自然数包括0", ...]   # 重点列表
}
```

#### `EXERCISES: dict[str, list[dict]]`
练习题字典，key 为知识点名称。启动时自动合并外部导入。

```python
EXERCISES["数的分类"] = [
    {
        "id": "1.1.1",          # 唯一ID（内置格式 x.x.x，导入格式 IMP-XXXXXX）
        "type": "选择",          # 选择/填空/判断/计算/解答
        "difficulty": 1,         # 1=基础, 2=中等, 3=困难
        "question": "题目文本",
        "answer": "正确答案",
        "explanation": "解析",
        "options": ["A. ...", "B. ..."],  # 仅选择题有
        "source": "来源文件",              # 仅导入题有
    },
    ...
]
```

### 函数

#### `get_all_topics() -> list[str]`
获取所有 54 个知识点名称列表，按知识树顺序排列。

#### `get_concept(topic: str) -> dict | None`
根据知识点名称获取概念讲解，返回含 `explanation` 和 `key_points` 的字典。

#### `get_exercises_by_topic(topic: str) -> list[dict]`
根据知识点名称获取该知识点下的所有练习题（含导入合并的）。

#### `get_topics_by_section(section_id: str) -> list[str]`
根据小节编号获取知识点列表。如 `get_topics_by_section("1.2")` 返回因数与倍数相关知识点。

#### `get_section_title(section_id: str) -> str`
获取小节标题，如 `get_section_title("1.1")` 返回 `"数的认识"`。

#### `print_knowledge_tree()`
在终端打印完整知识树（含概念/练习标记），用于调试。

---

## import_questions.py

自动导入管线：从文本文件中解析题目，分类到知识点，评估难度，保存到 JSON。

### 核心函数

#### `import_from_text_file(filepath: str, auto_save: bool = True) -> list[dict]`
从文本文件自动导入题目到题库。

**流程**：读取文本 → `parse_questions_from_text()` → `classify_topic()` → `assess_difficulty()` → `_save_imported()`

**参数**：
- `filepath`：文本文件路径（OCR 输出或 PDF 提取文本）
- `auto_save`：是否自动保存到 `imported_exercises.json`

**返回**：成功导入的题目列表

#### `import_from_pdf(pdf_path: str, use_ocr: bool = False) -> list[dict]`
从 PDF 文件直接导入。

**参数**：
- `pdf_path`：PDF 文件路径
- `use_ocr`：是否使用 OCR（扫描件设为 True）

#### `scan_and_import_all()`
扫描 `data/` 目录下所有 `.txt` 文件，自动逐个导入。

### 辅助函数

#### `parse_questions_from_text(text: str, source: str) -> list[dict]`
从文本中按题号（1. 2. 3.、1、2、3、等）拆分出独立题目。

#### `classify_topic(question_text: str) -> tuple[str, float]`
基于关键词映射表 `TOPIC_KEYWORDS` 将题目分类到最匹配的知识点。返回 `(topic_name, confidence_score)`。

#### `assess_difficulty(question_text: str) -> int`
基于文本长度、子问题数量、关键词等特征评估难度（1-3）。

#### `infer_question_type(question_text: str) -> str`
推断题型：选择/填空/判断/计算/解答。

#### `generate_id(question_text: str, source: str) -> str`
基于内容 MD5 哈希生成唯一 ID，格式 `IMP-XXXXXX`。

### 配置

#### `TOPIC_KEYWORDS: dict[str, list[str]]`
知识点关键词映射表，54 个知识点各有一组关键词。分类器按命中数排序取最高匹配。

### 命令行用法

```bash
# 扫描 data/ 下所有文本
python import_questions.py

# 导入指定文本文件
python import_questions.py data/GZMK数学试卷2_ocr.txt

# 从文字 PDF 直接导入
python import_questions.py --from-pdf "新试卷.pdf"

# 从扫描件 PDF 导入（先 OCR 再解析）
python import_questions.py --from-pdf "扫描件.pdf" --ocr
```

---

## ocr_extract.py

扫描件 PDF 的 OCR 文字提取工具。

### 函数

#### `extract_pdf_with_ocr(pdf_path, output_path=None, dpi=300, verbose=True) -> str`
对扫描件 PDF 进行全页 OCR 提取。

**参数**：
- `pdf_path`：PDF 文件路径
- `output_path`：输出文本文件路径（默认 `data/{名称}_ocr.txt`）
- `dpi`：渲染分辨率（默认 300，越高越清晰但越慢）
- `verbose`：是否打印进度

**返回**：提取的全部文本

#### `pdf_page_to_image(page, dpi=300) -> np.ndarray`
将 PDF 单页渲染为 RGB numpy 数组。

#### `quick_preview(pdf_path, pages=None, dpi=200)`
快速预览指定页面的 OCR 结果（不保存文件），用于调试。

#### `extract_all_scans(dpi=300)`
提取 `SCAN_PDFS` 列表中所有扫描件 PDF。

### 配置

```python
DPI = 300           # 默认渲染分辨率
SCAN_PDFS = [       # 扫描件 PDF 列表
    "GZMK数学试卷1.pdf",
    "GZMK数学试卷2.pdf",
]
```

### 命令行用法

```bash
# 提取指定 PDF
python ocr_extract.py "GZMK数学试卷1.pdf"

# 提取所有扫描件（SCAN_PDFS 列表）
python ocr_extract.py
```

---

## Notebook API

### teaching_learn.ipynb

| Cell | 功能 | 关键变量 |
|:----:|------|----------|
| 1 | 导入知识库 | — |
| 2 | 知识树总览（生成索引表） | `topic_index: dict` |
| 3 | 学习知识点（概念+练习） | `TOPIC_NUM: int` — 修改此值选择知识点 |
| 4 | 查看答案与解析 | — |
| 5 | 公式速查表 | — |

### quiz_test.ipynb

| Cell | 功能 | 关键变量 |
|:----:|------|----------|
| 1 | 初始化 + 加载记录 | `records: dict` |
| 2 | 列出可选知识点 | `available_topics: dict` |
| 3 | 组卷出题 | `TEST_MODE: int`（0=综合, N=专项）, `NUM_QUESTIONS: int` |
| 4 | 填写答案 + 批改 | `my_answers: list[str]` — 自动根据题目数量生成 |
| 5 | 错题本 | — |
| 6 | 学情分析 | — |
| 7 | 清空错题本 | 需手动取消注释 |

---

## app.py

独立 Web 应用（Streamlit），无需 VS Code 即可在浏览器中使用完整的教学与测验系统。

**代码行数**：954行

### 启动方式

```bash
python -m streamlit run app.py
```

### 页面结构

| 页面 | 功能 |
|------|------|
| 🌳 知识树总览 | 按章节展开知识体系，显示概念/练习覆盖情况 |
| 📖 学习知识点 | 选择知识点，展示概念讲解 + 配套练习 + 答案解析 |
| 🧮 公式速查表 | 平面图形/立体图形/统计/行程全套公式 |
| 🎯 测验系统 | 综合随机 / 专项知识点测验，自动组卷批改 |
| 📕 错题本 | 按知识点分组查看错题，含正确答案和解析 |
| 📈 学情分析 | 总体统计、薄弱知识点排行、历次记录、进步趋势 |
| ✏️ 题目编辑器 | 在线编辑/新增/删除题目，修改答案和解析，支持溯源 |

### 辅助函数

#### `_source_label(ex: dict) -> str`
将题目的 `source` 字段映射为可读的来源名称。

#### `_find_source_context(ex: dict, context_lines: int = 5) -> tuple`
在源 txt 文件中查找题目原文的上下文，用于溯源功能。

#### `build_topic_index() -> dict`
构建知识点编号到名称的映射表（带 `@st.cache_data` 缓存）。

#### `load_records() -> dict` / `save_records(records: dict)`
学习记录的持久化读写（`data/study_record.json`）。
