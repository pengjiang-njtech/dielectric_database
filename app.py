import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "dielectric.db"
BASE_QUALITY = "data_quality IN ('recommended','literature_mined')"

st.set_page_config(
    page_title="介电性质数据库",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
html, body, [class*="css"], [data-testid="stAppViewContainer"] {
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "SimHei", Arial, sans-serif;
}
.block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px;}
[data-testid="stSidebar"] {display:none;}
[data-testid="stMetricValue"] {font-size: 1.65rem;}
.small-note {color:#5f6b7a; font-size:0.90rem;}
.title-sub {color:#5f6b7a; margin-top:-10px; margin-bottom:16px;}
.stTabs [data-baseweb="tab"] {font-size:1.02rem; font-weight:600;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@st.cache_data
def load_compounds():
    return pd.read_sql(f"""
        SELECT c.id, c.name_en, c.name_cn, c.cas,
               COUNT(DISTINCT m.id) AS n_records
        FROM compounds c
        JOIN measurements m
          ON (m.component1_id=c.id OR m.component2_id=c.id)
        WHERE {BASE_QUALITY}
          AND c.name_en IS NOT NULL AND TRIM(c.name_en)<>''
        GROUP BY c.id
        HAVING COUNT(DISTINCT m.id)>0
        ORDER BY c.name_en
    """, get_conn())

@st.cache_data
def get_kpis():
    conn = get_conn()
    return pd.read_sql(f"""
        SELECT
          COUNT(DISTINCT CASE WHEN c.name_en IS NOT NULL AND TRIM(c.name_en)<>'' THEN c.id END) AS compounds,
          COUNT(DISTINCT m.id) AS measurements,
          COUNT(DISTINCT CASE WHEN m.sample_type='pure' THEN m.id END) AS pure_records,
          COUNT(DISTINCT CASE WHEN m.sample_type='mixture' THEN m.id END) AS mixture_records,
          COUNT(DISTINCT m.source_id) AS sources
        FROM measurements m
        JOIN compounds c ON c.id=m.component1_id
        WHERE {BASE_QUALITY}
    """, conn).iloc[0].to_dict()

@st.cache_data
def find_compounds(term):
    term = (term or '').strip()
    if not term:
        return pd.DataFrame(columns=['name_en','name_cn','cas','n_records'])
    s = f"%{term}%"
    return pd.read_sql(f"""
        SELECT c.name_en, c.name_cn, c.cas, COUNT(DISTINCT m.id) AS n_records
        FROM compounds c
        JOIN measurements m ON (m.component1_id=c.id OR m.component2_id=c.id)
        WHERE {BASE_QUALITY}
          AND c.name_en IS NOT NULL AND TRIM(c.name_en)<>''
          AND (c.name_en LIKE ? OR COALESCE(c.name_cn,'') LIKE ? OR c.cas LIKE ?)
        GROUP BY c.id
        ORDER BY CASE WHEN c.cas=? OR c.name_en=? OR c.name_cn=? THEN 0 ELSE 1 END,
                 n_records DESC, c.name_en
        LIMIT 50
    """, get_conn(), params=[s,s,s,term,term,term])

@st.cache_data
def query_data(search='', tmin=None, tmax=None, fmin=None, fmax=None, limit=5000):
    clauses=[BASE_QUALITY, "component1_en IS NOT NULL", "TRIM(component1_en)<>''"]
    params=[]
    if search:
        s=f"%{search.strip()}%"
        clauses.append("""(
            component1_en LIKE ? OR COALESCE(component1_cn,'') LIKE ? OR cas1 LIKE ?
            OR COALESCE(component2_en,'') LIKE ? OR COALESCE(component2_cn,'') LIKE ? OR COALESCE(cas2,'') LIKE ?
        )""")
        params += [s,s,s,s,s,s]
    if tmin is not None and tmax is not None:
        clauses.append("temperature_c BETWEEN ? AND ?")
        params += [tmin,tmax]
    if fmin is not None and fmax is not None:
        clauses.append("frequency_ghz BETWEEN ? AND ?")
        params += [fmin,fmax]
    sql=f"""
    SELECT sample_type AS 类型,
           component1_en AS 组分1英文名, component1_cn AS 组分1中文名, cas1 AS CAS_1,
           component2_en AS 组分2英文名, component2_cn AS 组分2中文名, cas2 AS CAS_2,
           x1 AS 组成1, x2 AS 组成2, composition_basis AS 组成基准,
           temperature_c AS "T / °C", frequency_ghz AS "Frequency / GHz",
           epsilon_static AS "εs", epsilon_real AS "ε′", epsilon_imag AS "ε″",
           data_kind AS 数据类型, source_name AS 数据来源, source_detail AS 来源详情, doi AS DOI
    FROM measurement_view
    WHERE {' AND '.join(clauses)}
    ORDER BY component1_en, component2_en, temperature_c, frequency_ghz
    LIMIT {int(limit)}
    """
    return pd.read_sql(sql, get_conn(), params=params)

compounds = load_compounds()
kpis = get_kpis()

st.title("介电性质数据库 · v4.1")
st.markdown(
    "<div class='title-sub'>有机溶剂与混合溶剂 · 静态介电常数 εs · 介电常数 ε′ · 介电损耗 ε″ · 更新于 2026-09-11</div>",
    unsafe_allow_html=True
)

# Only the four main pages requested by the user.
tab0, tab1, tab2, tab3 = st.tabs(["数据总览", "数据查询", "单物质", "混合物"])

with tab0:
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("物质", f"{int(kpis['compounds']):,}")
    c2.metric("可用数据", f"{int(kpis['measurements']):,}")
    c3.metric("纯物质数据", f"{int(kpis['pure_records']):,}")
    c4.metric("混合物数据", f"{int(kpis['mixture_records']):,}")
    c5.metric("数据源", f"{int(kpis['sources']):,}")
    st.caption("v4.1 修正版：已完整纳入 Deng & Jia (2022)、Bouteloup & Mathieu (2019)、Kohns (2020) 与 LJW 数据；默认不显示 NPL raw 重复测量层。")

    source_stats = pd.read_sql(f"""
        SELECT source_name AS 数据来源, COUNT(*) AS 数据条数,
               SUM(CASE WHEN sample_type='pure' THEN 1 ELSE 0 END) AS 纯物质,
               SUM(CASE WHEN sample_type='mixture' THEN 1 ELSE 0 END) AS 混合物
        FROM measurement_view
        WHERE {BASE_QUALITY}
          AND component1_en IS NOT NULL AND TRIM(component1_en)<>''
        GROUP BY source_name
        ORDER BY 数据条数 DESC
    """, get_conn())
    st.subheader("数据源构成")
    fig = px.bar(source_stats, x="数据来源", y="数据条数", text_auto=True)
    fig.update_layout(height=430, xaxis_tickangle=-25, font_family="Microsoft YaHei, Arial")
    st.plotly_chart(fig, use_container_width=True)

    left,right = st.columns(2)
    with left:
        st.subheader("介电数据类型")
        kind_stats = pd.read_sql(f"""
            SELECT data_kind AS 数据类型, COUNT(*) AS 数据条数
            FROM measurements
            WHERE {BASE_QUALITY}
            GROUP BY data_kind ORDER BY 数据条数 DESC
        """, get_conn())
        st.dataframe(kind_stats, use_container_width=True, hide_index=True)
    with right:
        st.subheader("温度与频率覆盖")
        ranges = pd.read_sql(f"""
            SELECT MIN(temperature_c) Tmin, MAX(temperature_c) Tmax,
                   MIN(frequency_ghz) Fmin, MAX(frequency_ghz) Fmax,
                   COUNT(temperature_c) nT, COUNT(frequency_ghz) nF
            FROM measurements WHERE {BASE_QUALITY}
        """, get_conn()).iloc[0]
        st.metric("温度范围", f"{ranges.Tmin:.1f}–{ranges.Tmax:.1f} °C" if pd.notna(ranges.Tmin) else "—")
        st.metric("频率范围", f"{ranges.Fmin:.5g}–{ranges.Fmax:.5g} GHz" if pd.notna(ranges.Fmin) else "—")
        st.caption(f"含温度记录：{int(ranges.nT):,}；含频率记录：{int(ranges.nF):,}")

with tab1:
    st.subheader("数据查询")
    search = st.text_input("物质名称 / 中文名 / CAS", placeholder="例如：Methanol、甲醇、67-56-1", key="query_search")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        tmin_txt = st.text_input("最低温度 / °C", placeholder="留空=不限", key="tmin")
    with c2:
        tmax_txt = st.text_input("最高温度 / °C", placeholder="留空=不限", key="tmax")
    with c3:
        fmin_txt = st.text_input("最低频率 / GHz", placeholder="留空=不限", key="fmin")
    with c4:
        fmax_txt = st.text_input("最高频率 / GHz", placeholder="留空=不限", key="fmax")

    def to_num(x):
        try: return float(x) if str(x).strip() else None
        except: return None
    tmin,tmax,fmin,fmax = map(to_num,[tmin_txt,tmax_txt,fmin_txt,fmax_txt])
    if (tmin is None) != (tmax is None):
        st.info("温度范围请同时填写最小值和最大值。")
        tmin=tmax=None
    if (fmin is None) != (fmax is None):
        st.info("频率范围请同时填写最小值和最大值。")
        fmin=fmax=None

    df = query_data(search,tmin,tmax,fmin,fmax,5000)
    st.caption(f"当前返回 {len(df):,} 条记录（最多显示 5000 条）")
    st.dataframe(df, use_container_width=True, hide_index=True, height=560)
    st.download_button("下载当前查询结果 CSV", df.to_csv(index=False).encode("utf-8-sig"), "dielectric_query.csv", "text/csv")

with tab2:
    st.subheader("单物质")
    term = st.text_input("输入英文名、中文名或 CAS", placeholder="例如：Methanol / 甲醇 / 67-56-1", key="pure_term")
    matches = find_compounds(term)
    if term and len(matches):
        st.dataframe(matches.rename(columns={"name_en":"英文名","name_cn":"中文名","cas":"CAS","n_records":"记录数"}),
                     use_container_width=True, hide_index=True, height=min(280, 42*(len(matches)+1)))
        cas = st.text_input("输入上表中的 CAS 查看详情", value=str(matches.iloc[0]['cas']), key="pure_cas")
        qdf = pd.read_sql(f"""
            SELECT temperature_c AS "T / °C", frequency_ghz AS "Frequency / GHz",
                   epsilon_static AS "εs", epsilon_real AS "ε′", epsilon_imag AS "ε″",
                   data_kind AS 数据类型, source_name AS 数据来源, source_detail AS 来源详情, doi AS DOI
            FROM measurement_view
            WHERE sample_type='pure' AND cas1=? AND {BASE_QUALITY}
            ORDER BY temperature_c, frequency_ghz
        """, get_conn(), params=[cas])
        if len(qdf):
            info = matches[matches.cas==cas]
            title = info.iloc[0] if len(info) else None
            if title is not None:
                st.markdown(f"### {title['name_en']}  {title['name_cn'] or ''}  ({cas})")
            m1,m2 = st.columns(2)
            m1.metric("记录数", f"{len(qdf):,}")
            m2.metric("来源数", qdf['数据来源'].nunique())

            static = qdf.dropna(subset=['εs','T / °C'])
            complex_df = qdf.dropna(subset=['Frequency / GHz'])
            a,b = st.columns(2)
            with a:
                st.markdown("#### 静态介电常数 vs 温度")
                if len(static):
                    fig = px.scatter(static, x='T / °C', y='εs', color='数据来源')
                    fig.update_layout(height=400, font_family="Microsoft YaHei, Arial")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("暂无带温度的静态介电常数数据。")
            with b:
                st.markdown("#### 复介电性质 vs 频率")
                if len(complex_df):
                    fig = go.Figure()
                    r=complex_df.dropna(subset=['ε′'])
                    im=complex_df.dropna(subset=['ε″'])
                    if len(r): fig.add_trace(go.Scatter(x=r['Frequency / GHz'], y=r['ε′'], mode='markers', name='ε′'))
                    if len(im): fig.add_trace(go.Scatter(x=im['Frequency / GHz'], y=im['ε″'], mode='markers', name='ε″'))
                    fig.update_layout(xaxis_title='Frequency / GHz', yaxis_title='Relative permittivity', height=400, font_family="Microsoft YaHei, Arial")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("暂无频率分辨的 ε′/ε″ 数据。")
            st.dataframe(qdf, use_container_width=True, hide_index=True, height=420)
        elif cas:
            st.warning("没有找到该 CAS 的纯物质介电数据。")
    elif term:
        st.info("没有找到匹配的物质。")
    else:
        st.caption("输入名称或 CAS 后显示匹配物质和介电数据。")

with tab3:
    st.subheader("混合物")
    c1,c2 = st.columns(2)
    with c1:
        term1 = st.text_input("组分 1：名称或 CAS", placeholder="例如 Methanol", key="mix1")
    with c2:
        term2 = st.text_input("组分 2：名称或 CAS", placeholder="例如 Water", key="mix2")

    if term1 and term2:
        a=find_compounds(term1)
        b=find_compounds(term2)
        if len(a) and len(b):
            cas1=str(a.iloc[0]['cas']); cas2=str(b.iloc[0]['cas'])
            mix = pd.read_sql(f"""
                SELECT component1_en AS 组分1, component1_cn AS 组分1中文名, cas1 AS CAS_1,
                       component2_en AS 组分2, component2_cn AS 组分2中文名, cas2 AS CAS_2,
                       x1 AS 组成1, x2 AS 组成2, composition_basis AS 组成基准,
                       temperature_c AS "T / °C", frequency_ghz AS "Frequency / GHz",
                       epsilon_static AS "εs", epsilon_real AS "ε′", epsilon_imag AS "ε″",
                       source_name AS 数据来源, source_detail AS 来源详情
                FROM measurement_view
                WHERE sample_type='mixture' AND {BASE_QUALITY}
                  AND ((cas1=? AND cas2=?) OR (cas1=? AND cas2=?))
                ORDER BY temperature_c, frequency_ghz, x1, x2
            """, get_conn(), params=[cas1,cas2,cas2,cas1])
            if len(mix):
                st.caption(f"找到 {len(mix):,} 条混合物数据；匹配 CAS：{cas1} + {cas2}")
                st.dataframe(mix, use_container_width=True, hide_index=True, height=560)
                st.download_button("下载该混合体系 CSV", mix.to_csv(index=False).encode("utf-8-sig"), "mixture_dielectric.csv", "text/csv")
            else:
                st.info(f"数据库中没有找到 {a.iloc[0]['name_en']} + {b.iloc[0]['name_en']} 的混合物数据。")
        else:
            st.info("至少有一个组分没有匹配到数据库中的标准物质名称/CAS。")
    else:
        st.caption("输入两个组分的名称或 CAS 后查询混合物数据。")

st.divider()
st.caption("SQLite backend · Streamlit interface · 仅显示具有明确物质名称的数据")
