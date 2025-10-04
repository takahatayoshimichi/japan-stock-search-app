"""
このファイルは、最初の画面読み込み時にのみ実行される初期化処理が記述されたファイルです。
"""

# initialize.py
import os
import streamlit as st
from dotenv import load_dotenv
from constants import APP_TITLE, APP_SUBTITLE, DEFAULT_TICKER, DEFAULT_YEARS, Settings

def init_page():
    st.set_page_config(page_title=APP_TITLE, page_icon="📈", layout="wide")
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)
    
    # セッション状態の初期化
    if 'financial_data' not in st.session_state:
        st.session_state.financial_data = None
    if 'price_data' not in st.session_state:
        st.session_state.price_data = None

def init_env() -> dict:
    load_dotenv()
    return dict(
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        EDINET_API_KEY=os.getenv("EDINET_API_KEY"),
    )

def init_sidebar(env_defaults: dict) -> Settings:
    with st.sidebar:
        st.header("設定")
        ticker = st.text_input("銘柄コード（yfinance形式）", DEFAULT_TICKER)
        years = st.slider("期間（年）", 1, 10, DEFAULT_YEARS)

        # APIキーの状態表示（値は表示しない）
        st.divider()
        st.subheader("API接続状況")
        
        openai_status = "✅ 設定済み" if env_defaults.get("OPENAI_API_KEY") else "❌ 未設定"
        edinet_status = "✅ 設定済み" if env_defaults.get("EDINET_API_KEY") else "❌ 未設定"
        
        st.write(f"OpenAI API: {openai_status}")
        st.write(f"EDINET API: {edinet_status}")
        
        if not env_defaults.get("EDINET_API_KEY"):
            st.warning("EDINET API キーが設定されていません。財務データの自動取得機能が利用できません。")

    return Settings(
        ticker=ticker.strip(),
        years=int(years),
        openai_api_key=env_defaults.get("OPENAI_API_KEY"),
        edinet_api_key=env_defaults.get("EDINET_API_KEY"),
    )