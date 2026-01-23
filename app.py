import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client
import google.generativeai as genai

# --- 1. 基礎連線設定 ---
st.set_page_config(page_title="富邦產險 | 企業財報核保助手", layout="wide")

# 配置您的金鑰
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
GEMINI_API_KEY = "AIzaSyB2BKcuYjsr7LWhv9JTQcqOM-LvVKFEEVQ"

# 清理 Key 以避免編碼報錯
CLEAN_SUPABASE_KEY = SUPABASE_KEY.strip().encode('ascii', 'ignore').decode('ascii')
supabase = create_client(SUPABASE_URL, CLEAN_SUPABASE_KEY)

# 初始化 Google AI
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. 輔助工具函數 ---

def find_stock_code(query):
    """從資料庫搜尋代碼"""
    if query.isdigit(): return f"{query}.TW"
    try:
        res = supabase.table("stock_isin_list").select("code, name").ilike("name", f"%{query}%").execute()
        if res.data:
            for item in res.data:
                if item['name'] == query: return f"{item['code']}.TW"
            return f"{res.data[0]['code']}.TW"
    except: return None

def safe_get(df, index_name, col_name):
    """恢復原本的安全取得數據邏輯"""
    try:
        if index_name in df.index:
            val = df.loc[index_name, col_name]
            return val if pd.notna(val) else 0
        return 0
    except: return 0

def fetch_analysis_report(symbol):
    """恢復原本 5 季 + 2 年的財報抓取邏輯"""
    try:
        ticker = yf.Ticker(symbol)
        q_inc, q_bal, q_cf = ticker.quarterly_financials, ticker.quarterly_balance_sheet, ticker.quarterly_cashflow
        fy_inc, fy_bal, fy_cf = ticker.financials, ticker.balance_sheet, ticker.cashflow

        if q_inc.empty: return None

        metrics = ["營業收入", "總資產", "負債比", "流動資產", "流動負債", "營業活動淨現金流"]
        result_df = pd.DataFrame({"項目": metrics})

        # A. 處理 5 個季度
        for col in q_inc.columns[:5]:
            label = f"{col.year}-Q{((col.month-1)//3)+1}"
            rev = safe_get(q_inc, "Total Revenue", col)
            assets = safe_get(q_bal, "Total Assets", col)
            liab = safe_get(q_bal, "Total Liabilities Net Minority Interest", col)
            if liab == 0: liab = safe_get(q_bal, "Total Liab", col)
            c_assets = safe_get(q_bal, "Current Assets", col)
            c_liab = safe_get(q_bal, "Current Liabilities", col)
            ocf = safe_get(q_cf, "Operating Cash Flow", col)
            d_ratio = (liab/assets)*100 if assets > 0 else 0
            result_df[label] = [rev, assets, d_ratio, c_assets, c_liab, ocf]

        # B. 處理 2 個年度 (FY)
        for col in fy_inc.columns[:2]:
            label = f"{col.year} (FY)"
            rev = safe_get(fy_inc, "Total Revenue", col)
            assets = safe_get(fy_bal, "Total Assets", col)
            liab = safe_get(fy_bal, "Total Liabilities Net Minority Interest", col)
            if liab == 0: liab = safe_get(fy_bal, "Total Liab", col)
            c_assets = safe_get(fy_bal, "Current Assets", col)
            c_liab = safe_get(fy_bal, "Current Liabilities", col)
            ocf = safe_get(fy_cf, "Operating Cash Flow", col)
            d_ratio = (liab/assets)*100 if assets > 0 else 0
            result_df[label] = [rev, assets, d_ratio, c_assets, c_liab, ocf]
            
        return result_df
    except: return None

def get_ai_opinion(company_name, report_df):
    """使用您指定的嚴格核保 Prompt"""
    latest_col = report_df.columns[1] 
    latest_data = report_df[latest_col].values
    
    prompt = f"""
    【一、最高優先執行規則：觸發即匯出與數據校準】
    針對公司：{company_name} 產出完整 D&O 核保報告。

    四、Pre-check List (拒限保條件檢核)
    請根據數據：營收 {latest_data[0]:,.0f}, 負債比 {latest_data[2]:.2f}%。
    標示「✔ 命中」 「❌ 未命中」

    六、Group A 判定 (嚴格)
    - 營業收入低於新台幣一百五十億元？
    - 負債比等於或高於百分之八十？

    七、核保結論輸出
    ✅「本案符合 Group A...」 或 ❌「本案不符合 Group A...」
    """
    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 分析失敗: {e}"

# --- 3. UI 介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手")

with st.sidebar:
    st.header("🔍 數據檢索")
    user_query = st.text_input("輸入名稱或代碼", value="台積電")
    search_btn = st.button("🚀 生成報告與 AI 分析")

if search_btn and user_query:
    with st.spinner(f"正在恢復原始邏輯並抓取數據..."):
        target_symbol = find_stock_code(user_query)
        if target_symbol:
            report = fetch_analysis_report(target_symbol)
            if report is not None:
                st.success(f"✅ 標的確認: {user_query} ({target_symbol})")
                
                # 數據美化
                display_df = report.copy()
                for col in display_df.columns[1:]:
                    display_df[col] = display_df.apply(lambda x: f"{x[col]:,.2f}%" if x['項目'] == "負債比" else f"{x[col]:,.0f}", axis=1)
                st.dataframe(display_df, use_container_width=True)
                
                st.markdown("---")
                st.subheader("🤖 Gemini 專家建議")
                st.info(get_ai_opinion(user_query, report))
            else:
                st.error("❌ 抓取財報失敗。")
