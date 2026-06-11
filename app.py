"""
员工流失分析系统 - FastAPI 服务
================================
功能：上传 CSV 数据 → 自动分析 → 输出预测结果 + 可视化看板
"""
import os, sys, pickle, json, io, base64
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ─── 常量 ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

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

# ─── FastAPI ───
app = FastAPI(title="员工流失分析系统", version="1.0")
os.makedirs(TEMPLATES_DIR, exist_ok=True)


def validate_and_encode(df: pd.DataFrame) -> pd.DataFrame:
    """验证数据并编码为模型可接受的格式"""
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise HTTPException(400, f"缺少字段: {', '.join(sorted(missing))}")
    
    extra = set(df.columns) - REQUIRED_COLS
    if extra:
        df = df.drop(columns=list(extra))
    
    df = df[FEATURE_COLUMNS].copy()
    
    for col, le in label_encoders.items():
        if col in df.columns:
            valid = set(le.classes_)
            unknown = set(df[col].dropna().unique()) - valid
            if unknown:
                raise HTTPException(400,
                    f"字段 '{col}' 包含无效值: {unknown}. "
                    f"有效值: {list(valid)}")
            df[col] = le.transform(df[col])
    
    if df.isnull().any().any():
        null_cols = df.columns[df.isnull().any()].tolist()
        raise HTTPException(400, f"以下字段存在空值: {null_cols}")
    
    return df


def generate_report(df_orig: pd.DataFrame, probas: np.ndarray,
                    risk_labels: list, importances: list) -> str:
    """生成 HTML 分析报告"""
    n = len(df_orig)
    n_high_risk = sum(1 for r in risk_labels if r == "高风险")
    avg_prob = probas.mean()
    
    # Charts
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    
    # 1. Risk distribution
    risk_counts = pd.Series(risk_labels).value_counts()
    colors = {"低风险": "#4caf50", "中低风险": "#ff9800",
              "中高风险": "#f44336", "高风险": "#d32f2f"}
    bars = axes[0].bar(risk_counts.index, risk_counts.values,
                       color=[colors.get(k, "#888") for k in risk_counts.index])
    axes[0].set_title("风险等级分布")
    axes[0].set_ylabel("人数")
    for b, v in zip(bars, risk_counts.values):
        axes[0].text(b.get_x()+b.get_width()/2, b.get_height()+0.5,
                     str(v), ha="center", fontsize=11)
    
    # 2. Probability histogram
    axes[1].hist(probas, bins=20, color="#5c6bc0", edgecolor="white", alpha=0.8)
    axes[1].axvline(probas.mean(), color="red", ls="--", label=f"均值={avg_prob:.1%}")
    axes[1].set_title("流失概率分布")
    axes[1].set_xlabel("流失概率")
    axes[1].set_ylabel("人数")
    axes[1].legend()
    
    # 3. Top factors (from importances)
    top = importances[:8]
    colors_bar = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(top)))
    axes[2].barh(range(len(top)), [t["importance"] for t in top],
                 color=colors_bar[::-1])
    axes[2].set_yticks(range(len(top)))
    axes[2].set_yticklabels([t["feature"] for t in top])
    axes[2].invert_yaxis()
    axes[2].set_title("Top 影响因子")
    
    plt.tight_layout()
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png", dpi=120, bbox_inches="tight")
    plt.close()
    chart_b64 = base64.b64encode(img_buf.getvalue()).decode()
    
    # Build HTML
    table_rows = ""
    for i in range(min(20, n)):
        row = df_orig.iloc[i]
        table_rows += f"""
        <tr>
            <td>{i+1}</td>
            <td>{row.get('Age', '-')}</td>
            <td>{row.get('Department', '-')}</td>
            <td>{row.get('JobRole', '-')}</td>
            <td>{row.get('MaritalStatus', '-')}</td>
            <td>{row.get('OverTime', '-')}</td>
            <td>{row.get('JobSatisfaction', '-')}</td>
            <td>{row.get('WorkLifeBalance', '-')}</td>
            <td>{probas[i]*100:.1f}%</td>
            <td class="risk-{risk_labels[i]}">{risk_labels[i]}</td>
        </tr>"""
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>员工流失分析报告</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;background:#f0f2f5;color:#333}}
.header{{background:linear-gradient(135deg,#1a237e,#283593);color:#fff;padding:30px 40px}}
.header h1{{font-size:24px;margin-bottom:6px}}
.header p{{font-size:13px;opacity:.85}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;padding:24px 40px}}
.stat-card{{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.stat-card .num{{font-size:30px;font-weight:700;color:#1a237e}}
.stat-card .label{{font-size:12px;color:#888;margin-top:4px}}
.content{{padding:0 40px 40px}}
.section{{background:#fff;border-radius:10px;padding:24px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.section h2{{font-size:16px;margin-bottom:14px;color:#1a237e;border-left:3px solid #1a237e;padding-left:10px}}
.chart-img{{width:100%;border-radius:6px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#e8eaf6;padding:8px 10px;text-align:center;font-weight:600}}
td{{padding:6px 10px;text-align:center;border-bottom:1px solid #eee}}
.risk-低风险{{color:#4caf50;font-weight:600}}
.risk-中低风险{{color:#ff9800;font-weight:600}}
.risk-中高风险{{color:#f44336;font-weight:600}}
.risk-高风险{{color:#d32f2f;font-weight:700}}
@media(max-width:800px){{.stats{{grid-template-columns:repeat(2,1fr);padding:16px}}.content{{padding:0 16px 16px}}.header{{padding:20px 16px}}}}
</style>
</head>
<body>
<div class="header">
    <h1>员工流失分析报告</h1>
    <p>上传数据 · {n} 名员工 · AI 预测模型</p>
</div>
<div class="stats">
    <div class="stat-card"><div class="num">{n}</div><div class="label">员工总数</div></div>
    <div class="stat-card"><div class="num" style="color:#e53935">{avg_prob*100:.1f}%</div><div class="label">预测总流失率</div></div>
    <div class="stat-card"><div class="num" style="color:#ff9800">{n_high_risk}</div><div class="label">高风险员工数</div></div>
    <div class="stat-card"><div class="num">{sum(1 for r in risk_labels if r in ["低风险","中低风险"])}</div><div class="label">低风险员工数</div></div>
</div>
<div class="content">
<div class="section"><h2>分析图表</h2><img class="chart-img" src="data:image/png;base64,{chart_b64}" alt="Analysis Charts"></div>
<div class="section">
    <h2>员工流失预测明细（Top 20）</h2>
    <div style="overflow-x:auto">
    <table>
        <tr><th>#</th><th>年龄</th><th>部门</th><th>岗位</th><th>婚姻</th><th>加班</th><th>工作满意度</th><th>工作生活平衡</th><th>流失概率</th><th>风险等级</th></tr>
        {table_rows}
    </table>
    </div>
</div>
</div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>员工流失分析系统</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;background:#f0f2f5;display:flex;justify-content:center;align-items:center;min-height:100vh}}
.card{{background:#fff;border-radius:16px;padding:48px;max-width:600px;width:90%;box-shadow:0 4px 24px rgba(0,0,0,.1);text-align:center}}
h1{{font-size:28px;color:#1a237e;margin-bottom:8px}}
p{{color:#666;margin-bottom:28px;font-size:14px;line-height:1.6}}
.upload-zone{{border:2px dashed #c5cae9;border-radius:12px;padding:36px 24px;margin-bottom:20px;cursor:pointer;transition:.2s}}
.upload-zone:hover{{border-color:#5c6bc0;background:#f5f6ff}}
.upload-zone input{{display:none}}
.upload-zone label{{cursor:pointer;font-size:14px;color:#5c6bc0;font-weight:600}}
.upload-zone .hint{{font-size:12px;color:#999;margin-top:8px}}
.btn{{background:#1a237e;color:#fff;border:none;padding:12px 36px;border-radius:8px;font-size:15px;cursor:pointer;transition:.2s}}
.btn:hover{{background:#283593}}
.btn:disabled{{background:#ccc;cursor:not-allowed}}
.links{{margin-top:20px;font-size:13px}}
.links a{{color:#5c6bc0;text-decoration:none;margin:0 10px}}
.links a:hover{{text-decoration:underline}}
.status{{margin-top:16px;padding:12px;border-radius:8px;display:none;font-size:13px}}
.status.loading{{display:block;background:#e8eaf6;color:#1a237e}}
.status.error{{display:block;background:#ffebee;color:#c62828}}
</style>
</head>
<body>
<div class="card">
    <h1>员工流失分析系统</h1>
    <p>上传员工 CSV 数据 → 自动预测流失风险 → 输出分析报告</p>
    <form id="uploadForm" enctype="multipart/form-data">
        <div class="upload-zone" onclick="document.getElementById('file').click()">
            <input type="file" id="file" name="file" accept=".csv" required>
            <label for="file">点击选择 CSV 文件</label>
            <div class="hint">支持 .csv 格式（UTF-8编码）</div>
        </div>
        <button type="submit" class="btn" id="submitBtn">开始分析</button>
    </form>
    <div class="links">
        <a href="/template">下载模板</a>
        <a href="/format">查看字段说明</a>
    </div>
    <div class="status" id="status"></div>
</div>
<script>
document.getElementById('uploadForm').onsubmit = async function(e){{
    e.preventDefault();
    const file = document.getElementById('file').files[0];
    if(!file) return;
    const status = document.getElementById('status');
    const btn = document.getElementById('submitBtn');
    status.className = 'status loading';
    status.textContent = '分析中，请稍候...';
    btn.disabled = true;
    const fd = new FormData();
    fd.append('file', file);
    try {{
        const res = await fetch('/analyze', {{method:'POST',body:fd}});
        if(!res.ok) throw new Error((await res.json()).detail || '分析失败');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
        status.className = 'status';
        status.textContent = '';
    }} catch(e) {{
        status.className = 'status error';
        status.textContent = '错误: ' + e.message;
    }} finally {{
        btn.disabled = false;
    }}
}};
document.getElementById('file').onchange = function() {{
    const label = document.querySelector('.upload-zone label');
    label.textContent = this.files[0] ? this.files[0].name : '点击选择 CSV 文件';
}};
</script>
</body>
</html>"""


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "仅支持 CSV 格式")
    
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"无法解析 CSV: {e}")
    
    if df.shape[0] == 0:
        raise HTTPException(400, "CSV 文件为空")
    
    df_orig = df.copy()
    df_encoded = validate_and_encode(df)
    
    X_scaled = scaler.transform(df_encoded)
    probas = model.predict_proba(X_scaled)[:, 1]
    
    bins = [0, 0.2, 0.4, 0.6, 1.0]
    labels = ["低风险", "中低风险", "中高风险", "高风险"]
    risk_labels = pd.cut(probas, bins=bins, labels=labels).astype(str).tolist()
    
    importances = [
        {"feature": "OverTime", "importance": 0.28},
        {"feature": "JobSatisfaction", "importance": 0.13},
        {"feature": "WorkLifeBalance", "importance": 0.07},
        {"feature": "YearsAtCompany", "importance": 0.06},
        {"feature": "YearsWithCurrManager", "importance": 0.05},
        {"feature": "YearsInCurrentRole", "importance": 0.05},
        {"feature": "Age", "importance": 0.04},
        {"feature": "TotalWorkingYears", "importance": 0.04},
    ]
    
    report_html = generate_report(df_orig, probas, risk_labels, importances)
    
    return HTMLResponse(content=report_html, media_type="text/html")


@app.get("/template")
async def download_template():
    from fastapi.responses import FileResponse
    path = os.path.join(BASE_DIR, "sample_template.csv")
    if not os.path.exists(path):
        raise HTTPException(404, "模板文件不存在")
    return FileResponse(path, filename="sample_template.csv",
                        media_type="text/csv")


@app.get("/format", response_class=HTMLResponse)
async def format_doc():
    path = os.path.join(BASE_DIR, "DATA_FORMAT.md")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            content = f.read()
        return f"<html><body><pre style='font-size:13px;padding:20px;max-width:900px;margin:auto'>{content}</pre></body></html>"
    raise HTTPException(404)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
