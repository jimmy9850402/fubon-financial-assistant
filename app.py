import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# --- 1. 初始化與設定 ---
st.set_page_config(page_title="富邦產險 | 企業財報診斷助手", layout="wide")

# Supabase 連線資訊
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 定義翻譯與對照表
METRIC_MAP = {
    "Total Revenue": "營業收入",
    "Total Assets": "總資產",
    "Total Liab": "總負債", # 用於計算負債比
    "Current Assets": "流動資產",
    "Current Liabilities": "流動負債",
    "Operating Cash Flow": "營業活動淨現金流"
}

# --- 2. 核心功能函數 ---
def get_financial_summary(stock_id):
    ticker = yf.Ticker(f"{stock_id}.TW")
    
    # 抓取損益表、資產負債表與現金流量表
    income = ticker.financials
    balance = ticker.balance_sheet
    cashflow = ticker.cashflow
    
    if income.empty or balance.empty:
        return None

    # 提取需要的年份資料 (假設 2023, 2024 為前兩欄)
    years = income.columns[:2].year.astype(str).tolist()
    
    # 建立回傳資料結構
    report_data = {
        "項目": ["營業收入", "總資產", "負債比", "流動資產", "流動負債", "營業活動淨現金流"]
    }

    for i, year in enumerate(years):
        col_name = f"{year} 年 (FY)"
        
        # 抓取各項數值 (單位：元)
        rev = income.loc["Total Revenue"].iloc[i] if "Total Revenue" in income.index else 0
        assets = balance.loc["Total Assets"].iloc[i] if "Total Assets" in balance.index else 0
        liab = balance.loc["Total Liabilities Net Minority Interest"].iloc[i] if "Total Liabilities Net Minority Interest" in balance.index else 0
        c_assets = balance.loc["Current Assets"].iloc[i] if "Current Assets" in balance.index else 0
        c_liab = balance.loc["Current Liabilities"].iloc[i] if "Current Liabilities" in balance.index else 0
        ocf = cashflow.loc["Operating Cash Flow"].iloc[i] if "Operating Cash Flow" in cashflow.index else 0
        
        debt_ratio = f"{(liab/assets)*100:.2f}%" if assets > 0 else "N/A"

        report_data[col_name] = [
            f"{rev:,.0f}", f"{assets:,.0f}", debt_ratio, 
            f"{c_assets:,.0f}", f"{c_liab:,.0f}", f"{ocf:,.0f}"
        ]
        
    return pd.DataFrame(report_data)

# --- 3. UI 介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報診斷助手")
st.markdown("請輸入股票代碼，系統將自動從雲端與 yfinance 獲取數據並生成核保參考表格。")

stock_code = st.text_input("請輸入公司股票代碼 (例如: 2330)", placeholder="2330")

if stock_code:
    with st.spinner(f"正在分析 {stock_code} 的財報數據..."):
        df_summary = get_financial_summary(stock_code)
        
        if df_summary is not None:
            st.success(f"✅ 已完成 {stock_code} 的數據檢索")
            
            # 顯示要求的表格
            st.table(df_summary)
            
            # 額外功能：匯出 CSV 給同仁
            csv = df_summary.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此核保參考表", csv, f"{stock_code}_report.csv", "text/csv")
        else:
            st.error("❌ 找不到該公司的財報資料，請確認代碼是否正確（需為上市櫃公司）。")

st.info("💡 註：最新季度 (Q) 數據目前正在整合中，目前提供年度 (FY) 數據供核保參考。")
