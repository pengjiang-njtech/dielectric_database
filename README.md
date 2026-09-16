# 介电性质数据库 v5.3 — 部署版

这是可直接部署的 Streamlit + SQLite 版本。数据库结构未改变，网页查询使用 SQLite 只读连接。

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
├── Procfile          # Render/Railway 等平台可用
└── runtime.txt
```

## 重要：GitHub 25 MB 提示

GitHub 网页上传单文件会提示 25 MB 限制。当前 `dielectric.db` 约 27.4 MB，因此不要用 GitHub 网页的 **Add file → Upload files** 上传数据库。

推荐在本地使用 Git 命令提交。GitHub 普通 Git push 的单文件硬限制通常是 100 MB，因此当前数据库可直接用 Git push，不需要拆库，也不需要改变数据库结构。

```bash
git clone <你的仓库地址>
cd <仓库目录>
# 将本部署包中的文件复制到仓库根目录
git add app.py dielectric.db requirements.txt README.md .gitignore .gitattributes .streamlit run_windows.bat run_mac_linux.sh Procfile runtime.txt
git commit -m "Deploy dielectric database v5.3"
git push origin main
```

如果数据库未来超过 100 MB，不建议直接改成 Git LFS 后部署到 Streamlit Community Cloud，因为部署环境对 LFS 文件的获取方式可能需要额外处理。届时更适合将数据库作为 Release/对象存储资产并在启动时下载，或使用外部数据库。

## Streamlit Community Cloud 部署

1. 将本目录完整推送到 GitHub 仓库根目录。
2. 登录 Streamlit Community Cloud。
3. 选择 **Create app / Deploy an app**。
4. Repository：选择你的 GitHub 仓库。
5. Branch：`main`。
6. Main file path：`app.py`。
7. 点击 Deploy。
8. 首次构建会安装 `requirements.txt` 中依赖并启动应用。

应用无需数据库账号和密码；`app.py` 直接读取同目录 `dielectric.db`，并以 `mode=ro` 只读方式连接。

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

浏览器默认访问 `http://localhost:8501`。

## Render / Railway 类平台

仓库已提供 `Procfile`：

```text
web: streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT
```

Build command 可使用：

```bash
pip install -r requirements.txt
```

## 数据库更新

以后数据库升级时，保持文件名仍为 `dielectric.db`，替换仓库中的该文件即可。不要修改表结构来适配部署；当前 `app.py` 已按现有数据库结构读取。

更新后建议本地检查：

```bash
python check_database.py
```

再执行：

```bash
git add dielectric.db
git commit -m "Update dielectric database"
git push origin main
```

Streamlit Cloud 通常会检测到仓库更新并重新部署。
