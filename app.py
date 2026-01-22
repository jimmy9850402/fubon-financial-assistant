import streamlit as st
import pandas as pd
from supabase import create_client

# =============================================================================
# 🛡️ 富邦產險 - 雲端資料庫診斷助理
# =============================================================================

st.set_page_config(page_title="富邦產險 | 雲端資料診斷", page_icon="📈", layout="wide")

# Supabase 連線資訊
SUPABASE_URL = "https://cemnzictjgunjyktrruc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNlbW56aWN0amd1bmp5a3RycnVjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTA1MTU2MSwiZXhwIjoyMDg0NjI3NTYxfQ.LScr9qrJV7EcjTxp_f47r6-PLMsxz-mJTTblL4ZTmbs"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.title("🛡️ 富邦產險 - 雲端資料庫診斷助理")
st.markdown(f"當前連線專案 ID: `cemnzictjgunjyktrruc`")

with st.sidebar:
    st.header("⚙️ 診斷設定")
    target_table = st.text_input("請輸入要檢查的 Table 名稱", value="financial_reports")
    diag_btn = st.button("🔍 開始診斷")

if diag_btn:
    try:
        response = supabase.table(target_table).select("*").execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            st.subheader(f"--- 資料表: {target_table} ---")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**欄位名稱:**")
                st.code(list(df.columns))
            with col2:
                st.write("**資料型別:**")
                st.write(df.dtypes.astype(str))

            st.metric("總資料筆數", f"{len(df):,}")
            
            st.divider()
            st.subheader("🧪 隨機抽樣驗證")
            st.dataframe(df.sample(min(3, len(df))), use_container_width=True)
            
            st.divider()
            st.subheader("📄 完整雲端數據一覽")
            st.dataframe(df)
            st.success("✅ 連線診斷成功！")
        else:
            st.warning("📭 雲端資料庫中目前查無此資料表，或該表尚無任何內容。")
    except Exception as e:
        st.error(f"⚠️ 讀取失敗: {e}")

st.markdown("---")
st.caption("⚠️ 注意事項：此工具使用 Service Role Key 具備最高權限。")
