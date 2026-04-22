import streamlit as st
import pandas as pd
import numpy as np
import os
import itertools

# ==========================================
# ⚙️ 1. 全局配置与状态初始化
# ==========================================
st.set_page_config(page_title="LottoTech 智能量化终端", layout="wide")

if 'main_nav' not in st.session_state: st.session_state.main_nav = '首页'
if 'sub_nav' not in st.session_state: st.session_state.sub_nav = '红球定位'
if 'lottery_type' not in st.session_state: st.session_state.lottery_type = '大乐透'
if 'filter_conditions' not in st.session_state: st.session_state.filter_conditions = []
if 'show_results' not in st.session_state: st.session_state.show_results = False

if 'b1_set' not in st.session_state: st.session_state.b1_set = set(range(1, 12))
if 'b2_set' not in st.session_state: st.session_state.b2_set = set(range(2, 13))
if 'bs_set' not in st.session_state: st.session_state.bs_set = set(range(1, 17))
if 'b_method' not in st.session_state: st.session_state.b_method = "循环使用"

# ==========================================
# 🎨 2. 全局 UI 样式
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;}
    ::-webkit-scrollbar {width: 6px; height: 6px;}
    ::-webkit-scrollbar-thumb {background: #00bcd4; border-radius: 3px;}

    div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none !important; }
    div[role="radiogroup"] { flex-direction: row; flex-wrap: wrap; gap: 15px; margin-bottom: 5px;}
    div[role="radiogroup"] label[data-baseweb="radio"] p { font-size: 16px; color: #888; margin: 0; padding: 5px 0px; cursor: pointer; transition: 0.2s; }
    div[role="radiogroup"] label[data-baseweb="radio"]:hover p { color: #ccc; }
    div[role="radiogroup"] label[data-baseweb="radio"] input:checked + div p { font-size: 22px !important; font-weight: 900 !important; color: #fff !important; }

    .analysis-frame { border: 2px solid #00FF7F; border-radius: 2px; padding: 30px; min-height: 60vh; margin-top: 10px; text-align: center; display: flex; flex-direction: column; justify-content: center; }
    .red-ball { background: #ff4b4b; color: white; border-radius: 50%; padding: 8px 12px; margin: 3px; display: inline-block; font-weight: bold;}
    .blue-ball { background: #00bcd4; color: white; border-radius: 50%; padding: 8px 12px; margin: 3px; display: inline-block; font-weight: bold;}
    .home-card { background: #1e2129; padding: 20px; border-radius: 8px; text-align: center; margin-top: 20px;}

    .stat-card { background-color: #1e2129; padding: 15px; border-radius: 8px; border: 1px solid #444; margin-bottom: 15px; text-align:center;}
    .alert-card { border-left: 5px solid #ff4b4b; background-color: #2b1c1c; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .safe-card { border-left: 5px solid #00FF7F; background-color: #1a2b22; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .bayesian-card { border-left: 5px solid #8a2be2; background-color: #1a1525; padding: 15px; border-radius: 8px; margin-bottom: 20px;}
    .warn-card { border-left: 5px solid #ff4b4b; background-color: #2b1c1c; padding: 15px; border-radius: 4px; margin-bottom: 10px;}
    .warn-card-green { border-left: 5px solid #00FF7F; background-color: #1a2b22; padding: 15px; border-radius: 4px; margin-bottom: 10px;}
    .def-card { border-left: 5px solid #00bcd4; background-color: #162436; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #00bcd4;}

    .num-ball-hot { display:inline-block; width:30px; height:30px; border-radius:50%; background-color:#ff4b4b; color:white; text-align:center; line-height:30px; margin:2px; font-weight:bold;}
    .num-ball-warm { display:inline-block; width:30px; height:30px; border-radius:50%; background-color:#f9d71c; color:#333; text-align:center; line-height:30px; margin:2px; font-weight:bold;}
    .num-ball-cold { display:inline-block; width:30px; height:30px; border-radius:50%; background-color:#1c83e1; color:white; text-align:center; line-height:30px; margin:2px; font-weight:bold;}

    .filter-box { background: #16181d; border: 1px solid #334; border-top: 3px solid #00bcd4; border-radius: 6px; padding: 15px; margin-bottom: 15px; height: 140px;}
    .filter-box-title { color: #00bcd4; font-size: 1.05em; font-weight: bold; margin-bottom: 5px; border-bottom: 1px solid #334; padding-bottom: 5px;}
    .cart-item { background: rgba(255,255,255,0.05); padding: 8px 12px; border-left: 3px solid #00bcd4; margin-bottom: 8px; font-size: 0.9em; display: flex; justify-content: space-between; align-items: center;}

    div[data-testid="stDialog"] div[data-testid="column"] { padding: 0 2px; }
    div[data-testid="stDialog"] button[kind="secondary"], div[data-testid="stDialog"] button[kind="primary"] { border-radius: 20px; height: 38px; }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 🗄️ 3. 全局基础函数库 (动态文件监听缓存版)
# ==========================================
def st_centered_df(df, **kwargs):
    styled_df = df.style.set_properties(**{'text-align': 'center'}).set_table_styles([{'selector': 'th', 'props': [('text-align', 'center')]}])
    st.dataframe(styled_df, **kwargs)

# --- 引擎 1：读取最新一期开奖数据 (监听文件修改时间) ---
@st.cache_data(show_spinner=False)
def _get_latest_result(lottery_name, mtime):
    file_path = f"{lottery_name}.xlsx"
    if not os.path.exists(file_path): return None
    try:
        df_raw = pd.read_excel(file_path, header=None)
        valid_df = df_raw.iloc[2:].dropna(how='all')
        if valid_df.empty: return None
        is_ssq = (lottery_name == "双色球")
        red_cols = range(2, 35) if is_ssq else range(2, 37)
        blue_cols = range(35, 51) if is_ssq else range(37, 49)
        last_row = valid_df.iloc[-1]
        return {'period': str(int(float(last_row.iloc[0]))),
                'reds': sorted([int(float(last_row.iloc[c])) for c in red_cols if pd.notna(last_row.iloc[c])]),
                'blues': sorted([int(float(last_row.iloc[c])) for c in blue_cols if pd.notna(last_row.iloc[c])])}
    except: return None

def get_latest_result(lottery_name):
    file_path = f"{lottery_name}.xlsx"
    # 获取文件的最后修改时间戳，文件一旦保存，mtime立刻改变，触发缓存刷新
    mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
    return _get_latest_result(lottery_name, mtime)


# --- 引擎 2：读取全量历史数据明细 (监听文件修改时间) ---
@st.cache_data(show_spinner=False)
def _get_full_detailed_data(lottery_name, mtime):
    file_path = f"{lottery_name}.xlsx"
    if not os.path.exists(file_path): return pd.DataFrame()
    try:
        df_raw = pd.read_excel(file_path, header=None)
        valid_df = df_raw.iloc[2:].dropna(how='all')
        is_ssq = (lottery_name == "双色球")
        red_cols = range(2, 35) if is_ssq else range(2, 37)
        blue_cols = range(35, 51) if is_ssq else range(37, 49)
        red_needed, blue_needed = (6, 1) if is_ssq else (5, 2)
        records = []
        for _, row in valid_df.iterrows():
            period = row.iloc[0]
            if pd.isna(period) or not str(period).replace('.0', '').isdigit(): continue
            reds = [int(float(row.iloc[c])) for c in red_cols if pd.notna(row.iloc[c]) and str(row.iloc[c]).replace('.0', '').isdigit()]
            blues = [int(float(row.iloc[c])) for c in blue_cols if pd.notna(row.iloc[c]) and str(row.iloc[c]).replace('.0', '').isdigit()]
            if len(reds) == red_needed and len(blues) >= blue_needed:
                records.append([str(int(float(period)))] + sorted(reds) + sorted(blues[:blue_needed]))
        cols = ['期号'] + [f'r{i + 1}' for i in range(red_needed)] + [f'b{i + 1}' for i in range(blue_needed)]
        return pd.DataFrame(records, columns=cols).sort_values(by='期号').reset_index(drop=True)
    except: return pd.DataFrame()

def get_full_detailed_data(lottery_name):
    file_path = f"{lottery_name}.xlsx"
    # 获取文件的最后修改时间戳
    mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
    return _get_full_detailed_data(lottery_name, mtime)


# --- 引擎 3：全局布林带极限动态阈值 ---
def calculate_dynamic_threshold(hit_series, window=100, min_thresh=4):
    if len(hit_series) < window: window = len(hit_series)
    recent_hits = hit_series.tail(window)
    gaps = (~recent_hits.astype(bool)).groupby((recent_hits != recent_hits.shift()).cumsum()).sum()
    gaps = gaps[gaps > 0]
    if len(gaps) == 0: return 12
    std_gap = gaps.std() if len(gaps) > 1 else 0.0
    if pd.isna(std_gap): std_gap = 0.0
    return max(int(gaps.mean() + 1.5 * std_gap), min_thresh)


# ==========================================
# 🧩 4. 核心分析模块展示
# ==========================================

# 🔴 模块 1：红球定位
def render_mod_red_position(df, is_ssq):
    red_n, red_max = 6 if is_ssq else 5, 33 if is_ssq else 35
    total_p = len(df)
    r_cols = [f'r{i + 1}' for i in range(red_n)]

    df_feat = df.copy()
    for i in range(1, red_n + 1): df_feat[f'r{i}_amp'] = df_feat[f'r{i}'].diff().abs().fillna(0).astype(int)
    for i in range(1, red_n): df_feat[f'step_{i}'] = df_feat[f'r{i + 1}'] - df_feat[f'r{i}']

    r_summary, pools = [], {}
    for i, col in enumerate(r_cols):
        counts = df_feat[col].value_counts().reindex(range(1, red_max + 1), fill_value=0)
        sorted_ns = sorted(range(1, red_max + 1), key=lambda x: counts[x], reverse=True)
        n_hot, n_cold = int(len(sorted_ns) * 0.3), int(len(sorted_ns) * 0.3)
        pools[col] = {'hot': sorted(sorted_ns[:n_hot]), 'warm': sorted(sorted_ns[n_hot:len(sorted_ns) - n_cold]),
                      'cold': sorted(sorted_ns[-n_cold:])}
        r_summary.append({"位置": f"红{i + 1}位", "热号池": ",".join([f"{x:02d}" for x in pools[col]['hot']]),
                          "温号池": ",".join([f"{x:02d}" for x in pools[col]['warm']]),
                          "冷号池": ",".join([f"{x:02d}" for x in pools[col]['cold']])})

    st.markdown("### 预警")
    alerts = []
    for col in r_cols:
        hit_series = df_feat[col].apply(lambda x: 1 if x in pools[col]['hot'] else 0)
        current_gap = (~hit_series.iloc[::-1].astype(bool)).cummin().sum()
        thresh = calculate_dynamic_threshold(hit_series, window=100)
        if current_gap >= thresh: alerts.append(
            f"<li>🎯 <b>{col.replace('r', '红')}位热号冰封</b>：现已遗漏 <b style='color:#ff4b4b;'>{current_gap}</b> 期 (阈值:{thresh})！强烈建议重仓热号 [{r_summary[int(col[1:]) - 1]['热号池']}]！</li>")

    for i in range(1, red_n + 1):
        amp_series = (df_feat[f'r{i}_amp'] <= 2).astype(int)
        micro_amp_streak = amp_series.iloc[::-1].cummin().sum()
        if micro_amp_streak >= 5: alerts.append(
            f"<li>🌊 <b>红{i}位纵向引力崩塌</b>：已连续 {micro_amp_streak} 期横盘！下期必发生活跃跳变！</li>")

    for i in range(1, red_n):
        wide_streak = (df_feat[f'step_{i}'] >= 10).iloc[::-1].cummin().sum()
        if wide_streak >= 3: alerts.append(
            f"<li>📏 <b>红{i}与红{i + 1}横向撕裂</b>：间距连续 {wide_streak} 期大于10！下期内部引力收缩，防连号！</li>")

    if alerts:
        st.markdown(
            f"<div class='alert-card'><h4 style='color: #ff4b4b; margin-top:0;'>⚠️ 警报：大盘局部突破极限！</h4><ul>{''.join(alerts)}</ul></div>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            "<div class='safe-card'><h4 style='color:#00FF7F; margin:0;'> 各位次冷热交替均在布林带常态范围内。</h4></div>",
            unsafe_allow_html=True)

    st.markdown("### 定胆矩阵")
    bayesian_dict = {}
    for i in range(1, red_n): bayesian_dict[f"{i}_to_{i + 1}"] = df_feat.groupby(f'r{i}')[
        f'r{i + 1}'].value_counts().reset_index(name='count')

    c_b1, c_b2 = st.columns([1, 2])
    with c_b1:
        st.markdown("<div class='stat-card'>", unsafe_allow_html=True)
        sel_pos = st.selectbox("选择已知锚点位置", [f"红{i}位推导红{i + 1}位" for i in range(1, red_n)])
        pos_idx = int(sel_pos[1])
        avail_nums = sorted(df_feat[f'r{pos_idx}'].unique())
        last_num = df_feat[f'r{pos_idx}'].iloc[-1]
        sel_num = st.selectbox(f"假设本期【红{pos_idx}位】开出号码：", avail_nums,
                               index=avail_nums.index(last_num) if last_num in avail_nums else 0)
        st.markdown("</div>", unsafe_allow_html=True)
    with c_b2:
        target_df = bayesian_dict[f"{pos_idx}_to_{pos_idx + 1}"]
        results = target_df[target_df[f'r{pos_idx}'] == sel_num].head(5)
        if not results.empty:
            res_html = "".join([
                                   f"<div style='display:inline-block; text-align:center; margin-right:20px;'><span style='display:block; font-size:1.5em; font-weight:bold; color:#ff4b4b;'>{int(r[f'r{pos_idx + 1}']):02d}</span><span style='color:#bbb;'>跟出 {int(r['count'])} 次</span></div>"
                                   for _, r in results.iterrows()])
            st.markdown(f"<div class='bayesian-card'><h4 style='color:#8a2be2;'>🧠 AI 贝叶斯推演</h4>{res_html}</div>",
                        unsafe_allow_html=True)

    st.markdown("### 🔍 二、 逐位深度拆解与落点追踪")
    tabs = st.tabs([f"红{i + 1}位详情" for i in range(red_n)])
    for i, tab in enumerate(tabs):
        with tab:
            c_n = r_cols[i]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("历史均值", f"{df_feat[c_n].mean():.2f}");
            c2.metric("当前振幅", f"{df_feat[f'{c_n}_amp'].mean():.2f}")
            c3.metric("最热号", f"{df_feat[c_n].mode()[0]:02d}");
            c4.metric("最新期振幅", f"{df_feat[f'{c_n}_amp'].iloc[-1]}")
            L, R = st.columns([2, 1])
            with L:
                f_df = df_feat[c_n].value_counts().reset_index()
                f_df.columns = ['号码', '发生次数'];
                f_df['占比'] = (f_df['发生次数'] / total_p).map('{:.2%}'.format)
                st_centered_df(f_df.sort_values("号码"), use_container_width=True, hide_index=True)
            with R:
                st.success(f"🔥 热号池\n\n{r_summary[i]['热号池']}");
                st.warning(f"⛅ 温号池\n\n{r_summary[i]['温号池']}");
                st.error(f"❄️ 冷号池\n\n{r_summary[i]['冷号池']}")

    st.markdown("### 🎯 三、 红球全量存活概率分布")
    red_full = []
    for n in range(1, red_max + 1):
        d = {"号码": f"{n:02d}"};
        tot_h = 0
        for i in range(red_n): hit = (df_feat[f'r{i + 1}'] == n).sum(); tot_h += hit; d[f"红{i + 1}位"] = hit
        d["总命中数"] = tot_h;
        d["覆盖率"] = f"{(tot_h / total_p):.2%}"
        red_full.append(d)
    st_centered_df(pd.DataFrame(red_full), use_container_width=True, hide_index=True)

    st.markdown("### 📅 四、 最近 20 期走势明细")
    recent_r = df_feat.tail(20).copy();
    disp_cols = ['期号']
    for i in range(1, red_n + 1):
        col = f'r{i}'
        recent_r[f'红{i}位'] = recent_r.apply(lambda row: f"{int(row[col]):02d}(" + (
            "热" if row[col] in pools[col]['hot'] else (
                "冷" if row[col] in pools[col]['cold'] else "温")) + f") |V|{int(row[f'{col}_amp'])}", axis=1)
        disp_cols.append(f'红{i}位')
        if i < red_n: recent_r[f'↔间距{i}'] = recent_r[f'step_{i}']; disp_cols.append(f'↔间距{i}')
    st_centered_df(recent_r[disp_cols].iloc[::-1], use_container_width=True, hide_index=True)


# 🏆 模块 2：奖项区间波动
@st.cache_data(show_spinner=False)
def calculate_combination_features(df, is_ssq):
    total = len(df)
    red_max = 33 if is_ssq else 35
    blue_max = 16 if is_ssq else 12

    R = np.zeros((total, red_max + 1), dtype=np.int8)
    B = np.zeros((total, blue_max + 1), dtype=np.int8)

    red_n, blue_n = (6, 1) if is_ssq else (5, 2)
    r_cols = [f'r{i + 1}' for i in range(red_n)]
    b_cols = [f'b{i + 1}' for i in range(blue_n)]

    for i in range(total):
        row = df.iloc[i]
        for c in r_cols: R[i, int(row[c])] = 1
        for c in b_cols: B[i, int(row[c])] = 1

    hits_R = np.dot(R, R.T)
    hits_B = np.dot(B, B.T)
    np.fill_diagonal(hits_R, -1)
    np.fill_diagonal(hits_B, -1)

    detailed_data = []
    last_name = "福运奖" if is_ssq else "7等奖"

    for i in range(total):
        hr = hits_R[i]
        hb = hits_B[i]

        if is_ssq:
            c2 = np.sum((hr == 6) & (hb == 0))
            c3 = np.sum((hr == 5) & (hb == 1))
            c4 = np.sum(((hr == 5) & (hb == 0)) | ((hr == 4) & (hb == 1)))
            c5 = np.sum(((hr == 4) & (hb == 0)) | ((hr == 3) & (hb == 1)))
            c6 = np.sum((hr <= 2) & (hb == 1))
            c_last = np.sum((hr == 3) & (hb == 0))

            total_companions = c3 + c4 + c5 + c6 + c_last
            combo_str = f"3等:{c3}次 | 4等:{c4}次 | 5等:{c5}次 | 6等:{c6}次 | {last_name}:{c_last}次"

            detailed_data.append({
                '期号': df.iloc[i]['期号'],
                '伴生2等奖': c2, '伴生3等奖': c3, '伴生4等奖': c4, '伴生5等奖': c5, '伴生6等奖': c6,
                f'伴生{last_name}': c_last,
                '固定组合特征': combo_str,
                '总伴生奖项数': total_companions,
                '4+5同现': 1 if (c4 > 0 and c5 > 0) else 0,
                '3+4+5同现': 1 if (c3 > 0 and c4 > 0 and c5 > 0) else 0
            })
        else:
            c3 = np.sum(((hr == 5) & (hb == 0)) | ((hr == 4) & (hb == 2)))
            c4 = np.sum((hr == 4) & (hb == 1))
            c5 = np.sum(((hr == 4) & (hb == 0)) | ((hr == 3) & (hb == 2)))
            c6 = np.sum(((hr == 3) & (hb == 1)) | ((hr == 2) & (hb == 2)))
            c_last = np.sum(
                ((hr == 3) & (hb == 0)) | ((hr == 2) & (hb == 1)) | ((hr == 1) & (hb == 2)) | ((hr == 0) & (hb == 2)))

            total_companions = c3 + c4 + c5 + c6 + c_last
            combo_str = f"3等:{c3}次 | 4等:{c4}次 | 5等:{c5}次 | 6等:{c6}次 | {last_name}:{c_last}次"

            detailed_data.append({
                '期号': df.iloc[i]['期号'],
                '伴生3等奖': c3, '伴生4等奖': c4, '伴生5等奖': c5, '伴生6等奖': c6, f'伴生{last_name}': c_last,
                '固定组合特征': combo_str,
                '总伴生奖项数': total_companions,
                '4及5等并发': 1 if (c4 > 0 and c5 > 0) else 0
            })

    return pd.DataFrame(detailed_data)


def render_mod_prize(df, is_ssq):
    total_p = len(df)
    last_prize_name = "福运奖" if is_ssq else "7等奖"
    lottery_choice = "双色球" if is_ssq else "大乐透"

    with st.spinner(f"正在执行全量数据 ({total_p} x {total_p}) 矩阵级深度交叉验证，请稍候..."):
        audit_df = calculate_combination_features(df, is_ssq)

    combo_counts = audit_df['固定组合特征'].value_counts()
    top_combo = combo_counts.index[0]

    is_top1_hit = (audit_df['固定组合特征'] == top_combo).astype(int)
    current_gap = (~is_top1_hit.iloc[::-1].astype(bool)).cummin().sum()

    gaps = (~is_top1_hit.astype(bool)).groupby((is_top1_hit != is_top1_hit.shift()).cumsum()).sum()
    gaps = gaps[gaps > 0]
    mode_gap = int(gaps.mode()[0]) if not gaps.empty else 0

    dynamic_thresh = calculate_dynamic_threshold(is_top1_hit)

    st.markdown("### 🚨 零、 架构师 AI 伴生基因预警系统")
    if current_gap >= dynamic_thresh:
        st.markdown(f"""
        <div class='alert-card'>
            <h3 style='color: #ff4b4b; margin-top:0;'>⚠️ 警报：核心伴生形态极度空窗，爆发临界点已触发！</h3>
            <p style='font-size:1.1em;'>历史发生率最高的绝对核心形态 <b>[{top_combo}]</b>，目前已经连续遗漏了 <b>{current_gap}</b> 期！</p>
            <p>该形态在历史上通常每隔 <b>{mode_gap}</b> 期回归。而系统最新计算的<b>动态极限波动阈值</b>为 <b>{dynamic_thresh}</b> 期。当前大盘已彻底击穿布林带上限，进入概率学上的<b>极高压报复性回补区</b>！</p>
            <hr style='border-color:#555;'>
            <h4 style='color:#f9d71c;'>🎯 本期动态智能容错过滤建议：</h4>
            <p>强烈建议在这一期的缩水软件中，<b>放弃使用模糊的置信区间</b>。直接将软件的伴生奖项过滤条件<b>精确死锁为</b>：<br />
            <span style='font-size:1.2em; font-weight:bold; color:white;'>{top_combo}</span><br />
            以博取极大概率的均值回归收益！</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='safe-card'>
            <h3 style='color: #00FF7F; margin-top:0;'>✅ 提示：核心伴生基因目前处于安全波动常态区</h3>
            <p style='font-size:1.1em;'>历史最强形态 <b>[{top_combo}]</b> 当前遗漏 <b>{current_gap}</b> 期，尚未击穿系统计算的动态极限波动阈值（<b>{dynamic_thresh}</b> 期）。</p>
            <hr style='border-color:#555;'>
            <h4 style='color:#00FF7F;'>💡 AI 智能常态防守推荐：</h4>
            <p>本期<b>不建议</b>死守某一个固定的伴生形态，请直接向下滚动，参考<b>【模块三：核心置信区间】</b>给出的[X ~ Y]宽泛范围，进行常态化容错过滤，以防误杀大奖组合。</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📊 一、 奖项伴生波动区间 (一等奖命中背景下)")

    def render_stat_card(title, series):
        non_zero = (series > 0).sum()
        rate = non_zero / total_p
        st.markdown(f"""
        <div class='stat-card'>
            <h5 style='color: #4da6ff; margin-bottom:10px;'>{title}</h5>
            <p style='margin-bottom:6px;'>🔹 绝对次数区间: <b>[{series.min()} - {series.max()}]</b></p>
            <p style='margin-bottom:6px;'>🔹 伴生平均值: <b>{series.mean():.4f}</b></p>
            <p style='margin-bottom:0;'>🔹 历史全量伴生率: <b>{rate:.2%}</b> (发生期数: {non_zero})</p>
        </div>
        """, unsafe_allow_html=True)

    if is_ssq:
        c1, c2, c3 = st.columns(3)
        with c1:
            render_stat_card("二等奖 (C2)", audit_df['伴生2等奖'])
        with c2:
            render_stat_card("三等奖 (C3)", audit_df['伴生3等奖'])
        with c3:
            render_stat_card("四等奖 (C4)", audit_df['伴生4等奖'])
        c4, c5, c6 = st.columns(3)
        with c4:
            render_stat_card("五等奖 (C5)", audit_df['伴生5等奖'])
        with c5:
            render_stat_card("六等奖 (C6)", audit_df['伴生6等奖'])
        with c6:
            render_stat_card(f"{last_prize_name} (CF)", audit_df[f'伴生{last_prize_name}'])
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_stat_card("四等奖 (C4)", audit_df['伴生4等奖'])
        with c2:
            render_stat_card("五等奖 (C5)", audit_df['伴生5等奖'])
        with c3:
            render_stat_card("六等奖 (C6)", audit_df['伴生6等奖'])
        with c4:
            render_stat_card(f"{last_prize_name} (C7)", audit_df[f'伴生{last_prize_name}'])

    st.markdown("### 🎯 二、 核心基因：伴生组合历史频次排行 (Top 100)")
    combo_stats = combo_counts.reset_index()
    combo_stats.columns = ['一等奖带出的精准伴生组合', '发生期数']
    combo_stats['全量概率占比'] = (combo_stats['发生期数'] / total_p).map('{:.2%}'.format)
    st_centered_df(combo_stats.head(100), use_container_width=True, hide_index=True)

    st.markdown("### 🛡️ 三、 容错过滤：各项伴生奖的核心置信区间 (覆盖常态情况)")
    prize_cols = ['伴生3等奖', '伴生4等奖', '伴生5等奖', '伴生6等奖', f'伴生{last_prize_name}']
    cols = st.columns(len(prize_cols))
    for i, p_col in enumerate(prize_cols):
        series = audit_df[p_col]
        q_low, q_high = int(series.quantile(0.05)), int(series.quantile(0.95))
        mean_val = series.mean()
        with cols[i]:
            st.markdown(f"""
            <div class='stat-card'>
                <h5 style='color: #4da6ff;'>{p_col.replace('伴生', '')} 常态区间</h5>
                <h3 style='text-align: center; color: white; margin: 10px 0;'>[{q_low} ~ {q_high}] 次</h3>
                <p style='color: #888; font-size: 12px; text-align: center; margin:0;'>历史平均: {mean_val:.2f} 次</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### ⚡ 四、复合伴生 / 并发专项统计 (一等奖命中前提)")

    # ==========================================
    # 基础固定统计：直接读取真实存在的 '伴生X等奖' 列
    # ==========================================
    if is_ssq:
        c3, c4, c5, c6, cfy = audit_df['伴生3等奖'], audit_df['伴生4等奖'], audit_df['伴生5等奖'], audit_df['伴生6等奖'], audit_df['伴生福运奖']
        cnt_345 = ((c3 > 0) & (c4 > 0) & (c5 > 0)).sum()
        cnt_456 = ((c4 > 0) & (c5 > 0) & (c6 > 0)).sum()
        cnt_456f = ((c4 > 0) & (c5 > 0) & (c6 > 0) & (cfy > 0)).sum()

        col1, col2, col3 = st.columns(3)
        with col1: st.info(f"**3,4,5等奖【同发】**\n\n共计出现: **{cnt_345}** 期\n\n全量占比: **{cnt_345/total_p if total_p else 0:.2%}**\n\n平均频次: 约 **{total_p/cnt_345 if cnt_345 else 0:.1f}** 期/次")
        with col2: st.warning(f"**4,5,6等奖【同发】**\n\n共计出现: **{cnt_456}** 期\n\n全量占比: **{cnt_456/total_p if total_p else 0:.2%}**\n\n平均频次: 约 **{total_p/cnt_456 if cnt_456 else 0:.1f}** 期/次")
        with col3: st.error(f"**4,5,6及福运奖【同发】**\n\n共计出现: **{cnt_456f}** 期\n\n全量占比: **{cnt_456f/total_p if total_p else 0:.2%}**\n\n平均频次: 约 **{total_p/cnt_456f if cnt_456f else 0:.1f}** 期/次")
        
        st.success("**💡 后期筛选建议**\n\n[核心过滤区] 在命中一等奖框架下，密切关注上述最高频组合。若某组合占比极高，建议在容错大底中强制绑定该形态！")
    
    else:
        c4, c5, c6, c7 = audit_df['伴生4等奖'], audit_df['伴生5等奖'], audit_df['伴生6等奖'], audit_df[f'伴生{last_prize_name}']
        cnt_45 = ((c4 > 0) & (c5 > 0)).sum()
        cnt_56 = ((c5 > 0) & (c6 > 0)).sum()
        cnt_567 = ((c5 > 0) & (c6 > 0) & (c7 > 0)).sum()

        col1, col2, col3 = st.columns(3)
        with col1: st.info(f"**4,5等奖【同发】**\n\n共计出现: **{cnt_45}** 期\n\n全量占比: **{cnt_45/total_p if total_p else 0:.2%}**\n\n平均频次: 约 **{total_p/cnt_45 if cnt_45 else 0:.1f}** 期/次")
        with col2: st.warning(f"**5,6等奖【同发】**\n\n共计出现: **{cnt_56}** 期\n\n全量占比: **{cnt_56/total_p if total_p else 0:.2%}**\n\n平均频次: 约 **{total_p/cnt_56 if cnt_56 else 0:.1f}** 期/次")
        with col3: st.error(f"**5,6,7等奖【同发】**\n\n共计出现: **{cnt_567}** 期\n\n全量占比: **{cnt_567/total_p if total_p else 0:.2%}**\n\n平均频次: 约 **{total_p/cnt_567 if cnt_567 else 0:.1f}** 期/次")

        best_c = max([("4、5等奖并发", cnt_45), ("5、6等奖并发", cnt_56), ("5、6、7等奖并发", cnt_567)], key=lambda x: x[1])
        st.success(f"**💡 后期筛选建议 (大乐透)**\n\n[数据洞察] 统计表明在命中一等奖期数中，**【{best_c[0]}】** 形态出现最多（**{best_c[1]}** 次）。\n\n[实战策略] 建议优先锚定该形态作为核心过滤条件！")


    # ==========================================
    # 🌟 模式一：自定义模糊同出组合追踪
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🎯 模式一：宽泛组合同出雷达 (只要发生即算)")
    options_v1 = ['伴生3等奖', '伴生4等奖', '伴生5等奖', '伴生6等奖', f'伴生{last_prize_name}'] if is_ssq else ['伴生4等奖', '伴生5等奖', '伴生6等奖', f'伴生{last_prize_name}']
    
    selected_prizes_v1 = st.multiselect("请选择需要追踪的奖项组合 (可多选):", options_v1, default=options_v1[:2], key="ms_v1")

    if selected_prizes_v1:
        mask_v1 = pd.Series([True] * total_p, index=audit_df.index)
        for p in selected_prizes_v1:
            mask_v1 = mask_v1 & (audit_df[p] > 0)
        
        match_cnt_v1 = mask_v1.sum()
        match_rate_v1 = match_cnt_v1 / total_p if total_p else 0
        match_gap_v1 = total_p / match_cnt_v1 if match_cnt_v1 else 0
        clean_names_v1 = "+".join([p.replace('伴生', '') for p in selected_prizes_v1])
        
        st.markdown(f"""
        <div style='background-color:rgba(0, 188, 212, 0.1); border-left:4px solid #00bcd4; padding:15px; border-radius:5px;'>
            <h5 style='color:#00bcd4; margin-top:0;'>🔭 【{clean_names_v1}】 只要同时出现过的统计：</h5>
            <ul style='font-size:1.05em; margin-bottom:0;'>
                <li>命中期数：<b style='color:white; font-size:1.2em;'>{match_cnt_v1}</b> 次</li>
                <li>全量比重：<b style='color:#00FF7F;'>{match_rate_v1:.2%}</b></li>
                <li>平均缺口：约 <b style='color:#ff4b4b;'>{match_gap_v1:.1f}</b> 期一次</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


    # ==========================================
    # 🌟 模式二：自定义精确次数追踪雷达 (精算级)
    # ==========================================
    st.markdown("---")
    st.markdown("#### 🎯 模式二：精确次数死锁雷达 (精算级)")
    available_prizes = [col for col in audit_df.columns if str(col).startswith('伴生')]
    
    selected_prizes_v2 = st.multiselect("第一步：选择需要【精确次数】死锁的奖项 (全量覆盖):", available_prizes, key="ms_v2")

    if selected_prizes_v2:
        st.markdown("<p style='font-size:0.95em; color:#bbb; margin-bottom: 5px;'>第二步：请输入这些奖项的<b>具体发生次数</b>：</p>", unsafe_allow_html=True)
        cols = st.columns(len(selected_prizes_v2))
        target_counts = {}
        for i, p_col in enumerate(selected_prizes_v2):
            with cols[i]:
                target_counts[p_col] = st.number_input(f"{p_col.replace('伴生', '')} (次):", min_value=0, max_value=1000, value=0, step=1, key=f"ni_{p_col}")
        
        mask_v2 = pd.Series([True] * total_p, index=audit_df.index)
        query_parts = []
        for p_col, target_val in target_counts.items():
            mask_v2 = mask_v2 & (audit_df[p_col] == target_val)
            query_parts.append(f"{p_col.replace('伴生', '')}={target_val}次")
        
        match_cnt_v2 = mask_v2.sum()
        match_rate_v2 = match_cnt_v2 / total_p if total_p else 0
        match_gap_v2 = total_p / match_cnt_v2 if match_cnt_v2 else 0
        query_display = " + ".join(query_parts)
        
        if match_cnt_v2 > 0:
            st.markdown(f"""
            <div style='background-color:rgba(255, 152, 0, 0.1); border-left:4px solid #ff9800; padding:15px; border-radius:5px; margin-top:15px;'>
                <h5 style='color:#ff9800; margin-top:0;'>🔬 精算组合 【{query_display}】 统计：</h5>
                <ul style='font-size:1.05em; margin-bottom:0;'>
                    <li>精确匹配期数：<b style='color:white; font-size:1.2em;'>{match_cnt_v2}</b> 次</li>
                    <li>全量比重：<b style='color:#00FF7F;'>{match_rate_v2:.2%}</b></li>
                    <li>平均缺口：约 <b style='color:#ff4b4b;'>{match_gap_v2:.1f}</b> 期一次</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"⚠️ 在历史库中，尚未出现过 **【{query_display}】** 这种精准次数的组合！这属于极端盲区，排雷时请避开！")
    
    st.markdown("### ⚠️ 五、 极值勘探：历史上的奇异伴生期数")
    min_comp = audit_df['总伴生奖项数'].min()
    cold_df = audit_df[audit_df['总伴生奖项数'] == min_comp]
    max_comp = audit_df['总伴生奖项数'].max()
    hot_df = audit_df[audit_df['总伴生奖项数'] == max_comp]

    m1, m2 = st.columns(2)
    with m1:
        st.markdown(
            f"<div class='warn-card'><b>❄️ 极度冷门期 (总伴生最少：{min_comp}次)</b><br />这些期数虽然中了一等奖，但几乎没有带出其他低等奖。</div>",
            unsafe_allow_html=True)
        st_centered_df(cold_df[['期号', '固定组合特征', '总伴生奖项数']].iloc[::-1], use_container_width=True,
                       hide_index=True)
    with m2:
        st.markdown(
            f"<div class='warn-card-green'><b>🔥 极度狂热期 (总伴生最多：{max_comp}次)</b><br />这些期数的号码特征极具普适性，带出了海量的下级奖项。</div>",
            unsafe_allow_html=True)
        st_centered_df(hot_df[['期号', '固定组合特征', '总伴生奖项数']].iloc[::-1], use_container_width=True,
                       hide_index=True)

    st.markdown("### 📋 六、 伴生区间波动明细 (全量数据)")
    st_centered_df(audit_df.iloc[::-1], use_container_width=True, hide_index=True)

    st.markdown("### 📑 七、 各奖项区间波动详情 (对齐 TXT 报告格式)")
    report_lines = []
    report_lines.append(f"========== {lottery_choice}历史奖项波动与伴生规律深度审计报告 ==========")
    report_lines.append(f"分析样本：{total_p} 期")
    report_lines.append("-" * 60)

    report_cols = ['伴生3等奖', '伴生4等奖', '伴生5等奖', '伴生6等奖', f'伴生{last_prize_name}']
    if is_ssq: report_cols.insert(0, '伴生2等奖')

    for p_col in report_cols:
        series = audit_df[p_col]
        min_c, max_c = int(series.min()), int(series.max())
        avg_c = series.mean()
        non_zero = (series > 0).sum()
        rate = non_zero / total_p
        p_name = p_col.replace('伴生', '')
        report_lines.append(
            f"【{p_name} 伴生特征】\n  - 伴生区间值：[{min_c}, {max_c}] 次\n  - 伴生的最大次数：{max_c} 次\n  - 伴生的最小次数：{min_c} 次\n  - 伴生的平均值：{avg_c:.4f} 次 / 期\n  - 历史中全量伴生率：{rate:.4%} (发生期数:{non_zero})\n")

    st.code("\n".join(report_lines), language="text")


# 🧬 模块 3：AC值
def render_mod_ac(df, is_ssq):
    total_p = len(df)
    r_cols = [f'r{i + 1}' for i in range(6 if is_ssq else 5)]

    if is_ssq:
        st.success("📌 **当前引擎 (双色球)**：提取 6 个红球两两作差去重，扣减基数【5】。理论范围：0 ~ 10。")
    else:
        st.info("📌 **当前引擎 (大乐透)**：提取 5 个红球两两作差去重，扣减基数【4】。理论范围：0 ~ 6。")

    def calc_ac(nums):
        v = [int(x) for x in nums if pd.notna(x)]
        if len(v) < 2: return 0
        return len(set(abs(x - y) for x, y in itertools.combinations(v, 2))) - (5 if is_ssq else 4)

    result_df = df.copy()
    result_df['AC值'] = result_df[r_cols].apply(calc_ac, axis=1)
    result_df['AC振幅'] = result_df['AC值'].diff().abs().fillna(0).astype(int)

    ac_counts_zero = result_df['AC值'].value_counts()
    top_ac = ac_counts_zero.index[0]
    top_ac_2_zero = ac_counts_zero.index[1] if len(ac_counts_zero) > 1 else top_ac

    is_hit = (result_df['AC值'] == top_ac).astype(int)
    curr_gap = (~is_hit.iloc[::-1].astype(bool)).cummin().sum()

    gaps_zero = (~is_hit.astype(bool)).groupby((is_hit != is_hit.shift()).cumsum()).sum()
    gaps_zero = gaps_zero[gaps_zero > 0]
    mode_gap_zero = int(gaps_zero.mode()[0]) if not gaps_zero.empty else 0

    dyn_thresh = calculate_dynamic_threshold(is_hit)

    st.markdown("### 🚨 零、 架构师 AI 核心 AC 值临界预警系统")
    if curr_gap >= dyn_thresh:
        st.markdown(f"""
        <div class='alert-card'>
            <h3 style='color: #ff4b4b; margin-top:0;'>⚠️ 警报：核心 AC 值爆发节点已触发！</h3>
            <p style='font-size:1.1em;'>历史最常开出的绝对主导 AC 值 <b>[{top_ac}]</b>，目前已经连续遗漏了 <b>{curr_gap}</b> 期！</p>
            <p>经系统测算，该 AC 值在历史上通常每隔 <b>{mode_gap_zero}</b> 期就会进行一次均值回归。当前已进入极限回补区！</p>
            <hr style='border-color:#555;'>
            <h4 style='color:#f9d71c;'>🎯 本期动态容错过滤建议：</h4>
            <p>本期在配置过滤大底时，<b>请放弃使用区间容错</b>。强烈建议直接将软件的 AC 值条件<b>单点锁定为</b>：<br />
            <span style='font-size:1.2em; font-weight:bold; color:white;'>AC值 = {top_ac}</span><br />
            以获取极致的缩水效果！</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='safe-card'>
            <h3 style='color: #00FF7F; margin-top:0;'>✅ 提示：核心 AC 值目前处于安全震荡区</h3>
            <p style='font-size:1.1em;'>历史最强 AC 值 <b>[{top_ac}]</b> 当前遗漏 <b>{curr_gap}</b> 期，尚未达到历史最易爆发的节点（<b>{mode_gap_zero}</b> 期）。</p>
            <hr style='border-color:#555;'>
            <h4 style='color:#00FF7F;'>💡 常规防守推荐：</h4>
            <p>本期 AC 走势可能出现横向偏移。建议在过滤条件中设置一定的容错区间，可将过滤条件放宽至：<br />
            <b>AC值 = {top_ac} 或 AC值 = {top_ac_2_zero}</b>，以防爆冷误杀大奖。</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📊 一、 AC 值历史频次与动态遗漏")
    mode_ac = int(result_df['AC值'].mode()[0])
    avg_ac = result_df['AC值'].mean()
    max_ac = int(result_df['AC值'].max())
    min_ac = int(result_df['AC值'].min())

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='stat-card'>历史最热 AC 值<br /><h2 style='color:#ff4b4b;margin:0;'>{mode_ac}</h2></div>",
                unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-card'>全量平均 AC 值<br /><h2 style='color:#f9d71c;margin:0;'>{avg_ac:.2f}</h2></div>",
                unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-card'>最大 AC 值<br /><h2 style='color:#1c83e1;margin:0;'>{max_ac}</h2></div>",
                unsafe_allow_html=True)
    c4.markdown(f"<div class='stat-card'>最小 AC 值<br /><h2 style='color:#1c83e1;margin:0;'>{min_ac}</h2></div>",
                unsafe_allow_html=True)

    ac_stats = result_df['AC值'].value_counts().reset_index()
    ac_stats.columns = ['特定 AC 值', '历史发生期数']
    ac_stats['全量占比'] = (ac_stats['历史发生期数'] / total_p).map('{:.2%}'.format)
    last_idx = result_df.reset_index().groupby('AC值')['index'].max()
    ac_stats['⏳ 当前遗漏 (期)'] = ac_stats['特定 AC 值'].map(lambda x: len(result_df) - 1 - last_idx.get(x, 0))

    ac_stats = ac_stats.sort_values(by='历史发生期数', ascending=False)

    L1, R1 = st.columns([2, 1])
    with L1:
        st.write("**(1) AC 值命中频次与遗漏排查表**")
        st_centered_df(ac_stats, use_container_width=True, hide_index=True)
    with R1:
        st.write("**(2) AC 值历史分布直方图**")
        st.bar_chart(result_df['AC值'].value_counts().sort_index(), color="#ff4b4b")

        top1_ac = ac_stats.iloc[0]['特定 AC 值']
        top2_ac = ac_stats.iloc[1]['特定 AC 值'] if len(ac_stats) > 1 else None
        st.success(
            f"**💡 AC 过滤锚点：**\n\n数据表明，**AC 值为 {top1_ac} 与 {top2_ac}** 涵盖了核心中奖特征区间。配置沙盒时，强烈建议将 AC 容错范围锁定在此范围内。")

    st.markdown("### 📈 二、 AC 振幅波动与近期波形走势")
    avg_amp = result_df['AC振幅'].mean()
    latest_amp = result_df['AC振幅'].iloc[-1]

    amp_stats = result_df['AC振幅'].value_counts().reset_index()
    amp_stats.columns = ['振幅数值', '历史出现期数']
    amp_stats['全量占比'] = (amp_stats['历史出现期数'] / total_p).map('{:.2%}'.format)
    amp_stats = amp_stats.sort_values("历史出现期数", ascending=False)

    L2, R2 = st.columns([1, 2])
    with L2:
        st.write("**(1) AC 振幅频次排列**")
        st.info(f"历史平均振幅：**{avg_amp:.2f}**\n\n最新期 AC 振幅：**{latest_amp}**")
        st_centered_df(amp_stats, use_container_width=True, hide_index=True)
    with R2:
        st.write("**(2) 最近 50 期 AC值 与 振幅 双重走势波形图**")
        trend_df = result_df.tail(50).set_index('期号')[['AC值', 'AC振幅']]
        st.line_chart(trend_df, color=["#f9d71c", "#1c83e1"])

    st.markdown("### 📋 三、 历史逐期数据明细 (倒序检视)")
    st_centered_df(result_df.iloc[::-1], use_container_width=True, hide_index=True, height=400)


# 🚥 模块 4：012路
def render_mod_012(df, is_ssq):
    total_p = len(df)
    r_cols = [f'r{i + 1}' for i in range(6 if is_ssq else 5)]

    if is_ssq:
        st.success(
            f"📌 **当前引擎 (双色球)**：已成功读取最新 **{total_p}** 期数据。红球 6 个，形态比值加和锁定为 **6** (例: 2:2:2)。")
        with st.expander("📄 点击查看【双色球】012路 详细使用说明", expanded=False):
            st.markdown("""
            **🎯 012路基础映射：**
            * **1路：** 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31
            * **2路：** 2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32
            * **0路：** 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33

            **🔢 012路个数排列值 (形态比值：0路:1路:2路)：**
            * **0：** 6零 (600) &nbsp;|&nbsp; **1：** 5零1一 (510) &nbsp;|&nbsp; **2：** 5零1二 (501) &nbsp;|&nbsp; **3：** 4零2一 (420) &nbsp;|&nbsp; **4：** 4零1一1二 (411)
            * **5：** 4零2二 (402) &nbsp;|&nbsp; **6：** 3零3一 (330) &nbsp;|&nbsp; **7：** 3零2一1二 (321) &nbsp;|&nbsp; **8：** 3零1一2二 (312) &nbsp;|&nbsp; **9：** 3零3二 (303)
            * **10：** 2零4一 (240) &nbsp;|&nbsp; **11：** 2零3一1二 (231) &nbsp;|&nbsp; **12：** 2零2一2二 (222) &nbsp;|&nbsp; **13：** 2零1一3二 (213) &nbsp;|&nbsp; **14：** 2零4二 (204)
            * **15：** 1零5一 (150) &nbsp;|&nbsp; **16：** 1零4一1二 (141) &nbsp;|&nbsp; **17：** 1零3一2二 (132) &nbsp;|&nbsp; **18：** 1零2一3二 (123) &nbsp;|&nbsp; **19：** 1零1一4二 (114)
            * **20：** 1零5二 (105) &nbsp;|&nbsp; **21：** 6一 (060) &nbsp;|&nbsp; **22：** 5一1二 (051) &nbsp;|&nbsp; **23：** 4一2二 (042) &nbsp;|&nbsp; **24：** 3一3二 (033)
            * **25：** 2一4二 (024) &nbsp;|&nbsp; **26：** 1一5二 (015) &nbsp;|&nbsp; **27：** 6二 (006)
            """)
    else:
        st.info(
            f"📌 **当前引擎 (大乐透)**：已成功读取最新 **{total_p}** 期数据。红球 5 个，形态比值加和锁定为 **5** (例: 1:2:2)。")
        with st.expander("📄 点击查看【大乐透】012路 详细使用说明", expanded=False):
            st.markdown("""
            **🎯 012路基础映射：**
            * **1路：** 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34
            * **2路：** 2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35
            * **0路：** 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33

            **🔢 012路个数排列值 (形态比值：0路:1路:2路)：**
            * **0：** 5零 (500) &nbsp;|&nbsp; **1：** 4零1一 (410) &nbsp;|&nbsp; **2：** 4零1二 (401) &nbsp;|&nbsp; **3：** 3零2一 (320) &nbsp;|&nbsp; **4：** 3零1一1二 (311)
            * **5：** 3零2二 (302) &nbsp;|&nbsp; **6：** 2零3一 (230) &nbsp;|&nbsp; **7：** 2零2一1二 (221) &nbsp;|&nbsp; **8：** 2零1一2二 (212) &nbsp;|&nbsp; **9：** 2零3二 (203)
            * **10：** 1零4一 (140) &nbsp;|&nbsp; **11：** 1零3一1二 (131) &nbsp;|&nbsp; **12：** 1零2一2二 (122) &nbsp;|&nbsp; **13：** 1零1一3二 (113) &nbsp;|&nbsp; **14：** 1零4二 (104)
            * **15：** 5一 (050) &nbsp;|&nbsp; **16：** 4一1二 (041) &nbsp;|&nbsp; **17：** 3一2二 (032) &nbsp;|&nbsp; **18：** 2一3二 (023) &nbsp;|&nbsp; **19：** 1一4二 (014) &nbsp;|&nbsp; **20：** 5二 (005)
            """)

    mod_mat = df[r_cols].values % 3
    result_df = df.copy()
    c0, c1, c2 = np.sum(mod_mat == 0, axis=1), np.sum(mod_mat == 1, axis=1), np.sum(mod_mat == 2, axis=1)
    result_df['0路'], result_df['1路'], result_df['2路'] = c0, c1, c2
    result_df['012形态'] = [f"{c0[i]}:{c1[i]}:{c2[i]}" for i in range(len(df))]

    ratio_counts = result_df['012形态'].value_counts()
    top_1_ratio = ratio_counts.index[0]
    top_2_ratio = ratio_counts.index[1] if len(ratio_counts) > 1 else top_1_ratio

    is_top1_hit = (result_df['012形态'] == top_1_ratio).astype(int)
    curr_gap = (~is_top1_hit.iloc[::-1].astype(bool)).cummin().sum()
    dyn_thresh = calculate_dynamic_threshold(is_top1_hit)

    st.markdown("### 🚨 零、 架构师 AI 核心 012路 临界预警")
    if curr_gap >= dyn_thresh:
        st.markdown(f"""
        <div class='alert-card'>
            <h3 style='color: #ff4b4b; margin-top:0;'>⚠️ 012路骨架极限回补触发！</h3>
            <p>绝对主导形态 <b>[{top_1_ratio}]</b> 遗漏 {curr_gap} 期，突破极限！放弃包围打法，直接单防锁定！</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='safe-card'><h3>✅ 012路骨架分布健康</h3><p>常规防守即可，勿偏态杀号。</p></div>",
                    unsafe_allow_html=True)

    st.markdown("### 📊 一、 形态历史频次与遗漏追踪")
    stats = result_df['012形态'].value_counts().reset_index()
    stats.columns = ['形态', '期数'];
    stats['占比'] = (stats['期数'] / len(df)).map('{:.2%}'.format)
    last_idx = result_df.reset_index().groupby('012形态')['index'].max()
    stats['当前遗漏'] = stats['形态'].map(lambda x: len(result_df) - 1 - last_idx.get(x, 0))

    c_l, c_r = st.columns([5, 3])
    with c_l:
        st_centered_df(stats.sort_values('期数', ascending=False), use_container_width=True, hide_index=True)
    with c_r:
        st.info(f"**🔥 绝对主导形态**\n\n数据表明，前两名形态涵盖了核心中奖区，建议容错锁定。")

    st.markdown("### 📈 二、 最近 50 期 012路 堆叠走势")
    trend = result_df.tail(50).set_index('期号')[['0路', '1路', '2路']]
    st.bar_chart(trend, color=["#ff4b4b", "#1c83e1", "#f9d71c"])

    st.markdown("### 📋 三、 底层明细")
    display_cols = ['期号'] + r_cols + ['012形态', '0路', '1路', '2路']
    st_centered_df(result_df[display_cols].iloc[::-1], use_container_width=True, hide_index=True, height=400)


# 🔄 模块 5：重号
def render_mod_repeat(df, is_ssq):
    total_p = len(df)
    r_cols = [f'r{i + 1}' for i in range(6 if is_ssq else 5)]
    total, red_max = len(df), 33 if is_ssq else 35
    O = np.zeros((total, red_max + 1), dtype=bool)
    for c in r_cols: O[np.arange(total), df[c].values.astype(int)] = True

    O_prev = np.roll(O, shift=1, axis=0);
    O_prev[0, :] = False
    O_prev2 = np.roll(O, shift=2, axis=0);
    O_prev2[0:2, :] = False
    repeats_mat = O & O_prev
    rep_freq = repeats_mat.sum(axis=0)
    trip_mat = O & O_prev & O_prev2
    trip_freq = trip_mat.sum(axis=0)

    result_df = df.copy()
    result_df['重号数'] = repeats_mat.sum(axis=1)
    result_df['三连重号数'] = trip_mat.sum(axis=1)

    s = (result_df['重号数'] > 0).astype(int)
    curr_gap = (~s.iloc[::-1].astype(bool)).cummin().sum()
    dyn_thresh = calculate_dynamic_threshold(s)

    last_nums = [int(df.iloc[-1][c]) for c in r_cols]
    best_pick = sorted([(n, rep_freq[n]) for n in last_nums], key=lambda x: x[1], reverse=True)[0]

    st.markdown("### 🚨 零、 架构师 AI 临界预警系统")
    if curr_gap >= dyn_thresh:
        st.markdown(f"""
        <div class='alert-card'>
            <h3 style='color: #ff4b4b; margin-top:0;'>⚠️ 警报：重号爆发临界点触发！</h3>
            <p style='font-size:1.1em;'>重号已断档 {curr_gap} 期！本期极大概率直落。上期号码中 <b>[{best_pick[0]:02d}]</b> 连庄基因最强！</p>
            <hr style='border-color:#555;'>
            <h4 style='color:#f9d71c;'>🎯 本期动态定胆推荐：</h4>
            <p>建议本期将号码 <b>[{best_pick[0]:02d}]</b> 作为核心胆码！</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='safe-card'>
            <h3 style='color: #00FF7F; margin-top:0;'>✅ 提示：重号指标目前处于安全波动区</h3>
            <p style='font-size:1.1em;'>当前重号遗漏了 <b>{curr_gap}</b> 期，尚未达到历史高频断档临界点。可按常规常态化过滤条件进行设防。</p>
            <hr style='border-color:#555;'>
            <h4 style='color:#00FF7F;'>💡 备用防守推荐：</h4>
            <p>如果本期你非要防一手重号，在上一期号码中，号码 <b>[{best_pick[0]:02d}]</b> 的连庄基因最强。</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📊 一、 宏观重号频次与当前遗漏追踪")
    stats = result_df['重号数'].value_counts().reset_index()
    stats.columns = ['本期出现重号个数', '历史开出期数']
    stats['发生概率'] = (stats['历史开出期数'] / total_p).map('{:.2%}'.format)
    last_idx = result_df.reset_index().groupby('重号数')['index'].max()
    stats['⏳ 当前遗漏 (期)'] = stats['本期出现重号个数'].map(lambda x: len(result_df) - 1 - last_idx.get(x, 0))
    stats = stats.sort_values('本期出现重号个数')

    c1, c2 = st.columns([1, 1])
    with c1:
        st_centered_df(stats, use_container_width=True, hide_index=True)
    with c2:
        st.bar_chart(result_df['重号数'].value_counts().sort_index(), color="#ff4b4b")

    st.markdown("### 🎯 二、 全盘号码【直落重号体质】全景剖析")
    hotness = [{'号码': f"{i:02d}", '历史直落重号次数': rep_freq[i]} for i in range(1, red_max + 1)]
    total_all_repeats = sum(rep_freq[1:red_max + 1])
    for i in range(red_max): hotness[i]['全盘重号占比'] = (
                hotness[i]['历史直落重号次数'] / total_all_repeats) if total_all_repeats > 0 else 0

    h_df = pd.DataFrame(hotness).sort_values('历史直落重号次数', ascending=False).reset_index(drop=True)
    h_df_display = h_df.copy()
    h_df_display['全盘重号占比'] = h_df_display['全盘重号占比'].map('{:.2%}'.format)

    ca, cb, cc = st.columns(3)
    ca.markdown(
        f"<div class='stat-card'><h4 style='color:#ff4b4b;'>🔥 最狂热重号</h4><h2>{h_df.iloc[0]['号码']}</h2><p>直落: {h_df.iloc[0]['历史直落重号次数']} 次</p></div>",
        unsafe_allow_html=True)
    cb.markdown(
        f"<div class='stat-card'><h4 style='color:#f9d71c;'>⚖️ 常态基准重号</h4><h2>{h_df.iloc[len(h_df) // 2]['号码']}</h2><p>直落: {h_df.iloc[len(h_df) // 2]['历史直落重号次数']} 次</p></div>",
        unsafe_allow_html=True)
    cc.markdown(
        f"<div class='stat-card'><h4 style='color:#1c83e1;'>❄️ 最抗拒重号</h4><h2>{h_df.iloc[-1]['号码']}</h2><p>直落: {h_df.iloc[-1]['历史直落重号次数']} 次</p></div>",
        unsafe_allow_html=True)

    with st.expander("📄 点击查看：所有号码【直落重号次数】完整排行榜", expanded=False):
        st_centered_df(h_df_display, use_container_width=True, hide_index=True)

    st.markdown("### ⏱️ 三、 重号连庄与断档时间线 (发生频次排行榜)")
    streaks = s.groupby((s != s.shift()).cumsum()).sum()
    streaks = streaks[streaks > 0]
    streak_counts = streaks.value_counts().reset_index()
    streak_counts.columns = ['连续出现重号的期数', '历史上发生的次数']
    streak_counts['发生概率'] = (streak_counts['历史上发生的次数'] / len(streaks)).map('{:.2%}'.format)
    streak_counts = streak_counts.sort_values('历史上发生的次数', ascending=False)

    gaps = (~s.astype(bool)).groupby((s != s.shift()).cumsum()).sum()
    gaps = gaps[gaps > 0]
    gap_counts = gaps.value_counts().reset_index()
    gap_counts.columns = ['重号消失的间隔期数', '历史上发生的次数']
    gap_counts['发生概率'] = (gap_counts['历史上发生的次数'] / len(gaps)).map('{:.2%}'.format)
    gap_counts = gap_counts.sort_values('历史上发生的次数', ascending=False)

    colA, colB = st.columns(2)
    with colA:
        st.markdown("<h5 style='color:#f9d71c;'>📊 连庄期数分布排行榜 (Top形态)</h5>", unsafe_allow_html=True)
        st_centered_df(streak_counts.head(8), use_container_width=True, hide_index=True)
    with colB:
        st.markdown("<h5 style='color:#1c83e1;'>📊 断档间隔分布排行榜 (Top形态)</h5>", unsafe_allow_html=True)
        st_centered_df(gap_counts.head(8), use_container_width=True, hide_index=True)

    st.markdown("### 🧬 四、 极限形态：三连重号 (连续 3 期开出) 深度剖析")
    t1, t2 = st.columns([1, 1])
    with t1:
        trip_hotness = [{'号码': f"{i:02d}", '连续3期开出总次数': trip_freq[i]} for i in range(1, red_max + 1)]
        trip_df = pd.DataFrame(trip_hotness).sort_values(by='连续3期开出总次数', ascending=False).reset_index(drop=True)
        st.markdown("<h5 style='color:#8a2be2;'>🏆 三连重号王 排行榜</h5>", unsafe_allow_html=True)
        st_centered_df(trip_df[trip_df['连续3期开出总次数'] > 0].head(10), use_container_width=True, hide_index=True)

    with t2:
        s_trip = (result_df['三连重号数'] > 0).astype(int)
        gaps_trip = (~s_trip.astype(bool)).groupby((s_trip != s_trip.shift()).cumsum()).sum()
        gaps_trip = gaps_trip[gaps_trip > 0]
        gap_trip_counts = gaps_trip.value_counts().reset_index()
        if not gap_trip_counts.empty:
            gap_trip_counts.columns = ['三连重号爆发的间隔期数', '历史上发生的次数']
            gap_trip_counts['发生概率'] = (gap_trip_counts['历史上发生的次数'] / len(gaps_trip)).map('{:.2%}'.format)
            gap_trip_counts = gap_trip_counts.sort_values('历史上发生的次数', ascending=False)
            st.markdown("<h5 style='color:#8a2be2;'>⏳ 三连重号爆发间隔 排行榜</h5>", unsafe_allow_html=True)
            st_centered_df(gap_trip_counts.head(10), use_container_width=True, hide_index=True)
        else:
            st.info("数据样本中暂无三连重号断档数据。")

    st.markdown("### 📈 五、 最近 50 期重号波形追踪图")
    st.line_chart(result_df.tail(50).set_index('期号')[['重号数', '三连重号数']], color=["#ff4b4b", "#8a2be2"])

    st.markdown("### 📋 六、 底层明细表")
    st_centered_df(result_df[['期号'] + r_cols + ['重号数', '三连重号数']].iloc[::-1], use_container_width=True,
                   hide_index=True, height=400)


# 🔥 模块 6：冷热温号
def render_mod_hot_cold(df, is_ssq):
    st.markdown("### ⚙️ 分析跨度雷达控制")
    c_m, c_s = st.columns([1, 2])
    mode = c_m.radio("选择温度测算范围：", ["🎯 自定义近期 (捕获短期波段)", "🌐 全量历史 (探明长期底层基准)"],
                     horizontal=True)

    if "自定义" in mode:
        window = c_s.slider("滑动选择最近 N 期：", min_value=30, max_value=min(len(df), 500), value=100, step=10)
    else:
        window = len(df)
        c_s.info(f"✅ 已开启全盘扫描：系统将对全部 **{len(df)}** 期历史数据进行底层的冷热温基因解析。")

    r_cols = [f'r{i + 1}' for i in range(6 if is_ssq else 5)]
    recent_df = df.tail(window).reset_index(drop=True)
    red_max = 33 if is_ssq else 35
    freq = {i: 0 for i in range(1, red_max + 1)}

    for c in r_cols:
        for n, cnt in recent_df[c].value_counts().items(): freq[int(n)] += cnt

    temp_df = pd.DataFrame([{'号码': f"{num:02d}", '频次': freq[num]} for num in range(1, red_max + 1)])

    latest_idx = len(df) - 1
    omis = {}
    for i in range(1, red_max + 1):
        mask = (df[r_cols] == i).any(axis=1)
        omis[i] = latest_idx - df[mask].index.max() if mask.any() else len(df)
    temp_df['当前遗漏'] = [omis[i] for i in range(1, red_max + 1)]

    temp_df = temp_df.sort_values('频次', ascending=False).reset_index(drop=True)
    hot_c, cold_c = int(red_max * 0.3), int(red_max * 0.3)
    temp_df['标签'] = '⚖️ 温号'
    temp_df.loc[:hot_c - 1, '标签'] = '🔥 热号'
    temp_df.loc[red_max - cold_c:, '标签'] = '❄️ 冷号'

    hot_set = set(temp_df[temp_df['标签'] == '🔥 热号']['号码'].astype(int))
    warm_set = set(temp_df[temp_df['标签'] == '⚖️ 温号']['号码'].astype(int))
    cold_set = set(temp_df[temp_df['标签'] == '❄️ 冷号']['号码'].astype(int))

    ratio_data = []
    for _, row in recent_df.iterrows():
        nums = [int(row[c]) for c in r_cols]
        h = sum(1 for n in nums if n in hot_set)
        w = sum(1 for n in nums if n in warm_set)
        c = sum(1 for n in nums if n in cold_set)
        ratio_data.append({'期号': row['期号'], '🔥热号数': h, '⚖️温号数': w, '❄️冷号数': c,
                           '冷热温结构比 (热:温:冷)': f"{h}:{w}:{c}"})
    ratio_df = pd.DataFrame(ratio_data)

    st.markdown("### 🚨 零、 架构师 AI 号码温度预警系统")
    hot_df = temp_df[temp_df['标签'] == '🔥 热号'].copy()
    hot_df['警戒阈值'] = (window / (hot_df['频次'] + 1)) * 2.5
    volcanoes = hot_df[hot_df['当前遗漏'] > hot_df['警戒阈值']]

    if not volcanoes.empty:
        volcano_nums = volcanoes['号码'].tolist()
        num_str = "、".join([f"[{n}]" for n in volcano_nums])
        st.markdown(f"""
        <div class='alert-card'>
            <h3 style='color: #ff4b4b; margin-top:0;'>⚠️ 警报：探明“休眠火山”级热号，极易井喷！</h3>
            <p style='font-size:1.1em;'>系统监测到，当前跨度内极度活跃的热号 <b>{num_str}</b>，目前的遗漏期数已严重超过其理论极值区！</p>
            <p>它们在过去的 {window} 期内属于绝对热点，但近期遭到了物理性压抑。目前处于随时爆发的临界点！</p>
            <hr style='border-color:#555;'>
            <h4 style='color:#f9d71c;'>🎯 本期动态定胆推荐：</h4>
            <p>本期在配置过滤大底或定胆时，强烈建议将 <b>{num_str}</b> 纳入核心定胆库。以博取高频均值回归的利润！</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='safe-card'>
            <h3 style='color: #00FF7F; margin-top:0;'>✅ 提示：大盘温度梯度健康，无极端休眠热号</h3>
            <p style='font-size:1.1em;'>当前所有的【热号】都在正常的活跃期内轮动开出，没有发现被严重压抑的极限号码。</p>
            <hr style='border-color:#555;'>
            <h4 style='color:#00FF7F;'>💡 常规防守推荐：</h4>
            <p>本期大盘无明显定胆干预信号。请参考下方的<b>冷热温结构比</b>配置常规缩水大底即可。</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"### 🌡️ 一、 指定跨度 ({window}期) 核心号码分级池")
    c1, c2, c3 = st.columns(3)
    c1.markdown("<h4>🔥 绝对热号池 (Top 30%)</h4>" + "".join(
        [f"<span class='num-ball-hot'>{x}</span>" for x in temp_df[temp_df['标签'] == '🔥 热号']['号码']]),
                unsafe_allow_html=True)
    c2.markdown("<h4>⚖️ 中坚温号池 (Middle 40%)</h4>" + "".join(
        [f"<span class='num-ball-warm'>{x}</span>" for x in temp_df[temp_df['标签'] == '⚖️ 温号']['号码']]),
                unsafe_allow_html=True)
    c3.markdown("<h4>❄️ 冰冻冷号池 (Bottom 30%)</h4>" + "".join(
        [f"<span class='num-ball-cold'>{x}</span>" for x in temp_df[temp_df['标签'] == '❄️ 冷号']['号码']]),
                unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"### 🧬 二、 “冷热温”黄金搭配比例与近期波形")
    st.write(
        "💡 *图表说明：横向柱子总高度固定（代表开奖总球数）。色块大小代表该期开出了几个热/温/冷号。一目了然看穿大盘偏移。*")

    L2, R2 = st.columns([1, 2])
    with L2:
        ratio_stats = ratio_df['冷热温结构比 (热:温:冷)'].value_counts().reset_index()
        ratio_stats.columns = ['冷热温结构比 (热:温:冷)', '发生期数']
        ratio_stats['概率占比'] = (ratio_stats['发生期数'] / window).map('{:.2%}'.format)

        st.markdown(f"**(1) 基于 {window} 期的结构分布排行榜**")
        st_centered_df(ratio_stats, use_container_width=True, hide_index=True)

        top1_ratio = ratio_stats.iloc[0]['冷热温结构比 (热:温:冷)']
        st.info(
            f"**🎯 过滤定胆建议：**\n\n在当前跨度中，最常规的组号比例是 **{top1_ratio}**。配号时，请严格参考这一梯队比例分配号码！")

    with R2:
        st.markdown("**(2) 最近 50 期冷热温结构堆叠走势图**")
        trend_ratio_df = ratio_df.tail(50).set_index('期号')[['🔥热号数', '⚖️温号数', '❄️冷号数']]
        st.bar_chart(trend_ratio_df, color=["#ff4b4b", "#f9d71c", "#1c83e1"])

    st.markdown("---")
    st.markdown(f"### 📈 三、 全盘号码【出现频次】分布直方图")
    st.bar_chart(temp_df.set_index('号码')[['频次']].sort_index(), color="#ff4b4b")

    st.markdown("### 📋 四、 底层温度特征明细表")
    st.write("💡 *操作提示：您可以点击表头（如点击“当前遗漏”），系统会自动为您排列出当前消失最久的号码。*")
    st_centered_df(temp_df, use_container_width=True, hide_index=True, height=400)


# ==========================================
# 🚀 连号/尾号系列 UNIVERSAL 终极解析引擎
# ==========================================
@st.cache_data(show_spinner=False)
def calculate_universal_sequence(df, is_ssq, mode):
    # mode: 1 (顺连), 2 (跳期), 3 (斜连)
    total, red_max = len(df), 33 if is_ssq else 35
    r_cols = [f'r{i + 1}' for i in range(6 if is_ssq else 5)]
    R = np.zeros((total, red_max + 1), dtype=bool)
    for i in range(total):
        for c in r_cols:
            if pd.notna(df.iloc[i][c]): R[i, int(df.iloc[i][c])] = True

    primes = {1, 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31}
    composites = {4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 21, 22, 24, 25, 26, 27, 28, 30, 32, 33, 34, 35}

    time_gap = 1 if mode == 3 else (2 if mode == 2 else 0)
    steps = [1, 2, 3, 4]
    keys = ['step_1', 'step_2_odd', 'step_2_even', 'step_3_prime', 'step_3_comp', 'step_4']

    results = [{k: [] for k in keys} for _ in range(total)]

    for t in range(total):
        for n in range(1, red_max + 1):
            if not R[t, n]: continue
            for s in steps:
                for dir_gap in ([1] if mode == 1 else [1, -1]):
                    v_gap = s * dir_gap
                    if mode != 1:
                        if t + time_gap < total and 1 <= n + v_gap <= red_max and R[t + time_gap, n + v_gap]: continue
                    else:
                        if 1 <= n - v_gap <= red_max and R[t, n - v_gap]: continue

                    l = 1;
                    tr_t, tr_n = t, n
                    seq_vals = [n]
                    while True:
                        tr_t -= time_gap;
                        tr_n -= (v_gap if mode != 1 else -v_gap)
                        if tr_t >= 0 and 1 <= tr_n <= red_max and R[tr_t, tr_n]:
                            l += 1;
                            seq_vals.append(tr_n)
                        else:
                            break

                    if l >= 2:
                        if mode != 1: seq_vals.reverse()
                        seq_str = ("->" if mode != 1 else ",").join([f"{x:02d}" for x in seq_vals])
                        start_val = seq_vals[0] if mode != 1 else min(seq_vals)

                        k = 'step_1' if s == 1 else 'step_4'
                        if s == 2: k = 'step_2_odd' if start_val % 2 != 0 else 'step_2_even'
                        if s == 3: k = 'step_3_prime' if start_val in primes else 'step_3_comp'
                        results[t][k].append((seq_vals, seq_str))

    res_df = []
    omits = {k: 0 for k in keys}
    for t in range(total):
        row_data = {'期号': df.iloc[t]['期号'],
                    '开奖红球': " ".join([f"{int(df.iloc[t][c]):02d}" for c in r_cols if pd.notna(df.iloc[t][c])])}
        has_event = False
        for k in keys:
            grp_data = results[t][k]
            c2 = c3 = c4 = p2 = c2_c = p3 = c3_c = p4 = c4_c = 0
            strs = []
            if grp_data:
                has_event = True;
                omits[k] = 0
                for vals, s_str in grp_data:
                    l = len(vals)
                    curr_p = sum(1 for x in vals if x in primes)
                    curr_c = sum(1 for x in vals if x in composites)
                    if l == 2:
                        c2 += 1; p2 += curr_p; c2_c += curr_c
                    elif l == 3:
                        c3 += 1; p3 += curr_p; c3_c += curr_c
                    elif l >= 4:
                        c4 += 1; p4 += curr_p; c4_c += curr_c
                    strs.append(f"[{s_str}]" if mode == 1 else s_str)
            else:
                omits[k] += 1

            row_data[f'{k}_明细'] = " | ".join(strs) if strs else "-"
            row_data[f'{k}_遗漏'] = omits[k]
            row_data[f'{k}_2连'] = c2;
            row_data[f'{k}_2连_质'] = p2;
            row_data[f'{k}_2连_合'] = c2_c
            row_data[f'{k}_3连'] = c3;
            row_data[f'{k}_3连_质'] = p3;
            row_data[f'{k}_3连_合'] = c3_c
            row_data[f'{k}_4连'] = c4;
            row_data[f'{k}_4连_质'] = p4;
            row_data[f'{k}_4连_合'] = c4_c

        if mode != 1: row_data['是否发生跳期' if mode == 2 else '是否发生斜连'] = '是' if has_event else '否'
        res_df.append(row_data)

    return pd.DataFrame(res_df)


@st.cache_data(show_spinner=False)
def calculate_tail_features(df, is_ssq):
    red_n = 6 if is_ssq else 5
    r_cols = [f'r{i + 1}' for i in range(red_n)]
    small_tails = {0, 1, 2, 3, 4}
    big_tails = {5, 6, 7, 8, 9}

    detailed_data = []
    keys_seq = ['step_1', 'step_2_odd', 'step_2_even', 'step_3']
    omits_seq = {k: 0 for k in keys_seq}
    omits_same = {'double': 0, 'triple': 0}

    for _, row in df.iterrows():
        reds = row[r_cols].values
        tails = [x % 10 for x in reds if pd.notna(x)]

        row_data = {'期号': row['期号'], '开奖红球': " ".join([f"{int(x):02d}" for x in reds if pd.notna(x)]),
                    '尾数阵列': " ".join([str(int(t)) for t in tails])}

        tail_counts = pd.Series(tails).value_counts()
        double_tails = tail_counts[tail_counts == 2].index.tolist()
        triple_tails = tail_counts[tail_counts >= 3].index.tolist()

        if double_tails:
            omits_same['double'] = 0
            row_data['同尾_双同尾组数'] = len(double_tails)
            row_data['同尾_双同尾明细'] = " | ".join([f"尾{int(t)}(2个)" for t in double_tails])
        else:
            omits_same['double'] += 1;
            row_data['同尾_双同尾组数'] = 0;
            row_data['同尾_双同尾明细'] = "-"
        row_data['同尾_双同尾遗漏'] = omits_same['double']

        if triple_tails:
            omits_same['triple'] = 0
            row_data['同尾_三同尾组数'] = len(triple_tails)
            row_data['同尾_三同尾明细'] = " | ".join([f"尾{int(t)}(3个+)" for t in triple_tails])
        else:
            omits_same['triple'] += 1;
            row_data['同尾_三同尾组数'] = 0;
            row_data['同尾_三同尾明细'] = "-"
        row_data['同尾_三同尾遗漏'] = omits_same['triple']

        unique_tails = sorted(list(set(tails)))
        row_groups = {k: [] for k in keys_seq}

        for step in [1, 2, 3]:
            visited = set()
            for n in unique_tails:
                if n not in visited and n - step not in unique_tails:
                    curr = [n];
                    visited.add(n);
                    next_n = n + step
                    while next_n in unique_tails: curr.append(next_n); visited.add(next_n); next_n += step
                    if len(curr) >= 2:
                        if step == 1:
                            row_groups['step_1'].append(curr)
                        elif step == 2:
                            if curr[0] % 2 != 0:
                                row_groups['step_2_odd'].append(curr)
                            else:
                                row_groups['step_2_even'].append(curr)
                        elif step == 3:
                            row_groups['step_3'].append(curr)

        for k in keys_seq:
            groups = row_groups[k]
            c2 = c3 = c4 = s2 = b2 = s3 = b3 = s4 = b4 = 0
            strs = []
            if groups:
                omits_seq[k] = 0
                for grp in groups:
                    l = len(grp)
                    c_s = sum(1 for n in grp if n in small_tails)
                    c_b = sum(1 for n in grp if n in big_tails)
                    if l == 2:
                        c2 += 1; s2 += c_s; b2 += c_b
                    elif l == 3:
                        c3 += 1; s3 += c_s; b3 += c_b
                    elif l >= 4:
                        c4 += 1; s4 += c_s; b4 += c_b
                    strs.append(f"[{','.join([str(int(x)) for x in grp])}]")
            else:
                omits_seq[k] += 1

            row_data[f'{k}_明细'] = " | ".join(strs) if strs else "-"
            row_data[f'{k}_遗漏'] = omits_seq[k]
            row_data[f'{k}_2连'] = c2;
            row_data[f'{k}_2连_小'] = s2;
            row_data[f'{k}_2连_大'] = b2
            row_data[f'{k}_3连'] = c3;
            row_data[f'{k}_3连_小'] = s3;
            row_data[f'{k}_3连_大'] = b3
            row_data[f'{k}_4连'] = c4;
            row_data[f'{k}_4连_小'] = s4;
            row_data[f'{k}_4连_大'] = b4

        detailed_data.append(row_data)

    return pd.DataFrame(detailed_data)


def render_tab_alert_shared(pillars, seq_df, recommendation):
    alerts = []
    for cnt_col, omit_col, name, multiplier in pillars:
        is_hit = (seq_df[cnt_col] > 0).astype(int)
        current_gap = seq_df.iloc[-1][omit_col]
        gaps = (~is_hit.astype(bool)).groupby((is_hit != is_hit.shift()).cumsum()).sum()
        gaps = gaps[gaps > 0]
        mode_gap = int(gaps.mode()[0]) if not gaps.empty else 0
        if current_gap >= mode_gap * multiplier and mode_gap > 0:
            alerts.append({'name': name, 'gap': current_gap, 'mode': mode_gap})
    if len(alerts) > 0:
        alert_msgs = "".join([
                                 f"<li style='margin-bottom: 5px;'>🎯 形态 <b>{a['name']}</b> 常态每 {a['mode']} 期回补，现已遗漏 <b style='color:#ff4b4b; font-size:1.1em;'>{a['gap']}</b> 期！(极度紧绷)</li>"
                                 for a in alerts])
        st.markdown(
            f"<div class='alert-card'><h4 style='color: #ff4b4b; margin-top:0;'>🚨 AI 局部形态爆发预警</h4><ul style='margin-bottom: 10px;'>{alert_msgs}</ul><span style='font-size:0.95em; color:#f9d71c;'><b>💡 定胆建议：</b>{recommendation}</span></div>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            f"<div class='safe-card'><h4 style='color: #00FF7F; margin-top:0;'>✅ 本页各形态指标处于安全震荡区</h4><span style='font-size:0.95em; color:#bbb;'>防守常态即可。</span></div>",
            unsafe_allow_html=True)


def render_metric_card_shared(title, c2, hit2, p2, c2_c, c3, hit3, p3, c3_c, c4, hit4, p4, c4_c, current_omit,
                              tot_hits_periods, total_p, color, is_tail=False):
    tot_groups = c2 + c3 + c4
    rate = tot_hits_periods / total_p if total_p else 0
    tag1, tag2 = ("卷入【小尾0-4】", "卷入【大尾5-9】") if is_tail else ("卷入质数", "卷入合数")

    def make_sub_row(label, cnt, hit, p, c):
        pc_tot = p + c if (p + c) > 0 else 1
        hit_rate = hit / total_p if total_p else 0
        return (
            f"<div style='background:rgba(0,0,0,0.15); padding:10px; border-radius:6px; margin-bottom:8px; text-align:left; border-left: 3px solid {color};'>"
            f"<span style='color:#fff; font-weight:bold;'>🔹 {label}:</span> 共 <b style='color:#fff'>{cnt}</b> 组 "
            f"<span style='color:#bbb; font-size:0.9em;'>(覆盖 <b>{hit}</b> 期，占比 <b>{hit_rate:.2%}</b>)</span><br />"
            f"<span style='font-size:0.9em; color:#bbb; display:block; margin-top:4px;'>🔸 {tag1}: <b style='color:#fff'>{p}</b> 个 ({(p / pc_tot):.1%}) &nbsp;|&nbsp; {tag2}: <b style='color:#fff'>{c}</b> 个 ({(c / pc_tot):.1%})</span></div>")

    lbl2, lbl3, lbl4 = ("尾数2连", "尾数3连", "尾数4连及以上") if is_tail else ("2连形态", "3连形态", "4连及以上")
    main_html = (f"<div class='stat-card'><h4 style='color: {color};'>{title}</h4>"
                 f"<p>全盘共发生: <span style='color:#ff4b4b;font-weight:bold;'>{tot_groups}</span> 组 (占总盘 <b>{rate:.2%}</b>)</p>"
                 f"<p style='color:#888;margin-bottom:12px;'>⏳ <b>当前遗漏: <span style='color:#ff4b4b'>{current_omit}</span> 期</b></p>"
                 f"{make_sub_row(lbl2, c2, hit2, p2, c2_c)}{make_sub_row(lbl3, c3, hit3, p3, c3_c)}{make_sub_row(lbl4, c4, hit4, p4, c4_c)}</div>")
    st.markdown(main_html, unsafe_allow_html=True)


def render_seq_shared(df, is_ssq, title, mode, recs):
    st.markdown(f"### 📊 一、 各步长规律{title}深度剖析 (全息拆解)")
    with st.spinner("正在提取基因矩阵..."):
        seq_df = calculate_universal_sequence(df, is_ssq, mode)

    last_row = seq_df.iloc[-1]
    tot_p = len(seq_df)
    name_t = "连" if mode == 1 else ("跳期" if mode == 2 else "斜连")

    tab1, tab2, tab3, tab4 = st.tabs(
        [f"🟢 步长=1 (顺序{name_t})", f"🟡 步长=2 (奇/偶分离)", f"🟣 步长=3 (质/合分离)", f"🟤 步长=4 (交叉{name_t})"])

    def pass_args(k):
        tot = ((seq_df[f'{k}_2连'] + seq_df[f'{k}_3连'] + seq_df[f'{k}_4连']) > 0).sum()
        return (seq_df[f'{k}_2连'].sum(), (seq_df[f'{k}_2连'] > 0).sum(), seq_df[f'{k}_2连_质'].sum(),
                seq_df[f'{k}_2连_合'].sum(),
                seq_df[f'{k}_3连'].sum(), (seq_df[f'{k}_3连'] > 0).sum(), seq_df[f'{k}_3连_质'].sum(),
                seq_df[f'{k}_3连_合'].sum(),
                seq_df[f'{k}_4连'].sum(), (seq_df[f'{k}_4连'] > 0).sum(), seq_df[f'{k}_4连_质'].sum(),
                seq_df[f'{k}_4连_合'].sum(),
                last_row[f'{k}_遗漏'], tot, tot_p)

    with tab1:
        render_tab_alert_shared([('step_1_2连', 'step_1_遗漏', f'【步长1:绝对顺序{name_t}】', 1.5)], seq_df, recs[0])
        render_metric_card_shared(f"📌 绝对顺序{name_t}", *pass_args('step_1'), "#4da6ff")
    with tab2:
        render_tab_alert_shared([('step_2_odd_2连', 'step_2_odd_遗漏', f'【纯奇数{name_t}】', 1.5),
                                 ('step_2_even_2连', 'step_2_even_遗漏', f'【纯偶数{name_t}】', 1.5)], seq_df, recs[1])
        c1, c2 = st.columns(2)
        with c1: render_metric_card_shared(f"🟡 纯奇数{name_t}", *pass_args('step_2_odd'), "#f9d71c")
        with c2: render_metric_card_shared(f"🟡 纯偶数{name_t}", *pass_args('step_2_even'), "#e6b800")
    with tab3:
        render_tab_alert_shared([('step_3_prime_2连', 'step_3_prime_遗漏', f'【质数起步{name_t}】', 1.5),
                                 ('step_3_comp_2连', 'step_3_comp_遗漏', f'【合数起步{name_t}】', 1.5)], seq_df, recs[2])
        c1, c2 = st.columns(2)
        with c1: render_metric_card_shared(f"🟣 质数起步{name_t}", *pass_args('step_3_prime'), "#8a2be2")
        with c2: render_metric_card_shared(f"🟣 合数起步{name_t}", *pass_args('step_3_comp'), "#6a1b9a")
    with tab4:
        render_tab_alert_shared([('step_4_2连', 'step_4_遗漏', f'【步长4:交叉{name_t}】', 1.5)], seq_df, recs[3])
        render_metric_card_shared(f"🟤 交叉{name_t}", *pass_args('step_4'), "#ff7f50")

    st.markdown(f"### 📈 二、 最近 50 期【四维核心 2{name_t}】阵营博弈走势图")
    st.line_chart(seq_df.tail(50).set_index('期号')[['step_1_2连', 'step_2_odd_2连', 'step_2_even_2连', 'step_4_2连']],
                  color=["#4da6ff", "#f9d71c", "#e6b800", "#ff7f50"])

    st.markdown("### 📋 三、 历史数据底层明细 (支持检视追踪详情)")
    disp_cols = ['期号', '开奖红球']
    if mode == 2: disp_cols.append('是否发生跳期')
    if mode == 3: disp_cols.append('是否发生斜连')
    disp_cols.extend(
        ['step_1_明细', 'step_1_遗漏', 'step_2_odd_明细', 'step_2_even_明细', 'step_3_prime_明细', 'step_3_comp_明细',
         'step_4_明细'])

    d_df = seq_df[disp_cols].iloc[::-1].copy()
    d_df.rename(columns={
        'step_1_明细': '步长1(顺序)明细', 'step_1_遗漏': '步长1遗漏',
        'step_2_odd_明细': '步长2(奇数)明细', 'step_2_even_明细': '步长2(偶数)明细',
        'step_3_prime_明细': '步长3(质起步)明细', 'step_3_comp_明细': '步长3(合起步)明细',
        'step_4_明细': '步长4(交叉)明细'
    }, inplace=True)
    st_centered_df(d_df, use_container_width=True, hide_index=True, height=500)


# 🎱 模块 10：尾号
def render_mod_tail(df, is_ssq):
    st.markdown("### 📊 一、 同尾与尾数连号 分布式深度解构")
    with st.spinner("正在将号码矩阵降维至尾数空间，剥离同尾与步长偏态..."):
        seq_df = calculate_tail_features(df, is_ssq)

    last_row = seq_df.iloc[-1]
    total_periods = len(seq_df)

    tab0, tab1, tab2, tab3 = st.tabs(
        ["🔥 基础: 同尾号(含三同尾)", "🟢 步长=1 (顺序尾连)", "🟡 步长=2 (奇/偶尾分离)", "🟣 步长=3 (等差尾连)"])

    def pass_args_tail(k):
        tot = ((seq_df[f'{k}_2连'] + seq_df[f'{k}_3连'] + seq_df[f'{k}_4连']) > 0).sum()
        return (seq_df[f'{k}_2连'].sum(), (seq_df[f'{k}_2连'] > 0).sum(), seq_df[f'{k}_2连_小'].sum(),
                seq_df[f'{k}_2连_大'].sum(),
                seq_df[f'{k}_3连'].sum(), (seq_df[f'{k}_3连'] > 0).sum(), seq_df[f'{k}_3连_小'].sum(),
                seq_df[f'{k}_3连_大'].sum(),
                seq_df[f'{k}_4连'].sum(), (seq_df[f'{k}_4连'] > 0).sum(), seq_df[f'{k}_4连_小'].sum(),
                seq_df[f'{k}_4连_大'].sum(),
                last_row[f'{k}_遗漏'], tot, total_periods)

    with tab0:
        render_tab_alert_shared([('同尾_双同尾组数', '同尾_双同尾遗漏', '【双同尾 (2个同尾号)】', 1.5),
                                 ('同尾_三同尾组数', '同尾_三同尾遗漏', '【三同尾 (3个同尾号)】', 1.3)], seq_df,
                                "若报警【三同尾】，本期请务必强行配置一组含 3 个同尾数的单子！")
        c1, c2 = st.columns(2)
        with c1:
            hit_d = (seq_df['同尾_双同尾组数'] > 0).sum()
            st.markdown(
                f"<div class='stat-card' style='border-left: 5px solid #ff4b4b;'><h4 style='color: #ff4b4b;'>📌 常态：双同尾 (如 13, 23)</h4><p>全盘共覆盖: <span class='highlight'>{hit_d}</span> 期 (占总盘 <b>{hit_d / total_periods:.2%}</b>)</p><p>⏳ 当前遗漏: <b style='color:#ff4b4b'>{last_row['同尾_双同尾遗漏']}</b> 期</p></div>",
                unsafe_allow_html=True)
        with c2:
            hit_t = (seq_df['同尾_三同尾组数'] > 0).sum()
            st.markdown(
                f"<div class='stat-card' style='border-left: 5px solid #e6b800;'><h4 style='color: #e6b800;'>📌 偏冷致命：三同尾 (如 05, 15, 25)</h4><p>全盘共覆盖: <span class='highlight'>{hit_t}</span> 期 (占总盘 <b>{hit_t / total_periods:.2%}</b>)</p><p>⏳ 当前遗漏: <b style='color:#ff4b4b'>{last_row['同尾_三同尾遗漏']}</b> 期</p></div>",
                unsafe_allow_html=True)

    with tab1:
        render_tab_alert_shared([('step_1_2连', 'step_1_遗漏', '【尾数步长1: 顺序尾连】', 1.5)], seq_df,
                                "配置至少一组尾数相邻的号码（如尾3和尾4）。")
        render_metric_card_shared("📌 顺序尾数连号 (如 尾1-2-3)", *pass_args_tail('step_1'), "#4da6ff", is_tail=True)
    with tab2:
        render_tab_alert_shared([('step_2_odd_2连', 'step_2_odd_遗漏', '【尾数步长2: 奇数尾连】', 1.5),
                                 ('step_2_even_2连', 'step_2_even_遗漏', '【尾数步长2: 偶数尾连】', 1.5)], seq_df,
                                "关注报警的特定奇偶属性，进行尾数隔离定胆。")
        c1, c2 = st.columns(2)
        with c1: render_metric_card_shared("🟡 纯奇数尾连号 (如 尾1-3-5)", *pass_args_tail('step_2_odd'), "#f9d71c",
                                           is_tail=True)
        with c2: render_metric_card_shared("🟡 纯偶数尾连号 (如 尾0-2-4)", *pass_args_tail('step_2_even'), "#e6b800",
                                           is_tail=True)
    with tab3:
        render_tab_alert_shared([('step_3_2连', 'step_3_遗漏', '【尾数步长3: 等差3尾连】', 1.5)], seq_df,
                                "选择尾数跨度为 3 的组合（如尾2和尾5）。")
        render_metric_card_shared("🟣 步长3等差尾连 (如 尾1-4-7)", *pass_args_tail('step_3'), "#8a2be2", is_tail=True)

    st.markdown("### 📈 二、 最近 50 期【尾数雷达】核心走势")
    chart_data = seq_df.tail(50).set_index('期号')[
        ['同尾_双同尾组数', '同尾_三同尾组数', 'step_1_2连', 'step_2_odd_2连', 'step_2_even_2连']].rename(
        columns={'同尾_双同尾组数': '双同尾数', '同尾_三同尾组数': '三同尾数', 'step_1_2连': '顺序尾2连',
                 'step_2_odd_2连': '奇数尾2连', 'step_2_even_2连': '偶数尾2连'})
    st.line_chart(chart_data, color=["#ff4b4b", "#e6b800", "#4da6ff", "#f9d71c", "#8a2be2"])

    st.markdown("### 📋 三、 历史数据底层明细 (支持检视追踪详情)")
    d_df = seq_df[
        ['期号', '开奖红球', '尾数阵列', '同尾_双同尾明细', '同尾_双同尾遗漏', '同尾_三同尾明细', '同尾_三同尾遗漏',
         'step_1_明细', 'step_1_遗漏', 'step_2_odd_明细', 'step_2_even_明细', 'step_3_明细', 'step_3_遗漏']].iloc[
        ::-1].copy()
    d_df.rename(
        columns={'step_1_明细': '步长1(顺序尾)明细', 'step_1_遗漏': '步长1遗漏', 'step_2_odd_明细': '步长2(奇数尾)明细',
                 'step_2_even_明细': '步长2(偶数尾)明细', 'step_3_明细': '步长3(等差尾)明细',
                 'step_3_遗漏': '步长3遗漏'}, inplace=True)
    st_centered_df(d_df, use_container_width=True, hide_index=True, height=500)


# 🗺️ 模块 11：前区三区
@st.cache_data(show_spinner=False)
def calculate_zone_features(df, is_ssq):
    red_n = 6 if is_ssq else 5
    r_cols = [f'r{i + 1}' for i in range(red_n)]

    if is_ssq:
        z1_set, z2_set, z3_set = set(range(1, 12)), set(range(12, 23)), set(range(23, 34))
        anchor_1_2, anchor_2_3 = {11, 12}, {22, 23}
    else:
        z1_set, z2_set, z3_set = set(range(1, 13)), set(range(13, 25)), set(range(25, 36))
        anchor_1_2, anchor_2_3 = {12, 13}, {24, 25}

    anchors = anchor_1_2 | anchor_2_3
    detailed_data = []
    omits = {k: 0 for k in ['z1_break', 'z1_burst', 'z2_break', 'z2_burst', 'z3_break', 'z3_burst', 'anchor_hit']}

    for _, row in df.iterrows():
        reds = row[r_cols].values
        c1, c2, c3 = sum(1 for x in reds if x in z1_set), sum(1 for x in reds if x in z2_set), sum(
            1 for x in reds if x in z3_set)
        ratio = f"{c1}:{c2}:{c3}"

        z1_brk, z1_bst = (c1 == 0), (c1 >= 4)
        z2_brk, z2_bst = (c2 == 0), (c2 >= 4)
        z3_brk, z3_bst = (c3 == 0), (c3 >= 4)
        hit_anchors = [x for x in reds if x in anchors]

        omits['z1_break'] = 0 if z1_brk else omits['z1_break'] + 1
        omits['z1_burst'] = 0 if z1_bst else omits['z1_burst'] + 1
        omits['z2_break'] = 0 if z2_brk else omits['z2_break'] + 1
        omits['z2_burst'] = 0 if z2_bst else omits['z2_burst'] + 1
        omits['z3_break'] = 0 if z3_brk else omits['z3_break'] + 1
        omits['z3_burst'] = 0 if z3_bst else omits['z3_burst'] + 1
        omits['anchor_hit'] = 0 if hit_anchors else omits['anchor_hit'] + 1

        detailed_data.append({
            '期号': row['期号'], '开奖红球': " ".join([f"{int(x):02d}" for x in reds]),
            '一区数量': c1, '二区数量': c2, '三区数量': c3, '三区比': ratio,
            '触碰边界锚点': " ".join([f"{int(x):02d}" for x in hit_anchors]) if hit_anchors else "-",
            '一区断区': int(z1_brk), '一区断区遗漏': omits['z1_break'], '一区爆区': int(z1_bst),
            '一区爆区遗漏': omits['z1_burst'],
            '二区断区': int(z2_brk), '二区断区遗漏': omits['z2_break'], '二区爆区': int(z2_bst),
            '二区爆区遗漏': omits['z2_burst'],
            '三区断区': int(z3_brk), '三区断区遗漏': omits['z3_break'], '三区爆区': int(z3_bst),
            '三区爆区遗漏': omits['z3_burst'],
            '锚点命中': int(len(hit_anchors) > 0), '锚点遗漏': omits['anchor_hit']
        })
    return pd.DataFrame(detailed_data), sorted(list(anchor_1_2)), sorted(list(anchor_2_3))


def render_mod_zone(df, is_ssq):
    st.markdown("### 📊 一、 大盘三区结构与极端偏态剖析")
    total_periods = len(df)

    with st.spinner("正在启动三区物理切分，扫描大盘极端偏态..."):
        zone_df, a12, a23 = calculate_zone_features(df, is_ssq)

    last_row = zone_df.iloc[-1]
    tab0, tab1, tab2, tab3, tab4 = st.tabs(
        ["🌐 全局结构比", "🔴 一区态势", "🟡 二区态势", "🔵 三区态势", "🧱 边界锚点(城墙号)"])

    def render_zone_alert(pillars, recommendation="常态分布中，根据历史大势配号即可。"):
        alerts = []
        for cnt_col, omit_col, name, multiplier in pillars:
            is_hit = (zone_df[cnt_col] > 0).astype(int)
            current_gap = zone_df.iloc[-1][omit_col]
            gaps = (~is_hit.astype(bool)).groupby((is_hit != is_hit.shift()).cumsum()).sum()
            gaps = gaps[gaps > 0]
            mode_gap = int(gaps.mode()[0]) if not gaps.empty else 0
            if current_gap >= mode_gap * multiplier and mode_gap > 0:
                alerts.append({'name': name, 'gap': current_gap, 'mode': mode_gap})
        if len(alerts) > 0:
            alert_msgs = "".join([
                                     f"<li style='margin-bottom: 5px;'>🎯 大盘极限 <b>{a['name']}</b> 常态每 {a['mode']} 期发生，现已遗漏 <b style='color:#ff4b4b; font-size:1.1em;'>{a['gap']}</b> 期！</li>"
                                     for a in alerts])
            st.markdown(
                f"<div class='alert-card'><h4 style='color: #ff4b4b; margin-top:0; margin-bottom: 10px;'>🚨 AI 宏观态势爆发预警</h4><ul style='margin-bottom: 10px;'>{alert_msgs}</ul><span style='font-size:0.95em; color:#f9d71c;'><b>💡 定胆与杀号建议：</b>{recommendation}</span></div>",
                unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='safe-card'><h4 style='color: #00FF7F; margin-top:0; margin-bottom: 5px;'>✅ 本区大盘指标处于安全震荡期</h4><span style='font-size:0.95em; color:#bbb;'>未发现极端的断区或爆区压抑信号，平稳防守即可。</span></div>",
                unsafe_allow_html=True)

    def render_zone_metric_card(title, break_cnt, burst_cnt, break_omit, burst_omit, color):
        brk_rate = break_cnt / total_periods if total_periods else 0
        bst_rate = burst_cnt / total_periods if total_periods else 0
        st.markdown(
            f"<div class='stat-card' style='border-left: 4px solid {color};'><h4 style='color: {color}; margin-bottom: 15px;'>{title}</h4><div style='background:rgba(0,0,0,0.15); padding:10px; border-radius:6px; margin-bottom:8px; text-align:left;'><span style='color:#fff; font-weight:bold;'>💀 绝杀断区 (0个号):</span> 发生 <b style='color:#ff4b4b'>{break_cnt}</b> 次 <span style='color:#bbb; font-size:0.9em;'>(占全盘 {brk_rate:.2%})</span><br /><span style='font-size:0.9em; color:#bbb; display:block; margin-top:4px;'>⏳ 当前遗漏: <b style='color:#fff'>{break_omit}</b> 期</span></div><div style='background:rgba(0,0,0,0.15); padding:10px; border-radius:6px; text-align:left;'><span style='color:#fff; font-weight:bold;'>🔥 极限爆区 (≥4个):</span> 发生 <b style='color:#f9d71c'>{burst_cnt}</b> 次 <span style='color:#bbb; font-size:0.9em;'>(占全盘 {bst_rate:.2%})</span><br /><span style='font-size:0.9em; color:#bbb; display:block; margin-top:4px;'>⏳ 当前遗漏: <b style='color:#fff'>{burst_omit}</b> 期</span></div></div>",
            unsafe_allow_html=True)

    with tab0:
        ratio_counts = zone_df['三区比'].value_counts().reset_index()
        ratio_counts.columns = ['三区比形态', '历史发生次数']
        ratio_counts['全盘占比'] = (ratio_counts['历史发生次数'] / total_periods).apply(lambda x: f"{x:.2%}")
        colA, colB = st.columns([1, 2])
        with colA:
            st.markdown("#### 🏆 历史主流结构比 TOP 10")
            st_centered_df(ratio_counts.head(10), hide_index=True, use_container_width=True)
        with colB:
            st.markdown("#### 📈 最近 50 期三区数量堆叠图")
            st.bar_chart(zone_df.tail(50).set_index('期号')[['一区数量', '二区数量', '三区数量']],
                         color=["#ff4b4b", "#f9d71c", "#4da6ff"])

    with tab1:
        render_zone_alert(
            [('一区断区', '一区断区遗漏', '【一区·断区】', 1.5), ('一区爆区', '一区爆区遗漏', '【一区·爆区】', 1.5)],
            "若报警断区，请大胆杀掉一区所有号码；若报警爆区，请重仓一区博取大奖！")
        render_zone_metric_card("🔴 第一区 (小号区) 极限特征", zone_df['一区断区'].sum(), zone_df['一区爆区'].sum(),
                                last_row['一区断区遗漏'], last_row['一区爆区遗漏'], "#ff4b4b")

    with tab2:
        render_zone_alert(
            [('二区断区', '二区断区遗漏', '【二区·断区】', 1.5), ('二区爆区', '二区爆区遗漏', '【二区·爆区】', 1.5)],
            "若报警断区，请大胆杀掉二区所有号码；若报警爆区，请重仓二区博取大奖！")
        render_zone_metric_card("🟡 第二区 (中号区) 极限特征", zone_df['二区断区'].sum(), zone_df['二区爆区'].sum(),
                                last_row['二区断区遗漏'], last_row['二区爆区遗漏'], "#f9d71c")

    with tab3:
        render_zone_alert(
            [('三区断区', '三区断区遗漏', '【三区·断区】', 1.5), ('三区爆区', '三区爆区遗漏', '【三区·爆区】', 1.5)],
            "若报警断区，请大胆杀掉三区所有号码；若报警爆区，请重仓三区博取大奖！")
        render_zone_metric_card("🔵 第三区 (大号区) 极限特征", zone_df['三区断区'].sum(), zone_df['三区爆区'].sum(),
                                last_row['三区断区遗漏'], last_row['三区爆区遗漏'], "#4da6ff")

    with tab4:
        all_anchors = a12 + a23
        st.markdown(
            f"#### 🧱 决定大盘重心的城墙号：<span class='highlight'>[{'、'.join([str(x) for x in all_anchors])}]</span>",
            unsafe_allow_html=True)

        last_hit = last_row['触碰边界锚点']
        if last_hit != "-":
            hit_nums = [int(x) for x in last_hit.split()]
            hit_1_2 = [x for x in hit_nums if x in a12]
            hit_2_3 = [x for x in hit_nums if x in a23]

            advice = ""
            if hit_1_2 and hit_2_3:
                advice = "💥 **一二区与二三区城墙同时告破！** 极其罕见的大盘撕裂信号！下期防守重心两极分化，或者全盘收缩回二区腹地。"
            elif hit_1_2:
                advice = f"⚠️ **一二区交界 (撞击了 {hit_1_2[0]})！** 这说明能量正在一二区之间摩擦。下一期大盘重心极易向二区渗透，防守斜连号 {hit_1_2[0] - 1} 或 {hit_1_2[0] + 1}！"
            elif hit_2_3:
                advice = f"⚠️ **二三区交界 (撞击了 {hit_2_3[0]})！** 这暗示大盘重心极有可能跨入三区大号区，或者被反弹回二区核心。重点防守斜连号 {hit_2_3[0] - 1} 或 {hit_2_3[0] + 1}！"

            st.markdown(
                f"<div class='alert-card' style='border-left-color:#8a2be2;'><h4 style='color: #8a2be2; margin-top:0; margin-bottom: 10px;'>🚨 AI 最新期锚点信号解读</h4><p style='font-size:1.05em;'>最新一期开出了边界锚点 <b>[{last_hit}]</b>！</p><span style='font-size:0.95em; color:#f9d71c;'><b>💡 实战推演：</b>{advice}</span></div>",
                unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='safe-card'><h4 style='color: #00FF7F; margin-top:0; margin-bottom: 5px;'>✅ 最新期未触碰边界锚点</h4><span style='font-size:0.95em; color:#bbb;'>当前大盘重心稳定在各区腹地，暂无明显的重心位移预警。</span></div>",
                unsafe_allow_html=True)

        hit_anc = zone_df['锚点命中'].sum()
        anc_rate = hit_anc / total_periods if total_periods else 0
        st.markdown(
            f"<div class='stat-card' style='border-left: 4px solid #8a2be2;'><h4 style='color: #8a2be2; margin-bottom: 15px;'>🧱 边界锚点活跃度历史统计</h4><div style='background:rgba(0,0,0,0.15); padding:10px; border-radius:6px; text-align:left;'><span style='color:#fff; font-weight:bold;'>🎯 触碰城墙号:</span> 发生 <b style='color:#8a2be2'>{hit_anc}</b> 次 <span style='color:#bbb; font-size:0.9em;'>(占全盘 {anc_rate:.2%})</span><br /><span style='font-size:0.9em; color:#bbb; display:block; margin-top:4px;'>⏳ 当前遗漏: <b style='color:#fff'>{last_row['锚点遗漏']}</b> 期</span></div></div>",
            unsafe_allow_html=True)

    st.markdown("### 📋 二、 历史数据底层明细 (支持检视追踪详情)")
    display_df = zone_df[
        ['期号', '开奖红球', '三区比', '一区断区遗漏', '一区爆区遗漏', '二区断区遗漏', '二区爆区遗漏', '三区断区遗漏',
         '三区爆区遗漏', '触碰边界锚点', '锚点遗漏']].iloc[::-1]
    st_centered_df(display_df, use_container_width=True, hide_index=True, height=500)


# 🚀 模块 12：和值跨度比
@st.cache_data(show_spinner=False)
def calculate_macro_features(df, is_ssq):
    red_n = 6 if is_ssq else 5
    r_cols = [f'r{i + 1}' for i in range(red_n)]
    primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31}

    detailed_data = []
    omits = {
        'sum_odd': 0, 'sum_even': 0, 'sum_small_tail': 0, 'sum_big_tail': 0,
        'span_odd': 0, 'span_even': 0, 'span_prime': 0, 'span_comp': 0, 'span_small_tail': 0, 'span_big_tail': 0,
        'link_odd_odd': 0, 'link_odd_even': 0, 'link_even_odd': 0, 'link_even_even': 0,
        'amp_extreme': 0, 'amp_micro': 0
    }
    prev_sum = None

    for _, row in df.iterrows():
        reds = row[r_cols].values
        sum_val = sum(reds)
        span_val = max(reds) - min(reds)
        sum_tail = sum_val % 10
        span_tail = span_val % 10
        avg_val = round(sum_val / red_n, 2)

        amplitude = abs(sum_val - prev_sum) if prev_sum is not None else 0
        prev_sum = sum_val

        is_amp_extreme = (amplitude >= 35)
        is_amp_micro = (amplitude <= 8)
        sum_is_odd = (sum_val % 2 != 0)
        sum_is_even = not sum_is_odd
        sum_is_small_tail = (sum_tail <= 4)
        sum_is_big_tail = not sum_is_small_tail
        span_is_odd = (span_val % 2 != 0)
        span_is_even = not span_is_odd
        span_is_prime = (span_val in primes)
        span_is_comp = (span_val > 1 and not span_is_prime)
        span_is_small_tail = (span_tail <= 4)
        span_is_big_tail = not span_is_small_tail

        link_oo = sum_is_odd and span_is_odd
        link_oe = sum_is_odd and span_is_even
        link_eo = sum_is_even and span_is_odd
        link_ee = sum_is_even and span_is_even

        omits['sum_odd'] = 0 if sum_is_odd else omits['sum_odd'] + 1
        omits['sum_even'] = 0 if sum_is_even else omits['sum_even'] + 1
        omits['sum_small_tail'] = 0 if sum_is_small_tail else omits['sum_small_tail'] + 1
        omits['sum_big_tail'] = 0 if sum_is_big_tail else omits['sum_big_tail'] + 1
        omits['span_odd'] = 0 if span_is_odd else omits['span_odd'] + 1
        omits['span_even'] = 0 if span_is_even else omits['span_even'] + 1
        omits['span_prime'] = 0 if span_is_prime else omits['span_prime'] + 1
        omits['span_comp'] = 0 if span_is_comp else omits['span_comp'] + 1
        omits['span_small_tail'] = 0 if span_is_small_tail else omits['span_small_tail'] + 1
        omits['span_big_tail'] = 0 if span_is_big_tail else omits['span_big_tail'] + 1
        omits['link_odd_odd'] = 0 if link_oo else omits['link_odd_odd'] + 1
        omits['link_odd_even'] = 0 if link_oe else omits['link_odd_even'] + 1
        omits['link_even_odd'] = 0 if link_eo else omits['link_even_odd'] + 1
        omits['link_even_even'] = 0 if link_ee else omits['link_even_even'] + 1
        omits['amp_extreme'] = 0 if is_amp_extreme else omits['amp_extreme'] + 1
        omits['amp_micro'] = 0 if is_amp_micro else omits['amp_micro'] + 1

        detailed_data.append({
            '期号': row['期号'], '开奖红球': " ".join([f"{int(x):02d}" for x in reds]),
            '和值': sum_val, '和值尾数': sum_tail, '重心均值': avg_val, '绝对振幅': amplitude,
            '跨度': span_val, '跨度尾数': span_tail,
            '和奇': int(sum_is_odd), '和奇漏': omits['sum_odd'], '和偶': int(sum_is_even), '和偶漏': omits['sum_even'],
            '和尾小': int(sum_is_small_tail), '和尾小漏': omits['sum_small_tail'], '和尾大': int(sum_is_big_tail),
            '和尾大漏': omits['sum_big_tail'],
            '跨奇': int(span_is_odd), '跨奇漏': omits['span_odd'], '跨偶': int(span_is_even),
            '跨偶漏': omits['span_even'],
            '跨质': int(span_is_prime), '跨质漏': omits['span_prime'], '跨合': int(span_is_comp),
            '跨合漏': omits['span_comp'],
            '跨尾小': int(span_is_small_tail), '跨尾小漏': omits['span_small_tail'], '跨尾大': int(span_is_big_tail),
            '跨尾大漏': omits['span_big_tail'],
            '联_奇奇': int(link_oo), '联_奇奇漏': omits['link_odd_odd'], '联_奇偶': int(link_oe),
            '联_奇偶漏': omits['link_odd_even'],
            '联_偶奇': int(link_eo), '联_偶奇漏': omits['link_even_odd'], '联_偶偶': int(link_ee),
            '联_偶偶漏': omits['link_even_even'],
            '极速震荡': int(is_amp_extreme), '极震漏': omits['amp_extreme'], '横盘锁死': int(is_amp_micro),
            '横盘漏': omits['amp_micro']
        })
    return pd.DataFrame(detailed_data)


def render_mod_sum_span(df, is_ssq):
    st.markdown("### ⚖️ 和跨双擎 动态联动大底控制台")
    total_periods = len(df)
    with st.spinner("正在计算大盘绝对温度与张力，构筑满血版多维矩阵..."):
        macro_df = calculate_macro_features(df, is_ssq)
    last_row = macro_df.iloc[-1]

    def render_macro_alert(pillars, seq_df, recommendation_template):
        alerts = []
        for cnt_col, omit_col, name in pillars:
            hit_series = (seq_df[cnt_col] > 0).astype(int)
            current_gap = seq_df.iloc[-1][omit_col]
            dynamic_thresh = calculate_dynamic_threshold(hit_series, window=100)
            if current_gap >= dynamic_thresh:
                alerts.append({'name': name, 'gap': current_gap, 'threshold': dynamic_thresh})
        if len(alerts) > 0:
            alert_msgs = "".join([
                                     f"<li style='margin-bottom: 5px;'>🎯 <b>{a['name']}</b> 动态极限允许遗漏为 {a['threshold']} 期，现已爆表遗漏 <b style='color:#ff4b4b; font-size:1.1em;'>{a['gap']}</b> 期！</li>"
                                     for a in alerts])
            st.markdown(
                f"<div class='alert-card'><h4 style='color: #ff4b4b; margin-top:0; margin-bottom: 10px;'>🚨 AI 动态波动偏态预警</h4><ul style='margin-bottom: 10px;'>{alert_msgs}</ul><span style='font-size:0.95em; color:#f9d71c;'><b>💡 智能战术指导：</b>{recommendation_template}</span></div>",
                unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='safe-card'><h4 style='color: #00FF7F; margin-top:0; margin-bottom: 5px;'>✅ 本页宏观指标未击穿布林带上限</h4><span style='font-size:0.95em; color:#bbb;'>大盘物理张力与温度均在合理范围内，无强烈回归信号。</span></div>",
                unsafe_allow_html=True)

    def render_macro_metric_card(title, hit_cnt, hit_omit, total_p, color, desc=""):
        rate = hit_cnt / total_p if total_p else 0
        st.markdown(
            f"<div class='stat-card' style='border-left: 4px solid {color};'><h4 style='color: {color}; margin-bottom: 10px;'>{title}</h4><span style='font-size:0.85em; color:#bbb; display:block; margin-bottom:15px;'>{desc}</span><div style='background:rgba(0,0,0,0.15); padding:10px; border-radius:6px; margin-bottom:8px; text-align:left;'><span style='color:#fff; font-weight:bold;'>🔹 全盘覆盖:</span> 共 <b style='color:#fff'>{hit_cnt}</b> 期 <span style='color:#bbb; font-size:0.9em;'>(占比 {rate:.2%})</span><br /><span style='font-size:0.9em; color:#bbb; display:block; margin-top:4px;'>⏳ 当前遗漏: <b style='color:#ff4b4b'>{hit_omit}</b> 期</span></div></div>",
            unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🌡️ 和值 (Sum) 分析", "🏹 跨度 (Span) 分析", "⚔️ 和跨联动矩阵", "📈 高阶：重心均值 & 振幅"])
    with tab1:
        render_macro_alert([('和奇', '和奇漏', '【和值为奇数】'), ('和偶', '和偶漏', '【和值为偶数】')], macro_df,
                           "若报警【奇数和值】，大底奇数球总数必是单数；若报警【偶数和值】，奇数球总数必是双数！")
        colA, colB = st.columns(2)
        with colA: render_macro_metric_card("🟡 奇数和值", macro_df['和奇'].sum(), last_row['和奇漏'], total_periods,
                                            "#f9d71c")
        with colB: render_macro_metric_card("🟡 偶数和值", macro_df['和偶'].sum(), last_row['和偶漏'], total_periods,
                                            "#e6b800")
        render_macro_alert([('和尾小', '和尾小漏', '【和值尾数0~4】'), ('和尾大', '和尾大漏', '【和值尾数5~9】')], macro_df,
                           "结合报警，精准切割和值的个位数范围，可毙掉 50% 废底！")
        colA, colB = st.columns(2)
        with colA: render_macro_metric_card("🧱 和值小尾 (0-4)", macro_df['和尾小'].sum(), last_row['和尾小漏'],
                                            total_periods, "#ff7f50")
        with colB: render_macro_metric_card("🧱 和值大尾 (5-9)", macro_df['和尾大'].sum(), last_row['和尾大漏'],
                                            total_periods, "#ff4b4b")
    with tab2:
        render_macro_alert([('跨奇', '跨奇漏', '【跨度为奇数】'), ('跨偶', '跨偶漏', '【跨度为偶数】')], macro_df,
                           "若报警【奇数跨度】，龙头凤尾必须【一奇一偶】；若报警【偶数跨度】，必须【同奇或同偶】！")
        colA, colB = st.columns(2)
        with colA: render_macro_metric_card("🟡 奇数跨度", macro_df['跨奇'].sum(), last_row['跨奇漏'], total_periods,
                                            "#f9d71c")
        with colB: render_macro_metric_card("🟡 偶数跨度", macro_df['跨偶'].sum(), last_row['跨偶漏'], total_periods,
                                            "#e6b800")
        render_macro_alert([('跨质', '跨质漏', '【跨度为质数】'), ('跨合', '跨合漏', '【跨度为合数】')], macro_df,
                           "若报警质数跨度，注意首尾张力将发生冷门偏态拉扯，防守跨度 23, 29, 31！")
        colA, colB = st.columns(2)
        with colA: render_macro_metric_card("🟣 质数跨度", macro_df['跨质'].sum(), last_row['跨质漏'], total_periods,
                                            "#8a2be2")
        with colB: render_macro_metric_card("🟣 合数跨度", macro_df['跨合'].sum(), last_row['跨合漏'], total_periods,
                                            "#6a1b9a")
    with tab3:
        render_macro_alert([('联_奇奇', '联_奇奇漏', '【和奇+跨奇】'), ('联_奇偶', '联_奇偶漏', '【和奇+跨偶】'),
                            ('联_偶奇', '联_偶奇漏', '【和偶+跨奇】'), ('联_偶偶', '联_偶偶漏', '【和偶+跨偶】')], macro_df,
                           "核弹级信号！若此处报警，代表大盘奇偶与首尾奇偶被【同时锁死】！")
        col1, col2 = st.columns(2)
        with col1:
            render_macro_metric_card("🎯 象限 1：和奇 - 跨奇", macro_df['联_奇奇'].sum(), last_row['联_奇奇漏'],
                                     total_periods, "#e91e63", "奇数球占单数，首尾一奇一偶")
            render_macro_metric_card("🎯 象限 3：和偶 - 跨奇", macro_df['联_偶奇'].sum(), last_row['联_偶奇漏'],
                                     total_periods, "#00bcd4", "奇数球占双数，首尾一奇一偶")
        with col2:
            render_macro_metric_card("🎯 象限 2：和奇 - 跨偶", macro_df['联_奇偶'].sum(), last_row['联_奇偶漏'],
                                     total_periods, "#9c27b0", "奇数球占单数，首尾同奇或同偶")
            render_macro_metric_card("🎯 象限 4：和偶 - 跨偶", macro_df['联_偶偶'].sum(), last_row['联_偶偶漏'],
                                     total_periods, "#009688", "奇数球占双数，首尾同奇或同偶")
    with tab4:
        render_macro_alert([('极速震荡', '极震漏', '【大盘振幅≥35】'), ('横盘锁死', '横盘漏', '【大盘振幅≤8】')], macro_df,
                           f"若报警极速震荡，和值必将暴跌或暴涨；若报警横盘锁死，请复制上一期选号重心！")
        col1, col2 = st.columns(2)
        with col1: render_macro_metric_card("🌊 极速震荡 (振幅 ≥ 35)", macro_df['极速震荡'].sum(), last_row['极震漏'],
                                            total_periods, "#ff4b4b", "大盘出现暴涨暴跌深V形态")
        with col2: render_macro_metric_card("🧊 横盘锁死 (振幅 ≤ 8)", macro_df['横盘锁死'].sum(), last_row['横盘漏'],
                                            total_periods, "#4da6ff", "和值停滞，重心与上一期重合")
        st.bar_chart(macro_df.tail(50).set_index('期号')[['绝对振幅']], color="#8a2be2")

    st.markdown("---")
    st.markdown("### 📊 大盘宏观指标 全量正态分布 (钟形曲线)")
    col_dist1, col_dist2 = st.columns(2)
    with col_dist1:
        st.markdown("#### 🌡️ 历史全量和值 (Sum) 分布")
        sum_counts = macro_df['和值'].value_counts().reset_index()
        sum_counts.columns = ['和值', '历史发生次数']
        st.bar_chart(sum_counts.sort_values(by='和值').set_index('和值'), color="#ff4b4b")
    with col_dist2:
        st.markdown("#### 🏹 历史全量跨度 (Span) 分布")
        span_counts = macro_df['跨度'].value_counts().reset_index()
        span_counts.columns = ['跨度', '历史发生次数']
        st.bar_chart(span_counts.sort_values(by='跨度').set_index('跨度'), color="#4da6ff")

    st.markdown("---")
    st.markdown("### 📋 宏观数据底层明细 (支持检视追踪详情)")
    display_df = macro_df[
        ['期号', '开奖红球', '和值', '跨度', '绝对振幅', '重心均值', '和奇漏', '和偶漏', '跨奇漏', '跨偶漏', '极震漏',
         '横盘漏', '联_奇奇漏', '联_奇偶漏', '联_偶奇漏', '联_偶偶漏']].iloc[::-1]
    st_centered_df(display_df, use_container_width=True, hide_index=True, height=500)


# 🚀 模块 13：大小奇偶比
@st.cache_data(show_spinner=False)
def calculate_ratio_features(df, is_ssq):
    red_n = 6 if is_ssq else 5
    r_cols = [f'r{i + 1}' for i in range(red_n)]

    if is_ssq:
        big_thresh, dom_thresh, ext_thresh = 17, 4, 5
    else:
        big_thresh, dom_thresh, ext_thresh = 18, 3, 4

    detailed_data = []
    omits = {'odd_dom': 0, 'even_dom': 0, 'odd_ext': 0, 'even_ext': 0, 'big_dom': 0, 'small_dom': 0, 'big_ext': 0,
             'small_ext': 0, 'link_odd_big': 0, 'link_odd_small': 0, 'link_even_big': 0, 'link_even_small': 0}

    for _, row in df.iterrows():
        reds = row[r_cols].values
        n_odd = sum(1 for x in reds if x % 2 != 0)
        n_even = red_n - n_odd
        n_big = sum(1 for x in reds if x >= big_thresh)
        n_small = red_n - n_big

        ratio_odd_even = f"{n_odd}:{n_even}"
        ratio_big_small = f"{n_big}:{n_small}"

        is_odd_dom, is_even_dom = (n_odd >= dom_thresh), (n_even >= dom_thresh)
        is_odd_ext, is_even_ext = (n_odd >= ext_thresh), (n_even >= ext_thresh)
        is_big_dom, is_small_dom = (n_big >= dom_thresh), (n_small >= dom_thresh)
        is_big_ext, is_small_ext = (n_big >= ext_thresh), (n_small >= ext_thresh)

        link_ob = is_odd_dom and is_big_dom
        link_os = is_odd_dom and is_small_dom
        link_eb = is_even_dom and is_big_dom
        link_es = is_even_dom and is_small_dom

        omits['odd_dom'] = 0 if is_odd_dom else omits['odd_dom'] + 1
        omits['even_dom'] = 0 if is_even_dom else omits['even_dom'] + 1
        omits['odd_ext'] = 0 if is_odd_ext else omits['odd_ext'] + 1
        omits['even_ext'] = 0 if is_even_ext else omits['even_ext'] + 1
        omits['big_dom'] = 0 if is_big_dom else omits['big_dom'] + 1
        omits['small_dom'] = 0 if is_small_dom else omits['small_dom'] + 1
        omits['big_ext'] = 0 if is_big_ext else omits['big_ext'] + 1
        omits['small_ext'] = 0 if is_small_ext else omits['small_ext'] + 1
        omits['link_odd_big'] = 0 if link_ob else omits['link_odd_big'] + 1
        omits['link_odd_small'] = 0 if link_os else omits['link_odd_small'] + 1
        omits['link_even_big'] = 0 if link_eb else omits['link_even_big'] + 1
        omits['link_even_small'] = 0 if link_es else omits['link_even_small'] + 1

        detailed_data.append({
            '期号': row['期号'], '开奖红球': " ".join([f"{int(x):02d}" for x in reds]),
            '奇偶比': ratio_odd_even, '大小比': ratio_big_small,
            '奇数主导': int(is_odd_dom), '奇主漏': omits['odd_dom'], '偶数主导': int(is_even_dom),
            '偶主漏': omits['even_dom'],
            '极限全奇': int(is_odd_ext), '极奇漏': omits['odd_ext'], '极限全偶': int(is_even_ext),
            '极偶漏': omits['even_ext'],
            '大号主导': int(is_big_dom), '大主漏': omits['big_dom'], '小号主导': int(is_small_dom),
            '小主漏': omits['small_dom'],
            '极限全大': int(is_big_ext), '极大漏': omits['big_ext'], '极限全小': int(is_small_ext),
            '极小漏': omits['small_ext'],
            '联_奇大': int(link_ob), '联_奇大漏': omits['link_odd_big'], '联_奇小': int(link_os),
            '联_奇小漏': omits['link_odd_small'],
            '联_偶大': int(link_eb), '联_偶大漏': omits['link_even_big'], '联_偶小': int(link_es),
            '联_偶小漏': omits['link_even_small']
        })
    return pd.DataFrame(detailed_data)


def render_mod_size_parity(df, is_ssq):
    st.markdown("### ⚖️ 大盘双轨比值 动态联动控制台")
    total_periods = len(df)

    if is_ssq:
        def_text = "<b>双色球 (33个红球)：</b>【小号区】定义为 <b>01 ~ 16</b>；【大号区】定义为 <b>17 ~ 33</b>。由于总数为奇数，大号天生多出1个球。"
        dom_text = "≥4个同属性球为【主导】，≥5个为【极限】"
    else:
        def_text = "<b>大乐透 (35个前区)：</b>【小号区】定义为 <b>01 ~ 17</b>；【大号区】定义为 <b>18 ~ 35</b>。大号天生多出1个球。"
        dom_text = "≥3个同属性球为【主导】，≥4个为【极限】"

    st.markdown(
        f"<div class='def-card'><h4 style='color: #00bcd4; margin-top:0; margin-bottom: 8px;'>📌 架构师物理切分基准（大盘公理）</h4><p style='color:#fff; font-size:1.05em; margin-bottom:4px;'>当前系统对【大小比】的底层切分逻辑执行如下：</p><ul style='color:#bbb; margin-bottom:0;'><li>{def_text}</li><li>系统判定标准：{dom_text}。</li></ul></div>",
        unsafe_allow_html=True)

    with st.spinner("正在计算大盘奇偶与大小比值，构筑联动矩阵..."):
        ratio_df = calculate_ratio_features(df, is_ssq)
    last_row = ratio_df.iloc[-1]

    def render_ratio_alert(pillars, seq_df, recommendation_template):
        alerts = []
        for cnt_col, omit_col, name in pillars:
            hit_series = (seq_df[cnt_col] > 0).astype(int)
            current_gap = seq_df.iloc[-1][omit_col]
            dynamic_thresh = calculate_dynamic_threshold(hit_series, window=100)
            if current_gap >= dynamic_thresh:
                alerts.append({'name': name, 'gap': current_gap, 'threshold': dynamic_thresh})
        if len(alerts) > 0:
            alert_msgs = "".join([
                                     f"<li style='margin-bottom: 5px;'>🎯 大盘偏态 <b>{a['name']}</b> 动态极限允许遗漏为 {a['threshold']} 期，现已爆表遗漏 <b style='color:#ff4b4b; font-size:1.1em;'>{a['gap']}</b> 期！</li>"
                                     for a in alerts])
            st.markdown(
                f"<div class='alert-card'><h4 style='color: #ff4b4b; margin-top:0; margin-bottom: 10px;'>🚨 AI 动态波动偏态预警</h4><ul style='margin-bottom: 10px;'>{alert_msgs}</ul><span style='font-size:0.95em; color:#f9d71c;'><b>💡 智能战术指导：</b>{recommendation_template}</span></div>",
                unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='safe-card'><h4 style='color: #00FF7F; margin-top:0; margin-bottom: 5px;'>✅ 本页比值指标未击穿布林带上限</h4><span style='font-size:0.95em; color:#bbb;'>大盘奇偶与大小分布处于近期的常态波动范围内，保持均衡选号即可。</span></div>",
                unsafe_allow_html=True)

    def render_ratio_metric_card(title, hit_cnt, hit_omit, color, desc=""):
        rate = hit_cnt / total_periods if total_periods else 0
        st.markdown(
            f"<div class='stat-card' style='border-left: 4px solid {color};'><h4 style='color: {color}; margin-bottom: 10px;'>{title}</h4><span style='font-size:0.85em; color:#bbb; display:block; margin-bottom:15px;'>{desc}</span><div style='background:rgba(0,0,0,0.15); padding:10px; border-radius:6px; margin-bottom:8px; text-align:left;'><span style='color:#fff; font-weight:bold;'>🔹 全盘发生:</span> 共 <b style='color:#fff'>{hit_cnt}</b> 期 <span style='color:#bbb; font-size:0.9em;'>(占比 {rate:.2%})</span><br /><span style='font-size:0.9em; color:#bbb; display:block; margin-top:4px;'>⏳ 当前遗漏: <b style='color:#ff4b4b'>{hit_omit}</b> 期</span></div></div>",
            unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🧬 基因轨：奇偶比分析", "🌌 空间轨：大小比分析", "⚔️ 双轨联动：比值四象限矩阵"])

    with tab1:
        render_ratio_alert([('奇数主导', '奇主漏', '【奇数球占绝对优势】'), ('偶数主导', '偶主漏', '【偶数球占绝对优势】')],
                           ratio_df,
                           "大盘基因报警！若报警【奇数主导】，请在本期大底中强行剔除 2:4、1:5、0:6 等偶数偏多的废底；反之亦然。顺势而为！")
        colA, colB = st.columns(2)
        with colA:
            render_ratio_metric_card("🟡 奇数主导 (优势区)", ratio_df['奇数主导'].sum(), last_row['奇主漏'], "#f9d71c",
                                     "当期开出奇数球数量过半")
            render_ratio_metric_card("🔥 极限全奇 (罕见区)", ratio_df['极限全奇'].sum(), last_row['极奇漏'], "#ff4b4b",
                                     "当期几乎或全部为奇数")
        with colB:
            render_ratio_metric_card("🟡 偶数主导 (优势区)", ratio_df['偶数主导'].sum(), last_row['偶主漏'], "#e6b800",
                                     "当期开出偶数球数量过半")
            render_ratio_metric_card("🔥 极限全偶 (罕见区)", ratio_df['极限全偶'].sum(), last_row['极偶漏'], "#ff4b4b",
                                     "当期几乎或全部为偶数")

    with tab2:
        render_ratio_alert([('大号主导', '大主漏', '【大号球占绝对优势】'), ('小号主导', '小主漏', '【小号球占绝对优势】')],
                           ratio_df,
                           "物理空间报警！若报警【小号主导】，下期重心必将极度左倾，请在龙头附近大量堆积号码；若报警【大号主导】，请将主力资金倾斜至凤尾区域！")
        colA, colB = st.columns(2)
        with colA:
            render_ratio_metric_card("🔵 大号主导 (右偏区)", ratio_df['大号主导'].sum(), last_row['大主漏'], "#4da6ff",
                                     "当期开出大号球数量过半")
            render_ratio_metric_card("🔥 极限全大 (罕见区)", ratio_df['极限全大'].sum(), last_row['极大漏'], "#ff4b4b",
                                     "当期几乎或全部为大号")
        with colB:
            render_ratio_metric_card("🟢 小号主导 (左偏区)", ratio_df['小号主导'].sum(), last_row['小主漏'], "#00FF7F",
                                     "当期开出小号球数量过半")
            render_ratio_metric_card("🔥 极限全小 (罕见区)", ratio_df['极限全小'].sum(), last_row['极小漏'], "#ff4b4b",
                                     "当期几乎或全部为小号")

    with tab3:
        render_ratio_alert([('联_奇大', '联_奇大漏', '【奇数主导 + 大号主导】双爆点'),
                            ('联_奇小', '联_奇小漏', '【奇数主导 + 小号主导】双爆点'),
                            ('联_偶大', '联_偶大漏', '【偶数主导 + 大号主导】双爆点'),
                            ('联_偶小', '联_偶小漏', '【偶数主导 + 小号主导】双爆点')], ratio_df,
                           "核弹级定胆信号！若某象限报警，说明大盘的基因与空间被同时锁死！例如报警【奇数+大号】，本期极易爆出 23, 25, 27, 29, 31, 33 这样的密集大号奇数组合，直接在核心区包号！")
        col1, col2 = st.columns(2)
        with col1:
            render_ratio_metric_card("🎯 象限 1：奇数主导 + 大号主导", ratio_df['联_奇大'].sum(), last_row['联_奇大漏'],
                                     "#e91e63", "锁定范围：右侧腹地的奇数球")
            render_ratio_metric_card("🎯 象限 3：偶数主导 + 大号主导", ratio_df['联_偶大'].sum(), last_row['联_偶大漏'],
                                     "#00bcd4", "锁定范围：右侧腹地的偶数球")
        with col2:
            render_ratio_metric_card("🎯 象限 2：奇数主导 + 小号主导", ratio_df['联_奇小'].sum(), last_row['联_奇小漏'],
                                     "#9c27b0", "锁定范围：左侧腹地的奇数球")
            render_ratio_metric_card("🎯 象限 4：偶数主导 + 小号主导", ratio_df['联_偶小'].sum(), last_row['联_偶小漏'],
                                     "#009688", "锁定范围：左侧腹地的偶数球")

    st.markdown("---")
    st.markdown("### 📈 最近 50 期【奇偶比】与【大小比】分布全景图")
    col_c1, col_c2 = st.columns(2)
    recent_50 = ratio_df.tail(50).set_index('期号')
    with col_c1:
        st.markdown("#### 🧬 奇偶比例走势 (数量分布)")
        st.write("💡 *偏离中心线(黄色/橙色)越远，代表奇偶越失衡。*")
        st.bar_chart(recent_50['奇偶比'].value_counts())
    with col_c2:
        st.markdown("#### 🌌 大小比例走势 (数量分布)")
        st.write("💡 *偏离中心线(蓝色/绿色)越远，代表大小重心越偏移。*")
        st.bar_chart(recent_50['大小比'].value_counts())

    st.markdown("---")
    st.markdown("### 📋 宏观数据底层明细 (支持检视追踪详情)")
    display_df = ratio_df[
        ['期号', '开奖红球', '奇偶比', '大小比', '奇主漏', '偶主漏', '极奇漏', '极偶漏', '大主漏', '小主漏', '极大漏',
         '极小漏', '联_奇大漏', '联_奇小漏', '联_偶大漏', '联_偶小漏']].iloc[::-1]
    st_centered_df(display_df, use_container_width=True, hide_index=True, height=500)

# ==========================================
# 🌊 模块 14：蓝区(后区) 动态极态狙击雷达
# ==========================================
@st.cache_data(show_spinner=False)
def calculate_blue_features(df, is_ssq):
    detailed_data = []
    primes = {2, 3, 5, 7, 11, 13}

    if is_ssq:
        omits = {'odd': 0, 'even': 0, 'big': 0, 'small': 0, 'prime': 0, 'comp': 0, 'amp_extreme': 0, 'amp_micro': 0}
        prev_b = None
        for _, row in df.iterrows():
            b = int(row['b1'])
            is_odd, is_even = (b % 2 != 0), (b % 2 == 0)
            is_big, is_small = (b >= 9), (b <= 8)
            is_prime, is_comp = (b in primes), (b > 1 and b not in primes)
            amp = abs(b - prev_b) if prev_b is not None else 0
            prev_b = b
            is_amp_ext, is_amp_micro = (amp >= 8), (amp <= 2)

            omits['odd'] = 0 if is_odd else omits['odd'] + 1
            omits['even'] = 0 if is_even else omits['even'] + 1
            omits['big'] = 0 if is_big else omits['big'] + 1
            omits['small'] = 0 if is_small else omits['small'] + 1
            omits['prime'] = 0 if is_prime else omits['prime'] + 1
            omits['comp'] = 0 if is_comp else omits['comp'] + 1
            omits['amp_extreme'] = 0 if is_amp_ext else omits['amp_extreme'] + 1
            omits['amp_micro'] = 0 if is_amp_micro else omits['amp_micro'] + 1

            detailed_data.append({
                '期号': row['期号'], '开奖蓝球': f"{b:02d}", '蓝球振幅': amp,
                '奇数': int(is_odd), '奇数漏': omits['odd'], '偶数': int(is_even), '偶数漏': omits['even'],
                '大号': int(is_big), '大号漏': omits['big'], '小号': int(is_small), '小号漏': omits['small'],
                '质数': int(is_prime), '质数漏': omits['prime'], '合数': int(is_comp), '合数漏': omits['comp'],
                '大振幅': int(is_amp_ext), '大振幅漏': omits['amp_extreme'], '小振幅': int(is_amp_micro), '小振幅漏': omits['amp_micro']
            })
    else:
        omits = {'both_odd': 0, 'both_even': 0, 'odd_even': 0, 'both_big': 0, 'both_small': 0, 'big_small': 0, 'sum_odd': 0, 'sum_even': 0, 'span_extreme': 0, 'span_micro': 0}
        for _, row in df.iterrows():
            b1, b2 = int(row['b1']), int(row['b2'])
            odd_cnt = sum(1 for x in [b1, b2] if x % 2 != 0)
            is_both_odd, is_both_even, is_odd_even = (odd_cnt == 2), (odd_cnt == 0), (odd_cnt == 1)
            big_cnt = sum(1 for x in [b1, b2] if x >= 7)
            is_both_big, is_both_small, is_big_small = (big_cnt == 2), (big_cnt == 0), (big_cnt == 1)
            sum_val, span_val = b1 + b2, b2 - b1
            is_sum_odd, is_sum_even = (sum_val % 2 != 0), (sum_val % 2 == 0)
            is_span_ext, is_span_micro = (span_val >= 7), (span_val <= 2)

            omits['both_odd'] = 0 if is_both_odd else omits['both_odd'] + 1
            omits['both_even'] = 0 if is_both_even else omits['both_even'] + 1
            omits['odd_even'] = 0 if is_odd_even else omits['odd_even'] + 1
            omits['both_big'] = 0 if is_both_big else omits['both_big'] + 1
            omits['both_small'] = 0 if is_both_small else omits['both_small'] + 1
            omits['big_small'] = 0 if is_big_small else omits['big_small'] + 1
            omits['sum_odd'] = 0 if is_sum_odd else omits['sum_odd'] + 1
            omits['sum_even'] = 0 if is_sum_even else omits['sum_even'] + 1
            omits['span_extreme'] = 0 if is_span_ext else omits['span_extreme'] + 1
            omits['span_micro'] = 0 if is_span_micro else omits['span_micro'] + 1

            detailed_data.append({
                '期号': row['期号'], '开奖蓝球': f"{b1:02d} {b2:02d}", '后区和值': sum_val, '后区跨度': span_val,
                '双奇': int(is_both_odd), '双奇漏': omits['both_odd'], '双偶': int(is_both_even), '双偶漏': omits['both_even'], '一奇一偶': int(is_odd_even), '一奇一偶漏': omits['odd_even'],
                '双大': int(is_both_big), '双大漏': omits['both_big'], '双小': int(is_both_small), '双小漏': omits['both_small'], '一大一小': int(is_big_small), '一大一小漏': omits['big_small'],
                '和奇': int(is_sum_odd), '和奇漏': omits['sum_odd'], '和偶': int(is_sum_even), '和偶漏': omits['sum_even'],
                '大跨度': int(is_span_ext), '大跨度漏': omits['span_extreme'], '小跨度': int(is_span_micro), '小跨度漏': omits['span_micro']
            })
    return pd.DataFrame(detailed_data)

@st.cache_data(show_spinner=False)
def calculate_blue_hc_positioning(df, is_ssq):
    if df.empty: return None
    total_draws = len(df)
    if is_ssq:
        b_series = df['b1'].astype(int)
        counts = b_series.value_counts().reindex(range(1, 17), fill_value=0).sort_values(ascending=False)
        return {'type': 'ssq', 'total': total_draws, 'hot': counts.iloc[:5], 'warm': counts.iloc[5:11], 'cold': counts.iloc[11:]}
    else:
        b1_s, b2_s = df['b1'].astype(int), df['b2'].astype(int)
        pos1_counts = b1_s.value_counts().reindex(range(1, 13), fill_value=0).sort_values(ascending=False)
        pos2_counts = b2_s.value_counts().reindex(range(1, 13), fill_value=0).sort_values(ascending=False)
        all_b = pd.concat([b1_s, b2_s])
        total_b_counts = all_b.value_counts().reindex(range(1, 13), fill_value=0).sort_values(ascending=False)
        return {'type': 'dlt', 'total': total_draws * 2, 'pos1': pos1_counts, 'pos2': pos2_counts, 'hot': total_b_counts.iloc[:4], 'warm': total_b_counts.iloc[4:8], 'cold': total_b_counts.iloc[8:]}

def render_mod_blue(df_raw, is_ssq):
    st.markdown("### 🔵 蓝球(后区) 动态极态狙击雷达")
    st.write("💡 *技术声明：独立隔离后区物理空间。包含【动态冷热聚类】、【后区全维空间定胆】与【2.0 动态布林带预警】！*")

    total_periods = len(df_raw)

    if is_ssq: def_text = "<b>双色球后区 (1~16)：</b>完美对称分布，【小号区】定义为 <b>01 ~ 08</b>；【大号区】定义为 <b>09 ~ 16</b>。"
    else: def_text = "<b>大乐透后区 (1~12)：</b>完美对称分布，【小号区】定义为 <b>01 ~ 06</b>；【大号区】定义为 <b>07 ~ 12</b>。"
    st.markdown(f"<div class='def-card'><h4 style='color: #00bcd4; margin-top:0; margin-bottom: 8px;'>📌 架构师物理切分基准（后流域公理）</h4><p style='color:#fff; font-size:1.05em; margin-bottom:4px;'>当前系统对蓝球/后区【大小形态】的底层切分逻辑执行如下：</p><ul style='color:#bbb; margin-bottom:0;'><li>{def_text}</li></ul></div>", unsafe_allow_html=True)

    with st.spinner("正在启动后区专域计算引擎，聚类冷热温号码与独立定位..."):
        blue_df = calculate_blue_features(df_raw, is_ssq)
        hc_stats = calculate_blue_hc_positioning(df_raw, is_ssq)
    last_row = blue_df.iloc[-1]

    def render_blue_alert_dynamic(pillars, seq_df, recommendation_template):
        alerts = []
        for cnt_col, omit_col, name in pillars:
            hit_series = (seq_df[cnt_col] > 0).astype(int)
            current_gap = seq_df.iloc[-1][omit_col]
            dynamic_thresh = calculate_dynamic_threshold(hit_series, window=100)
            if current_gap >= dynamic_thresh: alerts.append({'name': name, 'gap': current_gap, 'threshold': dynamic_thresh})
        if len(alerts) > 0:
            alert_msgs = "".join([f"<li style='margin-bottom: 5px;'>🎯 <b>{a['name']}</b> 动态极限允许遗漏为 {a['threshold']} 期，现已爆表遗漏 <b style='color:#ff4b4b; font-size:1.1em;'>{a['gap']}</b> 期！</li>" for a in alerts])
            st.markdown(f"<div class='alert-card' style='border-left-color:#00bcd4;'><h4 style='color: #00bcd4; margin-top:0; margin-bottom: 10px;'>🚨 AI 蓝球专属动态预警</h4><ul style='margin-bottom: 10px;'>{alert_msgs}</ul><span style='font-size:0.95em; color:#f9d71c;'><b>💡 一击必杀定胆：</b>{recommendation_template}</span></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='safe-card'><h4 style='color: #00FF7F; margin-top:0; margin-bottom: 5px;'>✅ 本页形态指标未击穿布林带上限</h4><span style='font-size:0.95em; color:#bbb;'>蓝球盘面平稳，无强制反弹信号，顺应近期热号防守即可。</span></div>", unsafe_allow_html=True)

    def render_blue_metric_card(title, hit_cnt, hit_omit, total_p, color, desc=""):
        rate = hit_cnt / total_p if total_p else 0
        st.markdown(f"<div class='stat-card' style='border-left: 4px solid {color};'><h4 style='color: {color}; margin-bottom: 10px;'>{title}</h4><span style='font-size:0.85em; color:#bbb; display:block; margin-bottom:15px;'>{desc}</span><div style='background:rgba(0,0,0,0.15); padding:10px; border-radius:6px; margin-bottom:8px; text-align:left;'><span style='color:#fff; font-weight:bold;'>🔹 全盘覆盖:</span> 共 <b style='color:#fff'>{hit_cnt}</b> 期 <span style='color:#bbb; font-size:0.9em;'>(占比 {rate:.2%})</span><br /><span style='font-size:0.9em; color:#bbb; display:block; margin-top:4px;'>⏳ 当前遗漏: <b style='color:#ff4b4b'>{hit_omit}</b> 期</span></div></div>", unsafe_allow_html=True)

    # 👑 架构师绝杀修复：直接在代码内强制写入暗黑科技风 CSS 背景框！
    def render_freq_card(title, series_data, total_hits, color):
        hits = series_data.sum()
        rate = hits / total_hits if total_hits else 0
        nums_html = "".join([
            f"<span style='display:inline-block; padding: 6px 15px; border-radius: 4px; background-color: #282c34; margin: 5px; font-family: monospace; font-size: 1.25em; font-weight: 900; color:{color}; border-bottom: 3px solid {color}; box-shadow: 0 2px 4px rgba(0,0,0,0.3);'>"
            f"{int(num):02d}</span>"
            for num in series_data.index
        ])
        st.markdown(f"<div class='stat-card' style='border-top: 4px solid {color}; text-align:center;'><h4 style='color: {color}; margin-bottom: 5px;'>{title}</h4><p style='color:#bbb; font-size:0.9em; margin-bottom:15px;'>总计命中 <b>{hits}</b> 次 (占该域出号率 <b>{rate:.2%}</b>)</p><div>{nums_html}</div></div>", unsafe_allow_html=True)

    if is_ssq:
        st.markdown("### 🎯 双色球蓝球：单点降维狙击")
        tab1, tab2, tab3, tab4 = st.tabs(["📍 冷热温聚类", "🧬 奇偶与大小", "🟣 质合与振幅", "📈 蓝球近期波形图"])
        with tab1:
            st.markdown("#### 🔥 全盘历史 1~16 蓝球冷热温分类")
            st.write("💡 *实战法则：大底定胆首选【极热号】保本；想要博取超级大盲盒冷门，在【极冷号】中挑选 1 颗作为刺客防守！*")
            c1, c2, c3 = st.columns(3)
            with c1: render_freq_card("🔥 极热主力号 (Top 5)", hc_stats['hot'], hc_stats['total'], "#ff4b4b")
            with c2: render_freq_card("🟡 常规温号 (Mid 6)", hc_stats['warm'], hc_stats['total'], "#f9d71c")
            with c3: render_freq_card("🧊 冰封极冷号 (Bottom 5)", hc_stats['cold'], hc_stats['total'], "#4da6ff")
        with tab2:
            render_blue_alert_dynamic([('奇数', '奇数漏', '【蓝球为奇数】'), ('偶数', '偶数漏', '【蓝球为偶数】'), ('大号', '大号漏', '【蓝球为大号】'), ('小号', '小号漏', '【蓝球为小号】')], blue_df, "蓝球极态报警！若报警大号，定胆范围直接缩减一半！若报警奇数，锁定 1,3,5... 结合【📍冷热温标签页】，在报警范围内优选热号！")
            col1, col2 = st.columns(2)
            with col1:
                render_blue_metric_card("🟡 蓝球为奇数", blue_df['奇数'].sum(), last_row['奇数漏'], total_periods, "#f9d71c")
                render_blue_metric_card("🟡 蓝球为偶数", blue_df['偶数'].sum(), last_row['偶数漏'], total_periods, "#e6b800")
            with col2:
                render_blue_metric_card("🔵 蓝球为大号 (09-16)", blue_df['大号'].sum(), last_row['大号漏'], total_periods, "#4da6ff")
                render_blue_metric_card("🟢 蓝球为小号 (01-08)", blue_df['小号'].sum(), last_row['小号漏'], total_periods, "#00FF7F")
        with tab3:
            last_b = last_row['开奖蓝球']
            render_blue_alert_dynamic([('质数', '质数漏', '【蓝球为质数】'), ('大振幅', '大振幅漏', '【蓝球极速跨区(振幅≥8)】'), ('小振幅', '小振幅漏', '【蓝球原地黏连(振幅≤2)】')], blue_df, f"结合上期蓝球({last_b})，若报警大振幅，本期必将飞越半个盘面；若报警小振幅，将在 {last_b} 附近打转！")
            col1, col2 = st.columns(2)
            with col1: render_blue_metric_card("🟣 蓝球为质数", blue_df['质数'].sum(), last_row['质数漏'], total_periods, "#8a2be2", "2,3,5,7,11,13")
            with col2: render_blue_metric_card("🌊 蓝球大振幅 (≥8)", blue_df['大振幅'].sum(), last_row['大振幅漏'], total_periods, "#ff4b4b", "走势呈大步长跳跃")
        with tab4:
            st.markdown("#### 📈 最近 50 期蓝球落点分布波形")
            recent_50 = blue_df.tail(50).set_index('期号').copy()
            recent_50['开奖蓝球_num'] = recent_50['开奖蓝球'].astype(int)
            st.line_chart(recent_50[['开奖蓝球_num']], color=["#00bcd4"])
    else:
        st.markdown("### 🎯 大乐透后区：双星联动与双轨定位")
        tab1, tab2, tab3, tab4 = st.tabs(["📍 独立定位与冷热分布", "🧬 结构比 (奇偶/大小)", "⚖️ 后区和值与跨度", "📈 后区近期波形图"])
        with tab1:
            st.markdown("#### 🎯 后区 第一位(小) 与 第二位(大) 历史最热落点剖析")
            st.write("💡 *实战法则：大乐透后区呈绝对的左小右大分布！第一位杀大号，第二位杀小号。以下是两星独立位置的 Top 热号！*")
            p1, p2 = st.columns(2)
            with p1: render_freq_card("🥇 第一位(小号位) 最热 Top 5", hc_stats['pos1'].iloc[:5], total_periods, "#00bcd4")
            with p2: render_freq_card("🥈 第二位(大号位) 最热 Top 5", hc_stats['pos2'].iloc[:5], total_periods, "#9c27b0")
            st.markdown("---")
            st.markdown("#### 🔥 后区全量号码 1~12 综合冷热温聚类")
            c1, c2, c3 = st.columns(3)
            with c1: render_freq_card("🔥 极热主力号 (Top 4)", hc_stats['hot'], hc_stats['total'], "#ff4b4b")
            with c2: render_freq_card("🟡 常规温号 (Mid 4)", hc_stats['warm'], hc_stats['total'], "#f9d71c")
            with c3: render_freq_card("🧊 冰封极冷号 (Bottom 4)", hc_stats['cold'], hc_stats['total'], "#4da6ff")
        with tab2:
            render_blue_alert_dynamic([('双奇', '双奇漏', '【后区 全奇数】'), ('双偶', '双偶漏', '【后区 全偶数】'), ('双大', '双大漏', '【后区 全大号】'), ('双小', '双小漏', '【后区 全小号】')], blue_df, "极限结构报警！若报警【双大】，本期后区两枚请全在 07~12 间挑选；若报警【双奇】，请在 01,03,05,07,09,11 中任选！")
            col1, col2 = st.columns(2)
            with col1:
                render_blue_metric_card("🟡 后区双奇", blue_df['双奇'].sum(), last_row['双奇漏'], total_periods, "#f9d71c")
                render_blue_metric_card("🟡 后区双偶", blue_df['双偶'].sum(), last_row['双偶漏'], total_periods, "#e6b800")
            with col2:
                render_blue_metric_card("🔵 后区双大", blue_df['双大'].sum(), last_row['双大漏'], total_periods, "#4da6ff")
                render_blue_metric_card("🟢 后区双小", blue_df['双小'].sum(), last_row['双小漏'], total_periods, "#00FF7F")
        with tab3:
            render_blue_alert_dynamic([('和奇', '和奇漏', '【后区和值为奇数】'), ('大跨度', '大跨度漏', '【后区跨度 ≥ 7】'), ('小跨度', '小跨度漏', '【后区跨度 ≤ 2】')], blue_df, "若报警大跨度，说明首尾极端撕裂，选01配10以上冷门！若报警和奇，两球必须一奇一偶！")
            col1, col2 = st.columns(2)
            with col1: render_blue_metric_card("⚖️ 后区和值为奇数", blue_df['和奇'].sum(), last_row['和奇漏'], total_periods, "#e91e63", "必为【一奇一偶】")
            with col2: render_blue_metric_card("🌊 后区大跨度 (≥7)", blue_df['大跨度'].sum(), last_row['大跨度漏'], total_periods, "#ff4b4b", "张力极大")
        with tab4:
            st.markdown("#### 📈 最近 50 期后区【和值】与【跨度】对比波形")
            st.line_chart(blue_df.tail(50).set_index('期号')[['后区和值', '后区跨度']])

    st.markdown("---")
    st.markdown("### 📋 蓝区数据底层明细 (支持检视追踪详情)")
    if is_ssq: d_cols = ['期号', '开奖蓝球', '蓝球振幅', '奇数漏', '偶数漏', '大号漏', '小号漏', '大振幅漏', '小振幅漏']
    else: d_cols = ['期号', '开奖蓝球', '后区和值', '后区跨度', '双奇漏', '双偶漏', '双大漏', '双小漏', '大跨度漏', '小跨度漏']
    st_centered_df(blue_df[d_cols].iloc[::-1], use_container_width=True, hide_index=True, height=500)


# ==========================================
# 🚀 核心路由与主干呈现逻辑 (防崩溃安全版)
# ==========================================
def main():
    main_options = ['首页', '大乐透', '双色球', '过滤缩水工具']
    # 依靠 st.radio 自身的刷新机制，绝对不要加 st.rerun()
    selected_main = st.radio("主导航", main_options, index=main_options.index(st.session_state.main_nav),
                             horizontal=True, label_visibility="collapsed")

    if selected_main != st.session_state.main_nav:
        st.session_state.main_nav = selected_main
        st.session_state.show_results = False

    st.markdown("<hr style='margin: 0px 0 15px 0; border-color: #333;' />", unsafe_allow_html=True)

    # ----------------- 首页 -----------------
    if st.session_state.main_nav == '首页':
        st.markdown(
            "<h1 style='text-align:center; font-weight:300; letter-spacing: 4px; margin-top:20px;'>智 能 数 据 分 析 工 具</h1>",
            unsafe_allow_html=True)
        c1, c_space, c2 = st.columns([4, 0.5, 4])
        with c1:
            st.markdown("<h3 style='text-align:center; color:#ff4b4b;'>🔴 大乐透</h3>", unsafe_allow_html=True)
            res_dlt = get_latest_result("大乐透")
            if res_dlt:
                r_html = "".join([f"<span class='red-ball'>{r:02d}</span>" for r in res_dlt['reds'][:5]])
                b_html = "".join([f"<span class='blue-ball'>{b:02d}</span>" for b in res_dlt['blues'][:2]])
                st.markdown(
                    f"<div class='home-card'><h5 style='color:#bbb;'>最新开奖：第 {res_dlt['period']} 期</h5><br />{r_html} &nbsp;&nbsp; {b_html}</div>",
                    unsafe_allow_html=True)
            else:
                st.info("请在目录放置 大乐透.xlsx")
        with c2:
            st.markdown("<h3 style='text-align:center; color:#00bcd4;'>🔵 双色球</h3>", unsafe_allow_html=True)
            res_ssq = get_latest_result("双色球")
            if res_ssq:
                r_html = "".join([f"<span class='red-ball'>{r:02d}</span>" for r in res_ssq['reds'][:6]])
                b_html = "".join([f"<span class='blue-ball'>{b:02d}</span>" for b in res_ssq['blues'][:1]])
                st.markdown(
                    f"<div class='home-card'><h5 style='color:#bbb;'>最新开奖：第 {res_ssq['period']} 期</h5><br />{r_html} &nbsp;&nbsp; {b_html}</div>",
                    unsafe_allow_html=True)
            else:
                st.info("请在目录放置 双色球.xlsx")

    # ----------------- 分析大屏 -----------------
    elif st.session_state.main_nav in ['大乐透', '双色球']:
        st.session_state.lottery_type = st.session_state.main_nav
        sub_options = ["红球定位", "奖项区间波动", "AC值", "012路", "重号", "冷热温号", "顺连号", "跳期连号", "斜连号",
                       "尾号", "前区三区", "和值跨度比", "大小奇偶比", "蓝区"]
        if st.session_state.sub_nav not in sub_options: st.session_state.sub_nav = "红球定位"

        selected_sub = st.radio("子导航", sub_options, index=sub_options.index(st.session_state.sub_nav),
                                horizontal=True, label_visibility="collapsed")
        if selected_sub != st.session_state.sub_nav:
            st.session_state.sub_nav = selected_sub

        df = get_full_detailed_data(st.session_state.lottery_type)
        is_ssq = (st.session_state.lottery_type == "双色球")

        st.markdown(
            f"<div style='font-size: 16px; color: #888; margin: 10px 0;'>你当前所在位置：{st.session_state.lottery_type}数据分析工具</div>",
            unsafe_allow_html=True)

        with st.container(border=True):
            if df.empty:
                st.error(f"⚠️ {st.session_state.lottery_type} 数据未加载，请确保 xlsx 文件存在。")
            else:
                if st.session_state.sub_nav == "红球定位":
                    render_mod_red_position(df, is_ssq)
                elif st.session_state.sub_nav == "奖项区间波动":
                    render_mod_prize(df, is_ssq)
                elif st.session_state.sub_nav == "AC值":
                    render_mod_ac(df, is_ssq)
                elif st.session_state.sub_nav == "012路":
                    render_mod_012(df, is_ssq)
                elif st.session_state.sub_nav == "重号":
                    render_mod_repeat(df, is_ssq)
                elif st.session_state.sub_nav == "冷热温号":
                    render_mod_hot_cold(df, is_ssq)
                elif st.session_state.sub_nav == "顺连号":
                    render_seq_shared(df, is_ssq, "顺连号", 1, ["若报警，请务必挑选 1~2 组相邻的号码（如 12,13）进行防守！",
                                                                "关注报警的奇偶属性，多配同属性组合。",
                                                                "大底强行加入跨度为 3 的组合拦截！",
                                                                "极其反常！尝试定胆跨度为 4 的偏门连号。"])
                elif st.session_state.sub_nav == "跳期连号":
                    render_seq_shared(df, is_ssq, "跳期连号", 2,
                                      ["防守【上上期】开奖号码的 ±1 邻码！", "结合上上期奇偶属性进行推演！",
                                       "重点关注【上上期】的 ±3 偏态跳期！", "配置【上上期号码】的 ±4 大跨度跳期！"])
                elif st.session_state.sub_nav == "斜连号":
                    render_seq_shared(df, is_ssq, "斜连号", 3,
                                      ["防守【上一期】开奖号码的 ±1 邻码！", "结合上一期奇偶属性定胆！",
                                       "关注【上一期号码】的 ±3 偏态防守！", "配置【上一期号码】的 ±4 大跨度斜连！"])
                elif st.session_state.sub_nav == "尾号":
                    render_mod_tail(df, is_ssq)
                elif st.session_state.sub_nav == "前区三区":
                    render_mod_zone(df, is_ssq)
                elif st.session_state.sub_nav == "和值跨度比":
                    render_mod_sum_span(df, is_ssq)
                elif st.session_state.sub_nav == "大小奇偶比":
                    render_mod_size_parity(df, is_ssq)
                elif st.session_state.sub_nav == "蓝区":
                    render_mod_blue(df, is_ssq)
                else:
                    st.warning(f"🚧 模块【{st.session_state.sub_nav}】代码暂未上传，等待融合接入。")

    # ----------------- 过滤缩水工具 -----------------
    elif st.session_state.main_nav == '过滤缩水工具':
        filter_opts = ["大乐透过滤工具", "双色球过滤工具"]
        curr_filter = f"{st.session_state.lottery_type}过滤工具"
        sel_f = st.radio("彩种过滤", filter_opts, index=filter_opts.index(curr_filter), horizontal=True,
                         label_visibility="collapsed")
        new_l = sel_f.replace("过滤工具", "")
        if new_l != st.session_state.lottery_type:
            st.session_state.lottery_type = new_l
            st.session_state.filter_conditions = []
            st.session_state.show_results = False

        sub_options = ["红球定位", "奖项区间波动", "AC值", "012路", "重号", "冷热温号", "顺连号", "跳期连号", "斜连号",
                       "尾号", "前区三区", "和值跨度比", "大小奇偶比", "蓝区"]
        if st.session_state.sub_nav not in sub_options: st.session_state.sub_nav = "红球定位"
        sel_sub = st.radio("过滤子导航", sub_options, index=sub_options.index(st.session_state.sub_nav),
                           horizontal=True, label_visibility="collapsed")
        if sel_sub != st.session_state.sub_nav:
            st.session_state.sub_nav = sel_sub

        st.markdown(
            f"<div style='font-size: 16px; color: #888; margin: 10px 0 20px 0;'>你当前所在位置：{st.session_state.lottery_type}过滤缩水工具</div>",
            unsafe_allow_html=True)

        col_left, col_right = st.columns([1, 2.5])
        with col_left:
            with st.container(border=True, height=600):
                st.markdown(f"<h3 style='margin-top:0;'>{st.session_state.sub_nav}</h3>", unsafe_allow_html=True)
                auto_mode = st.checkbox("让智能系统自动选择配置", key=f"auto_{st.session_state.sub_nav}")
                input_val = st.text_input("或手动输入核心规则:", placeholder="输入参数规则",
                                          key=f"input_{st.session_state.sub_nav}")
                if st.button("➕ 添加到保留条件池", use_container_width=True):
                    st.session_state.filter_conditions.append(
                        {"module": st.session_state.sub_nav, "rule": "智能自动设定" if auto_mode else str(input_val)})

        with col_right:
            with st.container(border=True, height=250):
                st.markdown("<div class='panel-title'>保留选择的条件展示窗口</div>", unsafe_allow_html=True)
                for i, cond in enumerate(st.session_state.filter_conditions):
                    c_tag, c_btn = st.columns([8, 1])
                    c_tag.markdown(f"<div class='cart-item'><b>[{cond['module']}]</b> &nbsp; {cond['rule']}</div>",
                                   unsafe_allow_html=True)
                    if c_btn.button("❌", key=f"del_{i}"): st.session_state.filter_conditions.pop(i)

            with st.container(border=True, height=330):
                if st.session_state.show_results:
                    mock_res = pd.DataFrame(
                        {"序号": ["1"], "号码": ["01 02 03 04 05 + 06 07"], "和值": ["15"], "跨度": ["4"],
                         "三区比": ["5:0:0"], "奇偶比": ["3:2"]})
                    st_centered_df(mock_res, use_container_width=True, hide_index=True)
                else:
                    empty_res = pd.DataFrame(columns=["序号", "号码", "和值", "跨度", "三区比", "奇偶比"])
                    st_centered_df(empty_res, use_container_width=True, hide_index=True)
                    st.markdown("<p style='color:#888; text-align:center; margin-top:-150px;'>过滤缩水结果展示区域</p>",
                                unsafe_allow_html=True)

        st.markdown("<br />", unsafe_allow_html=True)
        c_btn1, c_btn2, c_btn3 = st.columns([1.5, 7, 1.5])
        with c_btn1:
            pass
        with c_btn3:
            if st.button("⚡ 执行过滤", type="primary", use_container_width=True):
                st.session_state.show_results = True


if __name__ == "__main__":
    main()
