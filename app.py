import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client
from openai import OpenAI  # 匯入 OpenAI 客戶端

# --- 1. 基礎連線設定 ---
st.set_page_config(page_title="富邦產險 | 企業財報核保助手", layout="wide")

# 配置金鑰 (請確保 Key 正確，建議正式環境使用 st.secrets)
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
OPENAI_API_KEY = "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"

# 清理 Supabase Key 以避免 UnicodeEncodeError
CLEAN_SUPABASE_KEY = SUPABASE_KEY.strip().encode('ascii', 'ignore').decode('ascii')
supabase = create_client(SUPABASE_URL, CLEAN_SUPABASE_KEY)

# 初始化 OpenAI 客戶端
client = OpenAI(api_key=OPENAI_API_KEY)

# --- 2. 輔助工具函數 ---

def find_stock_code(query):
    """從資料庫搜尋代碼"""
    if query.isdigit():
        return f"{query}.TW"
    try:
        res = supabase.table("stock_isin_list").select("code, name").ilike("name", f"%{query}%").execute()
        if res.data:
            for item in res.data:
                if item['name'] == query:
                    return f"{item['code']}.TW"
            return f"{res.data[0]['code']}.TW"
    except: return None

def fetch_analysis_report(symbol):
    """抓取財報數據"""
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
    """呼叫 OpenAI GPT-4o 進行核保診斷"""
    latest_col = report_df.columns[1] 
    latest_data = report_df[latest_col].values
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # 使用最穩定的 GPT-4o 模型
            messages=[
                {"role": "system", "content": "你是一位富邦產險的 D&O (董監事責任險) 核保專家。"},
                {"role": "user", "content": f"""
                    請評估【{company_name}】最新財報數據的風險：
                    - 負債比率：{latest_data[2]:.2f}% (預警線 65%)
                    - 營業活動現金流：{latest_data[3]:,.0f}
                    請針對財務穩健度提供專業的承保建議。
                """}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ OpenAI 呼叫失敗: {e}"

# --- 3. UI 介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手 (OpenAI 版)")

with st.sidebar:
    st.header("🔍 數據檢索")
    user_query = st.text_input("輸入公司名稱或代碼", value="旺宏")
    search_btn = st.button("🚀 生成報告與 AI 分析")

if search_btn and user_query:
    with st.spinner(f"正在串接 OpenAI 解析 '{user_query}' 數據..."):
        target_symbol = find_stock_code(user_query)
        if target_symbol:
            report = fetch_analysis_report(target_symbol)
            if report is not None:
                st.success(f"標的確認: {user_query} ({target_symbol})")
                
                # 資料顯示格式化
                display_df = report.copy()
                for col in display_df.columns[1:]:
                    display_df[col] = display_df.apply(lambda x: f"{x[col]:,.2f}%" if x['項目'] == "負債比" else f"{x[col]:,.0f}", axis=1)
                st.dataframe(display_df, use_container_width=True)
                
                # AI 分析區塊
                st.markdown("---")
                st.subheader("🤖 GPT-4o 核保專家診斷")
                opinion = get_ai_opinion(user_query, report)
                st.info(opinion)
            else:
                st.error("無法抓取財報數據。")
        else:
            st.error("查無此公司名稱或代碼。")
