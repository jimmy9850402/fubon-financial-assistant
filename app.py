import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client

# --- 1. 基礎連線設定 ---
st.set_page_config(page_title="富邦產險 | 企業財報核保助手", layout="wide")

SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 輔助工具函數 ---
def safe_get(df, index_name, col_name):
    """安全取得數據，避免欄位缺失導致報錯"""
    try:
        if index_name in df.index:
            val = df.loc[index_name, col_name]
            return val if pd.notna(val) else 0
        return 0
    except: return 0

def find_stock_code(query):
    """從資料庫 stock_isin_list 搜尋名稱對應的代碼"""
    # 如果輸入是純數字代碼 (例如 2330)，直接回傳
    if query.isdigit():
        return f"{query}.TW"
    
    # 否則到雲端資料庫搜尋名稱
    try:
        # 支援模糊查詢 (包含輸入的關鍵字)
        res = supabase.table("stock_isin_list").select("code, name").ilike("name", f"%{query}%").execute()
        if res.data:
            # 如果找到多個，取第一個或完全匹配的項目
            for item in res.data:
                if item['name'] == query:
                    return f"{item['code']}.TW"
            return f"{res.data[0]['code']}.TW"
    except Exception as e:
        st.error(f"資料庫查詢異常: {e}")
    return None

def fetch_analysis_report(symbol):
    """執行 5 季 + 2 年的財報抓取"""
    try:
        ticker = yf.Ticker(symbol)
        q_inc, q_bal, q_cf = ticker.quarterly_financials, ticker.quarterly_balance_sheet, ticker.quarterly_cashflow
        fy_inc, fy_bal, fy_cf = ticker.financials, ticker.balance_sheet, ticker.cashflow

        if q_inc.empty: return None

        metrics = ["營業收入", "總資產", "負債比", "流動資產", "流動負債", "營業活動淨現金流"]
        result_df = pd.DataFrame({"項目": metrics})

        # A. 處理最新 5 個季度
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

        # B. 處理最新 2 個年度 (FY)
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

# --- 3. UI 介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手")
st.markdown("輸入 **公司名稱** (例: 旺宏) 或 **股票代碼** (例: 2330) 即可產出對照表。")

with st.sidebar:
    st.header("🔍 數據檢索")
    user_query = st.text_input("輸入名稱或代碼", value="旺宏")
    search_btn = st.button("🚀 生成核保報告")

if search_btn and user_query:
    with st.spinner(f"正在比對資料庫並分析 '{user_query}' 數據..."):
        # 步驟 1: 找出代碼
        target_symbol = find_stock_code(user_query)
        
        if target_symbol:
            # 步驟 2: 抓取財報
            report = fetch_analysis_report(target_symbol)
            if report is not None:
                st.success(f"✅ 已識別標的: {user_query} ({target_symbol})")
                st.dataframe(report, use_container_width=True)
                
                # 下載功能
                csv = report.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載此報表", csv, f"{user_query}_report.csv")
            else:
                st.error("❌ 找到公司但無法獲取財報數據 (yfinance 暫時無回應)。")
        else:
            st.error(f"❌ 資料庫查無 '{user_query}'，請改輸入股票代碼試試看。")
