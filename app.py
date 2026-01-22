import streamlit as st
import pandas as pd
import requests
from io import StringIO

# 設定網頁標題
st.set_page_config(page_title="富邦產險 | 企業財報分析助手", page_icon="🛡️")

# --- 1. 核心功能：獲取股票清單 (從證交所) ---
@st.cache_data(ttl=3600)
def get_stock_list():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    urls = ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]
    stock_dict = {}
    for url in urls:
        try:
            res = requests.get(url, headers=headers)
            res.encoding = 'big5'
            df = pd.read_html(StringIO(res.text))[0]
            df.columns = df.iloc[0]
            df = df.iloc[1:]
            for item in df['有價證券代號及名稱'].dropna():
                if '　' in item:
                    code, name = item.split('　')
                    if len(code) == 4: stock_dict[f"{code} {name}"] = code
        except: continue
    return stock_dict

# --- 2. 核心功能：爬取 Goodinfo 數據 (參考影片邏輯) ---
def fetch_goodinfo_data(stock_id):
    url = f"https://goodinfo.com.tw/tw/StockFinancialPerformance.asp?STOCK_ID={stock_id}"
    
    # 影片重點：必須加入正確的 Headers 與 Cookie 才能抓到資料
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://goodinfo.com.tw/tw/index.asp'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        
        # 影片重點：Goodinfo 資料通常在 ID 為 'txtFinancialDetailData' 的表格中
        dfs = pd.read_html(StringIO(res.text))
        for df in dfs:
            if '年度' in df.columns.get_level_values(0) or '獲利指標' in df.columns.get_level_values(0):
                # 清理多層表頭
                df.columns = df.columns.get_level_values(df.columns.nlevels - 1)
                return df
        return None
    except Exception as e:
        st.error(f"爬取失敗: {e}")
        return None

# --- 3. UI 介面 ---
st.title("🛡️ 富邦產險 - 企業財報分析助理")
st.markdown("本工具結合 **Goodinfo! 台灣股市資訊網** 數據，協助同仁快速進行核保評估。")

all_stocks = get_stock_list()
if all_stocks:
    options = ["--- 請輸入或選擇公司 ---"] + list(all_stocks.keys())
    selected_stock = st.selectbox("請選擇公司名稱/代碼", options=options)
    
    if selected_stock != "--- 請輸入或選擇公司 ---":
        target_id = all_stocks[selected_stock]
        
        if st.button("🚀 開始分析財報"):
            with st.spinner('正在從 Goodinfo 提取數據...'):
                df_result = fetch_goodinfo_data(target_id)
                
                if df_result is not None:
                    st.success(f"✅ 已獲取 {selected_stock} 的經營績效數據")
                    
                    # 顯示數據
                    st.subheader("📊 歷年經營績效概覽")
                    st.dataframe(df_result, use_container_width=True)
                    
                    # 下載功能
                    csv = df_result.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 下載數據 (CSV)", csv, f"{target_id}_financial.csv")
                else:
                    st.error("❌ 無法讀取表格，請確認 Goodinfo 網站是否暫時封鎖請求。")
else:
    st.error("無法載入股票清單，請檢查網路連線。")
