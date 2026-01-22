import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# --- 1. 初始化與對照表設定 ---
st.set_page_config(page_title="富邦產險 | 企業財報核保助手", layout="wide")

SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 核心數據處理函數 ---
def fetch_full_report(stock_id):
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        
        # 抓取季度與年度數據
        q_income = ticker.quarterly_financials
        q_balance = ticker.quarterly_balance_sheet
        q_cashflow = ticker.quarterly_cashflow
        
        fy_income = ticker.financials
        fy_balance = ticker.balance_sheet
        
        if q_income.empty or fy_income.empty: return None

        # 定義指標名稱
        metrics = ["營業收入", "總資產", "負債比", "流動資產", "流動負債", "營業活動淨現金流"]
        result_df = pd.DataFrame({"項目": metrics})

        # --- A. 處理最近 5 個季度數據 ---
        q_cols = q_income.columns[:5] # 取最新 5 季
        for col in q_cols:
            date_str = col.strftime('%Y-Q%q') # 格式化為 2024-Q3
            
            rev = q_income.loc["Total Revenue", col] if "Total Revenue" in q_income.index else 0
            assets = q_balance.loc["Total Assets", col] if "Total Assets" in q_balance.index else 0
            liab = q_balance.loc["Total Liabilities Net Minority Interest", col] if "Total Liabilities Net Minority Interest" in q_balance.index else 0
            c_assets = q_balance.loc["Current Assets", col] if "Current Assets" in q_balance.index else 0
            c_liab = q_balance.loc["Current Liabilities", col] if "Current Liabilities" in q_balance.index else 0
            ocf = q_cashflow.loc["Operating Cash Flow", col] if "Operating Cash Flow" in q_cashflow.index else 0
            
            d_ratio = f"{(liab/assets)*100:.2f}%" if assets > 0 else "N/A"
            
            result_df[date_str] = [
                f"{rev:,.0f}", f"{assets:,.0f}", d_ratio, 
                f"{c_assets:,.0f}", f"{c_liab:,.0f}", f"{ocf:,.0f}"
            ]

        # --- B. 處理最近 2 個年度數據 (FY) ---
        fy_cols = fy_income.columns[:2]
        for col in fy_cols:
            year_str = f"{col.year} (FY)"
            
            rev = fy_income.loc["Total Revenue", col] if "Total Revenue" in fy_income.index else 0
            assets = fy_balance.loc["Total Assets", col] if "Total Assets" in fy_balance.index else 0
            liab = fy_balance.loc["Total Liabilities Net Minority Interest", col] if "Total Liabilities Net Minority Interest" in fy_balance.index else 0
            
            d_ratio = f"{(liab/assets)*100:.2f}%" if assets > 0 else "N/A"
            # 年度僅補上收入與資產等關鍵項，其餘留空或不顯示以維持表格簡潔
            result_df[year_str] = [f"{rev:,.0f}", f"{assets:,.0f}", d_ratio, "-", "-", "-"]

        return result_df
    except:
        return None

# --- 3. 網頁介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手 (完整版)")
st.markdown("輸入股票代碼即可產出包含 **最新 5 季** 與 **近 2 年** 的關鍵數據對照表。")

with st.sidebar:
    st.header("🔍 數據檢索")
    stock_input = st.text_input("輸入股票代碼", placeholder="2330")
    if st.button("🚀 生成完整報告"):
        st.session_state.do_search = True

if "do_search" in st.session_state and stock_input:
    with st.spinner(f"正在深度分析 {stock_input} 近期財務趨勢..."):
        report = fetch_full_report(stock_input)
        if report is not None:
            st.success(f"✅ {stock_input} 分析完成")
            
            # 使用 container 寬度顯示大表格
            st.markdown(f"### 📈 {stock_input} 財務數據趨勢 (最新 5 季 + 2 年度)")
            st.dataframe(report, use_container_width=True)
            
            # 提供 CSV 下載
            csv = report.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 匯出核保參考表", csv, f"{stock_input}_full_report.csv", "text/csv")
        else:
            st.error("❌ 無法抓取數據，請確認代碼（如: 2881, 2330）。")
