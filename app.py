import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# --- 1. 基礎設定 ---
st.set_page_config(page_title="富邦產險 | 核保財報助手", layout="wide")

SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 常用公司對照表 (確保核心客戶必中) ---
COMMON_COMPANIES = {
    "台積電": "2330.TW",
    "富邦金": "2881.TW",
    "國泰金": "2882.TW",
    "中信金": "2891.TW",
    "旺宏": "2337.TW",
    "鴻海": "2317.TW",
    "聯電": "2303.TW"
}

def get_symbol(query):
    """智慧識別輸入：代碼、常用名稱或搜尋"""
    query = query.strip()
    
    # 1. 如果是純數字，直接補 .TW
    if query.isdigit():
        return f"{query}.TW"
    
    # 2. 如果在常用清單中
    if query in COMMON_COMPANIES:
        return COMMON_COMPANIES[query]
    
    # 3. 使用 yfinance 搜尋
    try:
        search = yf.Search(query, max_results=3)
        for result in search.quotes:
            symbol = result['symbol']
            if symbol.endswith(".TW") or symbol.endswith(".TWO"):
                return symbol
    except:
        pass
    return None

def safe_get(df, index_name, col_name):
    try:
        if index_name in df.index:
            val = df.loc[index_name, col_name]
            return val if pd.notna(val) else 0
        return 0
    except: return 0

def fetch_full_report(symbol):
    """抓取 5 季 + 2 年完整數據"""
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

        # 處理年度 (2 年)
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
    query_input = st.text_input("輸入公司名稱或代碼 (例如: 台積電 或 2881)", value="台積電")
    search_btn = st.button("🚀 生成核保報告")

if search_btn:
    with st.spinner(f"正在分析 '{query_input}' 的數據..."):
        target_symbol = get_symbol(query_input)
        if target_symbol:
            report = fetch_full_report(target_symbol)
            if report is not None:
                st.success(f"✅ 找到 {query_input} ({target_symbol})")
                st.dataframe(report, use_container_width=True)
                # 提供匯出 CSV 功能
                csv = report.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載此報表", csv, f"{query_input}_report.csv")
            else:
                st.error("❌ 獲取財報內容失敗，請稍後再試。")
        else:
            st.error(f"❌ 無法識別 '{query_input}'，請嘗試輸入股票代碼 (例: 2330)。")
