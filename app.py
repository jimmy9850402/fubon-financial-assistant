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

def fetch_analysis_report(symbol):
    """抓取 5 季財報數據"""
    try:
        ticker = yf.Ticker(symbol)
        q_inc, q_bal, q_cf = ticker.quarterly_financials, ticker.quarterly_balance_sheet, ticker.quarterly_cashflow
        if q_inc.empty: return None

        metrics = ["營業收入", "總資產", "負債比", "營業活動淨現金流"]
        result_df = pd.DataFrame({"項目": metrics})

        for col in q_inc.columns[:5]:
            label = f"{col.year}-Q{((col.month-1)//3)+1}"
            rev = q_inc.loc["Total Revenue", col] if "Total Revenue" in q_inc.index else 0
            assets = q_bal.loc["Total Assets", col] if "Total Assets" in q_bal.index else 0
            liab = q_bal.loc["Total Liabilities Net Minority Interest", col] if "Total Liabilities Net Minority Interest" in q_bal.index else 0
            ocf = q_cf.loc["Operating Cash Flow", col] if "Operating Cash Flow" in q_cf.index else 0
            d_ratio = (liab/assets)*100 if assets > 0 else 0
            result_df[label] = [rev, assets, d_ratio, ocf]
        return result_df
    except: return None

def get_ai_opinion(company_name, report_df):
    """呼叫 Gemini 進行核保診斷 (包含 404 自動修復邏輯)"""
    latest_col = report_df.columns[1] 
    latest_data = report_df[latest_col].values
    
    prompt = f"""
    你是一位富邦產險的 D&O 核保專家。請分析【{company_name}】最新財報：
    - 負債比率：{latest_data[2]:.2f}% (警示線 65%)
    - 營業活動現金流：{latest_data[3]:,.0f}
    請給予專業的承保建議。
    """
    
    # 嘗試多個可能的模型路徑，解決不同 SDK 版本的相容問題
    model_paths = ["models/gemini-1.5-flash", "gemini-1.5-flash", "models/gemini-pro"]
    
    for path in model_paths:
        try:
            model = genai.GenerativeModel(path)
            response = model.generate_content(prompt)
            return response.text
        except:
            continue
    return "❌ 所有 Gemini 模型路徑均失效。請檢查 API Key 權限或更新 google-generativeai 套件。"

# --- 3. UI 介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手 (Gemini 版)")

with st.sidebar:
    st.header("🔍 數據檢索")
    user_query = st.text_input("輸入公司名稱或代碼", value="旺宏")
    search_btn = st.button("🚀 生成報告與 AI 分析")

if search_btn and user_query:
    with st.spinner(f"正在連線 Gemini 並分析 '{user_query}'..."):
        target_symbol = find_stock_code(user_query)
        if target_symbol:
            report = fetch_analysis_report(target_symbol)
            if report is not None:
                st.success(f"標的確認: {user_query} ({target_symbol})")
                
                # 數據美化
                display_df = report.copy()
                for col in display_df.columns[1:]:
                    display_df[col] = display_df.apply(lambda x: f"{x[col]:,.2f}%" if x['項目'] == "負債比" else f"{x[col]:,.0f}", axis=1)
                st.dataframe(display_df, use_container_width=True)
                
                # AI 分析區塊
                st.markdown("---")
                st.subheader("🤖 Gemini 專家診斷意見")
                opinion = get_ai_opinion(user_query, report)
                st.info(opinion)
            else:
                st.error("無法抓取數據。")
        else:
            st.error("查無標的。")
