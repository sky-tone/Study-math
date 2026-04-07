# 开发指南与操作手册

---

## 环境搭建

### 1. 创建虚拟环境

```bash
python -m venv .venv
```

### 2. 安装依赖

```bash
.venv\Scripts\pip.exe install pymupdf rapidocr-onnxruntime ipykernel streamlit
```

依赖清单：

| 包 | 用途 |
|------|------|
| pymupdf (fitz) | PDF 文本提取 + 页面渲染 |
| rapidocr-onnxruntime | 中文 OCR 引擎 |
| ipykernel | Jupyter Notebook 内核 |
| streamlit | Web 版界面框架 |
| numpy | OCR 图像处理（自动安装） |
| opencv-python | OCR 依赖（自动安装） |
| onnxruntime | OCR 推理后端（自动安装） |
| Pillow | 图像处理（自动安装） |

### 3. VS Code 配置

- 选择 Python 解释器：`.venv\Scripts\python.exe`
- Notebook 内核：选择 `.venv` 对应的 Python

---

## 日常操作

### 导入新题库（最常用）

#### 场景一：新的扫描件 PDF

```bash
# Step 1: OCR 提取文字
python ocr_extract.py "新试卷.pdf"
# 输出: data/新试卷_ocr.txt

# Step 2: 解析并导入
python import_questions.py "data/新试卷_ocr.txt"
# 输出: 自动合并到 data/imported_exercises.json
```

#### 场景二：新的文字 PDF

```bash
python import_questions.py --from-pdf "新试卷.pdf"
```

#### 场景三：批量导入 data/ 下所有文本

```bash
python import_questions.py
```

**无需修改任何代码**，下次打开 Notebook 时 `knowledge_base.py` 自动加载新题目。

### 查看题库统计

```bash
python knowledge_base.py
```

### 启动 Web 版

```bash
python -m streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`，含教学/测验/错题本/学情分析/题目编辑器等全部功能。

### 启动桌面版

```bash
python desktop_app.py
# 或双击 run_desktop.bat
```

自动启动 Streamlit 服务器，用 Edge App 模式打开独立窗口（无地址栏），关闭窗口后自动退出。

### 验证数据完整性

```bash
python -c "
from knowledge_base import *
all_t = get_all_topics()
total = sum(len(v) for v in EXERCISES.values())
print(f'Topics: {len(all_t)}, Concepts: {len(CONCEPTS)}, Exercises: {total}')
missing = [t for t in all_t if t not in CONCEPTS]
print(f'Missing concepts: {missing}')
"
```

---

## 扩展开发

### 添加新知识点

1. 在 `knowledge_base.py` 的 `KNOWLEDGE_TREE` 中对应小节的 `topics` 列表里添加
2. 在 `CONCEPTS` 字典中添加概念讲解
3. 在 `import_questions.py` 的 `TOPIC_KEYWORDS` 中添加关键词映射
4. 可选：在 `EXERCISES` 中手动添加内置题目

### 添加新章节

在 `KNOWLEDGE_TREE` 中新增章 ID 和结构即可，Notebook 会自动枚举。

### 优化分类准确率

编辑 `import_questions.py` 中的 `TOPIC_KEYWORDS` 字典：

```python
TOPIC_KEYWORDS = {
    "知识点名称": ["关键词1", "关键词2", "正则表达式.*也支持"],
    ...
}
```

关键词支持正则表达式（`re.search` 匹配）。命中越多的知识点得分越高。

### 优化难度评估

编辑 `import_questions.py` 中的：
- `DIFFICULTY_HARD_KEYWORDS` — 困难关键词（匹配 +2 分）
- `DIFFICULTY_MEDIUM_KEYWORDS` — 中等关键词（匹配 +1 分）
- `assess_difficulty()` 函数中的评分逻辑

### 自定义 OCR 参数

编辑 `ocr_extract.py`：
- `DPI = 300` — 提高分辨率可改善识别率，但更慢
- `confidence > 0.5` — 降低阈值可保留更多结果（可能含噪声）

---

## 常见问题

### Q: Windows 终端报 UnicodeEncodeError

**原因**：终端使用 GBK 编码，不支持 emoji 字符。

**解决**：`.py` 文件的 `print()` 不要使用 emoji，改用 `[OK]` `[DONE]` 等纯 ASCII 标记。Notebook 中使用 emoji 没问题（IPython 使用 UTF-8）。

### Q: Pylance 报"无法解析导入"

**原因**：VS Code 没有选择 `.venv` 作为 Python 解释器。

**解决**：点击 VS Code 右下角 Python 版本 → 选择 `.venv\Scripts\python.exe`。这只是 IDE 警告，不影响实际运行。

### Q: OCR 结果质量差

**尝试**：
1. 提高 DPI（`ocr_extract.py` 中改为 400）
2. 使用 `quick_preview()` 测试特定页面
3. OCR 后手动修正 `data/xxx_ocr.txt` 再重新导入

### Q: 某些题目被错误分类

**解决**：
1. 在 `TOPIC_KEYWORDS` 中增加更精确的关键词
2. 手动编辑 `data/imported_exercises.json`，移动题目到正确的 topic 下
3. 重新运行 `python import_questions.py` 不会覆盖已有数据（基于 ID 去重）

### Q: 想清空所有导入数据重新开始

```bash
# 删除导入的题库
del data\imported_exercises.json

# 重新导入所有文本
python import_questions.py
```
