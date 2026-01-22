import streamlit as st
import pandas as pd
import requests
from io import StringIO
import time

# 設定網頁標題
st.set_page_config(page_title="富邦產險 | 財報分析助理", page_icon="🛡️", layout="wide")

# --- 1. 核心功能：抓取上市櫃股票清單 ---
@st.cache_data(ttl=3600) # 快取 1 小時，避免頻繁請求證交所
def get_stock_list():
    # 上市與上櫃代號對照表
    urls = ["https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", 
            "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"]
    stock_dict = {}
    for url in urls:
        try:
            res = requests.get(url)
            df = pd.read_html(res.text)[0]
            df.columns = df.iloc[0]
            df = df.iloc[1:]
            for item in df['有價證券代號及名稱'].dropna():
                if '　' in item: # 注意：這是全形空格
                    code, name = item.split('　')
                    if len(code) == 4: # 只取一般個股，排除權證/債券
                        stock_dict[f"{code} {name}"] = code
        except:
            continue
    return stock_dict

# --- 2. 核心功能：爬取財報數據 (MOPS) ---
def fetch_mops_data(stock_id, year, season, report_type):
    # 根據選擇切換 API 節點
    # ajax_t164sb04: 綜合損益表, ajax_t164sb03: 資產負債表
    api_map = {
        "綜合損益表": "ajax_t164sb04",
        "資產負債表": "ajax_t164sb03"
    }
    
    url = f'https://mops.twse.com.tw/mops/web/{api_map[report_type]}'
    
    payload = {
        'step': '1', 'firstin': '1', 'off': '1', 'queryName': 'co_id',
        'inpuType': 'co_id', 'TYPEK': 'all', 'isnew': 'false',
        'co_id': stock_id, 'year': year, 'season': season
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        res = requests.post(url, data=payload, headers=headers)
        res.encoding = 'utf-8'
        dfs = pd.read_html(StringIO(res.text))
        
        # 尋找包含財報數據的表格
        for df in dfs:
            if '會計項目' in df.columns.get_level_values(0):
                df.columns = df.columns.get_level_values(0)
                # 移除包含 NaN 的行，並確保數值欄位正確
                df = df[['會計項目', '金額']].dropna()
                return df
        return None
    except Exception as e:
        return f"Error: {e}"

# --- 3. Streamlit 介面設計 ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Fubon_Financial_Holding_Logo.svg/512px-Fubon_Financial_Holding_Logo.svg.png", width=200) # 預設 Fubon Logo
st.sidebar.title("🔍 查詢設定")

# 獲取清單
all_stocks = get_stock_list()
stock_options = ["--- 請選擇公司 ---"] + list(all_stocks.keys())

# 側邊欄輸入區
selected_stock = st.sidebar.selectbox("輸入公司名稱或代碼", options=stock_options)
report_type = st.sidebar.radio("報表類型", ["綜合損益表", "資產負債表"])
year = st.sidebar.selectbox("年份 (民國)", ["112", "111", "110", "109"], index=0)
season = st.sidebar.selectbox("季度", ["01", "02", "03", "04"], index=2)

st.title("🛡️ 富邦產險 - 企業財報分析助手")
st.info("本工具提供同仁快速調閱公開資訊觀測站數據，輔助核保與風險評估。")

# 邏輯判斷與顯示
if selected_stock != "--- 請選擇公司 ---":
    target_id = all_stocks[selected_stock]
    
    if st.sidebar.button("🚀 開始執行爬取"):
        with st.spinner(f'正在分析 {selected_stock} 數據中...'):
            df_result = fetch_mops_data(target_id, year, season, report_type)
            
            if isinstance(df_result, pd.DataFrame):
                st.success(f"✅ 已完成 {selected_stock} {year}Q{season} 之數據調閱")
                
                # 指標呈現區 (以損益表為例)
                if report_type == "綜合損益表":
                    st.subheader("📊 關鍵財務指標摘要")
                    # 過濾出產險同仁最關心的項目
                    key_items = ["營業收入合計", "營業利益（損失）", "本期淨利（淨損）", "基本每股盈餘"]
                    summary = df_result[df_result['會計項目'].str.strip().isin(key_items)]
                    
                    cols = st.columns(len(summary))
                    for idx, row in enumerate(summary.itertuples()):
                        cols[idx].metric(row.會計項目, f"{row.金額}")
                
                # 顯示原始資料表
                st.divider()
                st.subheader(f"📄 {report_type} 原始數據")
                st.dataframe(df_result, use_container_width=True, height=600)
                
                # CSV 下載功能
                csv = df_result.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 下載此報表 (CSV)",
                    data=csv,
                    file_name=f"{selected_stock}_{year}Q{season}_{report_type}.csv",
                    mime="text/csv"
                )
            else:
                st.error("❌ 抓取失敗：該公司可能尚未上傳此季度的數據，或網站結構變動。")
else:
    st.warning("👈 請先在左側選單選擇一家公司以開始查詢。")

# 頁尾說明
st.markdown("---")
st.caption("備註：本工具僅供內部參考，數據來源為公開資訊觀測站 (MOPS)。")