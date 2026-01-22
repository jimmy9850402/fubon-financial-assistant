import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# --- 1. 基礎設定 ---
st.set_page_config(page_title="富邦產險 | 核保財報助手", layout="wide")

SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def safe_get(df, index_name, col_name):
    try:
        if index_name in df.index:
            val = df.loc[index_name, col_name]
            return val if pd.notna(val) else 0
        return 0
    except:
        return 0

# --- 2. 核心數據處理函數 ---
def fetch_full_report(stock_id):
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        # 抓取季度數據
        q_inc = ticker.quarterly_financials
        q_bal = ticker.quarterly_balance_sheet
        q_cf  = ticker.quarterly_cashflow
        # 抓取年度數據
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

        # B. 處理最新 2 個年度數據 (FY) - 已補齊所有欄位
        for col in fy_inc.columns[:2]:
            year_label = f"{col.year} (FY)"
            
            rev = safe_get(fy_inc, "Total Revenue", col)
            assets = safe_get(fy_bal, "Total Assets", col)
            liab = safe_get(fy_bal, "Total Liabilities Net Minority Interest", col)
            if liab == 0: liab = safe_get(fy_bal, "Total Liab", col)
            
            # 補齊年度的流動項目與現金流
            c_assets = safe_get(fy_bal, "Current Assets", col)
            c_liab = safe_get(fy_bal, "Current Liabilities", col)
            ocf = safe_get(fy_cf, "Operating Cash Flow", col)
            
            d_ratio = f"{(liab/assets)*100:.2f}%" if assets > 0 else "N/A"
            
            result_df[year_label] = [
                f"{rev:,.0f}", f"{assets:,.0f}", d_ratio, 
                f"{c_assets:,.0f}", f"{c_liab:,.0f}", f"{ocf:,.0f}"
            ]

        return result_df
    except:
        return None

# --- 3. UI 介面 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手")

with st.sidebar:
    stock_input = st.text_input("輸入股票代碼", value="2337")
    search_btn = st.button("🚀 生成核保報告")

if search_btn:
    with st.spinner(f"正在同步 {stock_input} 年度與季度數據..."):
        report = fetch_full_report(stock_input)
        if report is not None:
            st.success(f"✅ {stock_input} 分析完成")
            st.dataframe(report, use_container_width=True)
            csv = report.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此報表", csv, f"{stock_input}_full_report.csv")
        else:
            st.error("❌ 無法獲取數據，請確認代碼是否正確。")
