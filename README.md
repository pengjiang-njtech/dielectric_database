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
