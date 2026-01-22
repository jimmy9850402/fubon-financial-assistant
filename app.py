import streamlit as st
import pandas as pd
import requests
from io import StringIO
import random
import time

# 設定網頁標題與配置
st.set_page_config(page_title="富邦產險 | 財報分析助理", page_icon="🛡️", layout="wide")

# --- 1. 核心功能：抓取股票清單 (從證交所) ---
@st.cache_data(ttl=3600)
def get_stock_list():
    # 增加模擬標頭以提高存取證交所的成功率
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    urls = ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]
    stock_dict = {}
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'big5'
            df = pd.read_html(StringIO(res.text))[0]
            df.columns = df.iloc[0]
            df = df.iloc[1:]
            for item in df['有價證券代號及名稱'].dropna():
                if '　' in item:
                    code, name = item.split('　')
                    if len(code) == 4: stock_dict[f"{code} {name}"] = code
        except Exception: continue
    return stock_dict

# --- 2. 核心功能：爬取 Goodinfo (強化防封鎖版) ---
def fetch_goodinfo_data(stock_id):
    url = f"https://goodinfo.com.tw/tw/StockFinancialPerformance.asp?STOCK_ID={stock_id}"
    
    # 影片與實務重點：Goodinfo 對 Headers 檢核極嚴，必須包含 Referer 與合理的 Cookie
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'referer': 'https://goodinfo.com.tw/tw/index.asp',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    try:
        # 建立一個 Session 來維持連線狀態，有助於通過部分檢查
        session = requests.Session()
        # 先存取首頁獲取基本 Cookie
        session.get("https://goodinfo.com.tw/tw/index.asp", headers=headers, timeout=10)
        
        # 增加一個隨機延遲，模擬真人操作行為
        time.sleep(random.uniform(1, 3))
        
        res = session.get(url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        
        # 檢查是否被轉向到驗證碼頁面或返回空資料
        if "請稍候" in res.text or "異常存取" in res.text:
            return "BLOCK"
            
        dfs = pd.read_html(StringIO(res.text))
        for df in dfs:
            if '年度' in df.columns.get_level_values(0):
                df.columns = df.columns.get_level_values(df.columns.nlevels - 1)
                return df
        return None
    except Exception as e:
        return None

# --- 3. UI 介面 ---
st.title("🛡️ 富邦產險 - 企業財報分析助理")
st.info("本工具協助同仁快速調閱數據。若出現頻率限制，請等待 1 分鐘後再試。")

all_stocks = get_stock_list()
target_id = None

# 侧邊欄設置
with st.sidebar:
    st.header("🔍 查詢設定")
    if not all_stocks:
        st.warning("⚠️ 無法獲取股票清單，請手動輸入")
        target_id = st.text_input("輸入股票代碼 (例: 2330)")
    else:
        options = ["--- 請選擇公司 ---"] + list(all_stocks.keys())
        selected_stock = st.selectbox("公司名稱/代碼", options=options)
        if selected_stock != "--- 請選擇公司 ---":
            target_id = all_stocks[selected_stock]

    search_btn = st.button("🚀 開始分析", disabled=(target_id is None))

# 執行邏輯
if search_btn:
    with st.spinner(f'正在分析 {target_id} 的財報趨勢...'):
        df_result = fetch_goodinfo_data(target_id)
        
        if isinstance(df_result, pd.DataFrame):
            st.success(f"✅ 已獲取 {target_id} 數據")
            st.dataframe(df_result, use_container_width=True, height=600)
            csv = df_result.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載報表 (CSV)", csv, f"{target_id}_report.csv")
        elif df_result == "BLOCK":
            st.error("🚨 抓取失敗：Goodinfo 網站偵測到異常存取。請同仁稍等 1-2 分鐘，或更換查詢的公司。")
        else:
            st.error("❌ 查無資料或網站結構變動。")
