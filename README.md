# Dielectric Property Database

这是一个基于用户提供的 7 组介电性质数据整理出的本地数据库软件。

## 当前数据规模

- 物质：1,200
- 介电记录：21,331
- 纯物质记录：15,859
- 混合体系记录：5,472
- 数据源：7

## 功能

- 英文名 / 中文名 / CAS 查询
- 纯物质与混合物筛选
- 温度、频率范围筛选
- εs、ε′、ε″ 查询
- 单物质温度/频率曲线
- 混合物组成-介电性质查看
- 不同来源对比
- 筛选结果 CSV 导出
- 数据层级：Recommended / literature-mined / raw

## 运行

### Windows

双击 `run_windows.bat`

或在 VS Code / PowerShell 中：

```bash
pip install -r requirements.txt
streamlit run app.py
```

### macOS / Linux

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 数据层级说明

- `recommended`：手册、CRC、NPL 推荐/拟合数据、专门静态数据库、人工整理综述数据
- `literature_mined`：Scidata 自动文献挖掘数据
- `raw`：NPL 原始测量数据，可用于验证和拟合

数据库文件为 `dielectric.db`，可直接使用 SQLite 软件或 Python 访问。

## v3 数据更新
- 新增 Deng & Jia (2022), DOI: 10.1016/j.fluid.2022.113545
- 新增 Bouteloup & Mathieu (2019), DOI: 10.1039/C9CP01704F
- 新增 Kohns (2020), DOI: 10.1016/j.fluid.2019.112393
- 全库按“物质/混合组成 + 温度 + 频率 + εs/ε′/ε″ + 数据类型”进行去重；模拟值、预测值、原始实测值、best-fit 数据不会互相合并。


## v4 数据更新：LJW 2026-04-15 数据集
- 导入文件：`0000-data collection-ljw-20260415.xlsx` 的 `pure-01` 工作表
- 仅导入实验介电常数 `εexp`；未将 CM / Debye / Onsager 模型计算值作为数据库实验值导入
- 温度由 K 转换为 °C；频率未提供，因此留空
- 通过现有数据库及已整理 CAS 表进行名称/CAS 标准化
- 候选数据：3,084 条；因 CAS/身份未可靠解析而未导入：206 条（81 种名称）
- 新数据源最终保留：3,053 条（与已有数据库重复的数据已优先保留原来源）
- 全库最终记录：17,418 条；物质：1,239；数据源：11
- 全库精确重复组：0
