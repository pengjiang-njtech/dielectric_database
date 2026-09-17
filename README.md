# 介电性质数据库软件（Streamlit + GitHub Pages 双部署版）

## 本次界面修复

- 修复页面顶部加载区与主界面同时占位造成的大空白。
- 顶部检索和单物质检索均支持中文名、英文名及 CAS，支持输入后按 Enter。
- 删除“请选择一个物质”的大块空白占位区。
- 单物质、频谱、Cole–Cole 和混合物图表统一增高并自适应显示。
- 混合物两个组分均改为可输入检索，并自动提示数据库已有组分。

## Streamlit Cloud 部署（推荐）

1. 在 GitHub 新建仓库，将本文件夹内的全部内容上传到仓库根目录。
2. 打开 https://share.streamlit.io/，使用 GitHub 登录。
3. 点击 **Create app**，选择刚才的仓库与 `main` 分支。
4. **Main file path** 填写 `app.py`，点击 **Deploy**。

部署时不需要填写 Secrets。首次打开需要载入约 30 MB 数据，可能等待数秒。

本版本同时保留静态入口 `index.html`，所以仍可按下文方式部署到 GitHub Pages。

本版本已将最新 SQLite 数据库与新版 UI 真正合并。网页读取由数据库导出的真实数据，而不是固定示意数据。

## 已接入的数据

- 1,621 个物质
- 72,357 条介电数据
- 65,114 条纯物质数据
- 7,243 条混合物数据
- 50 个数据来源
- 21,120 条物性来源记录

## 已实现功能

- 数据总览与数据源贡献统计
- 按名称、CAS、分子式、样品类型、温度和介电指标查询
- 单物质物性展示和来源追溯
- 静态介电常数–温度图：实验数据为散点，拟合或关联数据为曲线
- 复介电频谱按全部温度或单一温度显示
- Cole–Cole 数据可用性检查与原始复介电图
- 二元混合物按组分、组成基准、温度和指标查询
- 查询结果、物性、图表数据和混合物数据 CSV 下载

## 直接部署到 GitHub Pages

1. 新建 GitHub 仓库。
2. 将本文件夹内的全部内容上传到仓库根目录，确保 `index.html` 位于根目录。
3. 打开 `Settings → Pages`。
4. 在 `Build and deployment` 中选择 `Deploy from a branch`。
5. 选择 `main` 分支和 `/root`，保存。

发布完成后即可直接访问。页面首次打开需要下载约 30 MB 的数据库导出数据，载入时间取决于网络速度。

## 文件结构

- `index.html`：软件入口。
- `assets/app.js`：查询、绘图、来源映射和 CSV 下载逻辑。
- `assets/style.css`：界面样式。
- `data/*.json`：由最新 SQLite 数据库导出的网页数据，页面实际读取这些文件。
- `database/dielectric_database.db`：最新原始 SQLite 数据库备份。
- `source/export_static_data.py`：将 SQLite 数据库重新导出为网页 JSON 的脚本。

## 更新数据库

将新数据库替换为 `database/dielectric_database.db`，并调整导出脚本中的数据库路径后运行 `source/export_static_data.py`，再把生成的 JSON 文件更新到 `data/`。

静态网页不会在浏览器中直接修改 SQLite 数据库，适合只读查询与公开展示。
