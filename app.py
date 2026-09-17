from pathlib import Path
import json

import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parent
APP_VERSION = "2026.09.17-v3.3"

st.set_page_config(
    page_title="介电性质数据库",
    page_icon="ε",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(show_spinner="正在载入介电性质数据库…")
def build_application(version: str) -> str:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
    fixes_css = (ROOT / "assets" / "fixes.css").read_text(encoding="utf-8")
    app_js = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
    charts_js = (ROOT / "assets" / "charts-v2.js").read_text(encoding="utf-8")

    datasets = {}
    for name in ("meta", "compounds", "measurements", "provenance"):
        datasets[f"data/{name}.json"] = json.loads(
            (ROOT / "data" / f"{name}.json").read_text(encoding="utf-8")
        )

    payload = json.dumps(datasets, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    fetch_shim = fr"""
<script>
const __DB_FILES__ = {payload};
const __nativeFetch__ = window.fetch.bind(window);
window.fetch = (url, options) => {{
  const key = String(url).replace(/^\.\//, '');
  if (Object.prototype.hasOwnProperty.call(__DB_FILES__, key)) {{
    return Promise.resolve(new Response(JSON.stringify(__DB_FILES__[key]), {{
      status: 200,
      headers: {{'Content-Type': 'application/json; charset=utf-8'}}
    }}));
  }}
  return __nativeFetch__(url, options);
}};
</script>
"""

    html = html.replace('<link rel="stylesheet" href="assets/style.css">', f"<style>{css}</style>")
    html = html.replace('<link rel="stylesheet" href="assets/fixes.css">', f"<style>{fixes_css}</style>")
    html = html.replace('<script src="assets/app.js"></script>', f"{fetch_shim}<script>{app_js}</script>")
    html = html.replace('<script src="assets/charts-v2.js"></script>', f"<script>{charts_js}</script>")
    return html


st.markdown(
    """
    <style>
    .block-container {padding: 0 !important; max-width: 100% !important;}
    header[data-testid="stHeader"] {display: none;}
    iframe {border: 0 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

components.html(build_application(APP_VERSION), height=1000, scrolling=True)
