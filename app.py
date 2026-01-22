import streamlit as st
import pandas as pd
import requests
from io import StringIO
import time

# 設定網頁配置
st.set_page_config(page_title="富邦產險 | 財報分析助理", page_icon="🛡️", layout="wide")

# --- 1. 抓取股票清單 (強化穩定度) ---
@st.cache_data(ttl=3600)
def get_stock_list():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    urls = ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]
    stock_dict = {}
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'big5' # 證交所清單編碼
            df = pd.read_html(StringIO(res.text))[0]
            df.columns = df.iloc[0]
            df = df.iloc[1:]
            for item in df['有價證券代號及名稱'].dropna():
                if '　' in item:
                    code, name = item.split('　')
                    if len(code) == 4: stock_dict[f"{code} {name}"] = code
        except: continue
    return stock_dict

# --- 2. 爬取 MOPS 財報數據 (參考影片之 Headers 偽裝) ---
def fetch_mops_data(stock_id, year, season):
    url = 'https://mops.twse.com.tw/mops/web/ajax_t164sb04'
    payload = {
        'step': '1', 'firstin': '1', 'off': '1', 'queryName': 'co_id',
        'inpuType': 'co_id', 'TYPEK': 'all', 'isnew': 'false',
        'co_id': stock_id, 'year': str(year), 'season': str(season)
    }
    # 影片重點：模擬真實瀏覽器行為
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://mops.twse.com.tw/mops/web/t164sb04'
    }

    try:
        res = requests.post(url, data=payload, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        # 尋找包含「會計項目」的表格
        dfs = pd.read_html(StringIO(res.text))
        for df in dfs:
            if '會計項目' in df.columns.get_level_values(0):
                df.columns = df.columns.get_level_values(0)
                return df[['會計項目', '金額']].dropna()
        return None
    except: return None

# --- 3. UI 介面 ---
st.title("🛡️ 富邦產險 - 企業財報分析助理")
st.info("本工具協助同仁快速調閱官方財報數據。數據來源：公開資訊觀測站 (MOPS)。")

# 側邊欄設定
st.sidebar.title("🔍 查詢設定")
all_stocks = get_stock_list()

# 防呆邏輯
target_id = None
if not all_stocks:
    st.sidebar.warning("⚠️ 無法獲取股票清單，請改用手動輸入")
    target_id = st.sidebar.text_input("輸入股票代碼 (例: 2330)")
else:
    options = ["--- 請選擇公司 ---"] + list(all_stocks.keys())
    selected_stock = st.sidebar.selectbox("公司名稱/代碼", options=options)
    if selected_stock != "--- 請選擇公司 ---":
        target_id = all_stocks[selected_stock]

# 年份與季度
year = st.sidebar.selectbox("年份 (民國)", ["113", "112", "111", "110"], index=1) # 預設 112 年較穩定
season = st.sidebar.selectbox("季度", ["01", "02", "03", "04"], index=2) # 預設 Q3

if st.sidebar.button("🚀 執行爬取") and target_id:
    with st.spinner(f'正在分析 {target_id} 數據...'):
        # 增加一秒延遲模擬真人操作
        time.sleep(1)
        df_result = fetch_mops_data(target_id, year, season)
        
        if df_result is not None:
            st.success(f"✅ 已成功調閱 {target_id} {year}Q{season} 數據")
            
            # 關鍵數據呈現
            st.subheader("📊 關鍵會計項目摘要")
            key_metrics = ["營業收入合計", "營業利益（損失）", "本期淨利（淨損）", "基本每股盈餘"]
            summary = df_result[df_result['會計項目'].str.strip().isin(key_metrics)]
            
            if not summary.empty:
                cols = st.columns(len(summary))
                for i, row in enumerate(summary.itertuples()):
                    cols[i].metric(row.會計項目, f"{row.金額}")
            
            st.divider()
            st.subheader("📄 原始損益表數據")
            st.dataframe(df_result, use_container_width=True, height=500)
            
            # 提供 CSV 下載
            csv = df_result.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此報表 (CSV)", csv, f"{target_id}_report.csv", "text/csv")
        else:
            st.error(f"❌ 查無資料。提醒：{year}年第{season}季數據可能尚未上傳或該公司不適用此表。")
