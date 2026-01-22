import streamlit as st
import pandas as pd
import requests
from io import StringIO

# 設定網頁資訊
st.set_page_config(page_title="富邦產險 | 財報助理", page_icon="🛡️", layout="wide")

# --- 1. 抓取股票清單 (強化雲端穩定度) ---
@st.cache_data(ttl=3600)
def get_stock_list():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    urls = ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", 
            "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]
    stock_dict = {}
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'big5' # 證交所清單固定使用 big5
            df = pd.read_html(StringIO(res.text))[0]
            df.columns = df.iloc[0]
            df = df.iloc[1:]
            for item in df['有價證券代號及名稱'].dropna():
                if '　' in item:
                    code, name = item.split('　')
                    if len(code) == 4:
                        stock_dict[f"{code} {name}"] = code
        except Exception:
            continue
    return stock_dict

# --- 2. 爬取財報數據 ---
def fetch_mops_data(stock_id, year, season, report_type):
    api_map = {"綜合損益表": "ajax_t164sb04", "資產負債表": "ajax_t164sb03"}
    url = f'https://mops.twse.com.tw/mops/web/{api_map[report_type]}'
    payload = {
        'step': '1', 'firstin': '1', 'off': '1', 'queryName': 'co_id',
        'inpuType': 'co_id', 'TYPEK': 'all', 'isnew': 'false',
        'co_id': stock_id, 'year': str(year), 'season': str(season)
    }
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    try:
        res = requests.post(url, data=payload, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        dfs = pd.read_html(StringIO(res.text))
        for df in dfs:
            if '會計項目' in df.columns.get_level_values(0):
                df.columns = df.columns.get_level_values(0)
                return df[['會計項目', '金額']].dropna()
        return None
    except:
        return None

# --- 3. UI 介面 ---
st.title("🛡️ 富邦產險 - 企業財報分析助手")
st.info("輔助同仁核保風險評估，數據來源：公開資訊觀測站。")

st.sidebar.title("🔍 查詢設定")
all_stocks = get_stock_list()

# 解決 KeyError: None 與 No results 的防護逻辑
target_id = None
if not all_stocks:
    st.sidebar.error("⚠️ 無法獲取股票清單，請手動輸入代碼")
    target_id = st.sidebar.text_input("輸入股票代碼 (例: 2330)")
else:
    # 增加一個空選項作為預設，避免啟動時報錯
    options = ["--- 請選擇或輸入公司 ---"] + list(all_stocks.keys())
    selected_stock = st.sidebar.selectbox("公司名稱/代碼", options=options, index=0)
    
    if selected_stock != "--- 請選擇或輸入公司 ---":
        target_id = all_stocks.get(selected_stock)

report_type = st.sidebar.radio("報表類型", ["綜合損益表", "資產負債表"])
year = st.sidebar.selectbox("年份 (民國)", ["113", "112", "111", "110"])
season = st.sidebar.selectbox("季度", ["01", "02", "03", "04"], index=2)

if st.sidebar.button("🚀 執行爬取") and target_id:
    with st.spinner('數據調閱中...'):
        df_result = fetch_mops_data(target_id, year, season, report_type)
        if df_result is not None:
            st.success(f"✅ 查詢成功！({target_id})")
            st.dataframe(df_result, use_container_width=True, height=500)
            csv = df_result.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載報表 (CSV)", csv, f"{target_id}_report.csv")
        else:
            st.error("❌ 查無資料，可能該季報尚未上傳。")
elif not target_id:
    st.warning("👈 請先選擇一家公司以開始查詢。")
