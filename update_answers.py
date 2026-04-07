"""
GZMK 数学答案匹配工具 v3

核心策略：
1. 解析每个源文件，提取 (试卷名, 题型, 题号, 题目正文) 完整列表
2. 解析答案文件，建立 {试卷名: [(section, num, answer)]} 映射
3. 对每道导入题目，通过文本相似度匹配到源文件中的编号题目
4. 用匹配到的 (试卷名, section, 题号) 查答案

关键改进：不再依赖字符偏移位置（归一化文本偏移 vs 原文偏移不兼容），
         而是直接对比题目正文。
"""

import json
import re
import os
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)


# ============================================================
# 常量
# ============================================================

PAPER_NAMES_ANS = {
    1: "大奥", 2: "省实本部", 3: "天执", 4: "六中海珠",
    5: "花雅", 6: "广中小创", 7: "黄埔广附", 8: "黄埔军校",
    9: "黄埔铁英", 10: "金广附", 11: "荔省", 12: "南沙广附",
    13: "五中", 14: "白云实验", 15: "华初", 16: "华新",
    17: "明德", 18: "南沙朝阳", 19: "白云华赋", 20: "暨大附",
    21: "培英", 22: "广州实验", 23: "65中", 24: "六中花都",
    25: "番禺华附", 26: "为明",
}

PAPER_KEYWORDS = sorted([
    "大奥", "省实本部", "天执", "六中海珠", "花雅", "广中小创",
    "黄埔广附", "黄埔军校", "黄埔铁英", "金广附", "荔省", "南沙广附",
    "五中", "白云实验", "华初", "华新", "明德", "南沙朝阳",
    "白云华赋", "暨大附", "培英", "广州实验", "65中", "六中花都",
    "番禺华附", "为明",
], key=len, reverse=True)


# ============================================================
# 1. 解析答案
# ============================================================

def parse_answer_text(answer_file):
    """解析答案文本，返回 {试卷名: [(section, num, answer), ...]}"""
    with open(answer_file, "r", encoding="utf-8") as f:
        text = f.read()

    lines = text.strip().split("\n")
    result = {}
    current_paper = None
    current_section = "未知"

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 试卷标题: "1. 大奥", "25 番禺华附"
        m = re.match(r"^(\d+)[.\s、]+(.+)$", line)
        if m:
            num = int(m.group(1))
            rest = m.group(2).strip()
            if num in PAPER_NAMES_ANS:
                pname = PAPER_NAMES_ANS[num]
                if pname in rest or rest in pname or pname[:2] in rest:
                    current_paper = pname
                    result[current_paper] = []
                    current_section = "未知"
                    continue

        if current_paper is None:
            continue

        # 题型段落
        sec_match = re.match(
            r"^(填空题\d?|选择题|计算题|判断题|解答题|解决问题|解方程|应用题|"
            r"计算|填空|选择|判断|解答|简答题|实操题|面积计算|图形计算|"
            r"第[一二三]部分|求X)", line)
        if sec_match:
            sec = sec_match.group(1)
            if "填空" in sec:
                current_section = "填空"
            elif "选择" in sec:
                current_section = "选择"
            elif "判断" in sec:
                current_section = "判断"
            elif sec in ("计算题", "计算", "解方程", "求X", "图形计算", "面积计算"):
                current_section = "计算"
            elif sec in ("解答题", "解决问题", "应用题", "简答题", "实操题", "解答"):
                current_section = "解答"
            elif "第二部分" in sec:
                current_section = "第二部分"
            else:
                current_section = sec
            continue

        # 子问题答案: 追加到上一个答案
        if re.match(r"^[（(]\d+[）)]", line):
            if result.get(current_paper) and result[current_paper]:
                last = result[current_paper][-1]
                result[current_paper][-1] = (last[0], last[1],
                                              last[2] + "; " + line)
            continue

        # 批量选择题: "1-5：ADBCB" 或 "9.1–5：BCBBB"
        multi_batch = re.findall(
            r"(\d+)[\-\u2013~](\d+)[：:]\s*([A-D]{2,})", line)
        if multi_batch:
            for start_s, end_s, choices in multi_batch:
                start = int(start_s)
                for j, ch in enumerate(choices):
                    result[current_paper].append(("选择", start + j, ch))
            continue

        # 标准答案行: "1、49" "2、66"
        ans_m = re.match(r"^(\d+)[、.\s,，:：]+(.+)$", line)
        if ans_m:
            qnum = int(ans_m.group(1))
            ans_text = ans_m.group(2).strip()
            # 判断题答案: × √ 对 错
            if ans_text in ("×", "√", "对", "错", "V", "X"):
                result[current_paper].append(
                    (current_section, qnum, ans_text))
                continue
            clean = re.sub(r"[^\u4e00-\u9fa5\dA-Za-z/%.+\-]", "", ans_text)
            if len(clean) >= 1:
                result[current_paper].append(
                    (current_section, qnum, ans_text))

    return result


# ============================================================
# 2. 解析源文件 —— 提取编号题目及正文
# ============================================================

def normalize(s):
    """规范化文本：去空白、标点"""
    s = re.sub(r"\s+", "", s)
    s = re.sub(
        r"[（()）\[\]{}「」【】,，.。:：;；!！?？、''""'\"*\u3000·]", "", s)
    return s


def parse_source_questions(text_file):
    """
    解析源文件，提取每道编号题目。
    返回 [(paper, section, qnum, body_text), ...]
    body_text 是题号后面的正文内容（可能跨多行）。
    """
    with open(text_file, "r", encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    current_paper = None
    current_section = "未知"
    questions = []   # (paper, section, qnum, body_lines)
    current_q = None  # (paper, section, qnum, [lines])

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 检测试卷标题
        found_paper = None
        for kw in PAPER_KEYWORDS:
            if kw in stripped and len(stripped) < 100:
                found_paper = kw
                break
        if found_paper:
            # 保存之前的题目
            if current_q:
                questions.append(current_q)
                current_q = None
            current_paper = found_paper
            current_section = "未知"
            continue

        if current_paper is None:
            # 试卷2.txt 开头有几道没有标题的题
            # 尝试检测题号
            q_m = re.match(r"^(\d+)[、.．\s)）\uff09]\s*(.*)$", stripped)
            if q_m and 1 <= int(q_m.group(1)) <= 50:
                if current_q:
                    questions.append(current_q)
                qnum = int(q_m.group(1))
                body = q_m.group(2)
                current_q = ("__orphan__", "未知", qnum, [body] if body else [])
            elif current_q:
                current_q[3].append(stripped)
            continue

        # 检测题型段落
        sec_m = re.match(
            r"^[一二三四五六七八九十]+[、.\s]\s*"
            r"(填空题|选择题|计算题|判断题|解答题|解决问题|应用题|解方程|"
            r"简答题|火眼金睛|动动脑筋|看谁算得|巧设未知数|用心解答|"
            r"计算|填空|选择|判断|解答|仔细计算|认真填|操作|"
            r"加深理解|挑战自我|第[一二]部分)", stripped)
        if sec_m:
            if current_q:
                questions.append(current_q)
                current_q = None
            sec = sec_m.group(1)
            if "填空" in sec or "脑筋" in sec or "认真填" in sec:
                current_section = "填空"
            elif "选择" in sec or "火眼" in sec:
                current_section = "选择"
            elif "判断" in sec:
                current_section = "判断"
            elif any(k in sec for k in ["计算", "解方程", "看谁", "仔细"]):
                current_section = "计算"
            else:
                current_section = "解答"
            continue

        # 检测题号开始 (支持各种分隔符：1、1. 1．1) 1）等)
        q_m = re.match(r"^(\d+)[、.．\s)）\uff09]\s*(.*)$", stripped)
        if q_m:
            qnum = int(q_m.group(1))
            if 1 <= qnum <= 50:
                if current_q:
                    questions.append(current_q)
                body = q_m.group(2)
                current_q = (current_paper, current_section, qnum,
                             [body] if body else [])
                continue

        # 续行：追加到当前题目
        if current_q:
            current_q[3].append(stripped)

    if current_q:
        questions.append(current_q)

    # 把 body_lines 合并为单一字符串
    result = []
    for paper, sec, qnum, body_lines in questions:
        body = "\n".join(body_lines).strip()
        result.append((paper, sec, qnum, body))

    return result


# ============================================================
# 3. 匹配：导入题目 → 源文件编号题目
# ============================================================

def text_similarity(a, b):
    """
    计算两段文本的相似度分数。
    核心：检查归一化文本的公共前缀长度。
    """
    a_n = normalize(a)
    b_n = normalize(b)
    if not a_n or not b_n:
        return 0.0

    shorter = min(len(a_n), len(b_n))
    if shorter < 3:
        return 0.0

    # 方法1：直接前缀匹配
    prefix_len = 0
    for i in range(shorter):
        if a_n[i] == b_n[i]:
            prefix_len += 1
        else:
            break

    if prefix_len >= 6:
        return prefix_len / shorter

    # 方法2：子串搜索（处理导入时开头被截断的情况）
    best = 0
    # 用较短文本在较长文本中搜索（从长子串到短子串）
    short_t = a_n if len(a_n) <= len(b_n) else b_n
    long_t = b_n if len(a_n) <= len(b_n) else a_n

    # 尝试短文本的各种起始位置
    for start in range(0, min(len(short_t), 20), 2):
        end = min(len(short_t), start + 50)
        snippet = short_t[start:end]
        while len(snippet) >= 6:
            if snippet in long_t:
                best = max(best, len(snippet))
                break
            snippet = snippet[:-1]

    return best / shorter if shorter > 0 else 0


def find_best_match(q_text, source_questions, threshold=0.35):
    """
    在源文件编号题目列表中找到与导入题目最匹配的条目。
    返回 (paper, section, qnum, score) 或 None
    """
    q_norm = normalize(q_text)
    if len(q_norm) < 3:
        return None

    best_score = 0
    best_match = None

    for paper, sec, qnum, body in source_questions:
        score = text_similarity(q_text, body)
        if score > best_score:
            best_score = score
            best_match = (paper, sec, qnum, score)

    if best_match and best_score >= threshold:
        return best_match
    return None


# ============================================================
# 4. 答案查找
# ============================================================

def find_answer(ans_list, section, qnum, q_type):
    """
    在答案列表中查找匹配的答案。
    优先使用源文件索引中的 section（比导入的 q_type 更可靠）。
    """
    # 1. 最高优先：源文件索引的 section + num（最可靠）
    if section != "未知":
        for sec, num, ans in ans_list:
            if sec == section and num == qnum:
                return ans

    # 2. 使用导入的 q_type 推断 section
    type_to_sec = {
        "选择": "选择", "填空": "填空", "判断": "判断",
        "计算": "计算", "解答": "解答", "排序": "填空",
    }
    target_sec = type_to_sec.get(q_type, "")
    if target_sec and target_sec != section:
        for sec, num, ans in ans_list:
            if sec == target_sec and num == qnum:
                return ans

    # 3. 全局编号的试卷（答案全在"未知"section）
    for sec, num, ans in ans_list:
        if sec == "未知" and num == qnum:
            return ans

    # 4. 任意section中相同num（类型匹配优先）
    for sec, num, ans in ans_list:
        if num == qnum:
            if q_type == "选择" and re.match(r"^[A-D]$", ans.strip()):
                return ans
            elif q_type != "选择" and not re.match(r"^[A-D]$", ans.strip()):
                return ans

    # 5. 最后尝试
    for sec, num, ans in ans_list:
        if num == qnum:
            return ans

    return None


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("  GZMK 数学答案匹配工具 v3")
    print("=" * 60)

    # 1. 解析答案
    answers = parse_answer_text("data/GZMK数学答案.txt")
    total_ans = sum(len(v) for v in answers.values())
    print(f"\n[1] 解析答案: {len(answers)} 套试卷, {total_ans} 个答案")

    # 打印每套试卷答案数
    for pname, alist in answers.items():
        secs = defaultdict(int)
        for sec, num, ans in alist:
            secs[sec] += 1
        sec_str = ", ".join(f"{k}:{v}" for k, v in secs.items())
        print(f"    {pname}: {len(alist)} ({sec_str})")

    # 2. 加载题库
    with open("data/imported_exercises.json", "r", encoding="utf-8") as f:
        exercises = json.load(f)

    all_q = []
    for topic, qs in exercises.items():
        for q in qs:
            all_q.append(q)
    print(f"\n[2] 题库: {len(all_q)} 道题")

    # 3. 处理每个源文件
    source_files = [
        ("GZMK数学试卷1.txt", "data/GZMK数学试卷1.txt", "大奥"),
        ("GZMK数学试卷1_ocr.txt", "data/GZMK数学试卷1_ocr.txt", "大奥"),
        ("GZMK数学试卷2.txt", "data/GZMK数学试卷2.txt", "番禺华附"),
        ("GZMK数学试卷2_ocr.txt", "data/GZMK数学试卷2_ocr.txt", "番禺华附"),
    ]

    matched_total = 0
    unmatched_total = 0

    for src_name, src_path, default_paper in source_files:
        if not os.path.exists(src_path):
            continue

        src_questions = [q for q in all_q if q.get("source") == src_name]
        if not src_questions:
            continue

        # 解析源文件的编号题目
        ref_questions = parse_source_questions(src_path)

        # 将 __orphan__ 替换为默认试卷名
        ref_questions = [
            (default_paper if p == "__orphan__" else p, sec, qnum, body)
            for p, sec, qnum, body in ref_questions
        ]

        # 按试卷统计
        paper_count = defaultdict(int)
        for paper, sec, qnum, body in ref_questions:
            paper_count[paper] += 1

        print(f"\n[3] {src_name}: {len(src_questions)} 道导入题, "
              f"解析出 {len(ref_questions)} 个编号题目")
        for p, c in paper_count.items():
            print(f"    {p}: {c}")

        matched = 0
        unmatched = 0
        unmatched_samples = []
        wrong_samples = []

        for q in src_questions:
            q_text = q["question"]

            # 文本匹配
            result = find_best_match(q_text, ref_questions)
            if result is None:
                unmatched += 1
                if len(unmatched_samples) < 3:
                    unmatched_samples.append(
                        f"    [MATCH_FAIL] q={q_text[:60]}")
                continue

            paper, section, qnum, score = result

            # 孤儿题目（试卷2开头没标题的题）- 映射到默认试卷
            if paper == "__orphan__":
                paper = default_paper

            if paper not in answers:
                unmatched += 1
                if len(unmatched_samples) < 3:
                    unmatched_samples.append(
                        f"    [NO_ANS_PAPER] paper={paper} q={q_text[:50]}")
                continue

            # 查找答案
            ans = find_answer(answers[paper], section, qnum, q["type"])
            if ans:
                q["answer"] = ans
                matched += 1
            else:
                unmatched += 1
                if len(unmatched_samples) < 3:
                    unmatched_samples.append(
                        f"    [ANS_MISS] paper={paper} sec={section} "
                        f"num={qnum} type={q['type']} q={q_text[:40]}")

        print(f"    -> 匹配: {matched}, 未匹配: {unmatched}")
        for s in unmatched_samples:
            print(s)

        matched_total += matched
        unmatched_total += unmatched

    # 非GZMK来源的题目数
    other = sum(1 for q in all_q if "GZMK" not in q.get("source", ""))

    print(f"\n{'=' * 60}")
    print(f"  匹配结果")
    print(f"{'=' * 60}")
    print(f"  成功匹配: {matched_total}")
    print(f"  未能匹配: {unmatched_total}")
    print(f"  跳过(非GZMK): {other}")

    # 保存
    with open("data/imported_exercises.json", "w", encoding="utf-8") as f:
        json.dump(exercises, f, ensure_ascii=False, indent=2)

    print(f"  已保存到 data/imported_exercises.json")

    # 验证已知答案
    print(f"\n--- 抽样验证 ---")
    verify_cases = [
        ("a和b都是整数", "49", "大奥 填空1"),
        ("棱长是4厘米的正方体可以截成", "8", "大奥 填空3"),
        ("参加了五科的期末考试", "99", "大奥 填空6"),
        ("2-1+4-2+6-3+8-4", "210", "大奥 填空7"),
        ("某公园的门票为每人5元", "25", "大奥 解答1"),
        ("加工一批零件，师徒两人合作20天", "700", "大奥 解答5"),
        ("某书店上个月按应纳税", "11000", "金广附"),
        ("圆柱侧面展开", "2464", "南沙广附/五中"),
    ]
    for kw, expected, note in verify_cases:
        found = False
        for q in all_q:
            if kw in q["question"]:
                ans = q.get("answer", "")
                ok = "OK" if expected in ans else "MISS"
                print(f"  [{ok}] {note}: expected={expected} "
                      f"got={ans[:40]}")
                found = True
                break
        if not found:
            print(f"  [NOT_FOUND] {note}: keyword={kw}")

    return matched_total


if __name__ == "__main__":
    main()
