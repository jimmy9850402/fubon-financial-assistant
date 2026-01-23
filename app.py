import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client
import google.generativeai as genai

# --- 1. 基礎連線設定 ---
st.set_page_config(page_title="富邦產險 | 企業財報核保助手", layout="wide")

# 建議使用 Streamlit Secrets 確保安全
# 若在本地測試，請先在程式碼同層級建立 .streamlit/secrets.toml
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    # 僅供緊急測試使用，請務必更換為您新申請的 Key
    SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
    SUPABASE_KEY = "您的新_SUPABASE_KEY" 
    GEMINI_API_KEY = "您的新_GEMINI_API_KEY"

# 清理 Key 確保格式正確
CLEAN_SUPABASE_KEY = SUPABASE_KEY.strip().encode('ascii', 'ignore').decode('ascii')
supabase = create_client(SUPABASE_URL, CLEAN_SUPABASE_KEY)

# 初始化 Google AI
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. 輔助工具函數 ---

def find_stock_code(query):
    """資料庫搜尋代碼"""
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
        q_inc = ticker.quarterly_financials
        q_bal = ticker.quarterly_balance_sheet
        if q_inc.empty: return None

        metrics = ["營業收入", "總資產", "負債比"]
        result_df = pd.DataFrame({"項目": metrics})

        for col in q_inc.columns[:5]:
            label = f"{col.year}-Q{((col.month-1)//3)+1}"
            rev = q_inc.loc["Total Revenue", col] if "Total Revenue" in q_inc.index else 0
            assets = q_bal.loc["Total Assets", col] if "Total Assets" in q_bal.index else 0
            liab = q_bal.loc["Total Liabilities Net Minority Interest", col] if "Total Liabilities Net Minority Interest" in q_bal.index else 0
            d_ratio = (liab/assets)*100 if assets > 0 else 0
            result_df[label] = [rev, assets, d_ratio]
        return result_df
    except: return None

def get_ai_opinion(company_name, report_df):
    """動態偵測並呼叫 AI 模型"""
    latest_col = report_df.columns[1] 
    latest_data = report_df[latest_col].values
    
    prompt = f"你是一位核保專家。評估【{company_name}】最新負債比：{latest_data[2]:.2f}%。請給予簡短建議。"
    
    # 自動偵測可用的模型名稱
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = models[0] if models else "models/gemini-1.5-flash"
        
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI 分析失敗。請檢查 API Key 是否已更換。錯誤：{str(e)}"

# --- 3. UI 介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手")

user_query = st.text_input("輸入公司名稱 (例如: 旺宏)", value="旺宏")
if st.button("🚀 執行核保評估"):
    with st.spinner("正在進行 AI 診斷..."):
        target_symbol = find_stock_code(user_query)
        if target_symbol:
            report = fetch_analysis_report(target_symbol)
            if report is not None:
                st.dataframe(report, use_container_width=True)
                st.markdown("---")
                st.subheader("🤖 Gemini 專家建議")
                st.info(get_ai_opinion(user_query, report))
            else:
                st.error("獲取數據失敗。")
