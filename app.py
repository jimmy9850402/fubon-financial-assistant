import streamlit as st
import pandas as pd
from supabase import create_client
import os

# =============================================================================
# 🛡️ 富邦產險 - 雲端財報助理 (Supabase 版)
# =============================================================================

# 設定網頁配置
st.set_page_config(page_title="富邦產險 | 雲端財報助理", page_icon="🛡️", layout="wide")

# --- 1. Supabase 連線設定 ---
# 密碼外面需要有引號 ""
SUPABASE_URL = "https://你的ProjectRef.supabase.co" 
SUPABASE_KEY = "你的ServiceRoleKey" 

@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"❌ Supabase 連線失敗: {e}")
        return None

supabase = init_connection()

# --- 2. 核心功能：從雲端檢索財報 ---
def get_financial_report(stock_name):
    try:
        # 這裡假設您的 Table 名稱為 'financial_reports'
        # 使用 ilike 進行公司名稱模糊搜尋
        query = supabase.table("financial_reports") \
            .select("*") \
            .ilike("company_name", f"%{stock_name}%") \
            .order("year", desc=True) \
            .order("season", desc=True) \
            .execute()
        
        return pd.DataFrame(query.data)
    except Exception as e:
        st.error(f"⚠️ 讀取雲端資料失敗: {e}")
        return pd.DataFrame()

# --- 3. UI 介面設計 ---
st.title("🛡️ 富邦產險 - 企業財報診斷工具")
st.markdown("本工具對接 **Supabase 雲端資料庫**，提供同仁檢視已爬取的企業財報結構與數據。")

# 側邊欄查詢
with st.sidebar:
    st.header("🔍 查詢設定")
    search_query = st.text_input("請輸入公司名稱 (例如: 富邦金, 台積電)", placeholder="輸入關鍵字...")
    search_btn = st.button("🚀 執行檢索")

if search_btn and search_query:
    with st.spinner(f'正在從雲端調閱 {search_query} 的資料...'):
        df = get_financial_report(search_query)
        
        if not df.empty:
            st.success(f"📋 已找到與「{search_query}」相關的資料，共 {len(df)} 筆。")
            
            # --- 診斷功能：檢視資料表結構 ---
            st.subheader("📁 資料表結構診斷")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**欄位清單：**")
                st.write(list(df.columns))
            with col2:
                st.write("**資料型別概況：**")
                st.write(df.dtypes.astype(str))

            # --- 抽樣驗證 ---
            st.divider()
            st.subheader("🧪 隨機抽樣驗證 (Random Sample)")
            sample_size = min(3, len(df))
            st.dataframe(df.sample(sample_size), use_container_width=True)

            # --- 完整數據匯出 ---
            st.divider()
            st.subheader("📄 完整歷年財報數據")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此報表 (CSV)", csv, f"{search_query}_cloud_report.csv", "text/csv")
            
        else:
            st.warning(f"📭 雲端資料庫中目前查無「{search_query}」的紀錄。")
            st.info("💡 提示：請確認爬蟲腳本是否已將資料成功寫入 Supabase。")

elif not search_query:
    st.info("👈 請在左側輸入公司名稱開始診斷資料。")

st.markdown("---")
st.caption("🔒 安全聲明：本工具使用 Service Role Key 進行唯讀/寫入操作，請確保 API Key 不外流。")
