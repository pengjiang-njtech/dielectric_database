import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / 'dielectric.db'
BASE_QUALITY = "LOWER(COALESCE(data_quality,'')) NOT IN ('rejected','excluded','invalid','high_risk','high-risk')"

PROPERTY_FIELDS = [
    ('mass_g_mol','Mass / g mol⁻¹'),
    ('dipole_moment_d','Dipole moment / D'),
    ('hbond_acceptors','H-bond acceptors'),
    ('hbond_donors','H-bond donors'),
    ('logp','LogP'),
    ('polar_surface_area_a2','Polar surface area / Å²'),
    ('polarizability_a3','Polarizability / Å³'),
    ('molar_volume_cm3_mol','Molar volume / cm³ mol⁻¹'),
    ('refractive_index','Refractive index'),
    ('melting_point_c','Melting point / °C'),
    ('boiling_point_c','Boiling point / °C'),
    ('density_g_cm3','Density / g cm⁻³'),
    ('viscosity_mpas','Viscosity / mPa·s'),
]

st.set_page_config(page_title='介电性质数据库', layout='wide', initial_sidebar_state='collapsed')
st.markdown('''<style>
html,body,[class*="css"],[data-testid="stAppViewContainer"]{font-family:"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",Arial,sans-serif;}
.block-container{padding-top:1.1rem;padding-bottom:2rem;max-width:1550px;}
[data-testid="stSidebar"]{display:none;}
[data-testid="stMetricValue"]{font-size:1.48rem;}
.stTabs [data-baseweb="tab"]{font-size:1rem;font-weight:600}
.muted{color:#6b7280;font-size:.92rem}
.small-note{color:#6b7280;font-size:.85rem}
</style>''', unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    if not DB_PATH.exists():
        st.error(f'未找到数据库：{DB_PATH}')
        st.stop()
    c = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def table_exists(name):
    return get_conn().execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def cols_of(table):
    if not table_exists(table):
        return set()
    return {r['name'] for r in get_conn().execute(f'PRAGMA table_info({table})')}


@st.cache_data
def get_kpis():
    return pd.read_sql(f'''SELECT COUNT(DISTINCT c.id) compounds,COUNT(DISTINCT m.id) measurements,
    COUNT(DISTINCT CASE WHEN m.sample_type='pure' THEN m.id END) pure_records,
    COUNT(DISTINCT CASE WHEN m.sample_type='mixture' THEN m.id END) mixture_records,
    COUNT(DISTINCT m.source_id) sources,
    SUM(CASE WHEN lower(COALESCE(m.data_kind,'')) LIKE '%experimental%' THEN 1 ELSE 0 END) experimental_records,
    SUM(CASE WHEN lower(COALESCE(m.method,'')) LIKE '%figure%' THEN 1 ELSE 0 END) figure_records,
    SUM(CASE WHEN lower(COALESCE(m.data_kind,'')) LIKE '%simulat%' OR lower(COALESCE(m.data_kind,'')) LIKE '%predict%'
      OR lower(COALESCE(m.data_kind,'')) LIKE '%calculat%' OR lower(COALESCE(m.data_kind,'')) LIKE '%estimat%'
      OR lower(COALESCE(m.data_kind,'')) LIKE '%correlation%' THEN 1 ELSE 0 END) modeled_records
    FROM measurements m JOIN compounds c ON c.id=m.component1_id
    WHERE {BASE_QUALITY} AND c.name_en IS NOT NULL AND TRIM(c.name_en)<>'' ''', get_conn()).iloc[0].to_dict()


@st.cache_data
def property_completeness():
    if not table_exists('compound_properties'):
        return pd.DataFrame(columns=['Property','Filled','Missing','Completeness'])
    cols = cols_of('compound_properties')
    n = get_conn().execute('SELECT COUNT(*) FROM compound_properties').fetchone()[0]
    out = []
    special = [('smiles','SMILES'), ('molecular_formula','Molecular formula')]
    for f, label in special + PROPERTY_FIELDS:
        if f in cols:
            x = get_conn().execute(f"SELECT COUNT(*) FROM compound_properties WHERE {f} IS NOT NULL AND TRIM(CAST({f} AS TEXT))<>''").fetchone()[0]
            out.append([label, x, max(n-x,0), x/n if n else 0])
    return pd.DataFrame(out, columns=['Property','Filled','Missing','Completeness'])


@st.cache_data
def find_compounds(term):
    term = (term or '').strip()
    if not term:
        return pd.DataFrame(columns=['id','name_en','name_cn','cas','n_records'])
    s = f'%{term}%'
    return pd.read_sql(f'''SELECT c.id,c.name_en,c.name_cn,c.cas,COUNT(DISTINCT m.id) n_records FROM compounds c
    LEFT JOIN measurements m ON (m.component1_id=c.id OR m.component2_id=c.id) AND {BASE_QUALITY}
    WHERE c.name_en LIKE ? OR COALESCE(c.name_cn,'') LIKE ? OR c.cas LIKE ? GROUP BY c.id
    ORDER BY CASE WHEN c.cas=? OR c.name_en=? OR c.name_cn=? THEN 0 ELSE 1 END,n_records DESC,c.name_en LIMIT 80''',
    get_conn(), params=[s,s,s,term,term,term])


@st.cache_data
def get_property_row(cid):
    if not table_exists('compound_properties'):
        return pd.DataFrame()
    return pd.read_sql('''SELECT cp.*,c.name_en,c.name_cn,c.cas compound_cas
        FROM compound_properties cp JOIN compounds c ON c.id=cp.compound_id WHERE cp.compound_id=?''',
        get_conn(), params=[cid])


@st.cache_data
def get_provenance(cid):
    if not table_exists('property_provenance'):
        return pd.DataFrame()
    return pd.read_sql('''SELECT property_name 属性,value 数值,unit 单位,temperature_c "T / °C",pressure_kpa "P / kPa",
    data_type 数据类型,source_type 来源类型,source_name 来源名称,doi DOI,reference Reference,retrieval_date 检索日期,
    original_value 原始值,original_unit 原始单位,notes 备注 FROM property_provenance WHERE compound_id=?
    ORDER BY property_name,source_type,source_name''', get_conn(), params=[cid])


@st.cache_data
def pure_measurements(cas):
    return pd.read_sql(f'''SELECT temperature_c "T / °C",frequency_ghz "Frequency / GHz",epsilon_static "εs",
    epsilon_real "ε′",epsilon_imag "ε″",data_kind 数据类型,method 提取方法,source_name 数据来源,
    source_detail 来源详情,doi DOI,notes 备注 FROM measurement_view
    WHERE sample_type='pure' AND cas1=? AND {BASE_QUALITY} ORDER BY temperature_c,frequency_ghz''', get_conn(), params=[cas])


@st.cache_data
def query_data(search='', tmin=None, tmax=None, fmin=None, fmax=None, limit=5000):
    clauses = [BASE_QUALITY, "component1_en IS NOT NULL", "TRIM(component1_en)<>''"]
    params = []
    if search:
        s = f'%{search.strip()}%'
        clauses.append("(component1_en LIKE ? OR COALESCE(component1_cn,'') LIKE ? OR cas1 LIKE ? OR COALESCE(component2_en,'') LIKE ? OR COALESCE(component2_cn,'') LIKE ? OR COALESCE(cas2,'') LIKE ?)")
        params += [s,s,s,s,s,s]
    if tmin is not None and tmax is not None:
        clauses.append('temperature_c BETWEEN ? AND ?'); params += [tmin,tmax]
    if fmin is not None and fmax is not None:
        clauses.append('frequency_ghz BETWEEN ? AND ?'); params += [fmin,fmax]
    return pd.read_sql(f'''SELECT sample_type 类型,component1_en 组分1英文名,component1_cn 组分1中文名,cas1 CAS_1,
    component2_en 组分2英文名,component2_cn 组分2中文名,cas2 CAS_2,x1 组成1,x2 组成2,composition_basis 组成基准,
    temperature_c "T / °C",frequency_ghz "Frequency / GHz",epsilon_static "εs",epsilon_real "ε′",epsilon_imag "ε″",
    data_kind 数据类型,method 提取方法,source_name 数据来源,source_detail 来源详情,doi DOI,notes 备注
    FROM measurement_view WHERE {' AND '.join(clauses)}
    ORDER BY component1_en,component2_en,temperature_c,frequency_ghz LIMIT {int(limit)}''', get_conn(), params=params)


def tonum(x):
    try:
        return float(x) if str(x).strip() else None
    except Exception:
        return None


def add_T(df):
    z = df.copy()
    z['Temperature'] = z['T / °C'].apply(lambda v: 'T unknown' if pd.isna(v) else f'{v:g} °C')
    return z


def legend_above(fig, title=None):
    fig.update_layout(
        height=450,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        legend_title_text=title,
        margin=dict(t=90, l=40, r=30, b=45),
    )
    return fig


def csv_button(df, label, filename, key):
    st.download_button(label, df.to_csv(index=False).encode('utf-8-sig'), filename, 'text/csv', key=key)


def compact_sources(df):
    z = df.copy()
    srcs = [x for x in z['数据来源'].dropna().astype(str).unique()]
    mapping = {s: f'S{i+1}' for i, s in enumerate(srcs)}
    z['Source ID'] = z['数据来源'].astype(str).map(mapping).fillna('Unknown')
    source_table = pd.DataFrame([{'Source ID': sid, '数据来源': s} for s, sid in mapping.items()])
    return z, source_table


def make_spectrum_data(df, group_col='Temperature'):
    f = df.dropna(subset=['Frequency / GHz']).copy()
    if f.empty:
        return pd.DataFrame()
    if group_col == 'Temperature':
        f = add_T(f)
    parts = []
    for col in ['ε′','ε″']:
        keep = ['Frequency / GHz','T / °C',col]
        if group_col in f.columns and group_col not in keep:
            keep.append(group_col)
        z = f.dropna(subset=[col])[keep].rename(columns={col:'Value'})
        if len(z):
            z['Property'] = col
            parts.append(z)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def fmt_value(field, value):
    if value is None or pd.isna(value):
        return '—'
    if field in ('hbond_acceptors','hbond_donors'):
        try: return f'{int(round(float(value)))}'
        except Exception: return str(value)
    try:
        return f'{float(value):.3f}'
    except Exception:
        return str(value)


kpis = get_kpis()
comp_prop = property_completeness()
st.title('介电性质数据库 · v5.4')
st.markdown("<div class='muted'>v5.4 · 介电数据 + 基础分子物性 + 来源追溯 + 图表数据下载 + 完整性检查。查询软件为只读模式，不会修改数据库。</div>", unsafe_allow_html=True)
tabs = st.tabs(['数据总览','数据查询','单物质','混合物','数据完整性'])

with tabs[0]:
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric('物质', f"{int(kpis['compounds']):,}")
    c2.metric('可用数据', f"{int(kpis['measurements']):,}")
    c3.metric('纯物质', f"{int(kpis['pure_records']):,}")
    c4.metric('混合物', f"{int(kpis['mixture_records']):,}")
    c5.metric('数据源', f"{int(kpis['sources']):,}")
    c1,c2,c3 = st.columns(3)
    c1.metric('实验数据', f"{int(kpis['experimental_records'] or 0):,}")
    c2.metric('图像数字化', f"{int(kpis['figure_records'] or 0):,}")
    c3.metric('模拟/预测/关联式', f"{int(kpis['modeled_records'] or 0):,}")
    st.subheader('数据源构成')
    src = pd.read_sql(f'''SELECT source_name 数据来源,COUNT(*) 数据条数 FROM measurement_view
        WHERE {BASE_QUALITY} GROUP BY source_name ORDER BY 数据条数 DESC''', get_conn())
    if len(src):
        fig = px.bar(src.head(25), x='数据来源', y='数据条数', text_auto=True)
        fig.update_layout(height=480, xaxis_tickangle=-30, margin=dict(t=45,b=100))
        st.plotly_chart(fig, use_container_width=True)
        csv_button(src, '下载数据源统计 CSV', 'source_summary.csv', 'dl_source_summary')

with tabs[1]:
    st.subheader('数据查询')
    search = st.text_input('物质名称 / 中文名 / CAS', placeholder='例如 Methanol、甲醇、67-56-1', key='q_search')
    a,b,c,d = st.columns(4)
    tmin = tonum(a.text_input('最低温度 / °C'))
    tmax = tonum(b.text_input('最高温度 / °C'))
    fmin = tonum(c.text_input('最低频率 / GHz'))
    fmax = tonum(d.text_input('最高频率 / GHz'))
    if (tmin is None) != (tmax is None):
        st.info('温度范围需同时填写上下限。'); tmin=tmax=None
    if (fmin is None) != (fmax is None):
        st.info('频率范围需同时填写上下限。'); fmin=fmax=None
    df = query_data(search,tmin,tmax,fmin,fmax)
    st.caption(f'返回 {len(df):,} 条（最多 5000 条）')
    st.dataframe(df, use_container_width=True, hide_index=True, height=560)
    csv_button(df, '下载当前查询结果 CSV', 'dielectric_query.csv', 'dl_query')

with tabs[2]:
    st.subheader('单物质查询')
    term = st.text_input('英文名 / 中文名 / CAS', placeholder='Methanol / 甲醇 / 67-56-1', key='single_term')
    matches = find_compounds(term)
    if term and len(matches):
        st.dataframe(matches[['name_en','name_cn','cas','n_records']].rename(columns={
            'name_en':'英文名','name_cn':'中文名','cas':'CAS','n_records':'介电记录数'}),
            use_container_width=True, hide_index=True, height=min(260,38*(len(matches)+1)))
        opts = {f"{r.name_en} | {r.cas}": int(r.id) for _,r in matches.iterrows()}
        pick = st.selectbox('选择物质', list(opts))
        cid = opts[pick]
        row = matches[matches.id==cid].iloc[0]
        cas = row.cas
        st.markdown(f"### {row.name_en}  {row.name_cn or ''}  ({cas})")

        pr = get_property_row(cid)
        if len(pr):
            r = pr.iloc[0]
            st.markdown('#### 基础分子性质')
            if 'molecular_formula' in pr.columns:
                st.write(f"**Molecular formula:** {r.get('molecular_formula') if pd.notna(r.get('molecular_formula')) else '—'}")
            if 'smiles' in pr.columns:
                st.write(f"**SMILES:** {r.get('smiles') if pd.notna(r.get('smiles')) else '—'}")
            items = [(f,l,r.get(f)) for f,l in PROPERTY_FIELDS if f in pr.columns]
            cols = st.columns(4)
            for i,(f,l,v) in enumerate(items):
                cols[i%4].metric(l, fmt_value(f,v))
            prov = get_provenance(cid)
            if len(prov):
                with st.expander('查看基础物性来源与实验条件', expanded=False):
                    st.dataframe(prov, use_container_width=True, hide_index=True)
                    csv_button(prov, '下载基础物性来源 CSV', f'property_provenance_{cas}.csv', f'dl_prov_{cid}')

        q = pure_measurements(cas)
        st.markdown('#### 介电性质')
        if len(q):
            static = q.dropna(subset=['εs','T / °C']).copy()
            if len(static):
                static_plot, source_table = compact_sources(static)
                fig = px.scatter(static_plot, x='T / °C', y='εs', color='Source ID',
                                 hover_data=['数据来源','DOI','数据类型'], title='静态介电常数–温度')
                legend_above(fig, '数据源')
                st.plotly_chart(fig, use_container_width=True)
                csv_button(static, '下载该图数据 CSV', f'{cas}_epsilon_static_vs_T.csv', f'dl_static_{cid}')
                if len(source_table):
                    with st.expander('数据源编号对应关系', expanded=False):
                        st.dataframe(source_table, use_container_width=True, hide_index=True)
            else:
                st.info('暂无带温度的 εs 数据。')

            spectrum_data = make_spectrum_data(q, 'Temperature')
            if len(spectrum_data):
                fig = px.line(spectrum_data, x='Frequency / GHz', y='Value', color='Temperature',
                              line_dash='Property', markers=True, hover_data=['T / °C','Property'],
                              title='频率介电谱（按温度分组）')
                legend_above(fig, '温度 / 性质')
                st.plotly_chart(fig, use_container_width=True)
                csv_button(spectrum_data, '下载该图数据 CSV', f'{cas}_dielectric_spectrum.csv', f'dl_spectrum_{cid}')
            else:
                st.info('暂无频率分辨 ε′/ε″。')

            cc = q.dropna(subset=['ε′','ε″']).copy()
            if len(cc):
                cc = add_T(cc)
                fig = px.line(cc.sort_values(['T / °C','Frequency / GHz']), x='ε′', y='ε″',
                              color='Temperature', markers=True, hover_data=['Frequency / GHz','T / °C','数据来源'],
                              title='Cole–Cole 图（弛豫一致性检查）')
                legend_above(fig, '温度')
                st.plotly_chart(fig, use_container_width=True)
                csv_button(cc, '下载该图数据 CSV', f'{cas}_cole_cole.csv', f'dl_cc_{cid}')
            else:
                st.info('需要同一记录同时具有 ε′ 与 ε″ 才能绘制 Cole–Cole 图。')

            st.dataframe(q, use_container_width=True, hide_index=True, height=430)
            csv_button(q, '下载该物质全部介电数据 CSV', f'{cas}_dielectric_all.csv', f'dl_pure_{cid}')
        else:
            st.info('暂无该物质的纯物质介电记录。')
    elif term:
        st.info('未找到匹配物质。')
    else:
        st.caption('输入名称或 CAS 后查看基础物性与介电数据。')

with tabs[3]:
    st.subheader('混合物查询')
    a,b = st.columns(2)
    t1 = a.text_input('Component 1：名称或 CAS', key='mix_a')
    t2 = b.text_input('Component 2：名称或 CAS', key='mix_b')
    if t1 and t2:
        m1 = find_compounds(t1); m2 = find_compounds(t2)
        if len(m1) and len(m2):
            cas1 = str(m1.iloc[0].cas); cas2 = str(m2.iloc[0].cas)
            mix = pd.read_sql(f'''SELECT component1_en 组分1,cas1 CAS_1,component2_en 组分2,cas2 CAS_2,x1,x2,composition_basis 组成基准,
            temperature_c "T / °C",frequency_ghz "Frequency / GHz",epsilon_static "εs",epsilon_real "ε′",epsilon_imag "ε″",
            data_kind 数据类型,method 提取方法,source_name 数据来源,doi DOI,notes 备注 FROM measurement_view
            WHERE sample_type='mixture' AND {BASE_QUALITY} AND ((cas1=? AND cas2=?) OR (cas1=? AND cas2=?))
            ORDER BY temperature_c,frequency_ghz,x1,x2''', get_conn(), params=[cas1,cas2,cas2,cas1])
            if len(mix):
                c1,c2,c3 = st.columns(3)
                c1.metric('记录数', f'{len(mix):,}')
                c2.metric('温度点', mix['T / °C'].nunique(dropna=True))
                c3.metric('频率点', mix['Frequency / GHz'].nunique(dropna=True))
                if mix.x1.notna().any():
                    st.caption(f"x1 范围：{mix.x1.min():.4g}–{mix.x1.max():.4g}")
                st.markdown('#### 混合物介电行为')

                ss = mix.dropna(subset=['x1','εs']).copy()
                if len(ss):
                    ss = add_T(ss)
                    fig = px.line(ss.sort_values(['T / °C','x1']), x='x1', y='εs', color='Temperature',
                                  markers=True, hover_data=['数据来源','DOI'], title='εs–组成关系（按温度）')
                    legend_above(fig, '温度')
                    st.plotly_chart(fig, use_container_width=True)
                    csv_button(ss, '下载该图数据 CSV', f'{cas1}_{cas2}_epsilon_static_vs_x1.csv', 'dl_mix_static')
                else:
                    st.info('暂无可绘制的 εs–组成数据。')

                ff = mix.dropna(subset=['Frequency / GHz']).copy()
                parts = []
                if len(ff):
                    ff['Composition'] = ff.x1.apply(lambda v: 'x1 unknown' if pd.isna(v) else f'x1={v:g}')
                    for col in ['ε′','ε″']:
                        z = ff.dropna(subset=[col])[['Frequency / GHz','Composition','T / °C','x1','x2','数据来源','DOI',col]].rename(columns={col:'Value'})
                        if len(z):
                            z['Property'] = col
                            parts.append(z)
                if parts:
                    z = pd.concat(parts, ignore_index=True)
                    fig = px.line(z, x='Frequency / GHz', y='Value', color='Composition', line_dash='Property',
                                  markers=True, hover_data=['T / °C','数据来源','DOI'], title='频率介电谱（按组成）')
                    legend_above(fig, '组成 / 性质')
                    st.plotly_chart(fig, use_container_width=True)
                    csv_button(z, '下载该图数据 CSV', f'{cas1}_{cas2}_dielectric_spectrum.csv', 'dl_mix_spectrum')
                else:
                    st.info('暂无频率分辨混合物数据。')

                cc = mix.dropna(subset=['ε′','ε″']).copy()
                if len(cc):
                    cc['Composition'] = cc.x1.apply(lambda v: 'x1 unknown' if pd.isna(v) else f'x1={v:g}')
                    fig = px.line(cc.sort_values(['x1','T / °C','Frequency / GHz']), x='ε′', y='ε″',
                                  color='Composition', markers=True, hover_data=['Frequency / GHz','T / °C','数据来源','DOI'],
                                  title='混合物 Cole–Cole 图（按组成）')
                    legend_above(fig, '组成')
                    st.plotly_chart(fig, use_container_width=True)
                    csv_button(cc, '下载该图数据 CSV', f'{cas1}_{cas2}_cole_cole.csv', 'dl_mix_cc')
                else:
                    st.info('暂无可绘制的混合物 Cole–Cole 数据。')

                st.dataframe(mix, use_container_width=True, hide_index=True, height=520)
                csv_button(mix, '下载该混合体系全部数据 CSV', f'{cas1}_{cas2}_mixture_dielectric.csv', 'dl_mix_all')
            else:
                st.info('数据库中没有找到该二元体系。')
        else:
            st.info('至少有一个组分未匹配到标准物质。')
    else:
        st.caption('输入两个组分后查询。')

with tabs[4]:
    st.subheader('数据完整性与追溯')
    a,b,c,d = st.columns(4)
    dup = get_conn().execute('''SELECT COUNT(*) FROM (SELECT sample_type,component1_id,component2_id,x1,x2,composition_basis,temperature_c,frequency_ghz,epsilon_static,epsilon_real,epsilon_imag,doi,COUNT(*) n FROM measurements GROUP BY sample_type,component1_id,component2_id,x1,x2,composition_basis,temperature_c,frequency_ghz,epsilon_static,epsilon_real,epsilon_imag,doi HAVING COUNT(*)>1)''').fetchone()[0]
    missing = get_conn().execute(f"SELECT COUNT(*) FROM measurements WHERE {BASE_QUALITY} AND (doi IS NULL OR TRIM(doi)='')").fetchone()[0]
    a.metric('完全重复组', f'{dup:,}')
    b.metric('可用记录缺 DOI', f'{missing:,}')
    if table_exists('property_provenance'):
        n = get_conn().execute('SELECT COUNT(*) FROM property_provenance').fetchone()[0]
        m = get_conn().execute("SELECT COUNT(*) FROM property_provenance WHERE source_name IS NULL OR TRIM(source_name)=''").fetchone()[0]
        c.metric('物性来源记录', f'{n:,}')
        d.metric('物性来源缺失', f'{m:,}')
    if len(comp_prop):
        show = comp_prop.copy()
        show['Completeness'] = show.Completeness.map(lambda x:f'{x:.1%}')
        st.markdown('#### 基础物性缺失统计')
        st.dataframe(show.rename(columns={'Property':'属性','Filled':'已填','Missing':'缺失','Completeness':'完整率'}),
                     use_container_width=True, hide_index=True)
        csv_button(show, '下载基础物性完整性统计 CSV', 'property_completeness.csv', 'dl_completeness')
    st.markdown('#### 数据质量标签统计')
    kinds = pd.read_sql('SELECT COALESCE(data_quality,"(空)") 数据质量,COUNT(*) 记录数 FROM measurements GROUP BY data_quality ORDER BY 记录数 DESC', get_conn())
    st.dataframe(kinds, use_container_width=True, hide_index=True)
    csv_button(kinds, '下载质量标签统计 CSV', 'data_quality_summary.csv', 'dl_quality')

st.divider()
st.caption('SQLite backend · Streamlit interface · read-only query mode · v5.4')
