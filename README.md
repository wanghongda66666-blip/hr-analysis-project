# 员工流失预测分析系统

基于 IBM HR Analytics 数据集的机器学习项目，可上传真实员工数据进行分析预测。

## 🚀 快速使用

```bash
# 1. 下载模板（查看字段格式）
sample_template.csv

# 2. 按模板格式准备你的员工数据
# 3. 运行分析
uv run python3 analyze.py 你的数据.csv

# 4. 打开生成的 HTML 报告
```

## 📋 功能

- **员工数据上传分析**：支持 CSV 格式，30 个必填字段
- **流失概率预测**：随机森林模型（AUC 0.98）
- **风险分层**：低/中低/中高/高风险四级
- **可视化报告**：自动生成 HTML 分析看板
- **Top 影响因子分析**：识别核心流失因素

## 📁 项目结构

```
├── analyze.py              # CLI 分析工具（主入口）
├── app.py                  # FastAPI 网页版（可选）
├── model/
│   ├── rf_model.pkl        # 训练好的随机森林模型
│   ├── scaler.pkl          # 标准化器
│   ├── label_encoders.pkl  # 标签编码器
│   └── feature_columns.pkl # 特征列名
├── sample_template.csv     # 数据上传模板
├── DATA_FORMAT.md          # 字段格式详细说明
├── HR_Employee_Attrition.csv  # 原始训练数据
└── dashboard.html          # 训练集分析看板
```

## 🔧 技术栈

- **模型**：随机森林（300棵树）+ 逻辑回归对比
- **数据处理**：pandas, scikit-learn
- **可视化**：matplotlib, seaborn
- **服务**：FastAPI / CLI
- **评估指标**：准确率 91.8%，AUC 0.981

## 📖 数据格式

所有 30 个必填字段说明详见 [DATA_FORMAT.md](DATA_FORMAT.md)。

## 📊 模型性能

| 指标 | 值 |
|------|-----|
| 准确率 | 91.8% |
| AUC | 0.981 |
| 5折交叉验证AUC | 0.970 |
| Top1 特征 | OverTime (加班) |
