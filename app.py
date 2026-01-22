import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# --- 1. 基礎連線與翻譯對照 ---
st.set_page_config(page_title="富邦產險 | 核保財報助手", layout="wide")

SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 核心數據處理函數 ---
def fetch_analysis_report(stock_id):
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        # 同步抓取三大表
        income = ticker.financials
        balance = ticker.balance_sheet
        cashflow = ticker.cashflow
        
        if income.empty or balance.empty: return None

        # 取得年份清單 (前兩年)
        years = income.columns[:2].year.astype(str).tolist()
        
        # 建立對照表結構
        metrics = ["營業收入", "總資產", "負債比", "流動資產", "流動負債", "營業活動淨現金流"]
        result_df = pd.DataFrame({"項目": metrics})

        for i, year in enumerate(years):
            # 數值提取 (處理找不到欄位的情況)
            rev = income.loc["Total Revenue"].iloc[i] if "Total Revenue" in income.index else 0
            assets = balance.loc["Total Assets"].iloc[i] if "Total Assets" in balance.index else 0
            liab = balance.loc["Total Liabilities Net Minority Interest"].iloc[i] if "Total Liabilities Net Minority Interest" in balance.index else 0
            c_assets = balance.loc["Current Assets"].iloc[i] if "Current Assets" in balance.index else 0
            c_liab = balance.loc["Current Liabilities"].iloc[i] if "Current Liabilities" in balance.index else 0
            ocf = cashflow.loc["Operating Cash Flow"].iloc[i] if "Operating Cash Flow" in cashflow.index else 0
            
            # 計算負債比
            d_ratio = f"{(liab/assets)*100:.2f}%" if assets > 0 else "N/A"

            # 格式化並加入 DataFrame
            col_label = f"{year} 年 (FY)"
            result_df[col_label] = [
                f"{rev:,.0f}", f"{assets:,.0f}", d_ratio, 
                f"{c_assets:,.0f}", f"{c_liab:,.0f}", f"{ocf:,.0f}"
            ]
        return result_df
    except:
        return None

# --- 3. 網頁介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手")
st.markdown("---")

# 側邊欄輸入
with st.sidebar:
    st.header("🔍 查詢設定")
    stock_input = st.text_input("輸入股票代碼 (例: 2330)", placeholder="2330")
    search_btn = st.button("🚀 生成核保對照表")

if search_btn and stock_input:
    with st.spinner(f"正在從雲端解析 {stock_input} 財務數據..."):
        report = fetch_analysis_report(stock_input)
        
        if report is not None:
            st.success(f"✅ 已完成 {stock_input} 數據分析")
            
            # 顯示對照表格
            st.markdown(f"### 📊 {stock_input} 年度財務摘要對照表")
            st.table(report)
            
            # 下載功能
            csv = report.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載對照表 (CSV)", csv, f"{stock_input}_underwriting_report.csv", "text/csv")
        else:
            st.error("❌ 查無資料，請確認代碼是否正確。")

st.info("💡 提醒：最新季度 (Q) 數據目前正在與 Supabase 同步中，現階段提供年度對照。")
