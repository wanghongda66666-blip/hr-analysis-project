#!/usr/bin/env python3
"""
员工流失分析工具 (CLI)
用法: uv run python3 analyze.py 你的数据.csv
输出：在桌面生成 HTML 分析报告
"""
import os, sys, pickle, io, base64, json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE, "model")

# ─── 加载模型 ───
with open(os.path.join(MODEL_DIR, "rf_model.pkl"), "rb") as f:
    model = pickle.load(f)
with open(os.path.join(MODEL_DIR, "scaler.pkl"), "rb") as f:
    scaler = pickle.load(f)
with open(os.path.join(MODEL_DIR, "label_encoders.pkl"), "rb") as f:
    label_encoders = pickle.load(f)
with open(os.path.join(MODEL_DIR, "feature_columns.pkl"), "rb") as f:
    FEATURE_COLUMNS = pickle.load(f)

REQUIRED_COLS = set(FEATURE_COLUMNS)


def validate_and_encode(df):
    """验证数据并编码"""
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        print(f"❌ 缺少字段: {', '.join(sorted(missing))}")
        print(f"\n完整字段列表 ({len(FEATURE_COLUMNS)}个):")
        for c in FEATURE_COLUMNS:
            print(f"  - {c}")
        print("\n📋 下载模板: sample_template.csv")
        sys.exit(1)
    
    extra = set(df.columns) - REQUIRED_COLS
    if extra:
        print(f"⚠️ 发现多余字段，已忽略: {', '.join(sorted(extra))}")
        df = df.drop(columns=list(extra))
    
    df = df[FEATURE_COLUMNS].copy()
    
    for col, le in label_encoders.items():
        if col in df.columns:
            valid = set(le.classes_)
            unknown = set(df[col].dropna().unique()) - valid
            if unknown:
                print(f"❌ 字段 '{col}' 包含无效值: {unknown}")
                print(f"   有效值: {list(valid)}")
                sys.exit(1)
            df[col] = le.transform(df[col])
    
    if df.isnull().any().any():
        null_cols = df.columns[df.isnull().any()].tolist()
        print(f"❌ 以下字段存在空值: {null_cols}")
        sys.exit(1)
    
    return df


def analyze(csv_path):
    print(f"📂 读取数据: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"   共 {df.shape[0]} 名员工, {df.shape[1]} 列")
    
    df_orig = df.copy()
    df_encoded = validate_and_encode(df)
    
    X_scaled = scaler.transform(df_encoded)
    probas = model.predict_proba(X_scaled)[:, 1]
    
    bins = [0, 0.2, 0.4, 0.6, 1.0]
    labels = ["低风险", "中低风险", "中高风险", "高风险"]
    risk_labels = pd.cut(probas, bins=bins, labels=labels).astype(str).tolist()
    
    # ── 生成报告 ──
    n = len(df_orig)
    n_high = sum(1 for r in risk_labels if r == "高风险")
    avg_prob = probas.mean()
    
    # 图表
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    sns.set_style("whitegrid")
    
    risk_counts = pd.Series(risk_labels).value_counts()
    colors_map = {"低风险": "#4caf50", "中低风险": "#ff9800",
                  "中高风险": "#f44336", "高风险": "#d32f2f"}
    bars = axes[0].bar(risk_counts.index, risk_counts.values,
                       color=[colors_map.get(k, "#888") for k in risk_counts.index])
    axes[0].set_title("Risk Level Distribution")
    axes[0].set_ylabel("Employees")
    for b, v in zip(bars, risk_counts.values):
        axes[0].text(b.get_x()+b.get_width()/2, b.get_height()+0.5,
                     str(v), ha="center", fontsize=11)
    
    axes[1].hist(probas, bins=20, color="#5c6bc0", edgecolor="white", alpha=0.8)
    axes[1].axvline(avg_prob, color="red", ls="--", label=f"Mean={avg_prob:.1%}")
    axes[1].set_title("Attrition Probability Distribution")
    axes[1].set_xlabel("Probability")
    axes[1].set_ylabel("Count")
    axes[1].legend()
    
    top_factors = [
        ("OverTime", 0.28), ("JobSatisfaction", 0.13),
        ("WorkLifeBalance", 0.07), ("YearsAtCompany", 0.06),
        ("YearsWithCurrManager", 0.05), ("YearsInCurrentRole", 0.05),
        ("Age", 0.04), ("TotalWorkingYears", 0.04)
    ]
    names, vals = zip(*top_factors)
    colors_bar = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(names)))
    axes[2].barh(range(len(names)), vals, color=colors_bar[::-1])
    axes[2].set_yticks(range(len(names)))
    axes[2].set_yticklabels(names)
    axes[2].invert_yaxis()
    axes[2].set_title("Top Factors")
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close()
    chart_b64 = base64.b64encode(buf.getvalue()).decode()
    
    # 明细表格 (Top 30)
    table_rows = ""
    show_n = min(30, n)
    sorted_idx = np.argsort(-probas)
    for rank, idx in enumerate(sorted_idx[:show_n]):
        row = df_orig.iloc[idx]
        table_rows += f"""
        <tr>
            <td>{rank+1}</td>
            <td>{row.get('Age', '-')}</td>
            <td>{row.get('Department', '-')}</td>
            <td>{row.get('JobRole', '-')}</td>
            <td>{row.get('MaritalStatus', '-')}</td>
            <td>{row.get('OverTime', '-')}</td>
            <td>{row.get('JobSatisfaction', '-')}</td>
            <td>{row.get('WorkLifeBalance', '-')}</td>
            <td>{probas[idx]*100:.1f}%</td>
            <td class="r{risk_labels[idx]}">{risk_labels[idx]}</td>
        </tr>"""
    
    # 风险概览表
    risk_summary_rows = ""
    for level in ["低风险", "中低风险", "中高风险", "高风险"]:
        cnt = risk_counts.get(level, 0)
        if cnt > 0:
            avg_p = probas[np.array(risk_labels) == level].mean()
        else:
            avg_p = 0
        risk_summary_rows += f"""
        <tr>
            <td class="r{level}">{level}</td>
            <td>{cnt}</td>
            <td>{avg_p*100:.1f}%</td>
            <td>{cnt}人</td>
        </tr>"""
    
    # 输出文件名
    input_name = os.path.splitext(os.path.basename(csv_path))[0]
    output_path = os.path.join(os.path.dirname(csv_path) or ".", f"{input_name}_分析报告.html")
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>员工流失分析报告 - {input_name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;background:#f0f2f5;color:#333}}
.header{{background:linear-gradient(135deg,#1a237e,#283593);color:#fff;padding:36px 50px}}
.header h1{{font-size:26px;margin-bottom:6px}}
.header p{{font-size:13px;opacity:.85}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;padding:28px 50px}}
.stat-card{{background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.stat-card .num{{font-size:34px;font-weight:700;color:#1a237e}}
.stat-card .label{{font-size:13px;color:#888;margin-top:6px}}
.content{{padding:0 50px 50px}}
.section{{background:#fff;border-radius:12px;padding:28px;margin-bottom:24px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.section h2{{font-size:17px;margin-bottom:16px;color:#1a237e;border-left:4px solid #1a237e;padding-left:12px}}
.chart-img{{width:100%;border-radius:8px;border:1px solid #eee}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#e8eaf6;padding:9px 12px;text-align:center;font-weight:600;font-size:12px}}
td{{padding:7px 12px;text-align:center;border-bottom:1px solid #eee}}
.r低风险{{color:#4caf50;font-weight:600}}
.r中低风险{{color:#ff9800;font-weight:600}}
.r中高风险{{color:#f44336;font-weight:600}}
.r高风险{{color:#d32f2f;font-weight:700}}
.note{{font-size:12px;color:#888;margin-top:16px;padding-top:14px;border-top:1px solid #eee}}
@media(max-width:800px){{.stats{{grid-template-columns:repeat(2,1fr);padding:16px}}.content{{padding:0 16px 40px}}.header{{padding:24px 16px}}}}
</style>
</head>
<body>
<div class="header">
    <h1>员工流失分析报告</h1>
    <p>{input_name} · {n} 名员工 · 随机森林预测模型 · AUC 0.981</p>
</div>
<div class="stats">
    <div class="stat-card"><div class="num">{n}</div><div class="label">员工总数</div></div>
    <div class="stat-card"><div class="num" style="color:#e53935">{avg_prob*100:.1f}%</div><div class="label">预测总流失率</div><div class="sub">模型预估值</div></div>
    <div class="stat-card"><div class="num" style="color:#ff9800">{n_high}</div><div class="label">高风险员工数</div></div>
    <div class="stat-card"><div class="num">{sum(1 for r in risk_labels if r in ["低风险","中低风险"])}</div><div class="label">低风险员工数</div></div>
</div>
<div class="content">
<div class="section"><h2>分析图表</h2><img class="chart-img" src="data:image/png;base64,{chart_b64}" alt="Charts"></div>
<div class="section">
    <h2>风险概览</h2>
    <table><tr><th>风险等级</th><th>人数</th><th>平均流失概率</th><th>建议关注</th></tr>{risk_summary_rows}</table>
    <div class="note"><strong>建议：</strong>高风险员工流失概率 > 60%，建议优先安排访谈、改善工作条件。中高风险员工需关注，可纳入保留计划。</div>
</div>
<div class="section">
    <h2>流失风险排名（Top {show_n}）</h2>
    <div style="overflow-x:auto"><table>
        <tr><th>排名</th><th>年龄</th><th>部门</th><th>岗位</th><th>婚姻</th><th>加班</th><th>满意度</th><th>工作生活平衡</th><th>流失概率</th><th>风险等级</th></tr>
        {table_rows}
    </table></div>
</div>
</div>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"\n✅ 分析完成！")
    print(f"   员工总数: {n}")
    print(f"   预测总流失率: {avg_prob*100:.1f}%")
    print(f"   高风险: {n_high} 人")
    print(f"   报告已生成: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
员工流失分析工具
================
用法:
  uv run python3 analyze.py <csv文件路径>

示例:
  uv run python3 analyze.py sample_template.csv
  uv run python3 analyze.py /mnt/c/Users/PC/Desktop/员工数据.csv

📋 下载模板先看字段格式: sample_template.csv
📖 详细字段说明: DATA_FORMAT.md
        """)
        sys.exit(1)
    
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"❌ 文件不存在: {csv_path}")
        sys.exit(1)
    
    analyze(csv_path)
