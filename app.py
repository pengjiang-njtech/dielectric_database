
import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "dielectric.db"

st.set_page_config(
    page_title="Dielectric Property Database",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top: 1.3rem; padding-bottom: 2rem;}
[data-testid="stMetricValue"] {font-size: 1.75rem;}
.small-note {color:#5f6b7a; font-size:0.9rem;}
.title-sub {color:#5f6b7a; margin-top:-12px;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@st.cache_data
def load_sources():
    return pd.read_sql("SELECT * FROM sources ORDER BY source_name", get_conn())

@st.cache_data
def load_compounds():
    return pd.read_sql("""
        SELECT c.id, c.name_en, c.name_cn, c.cas,
               COUNT(m.id) AS n_records
        FROM compounds c
        LEFT JOIN measurements m
          ON m.component1_id=c.id OR m.component2_id=c.id
        GROUP BY c.id
        ORDER BY c.name_en
    """, get_conn())

@st.cache_data
def get_kpis():
    conn=get_conn()
    q = """
    SELECT
      (SELECT COUNT(*) FROM compounds) AS compounds,
      (SELECT COUNT(*) FROM measurements) AS measurements,
      (SELECT COUNT(*) FROM measurements WHERE sample_type='pure') AS pure_records,
      (SELECT COUNT(*) FROM measurements WHERE sample_type='mixture') AS mixture_records,
      (SELECT COUNT(*) FROM sources) AS sources
    """
    return pd.read_sql(q,conn).iloc[0].to_dict()

def quality_clause(mode):
    if mode == "Recommended only":
        return "data_quality = 'recommended'"
    if mode == "Recommended + literature-mined":
        return "data_quality IN ('recommended','literature_mined')"
    return "1=1"

def dataframe_from_filters(search, sample_types, source_keys, data_kinds, quality_mode,
                           use_temp, tmin, tmax, use_freq, fmin, fmax, limit=5000):
    clauses=[quality_clause(quality_mode)]
    params=[]
    if search:
        clauses.append("""(
            component1_en LIKE ? OR component1_cn LIKE ? OR cas1 LIKE ?
            OR COALESCE(component2_en,'') LIKE ? OR COALESCE(component2_cn,'') LIKE ?
            OR COALESCE(cas2,'') LIKE ?
        )""")
        s=f"%{search}%"
        params += [s,s,s,s,s,s]
    if sample_types:
        clauses.append("sample_type IN (%s)" % ",".join("?"*len(sample_types)))
        params += sample_types
    if source_keys:
        clauses.append("source_key IN (%s)" % ",".join("?"*len(source_keys)))
        params += source_keys
    if data_kinds:
        clauses.append("data_kind IN (%s)" % ",".join("?"*len(data_kinds)))
        params += data_kinds
    if use_temp:
        clauses.append("temperature_c BETWEEN ? AND ?")
        params += [tmin,tmax]
    if use_freq:
        clauses.append("frequency_ghz BETWEEN ? AND ?")
        params += [fmin,fmax]

    sql=f"""
    SELECT id, sample_type,
           component1_en AS component_1, component1_cn AS component_1_cn, cas1,
           component2_en AS component_2, component2_cn AS component_2_cn, cas2,
           x1, x2, composition_basis,
           temperature_c AS "T / °C", frequency_ghz AS "Frequency / GHz",
           epsilon_static AS "εs", epsilon_real AS "ε′", epsilon_imag AS "ε″",
           data_kind, data_quality, method,
           source_name, source_detail, doi, notes
    FROM measurement_view
    WHERE {' AND '.join(clauses)}
    ORDER BY component1_en, temperature_c, frequency_ghz
    LIMIT {int(limit)}
    """
    return pd.read_sql(sql,get_conn(),params=params)

sources=load_sources()
compounds=load_compounds()
kpis=get_kpis()

st.title("⚡ Dielectric Property Database")
st.markdown(
    "<div class='title-sub'>有机溶剂 / 混合溶剂介电性质数据库 · 静态介电常数 εs · 介电实部 ε′ · 介电损耗 ε″</div>",
    unsafe_allow_html=True
)

with st.sidebar:
    st.header("数据筛选")
    quality_mode=st.radio(
        "数据层级",
        ["Recommended only","Recommended + literature-mined","All (include raw NPL)"],
        index=0,
        help="默认推荐值不包含自动文献挖掘数据和 NPL 原始重复测量。"
    )
    sample_types=st.multiselect("样品类型",["pure","mixture"],default=["pure","mixture"])
    source_options=dict(zip(sources["source_key"],sources["source_name"]))
    source_keys=st.multiselect(
        "数据来源",
        list(source_options.keys()),
        format_func=lambda x: source_options[x]
    )
    data_kind_values=pd.read_sql(
        "SELECT DISTINCT data_kind FROM measurements WHERE data_kind IS NOT NULL ORDER BY data_kind",
        get_conn()
    )["data_kind"].tolist()
    data_kinds=st.multiselect("数据类型",data_kind_values)
    st.divider()
    st.caption("界面默认以可靠来源为主；需要大规模机器学习数据时再加入 literature-mined。")

tab0,tab1,tab2,tab3,tab4 = st.tabs(
    ["📊 总览","🔎 数据查询","🧪 单物质","🧬 混合物","📚 来源比较"]
)

with tab0:
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("物质",f"{kpis['compounds']:,}")
    c2.metric("总数据",f"{kpis['measurements']:,}")
    c3.metric("纯物质",f"{kpis['pure_records']:,}")
    c4.metric("混合体系",f"{kpis['mixture_records']:,}")
    c5.metric("数据源",f"{kpis['sources']:,}")

    st.subheader("数据源构成")
    source_stats=pd.read_sql("""
        SELECT source_name, source_type,
               COUNT(*) AS records,
               SUM(CASE WHEN sample_type='pure' THEN 1 ELSE 0 END) AS pure_records,
               SUM(CASE WHEN sample_type='mixture' THEN 1 ELSE 0 END) AS mixture_records
        FROM measurement_view
        GROUP BY source_name, source_type
        ORDER BY records DESC
    """,get_conn())
    fig=px.bar(source_stats,x="source_name",y="records",color="source_type",
               labels={"source_name":"来源","records":"数据条数","source_type":"来源类型"})
    fig.update_layout(height=420,xaxis_tickangle=-25,legend_title_text="")
    st.plotly_chart(fig,use_container_width=True)

    left,right=st.columns([1.1,1])
    with left:
        st.subheader("数据类型")
        kind_stats=pd.read_sql("""
            SELECT data_kind, COUNT(*) AS records
            FROM measurements GROUP BY data_kind ORDER BY records DESC
        """,get_conn())
        st.dataframe(kind_stats,use_container_width=True,hide_index=True)
    with right:
        st.subheader("温度与频率覆盖")
        ranges=pd.read_sql("""
            SELECT MIN(temperature_c) AS Tmin, MAX(temperature_c) AS Tmax,
                   MIN(frequency_ghz) AS Fmin, MAX(frequency_ghz) AS Fmax,
                   COUNT(temperature_c) AS nT, COUNT(frequency_ghz) AS nF
            FROM measurements
        """,get_conn()).iloc[0]
        st.metric("温度范围",f"{ranges.Tmin:.1f}–{ranges.Tmax:.1f} °C" if pd.notna(ranges.Tmin) else "—")
        st.metric("频率范围",f"{ranges.Fmin:.5g}–{ranges.Fmax:.5g} GHz" if pd.notna(ranges.Fmin) else "—")
        st.caption(f"含温度记录：{int(ranges.nT):,}；含频率记录：{int(ranges.nF):,}")

with tab1:
    a,b,c=st.columns([1.4,1,1])
    with a:
        search=st.text_input("物质 / 中文名 / CAS",placeholder="例如：Methanol、甲醇、67-56-1")
    temp_avail=pd.read_sql("SELECT MIN(temperature_c) mn, MAX(temperature_c) mx FROM measurements",get_conn()).iloc[0]
    freq_avail=pd.read_sql("SELECT MIN(frequency_ghz) mn, MAX(frequency_ghz) mx FROM measurements",get_conn()).iloc[0]
    with b:
        use_temp=st.checkbox("限制温度")
        if use_temp:
            tr=st.slider("T / °C",float(temp_avail.mn),float(temp_avail.mx),(max(float(temp_avail.mn),0.0),min(float(temp_avail.mx),100.0)))
        else:
            tr=(float(temp_avail.mn),float(temp_avail.mx))
    with c:
        use_freq=st.checkbox("限制频率")
        if use_freq:
            fr=st.slider("Frequency / GHz",float(freq_avail.mn),float(freq_avail.mx),(float(freq_avail.mn),min(float(freq_avail.mx),5.0)))
        else:
            fr=(float(freq_avail.mn),float(freq_avail.mx))

    limit=st.selectbox("最大显示行数",[500,1000,5000,20000],index=2)
    df=dataframe_from_filters(
        search,sample_types,source_keys,data_kinds,quality_mode,
        use_temp,tr[0],tr[1],use_freq,fr[0],fr[1],limit
    )
    st.caption(f"当前返回 {len(df):,} 条记录")
    st.dataframe(df,use_container_width=True,hide_index=True,height=520)
    st.download_button(
        "⬇️ 下载当前筛选结果 CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        "dielectric_filtered.csv","text/csv"
    )

with tab2:
    labels=(compounds["name_en"]+" | "+compounds["name_cn"].fillna("")+" | "+compounds["cas"])
    pick=st.selectbox("选择物质",labels.tolist(),index=labels.str.contains("Methanol").argmax() if labels.str.contains("Methanol").any() else 0)
    cas=pick.split(" | ")[-1]
    cinfo=compounds[compounds.cas==cas].iloc[0]
    qdf=pd.read_sql("""
        SELECT temperature_c,frequency_ghz,epsilon_static,epsilon_real,epsilon_imag,
               data_kind,data_quality,source_name,source_detail,doi,method
        FROM measurement_view
        WHERE sample_type='pure' AND cas1=?
        ORDER BY temperature_c,frequency_ghz
    """,get_conn(),params=[cas])
    if quality_mode=="Recommended only":
        qdf=qdf[qdf.data_quality=="recommended"]
    elif quality_mode=="Recommended + literature-mined":
        qdf=qdf[qdf.data_quality.isin(["recommended","literature_mined"])]

    m1,m2,m3=st.columns(3)
    m1.metric("CAS",cas)
    m2.metric("记录数",f"{len(qdf):,}")
    m3.metric("来源数",qdf["source_name"].nunique())
    st.caption(f"{cinfo.name_en} · {cinfo.name_cn if pd.notna(cinfo.name_cn) else ''}")

    static=qdf.dropna(subset=["epsilon_static","temperature_c"])
    complexdf=qdf.dropna(subset=["frequency_ghz"]).copy()

    col1,col2=st.columns(2)
    with col1:
        st.subheader("静态介电常数 vs 温度")
        if len(static):
            fig=px.scatter(static,x="temperature_c",y="epsilon_static",color="source_name",
                           labels={"temperature_c":"T / °C","epsilon_static":"εs","source_name":"来源"})
            fig.update_traces(marker_size=8)
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("当前筛选下没有带温度的 εs 数据。")
    with col2:
        st.subheader("复介电性质 vs 频率")
        if len(complexdf):
            temps=sorted(complexdf["temperature_c"].dropna().unique().tolist())
            if temps:
                target=st.select_slider("选择温度 / °C",options=temps,value=temps[len(temps)//2])
                plotdf=complexdf[(complexdf.temperature_c==target) | complexdf.temperature_c.isna()]
            else:
                plotdf=complexdf
            fig=go.Figure()
            r=plotdf.dropna(subset=["epsilon_real"])
            im=plotdf.dropna(subset=["epsilon_imag"])
            if len(r):
                fig.add_trace(go.Scatter(x=r.frequency_ghz,y=r.epsilon_real,mode="markers+lines",name="ε′"))
            if len(im):
                fig.add_trace(go.Scatter(x=im.frequency_ghz,y=im.epsilon_imag,mode="markers+lines",name="ε″"))
            fig.update_layout(xaxis_title="Frequency / GHz",yaxis_title="Relative permittivity",height=420)
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("当前筛选下没有频率分辨的 ε′/ε″ 数据。")

    st.subheader("全部记录")
    st.dataframe(qdf,use_container_width=True,hide_index=True,height=420)

with tab3:
    pairs=pd.read_sql("""
        SELECT DISTINCT component1_en, component1_cn, cas1, component2_en, component2_cn, cas2
        FROM measurement_view
        WHERE sample_type='mixture'
        ORDER BY component1_en, component2_en
    """,get_conn())
    if len(pairs):
        pair_labels=(pairs.component1_en+" + "+pairs.component2_en+" | "+pairs.cas1+" + "+pairs.cas2)
        pair=st.selectbox("选择混合体系",pair_labels.tolist())
        left=pair.split(" | ")[0]
        c1name,c2name=[x.strip() for x in left.split(" + ",1)]
        mix=pd.read_sql("""
            SELECT component1_en, component2_en,cas1,cas2,x1,x2,composition_basis,
                   temperature_c,frequency_ghz,epsilon_static,epsilon_real,epsilon_imag,
                   data_kind,data_quality,source_name,source_detail,notes
            FROM measurement_view
            WHERE sample_type='mixture' AND component1_en=? AND component2_en=?
            ORDER BY x2,temperature_c,frequency_ghz
        """,get_conn(),params=[c1name,c2name])
        if quality_mode=="Recommended only":
            mix=mix[mix.data_quality=="recommended"]
        elif quality_mode=="Recommended + literature-mined":
            mix=mix[mix.data_quality.isin(["recommended","literature_mined"])]

        st.caption(f"{len(mix):,} 条记录")
        numeric_comp=mix.dropna(subset=["x2"])
        if len(numeric_comp):
            prop=st.selectbox("绘图性质",["epsilon_static","epsilon_real","epsilon_imag"])
            p=numeric_comp.dropna(subset=[prop])
            if len(p):
                fig=px.scatter(p,x="x2",y=prop,color="temperature_c",
                               symbol="source_name",
                               labels={"x2":"Component 2 fraction",prop:prop,"temperature_c":"T / °C","source_name":"来源"})
                st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("该体系的组成数值不完整，先展示原始数据表。")
        st.dataframe(mix,use_container_width=True,hide_index=True,height=480)
    else:
        st.info("当前数据库没有混合物数据。")

with tab4:
    st.subheader("同一物质的来源对照")
    pick2=st.selectbox("物质",labels.tolist(),key="source_compare")
    cas2=pick2.split(" | ")[-1]
    comp=pd.read_sql("""
        SELECT source_name,data_kind,data_quality,
               COUNT(*) AS records,
               MIN(temperature_c) AS Tmin,MAX(temperature_c) AS Tmax,
               MIN(frequency_ghz) AS Fmin,MAX(frequency_ghz) AS Fmax,
               AVG(epsilon_static) AS mean_es,
               AVG(epsilon_real) AS mean_ep,
               AVG(epsilon_imag) AS mean_epp
        FROM measurement_view
        WHERE cas1=? AND sample_type='pure'
        GROUP BY source_name,data_kind,data_quality
        ORDER BY source_name,data_kind
    """,get_conn(),params=[cas2])
    st.dataframe(comp,use_container_width=True,hide_index=True)
    st.markdown("""
    <div class='small-note'>
    建议：静态 εs 优先参考 CRC / Dean / NPL / 专门静态数据库；频率分辨 ε′、ε″优先参考 NPL 和 Gabriel 等实验数据。
    Scidata 属于自动文献挖掘数据，适合扩大机器学习样本量，但默认不作为高精度基准值。
    </div>
    """,unsafe_allow_html=True)

st.divider()
st.caption("Database build: 7 imported sources · SQLite backend · Streamlit interface")
