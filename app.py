import streamlit as st
import pandas as pd
import requests
from io import StringIO
import time

# 設定網頁配置
st.set_page_config(page_title="富邦產險 | 財報分析助理", page_icon="🛡️", layout="wide")

# --- 1. 核心功能：抓取股票清單 (強化防封鎖) ---
@st.cache_data(ttl=3600)
def get_stock_list():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    urls = [
        "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", 
        "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
    ]
    stock_dict = {}
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'big5'
            # 影片重點：使用 pandas 解析 HTML
            df = pd.read_html(StringIO(res.text))[0]
            df.columns = df.iloc[0]
            df = df.iloc[1:]
            for item in df['有價證券代號及名稱'].dropna():
                if '　' in item:
                    code, name = item.split('　')
                    if len(code) == 4:
                        stock_dict[f"{code} {name}"] = code
        except:
            continue
    return stock_dict

# --- 2. 核心功能：爬取官方 MOPS 數據 (高穩定度方案) ---
def fetch_mops_financials(stock_id, year, season):
    # 使用 ajax 接口獲取綜合損益表
    url = 'https://mops.twse.com.tw/mops/web/ajax_t164sb04'
    payload = {
        'step': '1', 'firstin': '1', 'off': '1', 'queryName': 'co_id',
        'inpuType': 'co_id', 'TYPEK': 'all', 'isnew': 'false',
        'co_id': stock_id, 'year': year, 'season': season
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://mops.twse.com.tw/mops/web/t164sb04'
    }

    try:
        res = requests.post(url, data=payload, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        # 尋找目標表格
        dfs = pd.read_html(StringIO(res.text))
        for df in dfs:
            if '會計項目' in df.columns.get_level_values(0):
                df.columns = df.columns.get_level_values(0)
                return df[['會計項目', '金額']].dropna()
        return None
    except:
        return None

# --- 3. UI 介面 ---
st.title("🛡️ 富邦產險 - 企業財報分析助理")
st.markdown("本系統已優化連線穩定度，直接對接公開資訊觀測站官方數據。")

all_stocks = get_stock_list()
target_id = None

with st.sidebar:
    st.header("🔍 查詢設定")
    if not all_stocks:
        st.error("⚠️ 自動清單獲取失敗，請手動輸入")
        target_id = st.text_input("輸入股票代碼 (如: 2330)")
    else:
        options = ["--- 請選擇公司 ---"] + list(all_stocks.keys())
        selected_stock = st.selectbox("公司名稱/代碼", options=options)
        if selected_stock != "--- 請選擇公司 ---":
            target_id = all_stocks[selected_stock]

    year = st.selectbox("年份 (民國)", ["113", "112", "111", "110"])
    season = st.selectbox("季度", ["03", "02", "01", "04"])
    
    search_btn = st.button("🚀 執行爬取", disabled=(target_id is None))

if search_btn:
    with st.spinner(f'正在調閱 {target_id} 的官方財報...'):
        # 增加短暫延遲避免被視為攻擊
        time.sleep(1)
        df_result = fetch_mops_financials(target_id, year, season)
        
        if df_result is not None:
            st.success(f"✅ 成功獲取 {target_id} {year}Q{season} 數據")
            
            # 關鍵指標卡
            st.subheader("📊 關鍵科目分析")
            metrics = ["營業收入合計", "營業利益（損失）", "本期淨利（淨損）", "基本每股盈餘"]
            summary = df_result[df_result['會計項目'].str.strip().isin(metrics)]
            
            if not summary.empty:
                cols = st.columns(len(summary))
                for i, row in enumerate(summary.itertuples()):
                    cols[i].metric(row.會計項目, row.金額)
            
            st.divider()
            st.subheader("📄 損益表完整數據")
            st.dataframe(df_result, use_container_width=True, height=500)
            
            csv = df_result.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此報表 (CSV)", csv, f"{target_id}_financial.csv")
        else:
            st.error("❌ 查無資料。提醒：113年第4季數據通常在隔年3月底後才公佈。")

st.markdown("---")
st.caption("數據來源：公開資訊觀測站 (MOPS)。建議查詢 112年 Q1~Q3 進行測試。")
