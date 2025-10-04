"""
このファイルは、Webアプリのメイン処理が記述されたファイルです。
"""

# main.py
import streamlit as st
from initialize import init_page, init_env, init_sidebar
from components import render_price_section, render_auto_ingest_section, render_quant_tables

def main():
    init_page()
    env_defaults = init_env()
    settings = init_sidebar(env_defaults)

    tabs = st.tabs(["Overview", "Financials (Auto)", "Report"])

    with tabs[0]:
        price_df = render_price_section(settings.ticker, settings.years)

    with tabs[1]:
        current, previous, cur_date, prev_date = render_auto_ingest_section(
            settings.ticker, settings.edinet_api_key or "", price_df
        )
        if current:
            render_quant_tables(current, previous or {})
        else:
            st.info("上のボタンでEDINETから自動取得してください。")

    with tabs[2]:
        st.subheader("簡易レポート（Markdown）")
        md = st.text_area("追記メモ（任意）", height=180, placeholder="所感や注記事項をメモ…")
        if st.button("Markdownをダウンロード"):
            import datetime as dt
            content = f"# 企業分析レポート\n- 銘柄: {settings.ticker}\n- 期間: 過去{settings.years}年\n\n{md}\n"
            st.download_button("Download report.md",
                               data=content.encode("utf-8"),
                               file_name=f"report_{settings.ticker}_{dt.date.today()}.md",
                               mime="text/markdown")

if __name__ == "__main__":
    main()