import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# --- 1. 基礎設定 ---
st.set_page_config(page_title="富邦產險 | 核保財報助手", layout="wide")

SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 擴充公司代碼對照表 (整合台灣 50 / 中型 100) ---
# 已根據您提供的清單預載入核心公司
COMMON_COMPANIES = {
    "台積電": "2330.TW", "富邦金": "2881.TW", "國泰金": "2882.TW", "元大台灣50": "0050.TW",
    "元大中型100": "0051.TW", "鴻海": "2317.TW", "聯電": "2303.TW", "長榮": "2603.TW",
    "陽明": "2609.TW", "萬海": "2615.TW", "中鋼": "2002.TW", "台泥": "1101.TW",
    "亞泥": "1102.TW", "統一": "1216.TW", "台塑": "1301.TW", "南亞": "1303.TW",
    "台化": "1326.TW", "台塑化": "6505.TW", "中華電": "2412.TW", "台灣大": "3045.TW",
    "遠傳": "4904.TW", "旺宏": "2337.TW", "華邦電": "2344.TW", "仁寶": "2324.TW",
    "廣達": "2382.TW", "宏碁": "2353.TW", "華碩": "2357.TW", "日月光": "2311.TW",
    "大立光": "3008.TW", "聯發科": "2454.TW", "中信金": "2891.TW", "兆豐金": "2886.TW",
    "玉山金": "2884.TW", "台新金": "2887.TW", "第一金": "2892.TW", "合庫金": "5880.TW"
}

def get_symbol(query):
    query = query.strip()
    if query.isdigit(): return f"{query}.TW"
    if query in COMMON_COMPANIES: return COMMON_COMPANIES[query]
    
    # 若不在常用清單，啟動智慧搜尋
    try:
        search = yf.Search(query, max_results=3)
        for result in search.quotes:
            symbol = result['symbol']
            if symbol.endswith(".TW") or symbol.endswith(".TWO"):
                return symbol
    except: pass
    return None

def safe_get(df, index_name, col_name):
    try:
        if index_name in df.index:
            val = df.loc[index_name, col_name]
            return val if pd.notna(val) else 0
        return 0
    except: return 0

def fetch_full_report(symbol):
    """抓取 5 季 + 2 年完整數據並補齊年度空格"""
    try:
        ticker = yf.Ticker(symbol)
        q_inc, q_bal, q_cf = ticker.quarterly_financials, ticker.quarterly_balance_sheet, ticker.quarterly_cashflow
        fy_inc, fy_bal, fy_cf = ticker.financials, ticker.balance_sheet, ticker.cashflow

        if q_inc.empty: return None

        metrics = ["營業收入", "總資產", "負債比", "流動資產", "流動負債", "營業活動淨現金流"]
        result_df = pd.DataFrame({"項目": metrics})

        # 處理季度 (5 季)
        for col in q_inc.columns[:5]:
            label = f"{col.year}-Q{((col.month-1)//3)+1}"
            rev = safe_get(q_inc, "Total Revenue", col)
            assets = safe_get(q_bal, "Total Assets", col)
            liab = safe_get(q_bal, "Total Liabilities Net Minority Interest", col)
            if liab == 0: liab = safe_get(q_bal, "Total Liab", col)
            c_assets, c_liab = safe_get(q_bal, "Current Assets", col), safe_get(q_bal, "Current Liabilities", col)
            ocf = safe_get(q_cf, "Operating Cash Flow", col)
            d_ratio = f"{(liab/assets)*100:.2f}%" if assets > 0 else "N/A"
            result_df[label] = [f"{rev:,.0f}", f"{assets:,.0f}", d_ratio, f"{c_assets:,.0f}", f"{c_liab:,.0f}", f"{ocf:,.0f}"]

        # 處理年度 (2 年) - 數據補齊
        for col in fy_inc.columns[:2]:
            label = f"{col.year} (FY)"
            rev = safe_get(fy_inc, "Total Revenue", col)
            assets = safe_get(fy_bal, "Total Assets", col)
            liab = safe_get(fy_bal, "Total Liabilities Net Minority Interest", col)
            if liab == 0: liab = safe_get(fy_bal, "Total Liab", col)
            c_assets, c_liab = safe_get(fy_bal, "Current Assets", col), safe_get(fy_bal, "Current Liabilities", col)
            ocf = safe_get(fy_cf, "Operating Cash Flow", col)
            d_ratio = f"{(liab/assets)*100:.2f}%" if assets > 0 else "N/A"
            result_df[label] = [f"{rev:,.0f}", f"{assets:,.0f}", d_ratio, f"{c_assets:,.0f}", f"{c_liab:,.0f}", f"{ocf:,.0f}"]
        return result_df
    except: return None

# --- 3. UI 介面 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手")

with st.sidebar:
    query_input = st.text_input("輸入公司名稱 (例: 台積電、長榮) 或代碼", value="台積電")
    search_btn = st.button("🚀 生成核保報告")

if search_btn:
    with st.spinner(f"正在分析 '{query_input}' 的數據趨勢..."):
        target_symbol = get_symbol(query_input)
        if target_symbol:
            report = fetch_full_report(target_symbol)
            if report is not None:
                st.success(f"✅ 找到 {query_input} ({target_symbol})")
                # 顯示表格並自動補齊所有欄位
                st.dataframe(report, use_container_width=True)
                csv = report.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載此報表", csv, f"{query_input}_full_report.csv")
            else:
                st.error("❌ 獲取財報失敗，請確認代碼是否正確。")
        else:
            st.error(f"❌ 無法識別 '{query_input}'。")
