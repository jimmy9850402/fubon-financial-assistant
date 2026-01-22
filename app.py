import streamlit as st
import pandas as pd
from supabase import create_client
import os

# =============================================================================
# 🔍 [雲端診斷工具] Supabase 資料庫：檢視表結構 + 隨機抽樣資料
# =============================================================================
# 🎯 適用對象：富邦產險同仁核對雲端數據正確性
# =============================================================================

# 設定網頁配置
st.set_page_config(page_title="富邦產險 | 雲端資料診斷", page_icon="📈", layout="wide")

# --- 1. Supabase 連線資訊 (已填入您的專屬 ID 與 Key) ---
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"

@st.cache_resource
def init_supabase():
    # 使用引號將您的 Project ID 與密碼包覆以建立連線
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# --- 2. 核心功能：讀取並診斷資料表 ---
def diagnose_supabase_table(table_name):
    try:
        # 從雲端獲取所有資料
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        st.error(f"⚠️ 讀取資料表 '{table_name}' 失敗: {e}")
        return pd.DataFrame()

# --- 3. Streamlit 介面 ---
st.title("🛡️ 富邦產險 - 雲端資料庫診斷助理")
st.markdown(f"當前連線專案 ID: `cemnzictjgunjyktrruc`")

# 側邊欄：輸入要檢查的 Table 名稱
with st.sidebar:
    st.header("⚙️ 診斷設定")
    target_table = st.text_input("請輸入要檢查的 Table 名稱", value="financial_reports")
    diag_btn = st.button("🔍 開始診斷")

if diag_btn:
    with st.spinner(f"正在連線至雲端資料庫檢測表: {target_table}..."):
        df = diagnose_supabase_table(target_table)
        
        if not df.empty:
            print(f"📋 資料表 '{target_table}' 診斷結果：") # 同時在後台輸出
            
            # 1. 顯示欄位資訊與型別
            st.subheader(f"--- 資料表: {target_table} ---")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**欄位名稱:**")
                st.code(list(df.columns))
            with col2:
                st.write("**資料型別 (Pandas dtype):**")
                st.write(df.dtypes.astype(str))

            # 2. 顯示總筆數 (格式化千分位)
            total_count = len(df)
            st.metric("總資料筆數", f"{total_count:,}")

            # 3. 隨機抽樣資料 (原本腳本之亮點功能)
            st.divider()
            st.subheader("🧪 隨機抽樣驗證 (快速核對內容)")
            sample_size = min(3, total_count)
            # 使用隨機抽樣模擬 SQLite 的 ORDER BY RANDOM()
            df_sample = df.sample(sample_size)
            st.write(f"隨機抽取 {sample_size} 筆樣本：")
            st.dataframe(df_sample, use_container_width=True)

            # 4. 提供完整檢視
            st.divider()
            st.subheader("📄 完整雲端數據一覽")
            st.dataframe(df)
            
            st.success("✅ 資料庫檢查完成。")
        else:
            st.warning(f"📭 雲端資料庫中目前查無此資料表，或該表尚無任何內容。")

# 頁尾說明
st.markdown("---")
st.caption("⚠️ 注意事項：此工具使用 Service Role Key 具備最高權限，請確保不將此網頁網址公開。")
