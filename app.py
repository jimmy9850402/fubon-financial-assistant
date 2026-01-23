import streamlit as st
import google.generativeai as genai
from supabase import create_client
import pandas as pd

# --- 1. 基礎設定 (請替換為您的實際連線資訊) ---
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "您的_SUPABASE_ANON_KEY" # 請填入您的 Supabase Key
GEMINI_API_KEY = "AIzaSyB2BKcuYjsr7LWhv9JTQcqOM-LvVKFEEVQ"

# 初始化客戶端
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. 功能函式定義 ---

def get_ai_analysis(company_name):
    """從 Supabase 抓取數據並由 Gemini 進行 D&O 風險評估"""
    # 使用 ilike 確保查詢靈活性，避免之前的 400 錯誤
    result = supabase.table("agent_financial_cache") \
        .select("*") \
        .ilike("company_name", f"%{company_name}%") \
        .order("period", descending=True) \
        .limit(1) \
        .execute()

    if not result.data:
        return None, "❌ 查無快取數據，請先執行數據同步。"

    data = result.data[0]
    
    # 建立給 Gemini 的專業 Prompt
    prompt = f"""
    你是一位富邦產險的 D&O (董監事責任險) 核保專家。
    請針對以下財務數據進行風險評估：
    - 公司名稱：{data['company_name']}
    - 財報期間：{data['period']}
    - 負債比率：{data['debt_ratio']}% (核保預警線為 65%)
    - 營業活動現金流：{data['net_cash_flow']}
    - 總資產：{data['total_assets']}

    分析要求：
    1. 評估負債比是否健康。
    2. 根據現金流判斷經營穩定性。
    3. 給予最終核保建議（例如：建議承保、需進一步照會或拒保）。
    """

    response = model.generate_content(prompt)
    return data, response.text

# --- 3. Streamlit 網頁介面 ---

st.set_page_config(page_title="富邦產險 - D&O 財報核保助理", layout="wide")
st.title("📋 D&O 財報自動化與 AI 核保系統")

# 側邊欄：顯示目前資料庫狀態
with st.sidebar:
    st.header("數據管理")
    if st.button("查看目前快取列表"):
        cache_data = supabase.table("agent_financial_cache").select("company_name, period, debt_ratio").execute()
        st.write(pd.DataFrame(cache_data.data))

# 主要區塊：AI 診斷
st.subheader("🤖 AI 核保助理診斷")
target_comp = st.text_input("輸入公司名稱 (例如：旺宏)", placeholder="請輸入公司名稱...")

if st.button("執行 AI 風險評估"):
    if target_comp:
        with st.spinner(f"正在檢索 {target_comp} 的最新財報並進行 AI 分析..."):
            raw_data, analysis = get_ai_analysis(target_comp)
            
            if raw_data:
                # 顯示抓取到的真實數據
                st.success(f"已讀取 {raw_data['company_name']} ({raw_data['period']}) 數據")
                col1, col2, col3 = st.columns(3)
                col1.metric("負債比率", f"{raw_data['debt_ratio']}%")
                col2.metric("現金流", f"{raw_data['net_cash_flow']:,}")
                col3.metric("總資產", f"{raw_data['total_assets']:,}")
                
                # 顯示 AI 評估報告
                st.markdown("---")
                st.markdown("### 📝 Gemini 專家核保意見")
                st.write(analysis)
            else:
                st.error(analysis)
    else:
        st.warning("請先輸入公司名稱。")

# 頁尾資訊
st.markdown("---")
st.caption("本系統數據由 Supabase 提供，AI 分析由 Google Gemini 1.5 Flash 驅動。")
