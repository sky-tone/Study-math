"""
小升初数学 · 教学与测验系统（独立 Web 版）
==========================================
使用 Streamlit 构建，无需 VS Code，任意浏览器均可访问。

启动方式：
    python -m streamlit run app.py
"""

import sys, os, json, random, hashlib
from datetime import datetime
from collections import Counter, defaultdict

import streamlit as st

# ---------------------------------------------------------------------------
# 路径与数据加载
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from knowledge_base import (
    KNOWLEDGE_TREE, CONCEPTS, EXERCISES,
    get_all_topics, get_concept, get_exercises_by_topic,
)

RECORD_FILE = os.path.join(BASE_DIR, "data", "study_record.json")
IMPORT_FILE = os.path.join(BASE_DIR, "data", "imported_exercises.json")

SOURCE_NAMES = {
    'GZMK数学试卷1_ocr.txt': 'GZMK数学试卷1',
    'GZMK数学试卷2_ocr.txt': 'GZMK数学试卷2',
    '小学数学总复习2022.txt': '小学数学总复习2022',
    'manual_edit': '手动添加',
}


def _source_label(ex):
    s = ex.get('source', '')
    return SOURCE_NAMES.get(s, s) if s else '内置题库'


def _find_source_context(ex, context_lines=5):
    """在源 txt 文件中查找题目原文，返回 (source_file, context_text)"""
    source = ex.get('source', '')
    if not source or source == 'manual_edit':
        return None, None
    src_path = os.path.join(BASE_DIR, 'data', source)
    if not os.path.exists(src_path):
        return source, None
    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return source, None
    q = ex.get('question', '')
    for term in [q[:20], q[:15], q[:10]]:
        term_clean = term.replace(' ', '').replace('\n', '')
        if len(term_clean) < 5:
            continue
        for idx, line in enumerate(lines):
            if term_clean in line.replace(' ', '').strip():
                start = max(0, idx - context_lines)
                end = min(len(lines), idx + context_lines + 1)
                return source, ''.join(lines[start:end])
    return source, None


def load_records():
    if os.path.exists(RECORD_FILE):
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"history": [], "wrong_questions": []}


def save_records(records):
    os.makedirs(os.path.dirname(RECORD_FILE), exist_ok=True)
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def _load_json():
    with open(IMPORT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(data):
    with open(IMPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 知识点索引（全局缓存）
# ---------------------------------------------------------------------------
@st.cache_data
def build_topic_index():
    idx_map = {}
    idx = 1
    for ch in KNOWLEDGE_TREE.values():
        for sec in ch["sections"].values():
            for topic in sec["topics"]:
                idx_map[idx] = topic
                idx += 1
    return idx_map


TOPIC_INDEX = build_topic_index()
TOPIC_LIST = list(TOPIC_INDEX.values())

# 有题目的知识点
TOPICS_WITH_EX = {t: exs for t, exs in EXERCISES.items() if exs}

# ---------------------------------------------------------------------------
# 页面配置
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="小升初数学 · 教学系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 桌面模式：隐藏 Streamlit 自带的菜单栏和部署按钮
# ---------------------------------------------------------------------------
if os.environ.get("STUDY_MATH_DESKTOP"):
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    header[data-testid="stHeader"] {display: none;}
    .stAppDeployButton {display: none;}
    div[data-testid="stDecoration"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 全局样式
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* 卡片通用 */
.card {
    border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 18px 22px; margin: 10px 0; background: #fff;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.card:hover { box-shadow: 0 3px 10px rgba(0,0,0,0.12); }

/* 标签 */
.tag { padding: 2px 10px; border-radius: 12px; font-size: 12px;
    font-weight: 600; color: white; display: inline-block; margin: 0 3px; }
.tag-choice { background: #4299e1; }
.tag-fill { background: #48bb78; }
.tag-judge { background: #ed8936; }
.tag-calc { background: #9f7aea; }
.tag-answer { background: #e53e3e; }
.tag-sort { background: #38b2ac; }
.tag-other { background: #a0aec0; }
.diff-1 { background: #c6f6d5; color: #276749; }
.diff-2 { background: #fefcbf; color: #975a16; }
.diff-3 { background: #fed7d7; color: #9b2c2c; }

/* 横幅 */
.banner {
    color: white; padding: 14px 24px; border-radius: 10px;
    margin: 8px 0 16px 0; font-size: 20px; font-weight: bold;
}
.banner-blue { background: linear-gradient(90deg, #4299e1, #3182ce); }
.banner-green { background: linear-gradient(90deg, #38a169, #2f855a); }
.banner-red { background: linear-gradient(90deg, #e53e3e, #c53030); }
.banner-purple { background: linear-gradient(90deg, #667eea, #764ba2); }
.banner-orange { background: linear-gradient(90deg, #ed8936, #dd6b20); }
.banner-gray { background: linear-gradient(90deg, #4a5568, #718096); }

/* 知识树 */
.tree-table { width: 100%; border-collapse: separate; border-spacing: 0;
    border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    margin-bottom: 12px; }
.tree-table th { background: #edf2f7; color: #4a5568; padding: 8px 14px;
    font-size: 13px; text-align: center; border-bottom: 2px solid #cbd5e0; }
.tree-table td { padding: 7px 14px; font-size: 14px; border-bottom: 1px solid #edf2f7; }
.tree-section { background: #f7fafc; font-weight: bold; color: #2d3748; }

/* 重点记忆 */
.kp-box { background: #fffbeb; border: 1px solid #f6e05e; border-radius: 8px;
    padding: 16px 20px; margin: 16px 0; }
.kp-box .kp-title { color: #b7791f; font-size: 16px; font-weight: bold; margin-bottom: 10px; }

/* 答案卡 */
.ans-card { border: 1px solid #e2e8f0; border-left: 4px solid #48bb78;
    border-radius: 0 10px 10px 0; padding: 16px 22px; margin: 12px 0;
    background: linear-gradient(135deg, #f0fff4 0%, #fff 100%); }
.ans-value { background: #c6f6d5; padding: 6px 14px; border-radius: 6px;
    font-weight: bold; color: #22543d; display: inline-block; margin: 4px 0 8px 0; }

/* 成绩卡 */
.score-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; border-radius: 12px; padding: 24px 30px; margin: 20px 0;
    text-align: center; box-shadow: 0 4px 12px rgba(102,126,234,0.3); }
.score-num { font-size: 48px; font-weight: bold; }
.score-label { font-size: 14px; opacity: 0.9; margin-top: 4px; }
.score-comment { font-size: 16px; margin-top: 12px; }

/* 错题卡 */
.wrong-card { border: 1px solid #fed7d7; border-left: 4px solid #e53e3e;
    border-radius: 0 10px 10px 0; padding: 16px 22px; margin: 10px 0; background: #fff; }

/* 编辑器 */
.ed-old { background: #fed7d7; padding: 2px 8px; border-radius: 4px; text-decoration: line-through; }
.ed-new { background: #c6f6d5; padding: 2px 8px; border-radius: 4px; }

/* 统计 */
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr));
    gap: 12px; margin: 16px 0; }
.stat-item { background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 16px; text-align: center; }
.stat-val { font-size: 28px; font-weight: bold; color: #2d3748; }
.stat-lbl { font-size: 13px; color: #718096; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
TAG_CLS = {"选择": "tag-choice", "填空": "tag-fill", "判断": "tag-judge",
           "计算": "tag-calc", "解答": "tag-answer", "排序": "tag-sort"}
TAG_LBL = {"选择": "选择题", "填空": "填空题", "判断": "判断题",
           "计算": "计算题", "解答": "解答题", "排序": "排序题"}
DIFF_LBL = {1: "基础", 2: "提高", 3: "挑战"}


def _tags_html(ex):
    et = ex.get("type", "解答")
    d = ex.get("difficulty", 1)
    tc = TAG_CLS.get(et, "tag-other")
    tl = TAG_LBL.get(et, et + "题")
    return (f'<span class="tag {tc}">{tl}</span>'
            f'<span class="tag diff-{d}">{DIFF_LBL.get(d, "基础")}</span>')


def _opts_html(ex):
    if not ex.get("options"):
        return ""
    items = "".join(f"<li style='padding:4px 12px;margin:3px 0;"
                    f"background:#f7fafc;border-radius:6px;"
                    f"border:1px solid #edf2f7;font-size:14px;'>{o}</li>"
                    for o in ex["options"])
    return f"<ul style='list-style:none;padding:0;margin:8px 0 0 8px;'>{items}</ul>"


# ============================================================================
# 侧边栏导航
# ============================================================================
with st.sidebar:
    st.title("📚 小升初数学")
    st.caption("教学与测验系统")
    st.divider()
    page = st.radio("导航", [
        "🌳 知识树总览",
        "📖 学习知识点",
        "🧮 公式速查表",
        "🎯 测验系统",
        "📕 错题本",
        "📈 学情分析",
        "✏️ 题目编辑器",
    ], label_visibility="collapsed")

    st.divider()
    total_ex = sum(len(v) for v in EXERCISES.values())
    st.caption(f"知识点：{len(TOPIC_LIST)} 个 · 题目：{total_ex} 道")


# ============================================================================
# 🌳 知识树总览
# ============================================================================
if page == "🌳 知识树总览":
    st.header("🌳 知识树总览")
    st.info("浏览完整知识体系，了解每个知识点的概念和练习覆盖情况。")

    idx = 1
    for ch_id, ch in KNOWLEDGE_TREE.items():
        st.markdown(f'<div class="banner banner-gray">第{ch_id}章 &nbsp;{ch["title"]}</div>',
                    unsafe_allow_html=True)

        rows = ""
        for sec_id, sec in ch["sections"].items():
            rows += f'<tr><td class="tree-section" colspan="4">{sec_id} {sec["title"]}</td></tr>'
            for topic in sec["topics"]:
                has_c = '<span style="color:#38a169">📖 有</span>' if topic in CONCEPTS else '<span style="color:#cbd5e0">—</span>'
                ex_count = len(EXERCISES.get(topic, []))
                has_e = f'<span style="color:#38a169">{ex_count} 题</span>' if ex_count else '<span style="color:#cbd5e0">—</span>'
                rows += (f'<tr><td style="text-align:center;font-weight:bold;color:#4a90d9">{idx}</td>'
                         f'<td>{topic}</td><td style="text-align:center">{has_c}</td>'
                         f'<td style="text-align:center;font-size:13px">{has_e}</td></tr>')
                idx += 1

        st.markdown(f"""
        <table class="tree-table">
          <thead><tr><th style="width:60px">编号</th><th>知识点</th>
            <th style="width:70px">概念</th><th style="width:70px">练习</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>""", unsafe_allow_html=True)

    st.success(f"共 {len(TOPIC_LIST)} 个知识点。前往 **📖 学习知识点** 开始学习！")


# ============================================================================
# 📖 学习知识点
# ============================================================================
elif page == "📖 学习知识点":
    st.header("📖 学习知识点")

    selected_topic = st.selectbox(
        "选择知识点",
        options=TOPIC_LIST,
        format_func=lambda t: f"{TOPIC_LIST.index(t)+1}. {t}",
    )

    if selected_topic:
        # ── 概念讲解 ──
        concept = get_concept(selected_topic)
        if concept:
            st.markdown(concept["explanation"])
            kp_items = "".join(f"<li><b>{i}.</b> {kp}</li>"
                               for i, kp in enumerate(concept["key_points"], 1))
            st.markdown(f"""
            <div class="kp-box">
              <div class="kp-title">🔑 重点记忆</div>
              <ul style="margin:0;padding-left:18px;">{kp_items}</ul>
            </div>""", unsafe_allow_html=True)
        else:
            st.info("该知识点的概念讲解正在编写中...")

        # ── 配套练习 ──
        exercises = get_exercises_by_topic(selected_topic)
        if exercises:
            st.markdown(
                f'<div class="banner banner-green" style="display:flex;justify-content:space-between;">'
                f'<span>📝 配套练习</span><span style="font-size:14px;opacity:0.9">共 {len(exercises)} 题</span></div>',
                unsafe_allow_html=True)
            st.info("💡 先自己做，再展开下方查看答案！")

            for i, ex in enumerate(exercises, 1):
                q_text = ex.get("question", "").replace("\n", "<br>")
                src_lbl = _source_label(ex)
                st.markdown(f"""
                <div class="card">
                  <div style="display:flex;justify-content:space-between;margin-bottom:10px;
                    padding-bottom:8px;border-bottom:1px dashed #e2e8f0;">
                    <span style="font-weight:bold;font-size:16px;color:#2d3748">第 {i} 题</span>
                    <div>{_tags_html(ex)}</div>
                  </div>
                  <div style="font-size:15px;line-height:1.9;color:#1a202c">{q_text}</div>
                  {_opts_html(ex)}
                  <div style="margin-top:8px;padding-top:6px;border-top:1px solid #edf2f7;
                    font-size:12px;color:#a0aec0;">📄 出处：{src_lbl}</div>
                </div>""", unsafe_allow_html=True)

            # 答案折叠
            with st.expander("✅ 查看答案与解析", expanded=False):
                st.markdown(
                    f'<div class="banner banner-green">✅ 【{selected_topic}】答案与解析</div>',
                    unsafe_allow_html=True)
                for i, ex in enumerate(exercises, 1):
                    answer = ex.get("answer", "待补充")
                    explanation = str(ex.get("explanation", "待补充")).replace("\n", "<br>")
                    st.markdown(f"""
                    <div class="ans-card">
                      <div style="display:flex;justify-content:space-between;margin-bottom:8px;
                        padding-bottom:6px;border-bottom:1px dashed #c6f6d5;">
                        <span style="font-weight:bold;color:#276749">第 {i} 题</span>
                        <span style="color:#2f855a;font-weight:bold">答案</span>
                      </div>
                      <div class="ans-value">{answer}</div>
                      <div style="font-size:14px;color:#4a5568;background:#f7fafc;
                        padding:8px 12px;border-radius:6px;margin-top:6px;line-height:1.8;">
                        <b>解析：</b>{explanation}</div>
                    </div>""", unsafe_allow_html=True)
        else:
            st.info("该知识点的练习题正在编写中...")


# ============================================================================
# 🧮 公式速查表
# ============================================================================
elif page == "🧮 公式速查表":
    st.header("🧮 公式速查表")
    st.markdown(r"""
## 一、数与代数

| 公式 | 表达式 |
|------|--------|
| 分数基本性质 | $\frac{a}{b} = \frac{a \times n}{b \times n}$ |
| 加法交换律 | $a + b = b + a$ |
| 加法结合律 | $(a+b)+c = a+(b+c)$ |
| 乘法交换律 | $a \times b = b \times a$ |
| 乘法结合律 | $(a \times b) \times c = a \times (b \times c)$ |
| 乘法分配律 | $(a+b) \times c = ac + bc$ |
| 比例基本性质 | $a:b = c:d \Rightarrow ad = bc$ |
| 正比例 | $\frac{y}{x} = k$（比值不变）|
| 反比例 | $x \times y = k$（乘积不变）|

## 二、图形与几何

### 平面图形
| 图形 | 周长 | 面积 |
|------|------|------|
| 长方形 | $C = 2(a+b)$ | $S = ab$ |
| 正方形 | $C = 4a$ | $S = a^2$ |
| 平行四边形 | — | $S = ah$ |
| 三角形 | — | $S = \frac{1}{2}ah$ |
| 梯形 | — | $S = \frac{1}{2}(a+b)h$ |
| 圆 | $C = 2\pi r$ | $S = \pi r^2$ |

### 立体图形
| 图形 | 表面积 | 体积 |
|------|--------|------|
| 长方体 | $S = 2(ab+bh+ah)$ | $V = abh$ |
| 正方体 | $S = 6a^2$ | $V = a^3$ |
| 圆柱 | $S = 2\pi rh + 2\pi r^2$ | $V = \pi r^2 h$ |
| 圆锥 | — | $V = \frac{1}{3}\pi r^2 h$ |

## 三、统计
$$\text{平均数} = \frac{\text{总数}}{\text{份数}}$$

## 四、行程与工程
| 公式 | 表达式 |
|------|--------|
| 路程 | $s = vt$ |
| 相遇问题 | $s = (v_1 + v_2) \times t$ |
| 工程问题 | $\frac{1}{t_1} + \frac{1}{t_2} = \frac{1}{t_{\text{合}}}$ |
""")


# ============================================================================
# 🎯 测验系统
# ============================================================================
elif page == "🎯 测验系统":
    st.header("🎯 测验系统")

    # 初始化 session_state
    if "quiz_state" not in st.session_state:
        st.session_state.quiz_state = "setup"  # setup / answering / graded
    if "quiz_questions" not in st.session_state:
        st.session_state.quiz_questions = []

    # ── 设置面板 ──
    col1, col2 = st.columns([2, 1])
    with col1:
        topic_options = ["🎲 综合随机测验（所有知识点）"] + [
            f"{t}（{len(exs)}题）" for t, exs in TOPICS_WITH_EX.items()
        ]
        mode_sel = st.selectbox("测验范围", topic_options)
    with col2:
        num_q = st.slider("题目数量", 3, 20, 5)

    if st.button("🚀 开始测验", type="primary", use_container_width=True):
        # 组卷
        if mode_sel.startswith("🎲"):
            pool = []
            for t, exs in TOPICS_WITH_EX.items():
                for ex in exs:
                    pool.append({**ex, "_topic": t})
            title = "综合随机测验"
        else:
            t_name = mode_sel.split("（")[0]
            pool = [{**ex, "_topic": t_name} for ex in EXERCISES.get(t_name, [])]
            title = f"专项测验：{t_name}"

        if pool:
            st.session_state.quiz_questions = random.sample(pool, min(num_q, len(pool)))
            st.session_state.quiz_title = title
            st.session_state.quiz_state = "answering"
            st.rerun()

    # ── 答题界面 ──
    if st.session_state.quiz_state == "answering":
        qs = st.session_state.quiz_questions
        title = st.session_state.quiz_title
        st.markdown(
            f'<div class="banner banner-red" style="display:flex;justify-content:space-between;">'
            f'<span>🎯 {title}</span>'
            f'<span style="font-size:14px;opacity:0.9">共 {len(qs)} 题</span></div>',
            unsafe_allow_html=True)

        answers = []
        for i, q in enumerate(qs):
            q_text = q.get("question", "").replace("\n", "<br>")
            st.markdown(f"""
            <div class="card">
              <div style="display:flex;justify-content:space-between;margin-bottom:10px;
                padding-bottom:8px;border-bottom:1px dashed #e2e8f0;">
                <div><span style="font-weight:bold;font-size:16px;color:#2d3748">第 {i+1} 题</span>
                  <span style="font-size:12px;color:#718096;background:#edf2f7;
                    padding:2px 10px;border-radius:10px;margin-left:8px">{q.get('_topic','')}</span></div>
                <div>{_tags_html(q)}</div>
              </div>
              <div style="font-size:15px;line-height:1.9;color:#1a202c">{q_text}</div>
              {_opts_html(q)}
            </div>""", unsafe_allow_html=True)

            ans = st.text_input(f"第 {i+1} 题答案", key=f"ans_{i}",
                                placeholder="输入你的答案...")
            answers.append(ans)

        if st.button("📝 提交批改", type="primary", use_container_width=True):
            st.session_state.user_answers = answers
            st.session_state.quiz_state = "graded"
            st.rerun()

    # ── 批改结果 ──
    if st.session_state.quiz_state == "graded":
        qs = st.session_state.quiz_questions
        answers = st.session_state.user_answers
        title = st.session_state.quiz_title

        correct_count = 0
        wrong_list = []
        cards_html = ""

        for i, q in enumerate(qs):
            student = answers[i].strip() if i < len(answers) else ""
            correct = str(q.get("answer", "")).strip()
            is_correct = student.replace(" ", "").lower() == correct.replace(" ", "").lower()

            if is_correct:
                correct_count += 1
                cls = "border-left:4px solid #48bb78; background:linear-gradient(135deg,#f0fff4,#fff);"
                icon = "✅"
                expl = ""
            else:
                cls = "border-left:4px solid #e53e3e; background:linear-gradient(135deg,#fff5f5,#fff);"
                icon = "❌"
                wrong_list.append(q)
                exp = str(q.get("explanation", "待补充")).replace("\n", "<br>")
                expl = f'<div style="font-size:14px;color:#4a5568;background:#f7fafc;padding:8px 12px;border-radius:6px;margin-top:8px;line-height:1.8;"><b>解析：</b>{exp}</div>'

            cards_html += f"""
            <div class="card" style="{cls}">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <span style="font-size:22px">{icon}</span>
                <span style="font-weight:bold">第 {i+1} 题</span>
                <span style="font-size:12px;color:#718096;background:#edf2f7;
                  padding:2px 10px;border-radius:10px;">{q.get('_topic','')}</span>
              </div>
              <div style="font-size:14px;color:#4a5568;margin-bottom:6px;">{q.get('question','')[:120]}</div>
              <div><b>你的答案：</b><span style="color:#4299e1">{student if student else '（未作答）'}</span></div>
              <div><b>正确答案：</b><span style="color:#38a169">{correct}</span></div>
              {expl}
            </div>"""

        total = len(qs)
        score = round(correct_count / total * 100) if total else 0
        if score == 100:
            comment, emoji = "完美！全部正确！", "🏆"
        elif score >= 80:
            comment, emoji = "很棒！再看看错题就更好了！", "👍"
        elif score >= 60:
            comment, emoji = "继续努力！建议复习出错的知识点。", "💪"
        else:
            comment, emoji = "需要加油哦！建议重新学习相关知识点。", "📖"

        weak_html = ""
        if wrong_list:
            topics_str = "、".join(set(q["_topic"] for q in wrong_list))
            weak_html = f'<div style="margin-top:12px;font-size:14px;opacity:0.9;">薄弱知识点：{topics_str}</div>'

        st.markdown(f"""
        <div class="score-card">
          <div class="score-num">{score}</div>
          <div class="score-label">正确 {correct_count} / {total} 题</div>
          <div class="score-comment">{emoji} {comment}</div>
          {weak_html}
        </div>""", unsafe_allow_html=True)
        st.markdown(cards_html, unsafe_allow_html=True)

        # 保存记录
        records = load_records()
        records["history"].append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "mode": title,
            "total": total,
            "correct": correct_count,
            "score": score,
            "wrong_topics": list(set(q["_topic"] for q in wrong_list)),
        })
        for q in wrong_list:
            wr = {
                "id": q["id"], "topic": q["_topic"],
                "question": q["question"], "correct_answer": q["answer"],
                "explanation": q.get("explanation", ""), "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            if not any(w["id"] == q["id"] for w in records["wrong_questions"]):
                records["wrong_questions"].append(wr)
        save_records(records)
        st.success("测验记录已保存！")

        if st.button("🔄 再来一次", use_container_width=True):
            st.session_state.quiz_state = "setup"
            st.rerun()


# ============================================================================
# 📕 错题本
# ============================================================================
elif page == "📕 错题本":
    st.header("📕 错题本")
    records = load_records()
    wrong_qs = records.get("wrong_questions", [])

    if not wrong_qs:
        st.success("🎉 错题本为空！你还没有做错过题目，继续保持！")
    else:
        st.markdown(
            f'<div class="banner banner-red" style="display:flex;justify-content:space-between;">'
            f'<span>📕 错题本</span>'
            f'<span style="font-size:14px;opacity:0.9">共 {len(wrong_qs)} 题</span></div>',
            unsafe_allow_html=True)

        grouped = defaultdict(list)
        for q in wrong_qs:
            grouped[q["topic"]].append(q)

        for topic, questions in grouped.items():
            with st.expander(f"📌 {topic}（{len(questions)} 题）", expanded=True):
                for q in questions:
                    exp = str(q.get("explanation", "待补充")).replace("\n", "<br>")
                    st.markdown(f"""
                    <div class="wrong-card">
                      <div style="font-size:14px;line-height:1.8;color:#2d3748;margin-bottom:10px;">
                        <b>题目 {q['id']}：</b>{q['question'][:200]}</div>
                      <div><span class="ans-value">正确答案：{q['correct_answer']}</span></div>
                      <div style="font-size:13px;color:#718096;margin-top:8px;line-height:1.7;">解析：{exp}</div>
                      <div style="font-size:12px;color:#a0aec0;text-align:right;margin-top:6px;">
                        记录时间：{q['date']}</div>
                    </div>""", unsafe_allow_html=True)

        st.divider()
        if st.button("🗑️ 清空错题本", type="secondary"):
            records["wrong_questions"] = []
            save_records(records)
            st.success("错题本已清空！")
            st.rerun()


# ============================================================================
# 📈 学情分析
# ============================================================================
elif page == "📈 学情分析":
    st.header("📈 学情分析")
    records = load_records()
    history = records.get("history", [])

    if not history:
        st.info("还没有测验记录，完成一次测验后再来查看！")
    else:
        st.markdown('<div class="banner banner-purple">📈 学情分析报告</div>',
                    unsafe_allow_html=True)

        total_tests = len(history)
        total_qs = sum(h["total"] for h in history)
        total_correct = sum(h["correct"] for h in history)
        avg_score = round(sum(h["score"] for h in history) / total_tests)
        rate = round(total_correct / total_qs * 100)

        st.markdown(f"""
        <div class="stat-grid">
          <div class="stat-item"><div class="stat-val">{total_tests}</div><div class="stat-lbl">测验次数</div></div>
          <div class="stat-item"><div class="stat-val">{total_qs}</div><div class="stat-lbl">总做题数</div></div>
          <div class="stat-item"><div class="stat-val">{rate}%</div><div class="stat-lbl">总正确率</div></div>
          <div class="stat-item"><div class="stat-val">{avg_score}</div><div class="stat-lbl">平均分</div></div>
        </div>""", unsafe_allow_html=True)

        # 薄弱知识点
        wrong_counter = Counter()
        for h in history:
            for t in h.get("wrong_topics", []):
                wrong_counter[t] += 1

        if wrong_counter:
            st.subheader("⚠️ 薄弱知识点排行")
            rows = ""
            for rank, (topic, count) in enumerate(wrong_counter.most_common(), 1):
                if count >= 3:
                    badge = '<span style="color:#e53e3e;font-weight:bold;">🔴 急需复习</span>'
                elif count >= 2:
                    badge = '<span style="color:#d69e2e;font-weight:bold;">🟡 建议复习</span>'
                else:
                    badge = '<span style="color:#38a169;">🟢 偶尔出错</span>'
                rows += f"<tr><td style='text-align:center'>{rank}</td><td>{topic}</td><td style='text-align:center'>{count}</td><td style='text-align:center'>{badge}</td></tr>"

            st.markdown(f"""
            <table class="tree-table">
              <thead><tr><th style="width:50px">排名</th><th>知识点</th>
                <th style="width:80px">出错次数</th><th style="width:100px">建议</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>""", unsafe_allow_html=True)

        # 历次记录
        st.subheader("📅 历次测验记录")
        hist_rows = ""
        for h in reversed(history[-10:]):
            s = h["score"]
            sc = "#38a169" if s >= 80 else ("#d69e2e" if s >= 60 else "#e53e3e")
            hist_rows += (f'<tr><td style="text-align:center">{h["date"]}</td>'
                          f'<td>{h["mode"]}</td>'
                          f'<td style="text-align:center">{h["correct"]}/{h["total"]}</td>'
                          f'<td style="text-align:center;color:{sc};font-weight:bold;">{s}分</td></tr>')

        st.markdown(f"""
        <table class="tree-table">
          <thead><tr><th>日期</th><th>模式</th><th>正确/总题</th><th>得分</th></tr></thead>
          <tbody>{hist_rows}</tbody>
        </table>""", unsafe_allow_html=True)

        # 趋势
        if len(history) >= 3:
            recent = [h["score"] for h in history[-3:]]
            earlier = [h["score"] for h in history[:3]]
            trend = sum(recent) / 3 - sum(earlier) / 3
            if trend > 5:
                st.success(f"📈 进步趋势：+{trend:.0f}分，你在进步！继续保持！")
            elif trend < -5:
                st.warning(f"📉 成绩有所下降（{trend:.0f}分），建议回顾薄弱知识点。")
            else:
                st.info("➡️ 成绩稳定，继续努力向满分冲刺！")


# ============================================================================
# ✏️ 题目编辑器
# ============================================================================
elif page == "✏️ 题目编辑器":
    st.header("✏️ 题目编辑器")

    action = st.radio("操作", ["📋 查看", "✏️ 编辑", "➕ 添加", "🗑️ 删除"], horizontal=True)

    sel_topic = st.selectbox(
        "选择知识点",
        options=TOPIC_LIST,
        format_func=lambda t: f"{TOPIC_LIST.index(t)+1}. {t}",
        key="ed_topic",
    )
    exs = get_exercises_by_topic(sel_topic)

    # ── 查看 ──
    if action == "📋 查看":
        st.markdown(
            f'<div class="banner banner-blue">📋 查看【{sel_topic}】的题目（共 {len(exs)} 题）</div>',
            unsafe_allow_html=True)

        if not exs:
            st.info("该知识点暂无题目。")
        else:
            for i, ex in enumerate(exs, 1):
                opts = ""
                if ex.get("options"):
                    opts = "<br>".join(f"&nbsp;&nbsp;{o}" for o in ex["options"])
                    opts = f"<div><b>选项：</b><br>{opts}</div>"
                q_text = ex.get("question", "").replace("\n", "<br>")
                st.markdown(f"""
                <div class="card">
                  <div style="margin-bottom:6px;">
                    <b>序号：</b>{i} &nbsp;&nbsp;
                    <b>ID：</b><code>{ex.get('id','?')}</code> &nbsp;&nbsp;
                    <b>类型：</b>{ex.get('type','?')} &nbsp;&nbsp;
                    <b>难度：</b>{ex.get('difficulty','?')}
                  </div>
                  <div style="margin:8px 0;line-height:1.8;"><b>题目：</b>{q_text}</div>
                  {opts}
                  <div><b>答案：</b>{ex.get('answer','待补充')}</div>
                  <div style="color:#718096"><b>解析：</b>{ex.get('explanation','待补充')}</div>
                  <div style="color:#a0aec0;font-size:12px;margin-top:6px;padding-top:6px;
                    border-top:1px solid #edf2f7;">📄 出处：{_source_label(ex)}</div>
                </div>""", unsafe_allow_html=True)

    # ── 编辑 ──
    elif action == "✏️ 编辑":
        st.markdown(
            f'<div class="banner banner-orange">✏️ 编辑【{sel_topic}】的题目</div>',
            unsafe_allow_html=True)

        if not exs:
            st.warning("该知识点暂无题目。")
        else:
            ex_idx = st.selectbox(
                "选择题目",
                options=list(range(len(exs))),
                format_func=lambda i: f"第 {i+1} 题 — {exs[i].get('question','')[:50]}...",
            )
            ex = exs[ex_idx]

            # 原文对照
            src_file, src_context = _find_source_context(ex)
            if src_file:
                with st.expander(f"📄 原文对照 — {SOURCE_NAMES.get(src_file, src_file)}", expanded=False):
                    if src_context:
                        st.code(src_context, language=None)
                    else:
                        st.caption("未在源文件中找到匹配的原文段落")

            with st.form("edit_form"):
                new_q = st.text_area("题目内容", value=ex.get("question", ""), height=120)
                c1, c2 = st.columns(2)
                with c1:
                    new_type = st.selectbox("题型", ["选择", "填空", "判断", "计算", "解答", "排序"],
                                            index=["选择", "填空", "判断", "计算", "解答", "排序"].index(
                                                ex.get("type", "解答")))
                with c2:
                    new_diff = st.selectbox("难度", [1, 2, 3],
                                            index=ex.get("difficulty", 1) - 1,
                                            format_func=lambda d: f"{d} - {DIFF_LBL[d]}")
                new_ans = st.text_input("答案", value=str(ex.get("answer", "")))
                new_exp = st.text_area("解析", value=str(ex.get("explanation", "")), height=80)
                new_opts_str = st.text_area(
                    "选项（每行一个，留空表示无选项）",
                    value="\n".join(ex.get("options", [])),
                    height=80,
                )
                submitted = st.form_submit_button("💾 保存修改", type="primary",
                                                   use_container_width=True)

            if submitted:
                ex_id = ex.get("id", "")
                data = _load_json()
                changed = False
                opts = [l.strip() for l in new_opts_str.strip().split("\n") if l.strip()]

                # 先尝试在 JSON 中找到并修改
                if sel_topic in data:
                    for jex in data[sel_topic]:
                        if jex.get("id") == ex_id:
                            jex["question"] = new_q
                            jex["type"] = new_type
                            jex["difficulty"] = new_diff
                            jex["answer"] = new_ans
                            jex["explanation"] = new_exp
                            if opts:
                                jex["options"] = opts
                            elif "options" in jex:
                                del jex["options"]
                            changed = True
                            break

                if not changed:
                    # 内置题目：将修改后的完整副本写入 JSON 作为覆盖
                    updated_ex = dict(ex)
                    updated_ex["question"] = new_q
                    updated_ex["type"] = new_type
                    updated_ex["difficulty"] = new_diff
                    updated_ex["answer"] = new_ans
                    updated_ex["explanation"] = new_exp
                    if opts:
                        updated_ex["options"] = opts
                    elif "options" in updated_ex:
                        del updated_ex["options"]
                    if sel_topic not in data:
                        data[sel_topic] = []
                    data[sel_topic].append(updated_ex)
                    changed = True

                _save_json(data)
                # 同步内存
                ex["question"] = new_q
                ex["type"] = new_type
                ex["difficulty"] = new_diff
                ex["answer"] = new_ans
                ex["explanation"] = new_exp
                if opts:
                    ex["options"] = opts
                elif "options" in ex:
                    del ex["options"]
                st.success("✅ 已保存修改！")
                st.rerun()

    # ── 添加 ──
    elif action == "➕ 添加":
        st.markdown(
            f'<div class="banner banner-green">➕ 向【{sel_topic}】添加新题目</div>',
            unsafe_allow_html=True)

        with st.form("add_form"):
            new_q = st.text_area("题目内容", height=120, placeholder="输入题目...")
            c1, c2 = st.columns(2)
            with c1:
                new_type = st.selectbox("题型", ["选择", "填空", "判断", "计算", "解答", "排序"])
            with c2:
                new_diff = st.selectbox("难度", [1, 2, 3],
                                        format_func=lambda d: f"{d} - {DIFF_LBL[d]}")
            new_ans = st.text_input("答案", placeholder="输入正确答案...")
            new_exp = st.text_area("解析", height=80, placeholder="输入解题过程...")
            new_opts_str = st.text_area("选项（每行一个，非选择题留空）", height=80)
            submitted = st.form_submit_button("➕ 添加题目", type="primary",
                                               use_container_width=True)

        if submitted:
            if not new_q.strip():
                st.error("请填写题目内容！")
            else:
                new_id = "IMP-" + hashlib.md5(new_q.encode()).hexdigest()[:6].upper()
                new_ex = {
                    "id": new_id, "type": new_type, "difficulty": new_diff,
                    "question": new_q, "answer": new_ans or "(待补充)",
                    "explanation": new_exp or "(待补充)", "source": "manual_edit",
                }
                opts = [l.strip() for l in new_opts_str.strip().split("\n") if l.strip()]
                if opts:
                    new_ex["options"] = opts

                data = _load_json()
                if sel_topic not in data:
                    data[sel_topic] = []
                data[sel_topic].append(new_ex)
                _save_json(data)

                if sel_topic not in EXERCISES:
                    EXERCISES[sel_topic] = []
                EXERCISES[sel_topic].append(new_ex)
                st.success(f"✅ 已添加！【{sel_topic}】现有 {len(EXERCISES.get(sel_topic, []))} 题")
                st.rerun()

    # ── 删除 ──
    elif action == "🗑️ 删除":
        st.markdown(
            f'<div class="banner banner-red">🗑️ 删除【{sel_topic}】的题目</div>',
            unsafe_allow_html=True)

        if not exs:
            st.warning("该知识点暂无题目。")
        else:
            ex_idx = st.selectbox(
                "选择要删除的题目",
                options=list(range(len(exs))),
                format_func=lambda i: f"第 {i+1} 题 — {exs[i].get('question','')[:60]}...",
            )
            ex = exs[ex_idx]
            st.markdown(f"""
            <div class="card" style="border-left:4px solid #e53e3e;">
              <div style="line-height:1.8;"><b>题目：</b>{ex.get('question','')[:200]}</div>
              <div><b>答案：</b>{ex.get('answer','待补充')}</div>
            </div>""", unsafe_allow_html=True)

            if st.button("⚠️ 确认删除", type="primary"):
                ex_id = ex.get("id", "")
                data = _load_json()
                deleted = False

                # 尝试从 JSON 中删除
                if sel_topic in data:
                    before = len(data[sel_topic])
                    data[sel_topic] = [e for e in data[sel_topic] if e.get("id") != ex_id]
                    if len(data[sel_topic]) < before:
                        if not data[sel_topic]:
                            del data[sel_topic]
                        deleted = True

                if not deleted:
                    # 内置题目：添加到删除标记列表
                    if "_deleted" not in data:
                        data["_deleted"] = []
                    if ex_id and ex_id not in data["_deleted"]:
                        data["_deleted"].append(ex_id)

                _save_json(data)
                EXERCISES[sel_topic] = [e for e in EXERCISES.get(sel_topic, [])
                                        if e.get("id") != ex_id]
                st.success(f"✅ 已删除！【{sel_topic}】剩余 {len(EXERCISES.get(sel_topic, []))} 题")
                st.rerun()
