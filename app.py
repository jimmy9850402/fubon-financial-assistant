import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# --- 1. 基礎設定 ---
st.set_page_config(page_title="富邦產險 | 核保財報助手", layout="wide")

SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 輔助工具函數 ---
def safe_get(df, index_name, col_name):
    try:
        if index_name in df.index:
            val = df.loc[index_name, col_name]
            return val if pd.notna(val) else 0
        return 0
    except:
        return 0

def get_symbol_by_name(company_name):
    """將公司名稱轉換為股票代碼"""
    try:
        # 使用 yfinance 的搜尋功能
        search = yf.Search(company_name, max_results=5)
        for result in search.quotes:
            symbol = result['symbol']
            # 確保是台股代碼 (.TW 或 .TWO)
            if symbol.endswith(".TW") or symbol.endswith(".TWO"):
                return symbol
        # 如果沒找到 .TW，嘗試直接加 .TW
        return None
    except:
        return None

def fetch_full_report(symbol):
    """抓取完整的季度與年度數據"""
    try:
        ticker = yf.Ticker(symbol)
        q_inc = ticker.quarterly_financials
        q_bal = ticker.quarterly_balance_sheet
        q_cf  = ticker.quarterly_cashflow
        fy_inc = ticker.financials
        fy_bal = ticker.balance_sheet
        fy_cf  = ticker.cashflow

        if q_inc.empty or fy_inc.empty: return None

        metrics = ["營業收入", "總資產", "負債比", "流動資產", "流動負債", "營業活動淨現金流"]
        result_df = pd.DataFrame({"項目": metrics})

        # A. 處理最新 5 個季度數據
        for col in q_inc.columns[:5]:
            quarter_label = f"{col.year}-Q{((col.month-1)//3)+1}"
            rev = safe_get(q_inc, "Total Revenue", col)
            assets = safe_get(q_bal, "Total Assets", col)
            liab = safe_get(q_bal, "Total Liabilities Net Minority Interest", col)
            if liab == 0: liab = safe_get(q_bal, "Total Liab", col)
            c_assets = safe_get(q_bal, "Current Assets", col)
            c_liab = safe_get(q_bal, "Current Liabilities", col)
            ocf = safe_get(q_cf, "Operating Cash Flow", col)
            d_ratio = f"{(liab/assets)*100:.2f}%" if assets > 0 else "N/A"
            result_df[quarter_label] = [f"{rev:,.0f}", f"{assets:,.0f}", d_ratio, f"{c_assets:,.0f}", f"{c_liab:,.0f}", f"{ocf:,.0f}"]

        # B. 處理最新 2 個年度數據 (FY)
        for col in fy_inc.columns[:2]:
            year_label = f"{col.year} (FY)"
            rev = safe_get(fy_inc, "Total Revenue", col)
            assets = safe_get(fy_bal, "Total Assets", col)
            liab = safe_get(fy_bal, "Total Liabilities Net Minority Interest", col)
            if liab == 0: liab = safe_get(fy_bal, "Total Liab", col)
            c_assets = safe_get(fy_bal, "Current Assets", col)
            c_liab = safe_get(fy_bal, "Current Liabilities", col)
            ocf = safe_get(fy_cf, "Operating Cash Flow", col)
            d_ratio = f"{(liab/assets)*100:.2f}%" if assets > 0 else "N/A"
            result_df[year_label] = [f"{rev:,.0f}", f"{assets:,.0f}", d_ratio, f"{c_assets:,.0f}", f"{c_liab:,.0f}", f"{ocf:,.0f}"]

        return result_df
    except:
        return None

# --- 3. UI 介面 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手")

with st.sidebar:
    st.header("🔍 數據檢索")
    query_input = st.text_input("輸入公司名稱或代碼", value="台積電")
    search_btn = st.button("🚀 生成核保報告")

if search_btn:
    with st.spinner(f"正在搜尋 '{query_input}' 並分析財報數據..."):
        # 先判斷是否需要名稱轉代碼
        target_symbol = query_input
        if not (query_input.endswith(".TW") or query_input.endswith(".TWO")):
            # 判斷是否為純數字，如果是數字則補上 .TW
            if query_input.isdigit():
                target_symbol = f"{query_input}.TW"
            else:
                # 名稱轉代碼
                target_symbol = get_symbol_by_name(query_input)
        
        if target_symbol:
            report = fetch_full_report(target_symbol)
            if report is not None:
                st.success(f"✅ 已找到 {query_input} ({target_symbol}) 的數據")
                st.dataframe(report, use_container_width=True)
                csv = report.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載此報表", csv, f"{query_input}_report.csv")
            else:
                st.error("❌ 抓取數據失敗。這可能是因為 Yahoo 股市暫時無該公司的詳細財報。")
        else:
            st.error(f"❌ 找不到與 '{query_input}' 相關的台灣股票代碼。")
