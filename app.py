import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# --- 基礎設定 ---
st.set_page_config(page_title="富邦產險 | 雲端財報助理", layout="wide")
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🛡️ 富邦產險 - 雲端財報助手")

# --- 功能：自動更新數據 ---
def update_stock_data(stock_id):
    ticker = yf.Ticker(f"{stock_id}.TW")
    df = ticker.financials
    if not df.empty:
        latest_data = df.iloc[:, 0]
        data_list = []
        for acc, amt in latest_data.items():
            if pd.isna(amt): continue
            data_list.append({
                "stock_id": stock_id,
                "company_name": "核保查詢對象",
                "year": str(df.columns[0].year),
                "season": "Annual",
                "account_name": acc,
                "amount": int(amt),
                "report_type": "Income Statement"
            })
        # 寫入 Supabase
        supabase.table("financial_reports").insert(data_list).execute()
        return True
    return False

# --- UI 介面 ---
with st.sidebar:
    st.header("🔍 更新與查詢")
    stock_input = st.text_input("輸入股票代碼 (例: 2881)", placeholder="2881")
    if st.button("🚀 更新雲端資料並查詢"):
        with st.spinner("正在同步 yfinance 數據..."):
            success = update_stock_data(stock_input)
            if success: st.success(f"✅ {stock_input} 資料已同步！")

# --- 顯示資料表 ---
st.subheader("📋 雲端資料庫現有數據診斷")
# 原有的診斷邏輯...
