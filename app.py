import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client
import google.generativeai as genai

# --- 1. 基礎連線設定 ---
st.set_page_config(page_title="富邦產險 | 企業財報核保助手", layout="wide")

# 請在此處填入您剛申請到的新金鑰
GEMINI_API_KEY = "AIzaSyC9dlxv5uwRtlAxmTeJKBEDCtAMKlA-iXw" 
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"

# 初始化設定
CLEAN_SUPABASE_KEY = SUPABASE_KEY.strip().encode('ascii', 'ignore').decode('ascii')
supabase = create_client(SUPABASE_URL, CLEAN_SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. 穩定版數據抓取函數 ---
def safe_get(df, index_name, col_name):
    try:
        if index_name in df.index:
            val = df.loc[index_name, col_name]
            return val if pd.notna(val) else 0
        return 0
    except: return 0

def fetch_analysis_report(symbol):
    """恢復原本正確的數據抓取邏輯"""
    try:
        ticker = yf.Ticker(symbol)
        q_inc = ticker.quarterly_financials
        q_bal = ticker.quarterly_balance_sheet
        q_cf = ticker.quarterly_cashflow
        if q_inc.empty: return None

        metrics = ["營業收入", "總資產", "負債比", "流動資產", "流動負債", "營業活動淨現金流"]
        result_df = pd.DataFrame({"項目": metrics})

        for col in q_inc.columns[:5]:
            label = f"{col.year}-Q{((col.month-1)//3)+1}"
            rev = safe_get(q_inc, "Total Revenue", col)
            assets = safe_get(q_bal, "Total Assets", col)
            liab = safe_get(q_bal, "Total Liabilities Net Minority Interest", col)
            if liab == 0: liab = safe_get(q_bal, "Total Liab", col)
            c_assets, c_liab = safe_get(q_bal, "Current Assets", col), safe_get(q_bal, "Current Liabilities", col)
            ocf = safe_get(q_cf, "Operating Cash Flow", col)
            d_ratio = (liab/assets)*100 if assets > 0 else 0
            result_df[label] = [rev, assets, d_ratio, c_assets, c_liab, ocf]
        return result_df
    except: return None

def get_ai_opinion(company_name, report_df):
    """執行您原本精確的 D&O 核保 Prompt"""
    latest_col = report_df.columns[1] 
    latest_data = report_df[latest_col].values
    
    prompt = f"""
    【一、最高優先執行規則：觸發即匯出與數據校準】
    針對公司：{company_name} 產出完整 D&O 核保報告。
    數據：營收 {latest_data[0]:,.0f}, 負債比 {latest_data[2]:.2f}%。

    四、Pre-check List (檢核✔/❌)
    六、Group A 判定 (營收是否達 150 億、負債比是否低於 80%)
    七、核保結論輸出
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 執行失敗：{e}"

# --- 3. UI 介面 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手")
user_query = st.text_input("輸入公司名稱 (如: 台積電)", value="台積電")

if st.button("🚀 生成完整核保報告"):
    with st.spinner("更新數據並調用新 API Key 中..."):
        # (此處需包含 find_stock_code 邏輯)
        report = fetch_analysis_report("2330.TW") # 範例
        if report is not None:
            st.dataframe(report, use_container_width=True)
            st.info(get_ai_opinion(user_query, report))
