import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client
import google.generativeai as genai

# --- 1. 基礎設定 ---
st.set_page_config(page_title="富邦產險 | D&O 核保助手 Pro", layout="wide")

# 金鑰管理 (請替換為您新申請的 API Key)
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "您的新_SUPABASE_KEY"
GEMINI_API_KEY = "您的新_GEMINI_API_KEY"

# 連線初始化
CLEAN_SUPABASE_KEY = SUPABASE_KEY.strip().encode('ascii', 'ignore').decode('ascii')
supabase = create_client(SUPABASE_URL, CLEAN_SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. 升級版數據抓取函數 ---
def fetch_analysis_report(symbol):
    """抓取並運算 CMCR 關鍵指標：FFO, EBITDA, 有息負債, FOCF"""
    try:
        ticker = yf.Ticker(symbol)
        # 抓取財報三表 (季度)
        q_inc = ticker.quarterly_financials
        q_bal = ticker.quarterly_balance_sheet
        q_cf = ticker.quarterly_cashflow

        if q_inc.empty: return None

        # 定義指標名稱
        metrics = [
            "營業收入", "總資產", "負債比", "流動資產", "流動負債", 
            "營業活動淨現金流", "資本支出", "稅後淨利", "利息支出", 
            "折舊與攤銷", "有息負債(DEBT)", "EBITDA", "FFO", "FOCF"
        ]
        result_df = pd.DataFrame({"項目": metrics})

        for col in q_inc.columns[:5]:
            label = f"{col.year}-Q{((col.month-1)//3)+1}"
            
            # A. 基礎項
            rev = q_inc.loc["Total Revenue", col] if "Total Revenue" in q_inc.index else 0
            assets = q_bal.loc["Total Assets", col] if "Total Assets" in q_bal.index else 0
            liab = q_bal.loc["Total Liabilities Net Minority Interest", col] if "Total Liabilities Net Minority Interest" in q_bal.index else 0
            c_assets = q_bal.loc["Current Assets", col] if "Current Assets" in q_bal.index else 0
            c_liab = q_bal.loc["Current Liabilities", col] if "Current Liabilities" in q_bal.index else 0
            ocf = q_cf.loc["Operating Cash Flow", col] if "Operating Cash Flow" in q_cf.index else 0
            capex = q_cf.loc["Capital Expenditure", col] if "Capital Expenditure" in q_cf.index else 0
            net_income = q_inc.loc["Net Income", col] if "Net Income" in q_inc.index else 0
            interest = q_inc.loc["Interest Expense", col] if "Interest Expense" in q_inc.index else 0
            depreciation = q_cf.loc["Depreciation And Amortization", col] if "Depreciation And Amortization" in q_cf.index else 0
            ebit = q_inc.loc["EBIT", col] if "EBIT" in q_inc.index else 0

            # B. 運算項 (依照使用者公式)
            # 有息負債 = 短期借款 + 長期借款 + 應付債券
            st_debt = q_bal.loc["Short Term Debt", col] if "Short Term Debt" in q_bal.index else 0
            lt_debt = q_bal.loc["Long Term Debt", col] if "Long Term Debt" in q_bal.index else 0
            debt = st_debt + lt_debt
            
            ebitda = ebit + depreciation
            ffo = net_income + depreciation
            focf = ocf + capex  # capex 通常在 yf 是負值，所以用加的
            d_ratio = (liab/assets)*100 if assets > 0 else 0

            result_df[label] = [
                rev, assets, d_ratio, c_assets, c_liab, 
                ocf, capex, net_income, interest, 
                depreciation, debt, ebitda, ffo, focf
            ]
        return result_df
    except Exception as e:
        st.error(f"數據解析錯誤: {e}")
        return None

# --- 3. 整合嚴格 Prompt 的 AI 函數 ---
def get_ai_opinion(company_name, report_df):
    latest_col = report_df.columns[1] 
    d = report_df.set_index("項目")[latest_col] # 轉為易讀格式
    
    prompt = f"""
    你是富邦產險 D&O 核保專家。針對【{company_name}】進行 CMCR 精確運算。
    
    最新數據摘要 (百萬元)：
    - 營收: {d['營業收入']:,.0f}
    - 總資產: {d['總資產']:,.0f}
    - 負債比: {d['負債比']:.2f}%
    - EBITDA: {d['EBITDA']:,.0f}
    - 有息負債(DEBT): {d['有息負債(DEBT)']:,.0f}
    - FFO: {d['FFO']:,.0f}
    - 營業現金流(CFO): {d['營業活動淨現金流']:,.0f}
    - 自由現金流(FOCF): {d['FOCF']:,.0f}

    請嚴格執行：
    1. Pre-check List 檢核 (✔/❌)。
    2. Group A 判定 (營收是否滿 150 億？負債比是否低於 80%？)。
    3. 計算 CMCR 分數 (1-9分)：
       - FFO/DEBT (30%)
       - DEBT/EBITDA (30%)
       - CFO/DEBT (15%)
       - FOCF/DEBT (15%)
       - EBITDA/Interest (10%)
    4. 輸出核保結論 (✅本案符合 Group A... 或 ❌本案不符合...)
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 運算失敗: {e}"

# --- 4. UI 介面 ---
st.title("🛡️ 富邦產險 - D&O 企業財報核保助手 Pro")

user_query = st.text_input("輸入公司名稱", value="旺宏")
if st.button("🚀 生成完整核保報告"):
    # 邏輯：find_stock_code -> fetch_analysis_report -> get_ai_opinion
    # (此處省略 find_stock_code 函數，請延用之前的版本)
    target_symbol = "2337.TW" # 範例代碼
    report = fetch_analysis_report(target_symbol)
    if report is not None:
        st.dataframe(report.style.format(precision=0), use_container_width=True)
        st.markdown("---")
        st.subheader("🤖 CMCR 專家系統核保報告")
        st.write(get_ai_opinion(user_query, report))
