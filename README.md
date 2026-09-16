# 介电性质数据库 v5.4 — 部署版

这是可直接部署的 Streamlit + SQLite 版本。数据库结构未改变，网页查询使用 SQLite 只读连接。

## v5.4 更新

- 软件统计恢复为全部可用介电记录：72,357 条（纯物质 65,114；混合物 7,243）。
- 单物质页显示基础分子物性及来源追溯。
- 基础物性连续数值统一显示 3 位小数；H-bond acceptors/donors 显示为整数。
- 单物质频率介电谱按温度分组，并增加 Cole–Cole 图。
- 混合物增加 εs–组成、频率介电谱和 Cole–Cole 图。
- 科学图全部改为单行全宽显示；图例移到图上方，静态 ε–T 图用 S1/S2… 简写来源，避免长文献名称遮挡图形。
- 每一张科学图均可下载其绘图数据 CSV。
- 继续保留查询结果、混合体系全数据、基础物性来源及完整性统计 CSV 下载。
- 删除独立“基础物性”标签页，基础物性整合到单物质查询和完整性页面。
- 当前 `dielectric.db` 已包含截至 CRC Handbook 整理完成阶段的基础物性补充和来源记录。

## 仓库必须包含

```text
.
├── app.py
├── dielectric.db
├── requirements.txt
├── README.md
├── .gitignore
├── .gitattributes
├── .streamlit/
│   └── config.toml
├── run_windows.bat
├── run_mac_linux.sh
├── Procfile
└── runtime.txt
```

## GitHub Desktop 更新

建议直接用 GitHub Desktop：

1. 将本部署包中的文件覆盖到本地仓库根目录。
2. GitHub Desktop 会显示变更。
3. Commit，例如 `Update dielectric database v5.4`。
4. Push origin。

`dielectric.db` 超过 GitHub 网页 25 MB 上传提示限制，但仍低于 GitHub 普通 Git push 的 100 MB 单文件硬限制，因此用 GitHub Desktop 即可。

## Streamlit Community Cloud

Main file path 使用 `app.py`。应用无需数据库账号和密码；`app.py` 直接读取同目录 `dielectric.db`，并以 SQLite `mode=ro` 只读连接。

## 本地运行

Windows 可双击 `run_windows.bat`，或执行：

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

macOS/Linux：

```bash
chmod +x run_mac_linux.sh
./run_mac_linux.sh
```

## 数据库检查

替换数据库后建议运行：

```bash
python check_database.py
```

当前数据库预期核心统计：

- `measurements`: 72,357
- `compound_properties`: 1,621
- `property_provenance`: 15,010
- SQLite integrity check: `ok`
