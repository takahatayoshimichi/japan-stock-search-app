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

        st.divider()
        st.subheader(".env からのキー（表示のみ・必要なら上書き可）")
        openai_api_key = st.text_input("OpenAI API Key", type="password",
                                       value=env_defaults.get("OPENAI_API_KEY") or "")
        edinet_api_key = st.text_input("EDINET API Key", type="password",
                                       value=env_defaults.get("EDINET_API_KEY") or "")

    return Settings(
        ticker=ticker.strip(),
        years=int(years),
        openai_api_key=openai_api_key or None,
        edinet_api_key=edinet_api_key or None,
    )