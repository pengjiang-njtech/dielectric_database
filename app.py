import io
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "dielectric_database.db"
st.set_page_config(page_title="介电性质数据库", page_icon="ε", layout="wide")
st.markdown("<style>.block-container{max-width:1500px;padding-top:1.5rem} [data-testid='stMetricValue']{font-size:1.7rem}</style>", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_data():
    with sqlite3.connect(DB) as con:
        compounds = pd.read_sql_query("SELECT c.id,c.name_en,c.name_cn,c.cas,p.smiles,p.molecular_formula,p.mass_g_mol,p.dipole_moment_d,p.refractive_index,p.melting_point_c,p.boiling_point_c,p.density_g_cm3,p.density_temperature_c,p.viscosity_mpas,p.viscosity_temperature_c FROM compounds c JOIN compound_properties p ON p.compound_id=c.id", con)
        measurements = pd.read_sql_query("SELECT m.*,c.name_en AS compound_name,a.name_en AS component1_name,b.name_en AS component2_name,s.source_name FROM measurements m LEFT JOIN compounds c ON c.id=m.compound_id LEFT JOIN compounds a ON a.id=m.component1_id LEFT JOIN compounds b ON b.id=m.component2_id LEFT JOIN sources s ON s.id=m.source_id", con)
    return compounds, measurements

def csv_bytes(frame):
    return frame.to_csv(index=False).encode("utf-8-sig")

compounds, measurements = load_data()
st.title("介电性质数据库")
st.caption("本地 SQLite 部署版 · 介电测量、基础物性与可追溯来源")

tab0, tab1, tab2, tab3 = st.tabs(["数据总览", "数据查询", "单物质", "混合物"])
with tab0:
    pure = int((measurements.sample_type == "pure").sum())
    mixture = int((measurements.sample_type == "mixture").sum())
    a,b,c,d = st.columns(4)
    a.metric("化合物", f"{len(compounds):,}")
    b.metric("介电记录", f"{len(measurements):,}")
    c.metric("纯物质记录", f"{pure:,}")
    d.metric("混合物记录", f"{mixture:,}")
    st.subheader("数据源")
    sources = measurements.source_name.fillna("未标注来源").value_counts().rename_axis("来源").reset_index(name="记录数")
    st.bar_chart(sources.set_index("来源").head(20))
    st.dataframe(sources, hide_index=True, use_container_width=True, height=360)

with tab1:
    keyword = st.text_input("名称、中文名或 CAS", placeholder="例如：Methanol、甲醇、67-56-1")
    c1,c2,c3 = st.columns(3)
    sample = c1.selectbox("样品类型", ["全部", "pure", "mixture"])
    t_range = c2.slider("温度 / °C", -150.0, 500.0, (-150.0, 500.0))
    eps_min = c3.number_input("最小 ε", min_value=0.0, value=0.0)
    data = measurements.copy()
    if keyword.strip():
        hits = compounds[compounds[["name_en","name_cn","cas"]].fillna("").astype(str).apply(lambda x: x.str.contains(keyword.strip(), case=False, regex=False)).any(axis=1)]
        ids = set(hits.id)
        data = data[data.compound_id.isin(ids) | data.component1_id.isin(ids) | data.component2_id.isin(ids)]
    if sample != "全部": data = data[data.sample_type == sample]
    data = data[data.temperature_c.between(*t_range) | data.temperature_c.isna()]
    eps = data[["epsilon_static","epsilon_real","epsilon_imag"]].max(axis=1, skipna=True)
    data = data[eps.fillna(0) >= eps_min]
    cols=["sample_type","compound_name","component1_name","component2_name","x1","temperature_c","frequency_ghz","epsilon_static","epsilon_real","epsilon_imag","source_name","doi"]
    st.caption(f"匹配 {len(data):,} 条记录")
    st.dataframe(data[cols], hide_index=True, use_container_width=True, height=540)
    st.download_button("下载当前结果 CSV", csv_bytes(data[cols]), "dielectric_query.csv", "text/csv")

with tab2:
    query = st.text_input("输入物质名称或 CAS", key="compound")
    hits = compounds.iloc[0:0] if not query else compounds[compounds[["name_en","name_cn","cas"]].fillna("").astype(str).apply(lambda x: x.str.contains(query, case=False, regex=False)).any(axis=1)]
    if len(hits):
        selected = st.selectbox("选择物质", hits.name_en.tolist())
        item = compounds[compounds.name_en == selected].iloc[0]
        st.dataframe(pd.DataFrame([item]).drop(columns=["id"]), hide_index=True, use_container_width=True)
        pure_data = measurements[(measurements.sample_type == "pure") & (measurements.compound_id == item.id)]
        st.subheader("介电测量")
        st.dataframe(pure_data, hide_index=True, use_container_width=True, height=420)
        st.download_button("下载该物质记录 CSV", csv_bytes(pure_data), "compound_measurements.csv", "text/csv")
    elif query:
        st.info("没有找到匹配物质。")

with tab3:
    left,right = st.columns(2)
    a = left.text_input("组分 1")
    b = right.text_input("组分 2")
    if a and b:
        a_ids=set(compounds[compounds[["name_en","name_cn","cas"]].fillna("").astype(str).apply(lambda x:x.str.contains(a,case=False,regex=False)).any(axis=1)].id)
        b_ids=set(compounds[compounds[["name_en","name_cn","cas"]].fillna("").astype(str).apply(lambda x:x.str.contains(b,case=False,regex=False)).any(axis=1)].id)
        mix=measurements[(measurements.sample_type=="mixture") & (((measurements.component1_id.isin(a_ids)) & (measurements.component2_id.isin(b_ids))) | ((measurements.component1_id.isin(b_ids)) & (measurements.component2_id.isin(a_ids))))]
        st.caption(f"匹配 {len(mix):,} 条记录")
        st.dataframe(mix, hide_index=True, use_container_width=True, height=540)
        st.download_button("下载混合物记录 CSV", csv_bytes(mix), "mixture_measurements.csv", "text/csv")
