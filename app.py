import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client
import json

# --- 1. 初始化連線 ---
st.set_page_config(page_title="富邦產險 | 核保 Copilot 數據中樞", layout="wide")

# Supabase 連線資訊
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 核心數據處理邏輯 ---

def safe_get(df, index_name, col_name):
    """安全取得數據，避免 Agent 讀取到空值"""
    try:
        if index_name in df.index:
            val = df.loc[index_name, col_name]
            return float(val) if pd.notna(val) else 0.0
        return 0.0
    except: return 0.0

def find_stock_code(query):
    """從 stock_isin_list 檢索正確代碼"""
    if query.isdigit(): return f"{query}.TW"
    try:
        res = supabase.table("stock_isin_list").select("code, name").ilike("name", f"%{query}%").execute()
        if res.data:
            for item in res.data:
                if item['name'] == query: return f"{item['code']}.TW"
            return f"{res.data[0]['code']}.TW"
    except: pass
    return None

def fetch_and_sync_agent_data(symbol, company_display_name):
    """抓取數據並同步至 Agent 專用資料表"""
    try:
        ticker = yf.Ticker(symbol)
        q_inc, q_bal, q_cf = ticker.quarterly_financials, ticker.quarterly_balance_sheet, ticker.quarterly_cashflow
        fy_inc, fy_bal = ticker.financials, ticker.balance_sheet
        
        if q_inc.empty: return None

        metrics = ["營業收入", "總資產", "負債比", "流動資產", "流動負債", "營業活動淨現金流"]
        result_df = pd.DataFrame({"項目": metrics})
        
        # 準備要存入 Supabase 的 JSON 格式 (供 Agent 讀取)
        agent_data_bundle = []

        # 處理 5 季 + 2 年
        columns_to_process = list(q_inc.columns[:5]) + list(fy_inc.columns[:2])
        
        for col in columns_to_process:
            is_fy = col in fy_inc.columns
            label = f"{col.year} (FY)" if is_fy else f"{col.year}-Q{((col.month-1)//3)+1}"
            
            # 使用年度或季度表格
            inc_src = fy_inc if is_fy else q_inc
            bal_src = fy_bal if is_fy else q_bal
            cf_src = ticker.cashflow if is_fy else q_cf

            rev = safe_get(inc_src, "Total Revenue", col)
            assets = safe_get(bal_src, "Total Assets", col)
            liab = safe_get(bal_src, "Total Liabilities Net Minority Interest", col)
            if liab == 0: liab = safe_get(bal_src, "Total Liab", col)
            c_assets = safe_get(bal_src, "Current Assets", col)
            c_liab = safe_get(bal_src, "Current Liabilities", col)
            ocf = safe_get(cf_src, "Operating Cash Flow", col)
            
            d_ratio_val = (liab/assets) if assets > 0 else 0
            
            result_df[label] = [
                f"{rev:,.0f}", f"{assets:,.0f}", f"{d_ratio_val*100:.2f}%", 
                f"{c_assets:,.0f}", f"{c_liab:,.0f}", f"{ocf:,.0f}"
            ]

            # 同步至 Agent 專用結構
            agent_data_bundle.append({
                "stock_id": symbol.split('.')[0],
                "company_name": company_display_name,
                "period": label,
                "revenue": rev,
                "total_assets": assets,
                "debt_ratio": d_ratio_val,
                "net_cash_flow": ocf
            })

        # --- 3. 寫入 Supabase 供 Copilot Agent 調用 ---
        supabase.table("agent_financial_cache").upsert(agent_data_bundle).execute()
        
        return result_df
    except Exception as e:
        st.error(f"數據解析失敗: {e}")
        return None

# --- 4. 網頁 UI 介面 ---
st.title("🛡️ 富邦產險 - 核保 Copilot 數據中樞")
st.info("本系統數據已與 Copilot Agent 串接，在此查詢後，Agent 將自動獲得最新精準數據。")

with st.sidebar:
    st.header("🔍 數據同步設定")
    user_query = st.text_input("輸入公司名稱或代碼", value="旺宏")
    sync_btn = st.button("🚀 更新數據並同步至 Agent")

if sync_btn and user_query:
    with st.spinner(f"正在分析 '{user_query}' 並同步至核保 Agent..."):
        target_symbol = find_stock_code(user_query)
        
        if target_symbol:
            report = fetch_and_sync_agent_data(target_symbol, user_query)
            if report is not None:
                st.success(f"✅ 同步成功！Agent 現在已獲得 {user_query} 的最新財報。")
                st.dataframe(report, use_container_width=True)
                
                # 數據視覺化輔助
                st.subheader("📊 關鍵指標趨勢 (負債比)")
                # 轉置資料以利畫圖
                chart_data = report.T.iloc[1:]
                chart_data.columns = report['項目'].values
                chart_data['負債比'] = chart_data['負債比'].str.replace('%','').astype(float)
                st.line_chart(chart_data['負債比'])
            else:
                st.error("❌ 無法抓取財報，請檢查網路。")
        else:
            st.error(f"❌ 資料庫找不到 '{user_query}'。")
