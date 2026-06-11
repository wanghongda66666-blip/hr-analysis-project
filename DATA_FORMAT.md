# 员工流失分析系统 - 数据上传格式说明

## 快速上手

1. 下载 `sample_template.csv` 作为模板
2. 按模板格式填入你的员工数据
3. 上传到系统，自动返回预测结果 + 分析报告

---

## 必填字段（30个）

以下30个字段 **必须全部包含**，列名需完全一致。

### 1. 个人信息

| 字段名 | 类型 | 说明 | 取值范围 |
|--------|------|------|----------|
| Age | 整数 | 员工年龄 | 18-70 |
| Gender | 文本 | 性别 | Male / Female |
| MaritalStatus | 文本 | 婚姻状况 | Single / Married / Divorced |
| DistanceFromHome | 整数 | 家到公司的距离（公里） | 1-50 |

### 2. 工作信息

| 字段名 | 类型 | 说明 | 取值范围 |
|--------|------|------|----------|
| Department | 文本 | 所属部门 | Sales / Research & Development / Human Resources |
| JobRole | 文本 | 岗位名称 | Sales Executive / Research Scientist / Laboratory Technician / Manufacturing Director / Healthcare Representative / Manager / Sales Representative / Research Director / Human Resources |
| JobLevel | 整数 | 岗位级别（1低→5高） | 1-5 |
| BusinessTravel | 文本 | 出差频率 | Travel_Rarely / Travel_Frequently / Non-Travel |
| OverTime | 文本 | 是否加班 | Yes / No |
| NumCompaniesWorked | 整数 | 此前工作过的公司数 | 0-15 |

### 3. 薪酬信息

| 字段名 | 类型 | 说明 | 取值范围 |
|--------|------|------|----------|
| MonthlyIncome | 整数 | 月收入（元） | 2000-50000 |
| DailyRate | 整数 | 日薪 | 100-2000 |
| HourlyRate | 整数 | 时薪 | 10-200 |
| MonthlyRate | 整数 | 月费率（工资表基准值） | 2000-50000 |
| PercentSalaryHike | 整数 | 最近一次调薪百分比 | 10-30 |
| StockOptionLevel | 整数 | 股权激励级别（0=无） | 0-3 |

### 4. 教育与经验

| 字段名 | 类型 | 说明 | 取值范围 |
|--------|------|------|----------|
| Education | 整数 | 学历等级（1=高中→5=博士） | 1-5 |
| EducationField | 文本 | 专业领域 | Life Sciences / Medical / Marketing / Technical Degree / Human Resources / Other |
| TotalWorkingYears | 整数 | 总工作年限 | 0-50 |
| YearsAtCompany | 整数 | 在当前公司年数 | 0-45 |
| YearsInCurrentRole | 整数 | 当前岗位年数 | 0-20 |
| YearsWithCurrManager | 整数 | 当前上司共事年数 | 0-20 |
| YearsSinceLastPromotion | 整数 | 距离上次晋升年数 | 0-20 |
| TrainingTimesLastYear | 整数 | 去年培训次数 | 0-10 |

### 5. 满意度与绩效

| 字段名 | 类型 | 说明 | 取值范围 |
|--------|------|------|----------|
| JobSatisfaction | 整数 | 工作满意度（1低→4高） | 1-4 |
| EnvironmentSatisfaction | 整数 | 环境满意度（1低→4高） | 1-4 |
| JobInvolvement | 整数 | 工作投入度（1低→4高） | 1-4 |
| RelationshipSatisfaction | 整数 | 人际关系满意度（1低→4高） | 1-4 |
| WorkLifeBalance | 整数 | 工作生活平衡度（1差→4好） | 1-4 |
| PerformanceRating | 整数 | 绩效评级（3=良好，4=优秀） | 3-4 |

---

## 数据要求

- **文件格式**：CSV（UTF-8编码）
- **每行一条员工记录**
- **列名必须与上方完全一致**（区分大小写）
- **不允许空值**，缺失数据会导致预测失败

## 输出结果

上传分析后，系统返回：

1. **每位员工的流失概率**（0-100%）
2. **风险等级**（低/中低/中高/高风险）
3. **全公司风险分布概况**
4. **Top影响因素分析**
5. **可视化看板**（HTML，可直接在浏览器打开）

---

## 示例

可下载 `sample_template.csv` 查看完整示例数据格式。
