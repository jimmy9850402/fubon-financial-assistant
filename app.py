import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client
import google.generativeai as genai

# --- 1. 基礎連線設定 ---
st.set_page_config(page_title="富邦產險 | 企業財報核保助手", layout="wide")

# 配置金鑰 (建議正式環境改用 st.secrets)
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"
GEMINI_API_KEY = "AIzaSyB2BKcuYjsr7LWhv9JTQcqOM-LvVKFEEVQ"

# 修復 UnicodeEncodeError: 清理 Key
CLEAN_SUPABASE_KEY = SUPABASE_KEY.strip().encode('ascii', 'ignore').decode('ascii')
supabase = create_client(SUPABASE_URL, CLEAN_SUPABASE_KEY)

# 初始化 Gemini：修復 404 錯誤，使用完整路徑
genai.configure(api_key=GEMINI_API_KEY)
# 使用 gemini-1.5-flash-latest 或 models/gemini-1.5-flash 以確保路徑正確
model = genai.GenerativeModel('gemini-1.5-flash-latest')

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
    """從資料庫搜尋名稱對應的代碼"""
    if query.isdigit():
        return f"{query}.TW"
    try:
        res = supabase.table("stock_isin_list").select("code, name").ilike("name", f"%{query}%").execute()
        if res.data:
            for item in res.data:
                if item['name'] == query:
                    return f"{item['code']}.TW"
            return f"{res.data[0]['code']}.TW"
    except Exception as e:
        st.error(f"資料庫查詢異常: {e}")
    return None

def fetch_analysis_report(symbol):
    """執行財報抓取"""
    try:
        ticker = yf.Ticker(symbol)
        q_inc, q_bal, q_cf = ticker.quarterly_financials, ticker.quarterly_balance_sheet, ticker.quarterly_cashflow
        fy_inc, fy_bal, fy_cf = ticker.financials, ticker.balance_sheet, ticker.cashflow

        if q_inc.empty: return None

        metrics = ["營業收入", "總資產", "負債比", "流動資產", "流動負債", "營業活動淨現金流"]
        result_df = pd.DataFrame({"項目": metrics})

        # 處理季度數據
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

        return result_df
    except: return None

def get_ai_opinion(company_name, report_df):
    """將真實數據餵給 Gemini 進行專業分析"""
    # 取得最新一列數據
    latest_col = report_df.columns[1] 
    latest_data = report_df[latest_col].values
    
    # 建立結合 D&O 核保邏輯的 Prompt
    prompt = f"""
    你是一位富邦產險的 D&O (董監事責任險) 核保專家。
    請針對【{company_name}】最新一季 ({latest_col}) 的財務數據進行風險評估：
    - 負債比率：{latest_data[2]:.2f}% (核保預警線為 65%)
    - 營業活動現金流：{latest_data[5]:,.0f}
    - 總資產：{latest_data[1]:,.0f}

    分析要求：
    1. 判斷負債比是否低於 65% 的核保門檻。
    2. 根據現金流判斷公司短期內是否有經營危機。
    3. 給予專業核保意見：建議承保、需進一步照會或加費承保。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 分析失敗 (404/500): {e}。請檢查模型名稱或 API Key 狀態。"

# --- 3. UI 介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報核保助手")
st.markdown("輸入 **公司名稱** (例: 旺宏) 產出對照表並由 **Gemini AI** 進行風險診斷。")

with st.sidebar:
    st.header("🔍 數據檢索")
    user_query = st.text_input("輸入名稱或代碼", value="旺宏")
    search_btn = st.button("🚀 生成核保報告")

if search_btn and user_query:
    with st.spinner(f"正在分析 '{user_query}' 並串接 Gemini AI 專家系統..."):
        target_symbol = find_stock_code(user_query)
        
        if target_symbol:
            report = fetch_analysis_report(target_symbol)
            if report is not None:
                st.success(f"✅ 已識別標的: {user_query} ({target_symbol})")
                
                # 表格美化顯示
                display_df = report.copy()
                for col in display_df.columns[1:]:
                    display_df[col] = display_df.apply(
                        lambda x: f"{x[col]:,.2f}%" if x['項目'] == "負債比" else f"{x[col]:,.0f}", axis=1
                    )
                st.dataframe(display_df, use_container_width=True)
                
                # --- AI 核保分析區塊 ---
                st.markdown("---")
                st.subheader("🤖 Gemini AI 專家診斷意見")
                opinion = get_ai_opinion(user_query, report)
                st.info(opinion) # 使用藍色區塊顯示建議
                
                # 下載報告
                csv = display_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載此報表 (CSV)", csv, f"{user_query}_report.csv")
            else:
                st.error("❌ 獲取財報失敗，請確認該公司是否有公開財報。")
        else:
            st.error(f"❌ 資料庫查無 '{user_query}'。")
