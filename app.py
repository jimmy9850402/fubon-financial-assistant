import streamlit as st
import pandas as pd
import requests
from io import StringIO

# 設定網頁標題與配置
st.set_page_config(page_title="富邦產險 | 財報分析助理", page_icon="🛡️", layout="wide")

# --- 1. 核心功能：抓取股票清單 (強化防排機制) ---
@st.cache_data(ttl=3600)
def get_stock_list():
    # 影片重點：必須模擬真實瀏覽器標頭
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    urls = [
        "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", # 上市
        "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"  # 上櫃
    ]
    stock_dict = {}
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'big5' # 證交所使用 big5 編碼
            # 使用 pandas 解析 HTML 表格
            df = pd.read_html(StringIO(res.text))[0]
            df.columns = df.iloc[0]
            df = df.iloc[1:]
            for item in df['有價證券代號及名稱'].dropna():
                if '　' in item:
                    code, name = item.split('　')
                    if len(code) == 4: # 過濾一般股票
                        stock_dict[f"{code} {name}"] = code
        except Exception:
            continue
    return stock_dict

# --- 2. 核心功能：爬取 Goodinfo 經營績效 (參考影片邏輯) ---
def fetch_goodinfo_data(stock_id):
    # 影片中使用的 Goodinfo 經營績效 URL
    url = f"https://goodinfo.com.tw/tw/StockFinancialPerformance.asp?STOCK_ID={stock_id}"
    
    # 影片重點：必須包含 referer 與 User-Agent 以免被偵測為機器人
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://goodinfo.com.tw/tw/index.asp'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        
        # 尋找包含財報數據的表格
        dfs = pd.read_html(StringIO(res.text))
        for df in dfs:
            if '年度' in df.columns.get_level_values(0):
                # 清理多層表頭，取最底層標籤
                df.columns = df.columns.get_level_values(df.columns.nlevels - 1)
                return df
        return None
    except Exception:
        return None

# --- 3. Streamlit 介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報分析助理")
st.info("本工具結合 Goodinfo 數據，協助同仁快速進行核保與徵信分析。")

# 側邊欄設定
st.sidebar.title("🔍 查詢設定")
all_stocks = get_stock_list()

# 解決「無法載入清單」的備案邏輯
target_id = None
if not all_stocks:
    st.sidebar.warning("⚠️ 自動清單獲取失敗，請手動輸入")
    target_id = st.sidebar.text_input("請輸入股票代碼 (例: 2330)")
else:
    options = ["--- 請選擇或輸入公司 ---"] + list(all_stocks.keys())
    selected_stock = st.sidebar.selectbox("公司名稱/代碼", options=options)
    if selected_stock != "--- 請選擇或輸入公司 ---":
        target_id = all_stocks[selected_stock]

# 執行爬取
if st.sidebar.button("🚀 開始執行分析") and target_id:
    with st.spinner(f'正在從 Goodinfo 調閱 {target_id} 數據...'):
        df_result = fetch_goodinfo_data(target_id)
        
        if df_result is not None:
            st.success(f"✅ 已完成 {target_id} 數據調閱")
            
            # 數據摘要呈現
            st.subheader("📊 經營績效概覽 (歷年)")
            st.dataframe(df_result, use_container_width=True, height=600)
            
            # 下載 CSV 功能
            csv = df_result.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載報表 (CSV)", csv, f"{target_id}_financial.csv", "text/csv")
        else:
            st.error("❌ 抓取失敗：可能受到 Goodinfo 網站頻率限制，請稍後再試。")
elif not target_id:
    st.warning("👈 請先選擇或輸入一家公司代碼以開始。")

st.markdown("---")
st.caption("備註：本工具數據來源為 Goodinfo!台灣股市資訊網，僅供內部參考。")
