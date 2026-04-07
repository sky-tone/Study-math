# Copilot Instructions — Study-math

## Project Overview
小升初数学教学与测验系统。基于全国真题题库（PDF），自动提取知识点，提供**概念教学→例题演示→测验→错题回顾→学情分析**的完整学习闭环。面向小学六年级学生。

## Tech Stack & Structure
- Language: Python 3.14 / Jupyter Notebooks
- Key dependencies: `pymupdf`（PDF文本提取）, `rapidocr-onnxruntime`（扫描件OCR）, `python-docx`（Word文档提取）, `IPython.display`（Notebook富文本展示）, `streamlit`（Web版界面）
- Key files:
  - `knowledge_base.py` — 核心知识点数据库（KNOWLEDGE_TREE / CONCEPTS / EXERCISES），启动时自动合并 `data/imported_exercises.json`
  - `import_questions.py` — 自动导入管线：文本→解析题目→分类知识点→评估难度→写入JSON
  - `ocr_extract.py` — OCR 提取工具：扫描件 PDF → 文本
  - `app.py` — 独立 Web 版应用（Streamlit），含教学/测验/错题本/学情分析/题目编辑器
  - `desktop_app.py` — 桌面版启动器：自动启动 Streamlit + Edge App 模式窗口
  - `run_desktop.bat` — Windows 双击启动脚本
  - `teaching_learn.ipynb` — 教学系统 Notebook
  - `quiz_test.ipynb` — 测验与学情分析 Notebook
  - `data/imported_exercises.json` — 自动导入的题库（被 knowledge_base.py 动态加载）
  - `data/study_record.json` — 学习记录
  - `data/*.txt` — OCR / PDF 提取的原始文本
  - 根目录 PDF — 原始题库文件

## Architecture
知识体系为 4章 → 14小节 → 54个知识点（`KNOWLEDGE_TREE`），每个知识点挂载：
- `CONCEPTS[topic]` — 含 `explanation`（Markdown/LaTeX）和 `key_points` 列表
- `EXERCISES[topic]` — 内置题目 + 自动从 `data/imported_exercises.json` 合并的外部题目

### 自动导入管线
```
新 PDF → ocr_extract.py（扫描件）或 PyMuPDF（文字PDF）
       → data/xxx.txt
       → import_questions.py（解析+分类+评估难度）
       → data/imported_exercises.json
       → knowledge_base.py 启动时自动合并（无需改代码）
```

## Conventions
- 用 **Jupyter Notebooks** 做交互式教学/测验；用 `.py` 做数据模块
- Notebook中用 `IPython.display.Markdown` 渲染 LaTeX 公式
- 练习题 `type` 可选：选择/填空/判断/计算/解答
- `difficulty` 用 1-3 表示难度等级（由 `import_questions.py` 自动评估）
- 终端输出避免使用 emoji（Windows GBK 编码问题）

## Adding New Content

### 方式一：自动导入（推荐）
```bash
# 扫描件 PDF
python ocr_extract.py "新试卷.pdf"
python import_questions.py "data/新试卷_ocr.txt"

# 文字 PDF
python import_questions.py --from-pdf "新试卷.pdf"

# Word 文档
python import_questions.py --from-docx "新试卷.docx"

# 批量扫描 data/ 下所有文本
python import_questions.py
```
无需修改任何代码，`knowledge_base.py` 下次加载时自动合并新题目。

### 方式二：手动添加
在 `knowledge_base.py` 的 `CONCEPTS` / `EXERCISES` 字典中直接添加。

## Workflow
- 运行 Notebooks 通过 VS Code 内置 Jupyter 支持
- 无构建步骤；直接运行 `.ipynb` 单元格即可
