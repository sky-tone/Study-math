# 系统架构设计

## 项目定位

小升初数学教学与测验系统，面向小学六年级学生。基于全国真题题库（PDF），提供：

**概念教学 → 例题演示 → 测验 → 错题回顾 → 学情分析** 的完整学习闭环。

---

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.14 | 全项目统一使用 |
| 交互界面 | Jupyter Notebook | VS Code 内置支持 |
| Web 界面 | Streamlit | 独立 Web 应用，浏览器访问 |
| PDF 文本提取 | PyMuPDF (fitz) | 文字型 PDF |
| 扫描件 OCR | rapidocr-onnxruntime | 基于 ONNX 的中文 OCR |
| 富文本渲染 | IPython.display | Markdown + LaTeX 公式 |
| 数据存储 | JSON 文件 | 无需数据库 |
| 虚拟环境 | .venv | pip 管理依赖 |

---

## 目录结构

```
Study-math/
├── .github/
│   └── copilot-instructions.md    # AI 编码指令
├── docs/                          # 开发文档（本目录）
├── data/
│   ├── imported_exercises.json    # 自动导入的题库（动态加载）
│   ├── study_record.json          # 学生学习记录
│   ├── GZMK数学试卷1_ocr.txt      # OCR 提取文本
│   ├── GZMK数学试卷2_ocr.txt      # OCR 提取文本
│   └── 小学数学总复习2022.txt      # PDF 提取文本
├── app.py                         # Web 版应用（Streamlit，954行）
├── desktop_app.py                 # 桌面版启动器（Edge App 模式）
├── run_desktop.bat                # 桌面版双击启动脚本
├── knowledge_base.py              # 核心知识库（2003行）
├── import_questions.py            # 自动导入管线（555行）
├── ocr_extract.py                 # OCR 提取工具（196行）
├── teaching_learn.ipynb           # 教学系统 Notebook
├── quiz_test.ipynb                # 测验系统 Notebook
├── GZMK数学试卷1.pdf              # 原始题库（95页扫描件）
├── GZMK数学试卷2.pdf              # 原始题库（11页扫描件）
└── 小学数学总复习2022.pdf          # 原始教材（86页文字PDF）
```

---

## 知识体系结构

```
KNOWLEDGE_TREE（4章 → 14小节 → 54知识点）
│
├── 第1章 数与代数（20个知识点）
│   ├── 1.1 数的认识
│   ├── 1.2 因数与倍数
│   ├── 1.3 数的运算
│   ├── 1.4 式与方程
│   ├── 1.5 比和比例
│   └── 1.6 计量单位
│
├── 第2章 图形与几何（13个知识点）
│   ├── 2.1 平面图形
│   ├── 2.2 立体图形
│   ├── 2.3 图形运动与位置
│   └── 2.4 面积与体积
│
├── 第3章 统计与概率（6个知识点）
│   ├── 3.1 统计图
│   └── 3.2 可能性
│
└── 第4章 综合与实践（15个知识点）
    ├── 4.1 分数乘除法应用
    ├── 4.2 百分数问题
    ├── 4.3 工程问题
    ├── 4.4 分段计费问题
    ├── 4.5 行程问题
    ├── 4.6 比与比例应用
    └── 4.7 图象问题
```

每个知识点挂载：
- `CONCEPTS[topic]` — 概念讲解（Markdown/LaTeX + key_points 列表）
- `EXERCISES[topic]` — 练习题列表（内置 + 自动导入合并）

---

## 数据流

### 教学流程
```
学生打开 teaching_learn.ipynb
  → 浏览知识树（54个知识点索引表）
  → 选择知识点编号
  → 显示概念讲解（Markdown + LaTeX）
  → 显示配套练习题
  → 查看答案与解析
```

### 测验流程
```
学生打开 quiz_test.ipynb
  → 选择测验模式（综合随机 / 专项知识点）
  → 系统组卷（随机抽题）
  → 学生填写答案
  → 自动批改（字符串匹配）
  → 生成成绩单 + 薄弱知识点分析
  → 错题记入错题本
  → 记录保存到 data/study_record.json
```

### 自动导入流程
```
新 PDF
  │
  ├── 扫描件 → ocr_extract.py → data/xxx_ocr.txt
  │                                    │
  ├── 文字PDF → PyMuPDF 提取 → data/xxx.txt
  │                                    │
  └─────────────────────────────────────┘
                                        │
                                        ↓
                              import_questions.py
                                        │
                           ┌────────────┼────────────┐
                           │            │            │
                       解析题目    分类知识点    评估难度
                           │            │            │
                           └────────────┼────────────┘
                                        │
                                        ↓
                          data/imported_exercises.json
                                        │
                                        ↓
                    knowledge_base.py 启动时自动合并
                         （无需修改任何代码）
```

---

## 关键设计决策

| 决策 | 理由 |
|------|------|
| JSON 而非数据库 | 项目规模小，JSON 足够且无需安装数据库 |
| 内置题目 + 外部 JSON 合并 | 保证基础可用，同时支持无代码扩展 |
| 关键词匹配分类 | 不依赖 LLM API，离线可用，小学数学题目关键词特征明显 |
| 难度 1-3 三级 | 对应基础/中等/困难，适合小学生理解 |
| Notebook 交互 | 教学场景天然适合 cell-by-cell 执行 |
| Streamlit Web 版 | 降低使用门槛，无需 VS Code，浏览器即可访问 |
| 终端不用 emoji | Windows GBK 编码不支持，避免 UnicodeEncodeError |
