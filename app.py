import streamlit as st
import pandas as pd
import requests
from io import StringIO
import time

# 設定網頁標題與寬度
st.set_page_config(page_title="富邦產險 | 財報分析助理", page_icon="🛡️", layout="wide")

# --- 1. 核心功能：抓取上市櫃股票清單 (強化穩定版) ---
@st.cache_data(ttl=3600)
def get_stock_list():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    urls = ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", 
            "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]
    stock_dict = {}
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'big5'
            # 使用 StringIO 包裝避免警告
            df = pd.read_html(StringIO(res.text))[0]
            df.columns = df.iloc[0]
            df = df.iloc[1:]
            for item in df['有價證券代號及名稱'].dropna():
                if '　' in item:
                    code, name = item.split('　')
                    if len(code) == 4:
                        stock_dict[f"{code} {name}"] = code
        except Exception as e:
            continue # 若單一來源失敗，嘗試下一個
    return stock_dict

# --- 2. 核心功能：爬取財報數據 ---
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
st.title("🛡️ 富邦產險 - 企業財報分析助理")
st.info("本工具協助同仁快速調閱公開資訊觀測站數據，輔助核保風險評估。")

# 側邊欄設定
st.sidebar.title("🔍 查詢設定")
all_stocks = get_stock_list()

# 防呆處理：若清單抓取失敗的替代方案
if not all_stocks:
    st.sidebar.warning("⚠️ 自動清單獲取失敗，請手動輸入代碼")
    target_id = st.sidebar.text_input("請輸入股票代碼 (例: 2330)", value="")
    selected_stock_name = target_id
else:
    stock_options = ["--- 請選擇公司 ---"] + list(all_stocks.keys())
    selected_stock = st.sidebar.selectbox("輸入公司名稱或代碼", options=stock_options)
    
    # 解決 KeyError: None 的核心逻辑
    if selected_stock != "--- 請選擇公司 ---":
        target_id = all_stocks[selected_stock]
        selected_stock_name = selected_stock
    else:
        target_id = None

# 其他參數
report_type = st.sidebar.radio("報表類型", ["綜合損益表", "資產負債表"])
year = st.sidebar.selectbox("年份 (民國)", ["113", "112", "111", "110"])
season = st.sidebar.selectbox("季度", ["01", "02", "03", "04"], index=2)

# 執行查詢
if st.sidebar.button("🚀 開始執行爬取") and target_id:
    with st.spinner(f'正在調閱 {selected_stock_name} 數據...'):
        df_result = fetch_mops_data(target_id, year, season, report_type)
        
        if df_result is not None:
            st.success(f"✅ 已完成 {selected_stock_name} {year}Q{season} 數據調閱")
            
            # 指標摘要 (僅損益表顯示)
            if report_type == "綜合損益表":
                st.subheader("📊 關鍵財務指標摘要")
                key_items = ["營業收入合計", "營業利益（損失）", "本期淨利（淨損）", "基本每股盈餘"]
                summary = df_result[df_result['會計項目'].str.strip().isin(key_items)]
                if not summary.empty:
                    cols = st.columns(len(summary))
                    for i, row in enumerate(summary.itertuples()):
                        cols[i].metric(row.會計項目, f"{row.金額}")
            
            st.divider()
            st.subheader(f"📄 {report_type} 原始數據")
            st.dataframe(df_result, use_container_width=True, height=500)
            
            # 下載功能
            csv = df_result.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此報表 (CSV)", csv, f"{target_id}_{year}Q{season}.csv", "text/csv")
        else:
            st.error("❌ 抓取失敗：該公司可能尚未上傳此季度數據。")
elif not target_id:
    st.warning("👈 請先在左側選單選擇或輸入公司。")

st.markdown("---")
st.caption("備註：數據來源為公開資訊觀測站 (MOPS)。")
