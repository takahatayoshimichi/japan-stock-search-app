"""
このファイルは、画面表示に特化した関数定義のファイルです。
"""

# components.py
import streamlit as st
import pandas as pd

from utils import (
    get_price_data, autofill_financials_from_edinet,
    calc_health, calc_profitability, calc_growth,
    calc_asset_value, calc_income_value, calc_price_metrics,
)

def render_price_section(ticker: str, years: int):
    st.subheader("1) 株価（終値・出来高）")
    df = get_price_data(ticker, years)
    if df is None or df.empty:
        st.warning("株価データが取得できませんでした（例: 7203.T）。")
        return None
    c1, c2 = st.columns([3,2])
    with c1:
        st.line_chart(df.set_index("date")[["close"]], height=280)
    with c2:
        st.bar_chart(df.set_index("date")[["volume"]], height=280)
    st.metric("直近終値", f"{df['close'].iloc[-1]:,.0f}")
    return df

def render_auto_ingest_section(ticker: str, edinet_api_key: str, price_df: pd.DataFrame):
    st.subheader("2) EDINET 自動取り込み（手入力なし）")
    st.caption("直近の有報/四半期/半期を自動検出→XBRLから主要KPIを抽出します。")
    
    if not edinet_api_key:
        st.info("EDINET API Key を .env に設定してください。")
        return None, None, None, None
    
    if st.button("EDINET から自動取得して計算", key="edinet_fetch_button"):
        with st.spinner("EDINET からデータを取得中..."):
            try:
                current, previous, cur_date, prev_date = autofill_financials_from_edinet(ticker, edinet_api_key)
                # 株価を充填
                if price_df is not None and not price_df.empty:
                    current["price"] = float(price_df["close"].iloc[-1])
                st.success(f"取得完了：当期={cur_date} 前期={prev_date}")
                return current, previous, cur_date, prev_date
            except Exception as e:
                error_msg = str(e)
                st.error(f"EDINET 取得エラー:")
                st.code(error_msg)
                
                # ヘルプメッセージ
                with st.expander("💡 トラブルシューティング"):
                    st.write("**よくある原因:**")
                    st.write("- 銘柄コードの形式が正しくない（例: 7203.T が正しい形式）")
                    st.write("- 該当企業の財務報告書がまだ提出されていない")
                    st.write("- EDINET API キーが無効")
                    st.write("- 休日や祝日で新しい書類が提出されていない")
                    st.write("")
                    st.write("**推奨する対処法:**")
                    st.write("1. 銘柄コードを確認する（例: トヨタ = 7203.T）")
                    st.write("2. 他の大手企業で試してみる（例: 9984.T = ソフトバンク）")
                    st.write("3. 数日後に再度試す")
                
                return None, None, None, None
    
    return None, None, None, None

def render_quant_tables(current: dict, previous: dict):
    st.markdown("### 健全性")
    st.dataframe(calc_health(current), use_container_width=True, hide_index=True)
    st.markdown("### 収益性")
    st.dataframe(calc_profitability(current), use_container_width=True, hide_index=True)
    st.markdown("### 成長性")
    st.dataframe(calc_growth(current, previous or {}), use_container_width=True, hide_index=True)

    st.markdown("### 企業価値（資産/収益）")
    av = calc_asset_value(current)
    iv = calc_income_value(current)
    st.write({
        "修正資産合計": f"{av['adjusted_assets']:,.0f}",
        "清算価値": f"{av['liquidation_value']:,.0f}",
        "収益バリュー（弱気/簡易）": f"{iv['weak_simple']:,.0f}",
        "収益バリュー（強気/簡易）": f"{iv['strong_simple']:,.0f}",
        "正統DCF（弱気）": f"{iv['weak_dcf']:,.0f}",
        "正統DCF（強気）": f"{iv['strong_dcf']:,.0f}",
    })

    st.markdown("### 株価指標")
    st.dataframe(calc_price_metrics(current, previous or {}), use_container_width=True, hide_index=True)
