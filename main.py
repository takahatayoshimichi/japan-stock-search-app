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
        try:
            price_df = render_price_section(settings.ticker, settings.years)
        except Exception as e:
            st.error(f"株価データの取得に失敗しました: {e}")
            price_df = None

    with tabs[1]:
        try:
            current, previous, cur_date, prev_date = render_auto_ingest_section(
                settings.ticker, settings.edinet_api_key or "", price_df
            )
            
            # 財務データがある場合は必ず分析を表示
            if current:
                st.success("✅ 財務データ取得完了 - 分析結果を表示")
                render_quant_tables(current, previous or {})
                
                # 基本情報も表示
                with st.expander("📊 取得された財務データ詳細"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**損益情報**")
                        if current.get("sales"): st.write(f"売上高: {current['sales']:,}百万円")
                        if current.get("op"): st.write(f"営業利益: {current['op']:,}百万円")
                        if current.get("net"): st.write(f"当期純利益: {current['net']:,}百万円")
                        
                    with col2:
                        st.write("**財務状況**")
                        if current.get("assets"): st.write(f"総資産: {current['assets']:,}百万円")
                        if current.get("equity"): st.write(f"純資産: {current['equity']:,}百万円")
                        if current.get("debt"): st.write(f"有利子負債: {current['debt']:,}百万円")
                        
                    if cur_date:
                        st.info(f"データ期間: {cur_date} (前期: {prev_date if prev_date else 'N/A'})")
                
            else:
                st.info("📊 EDINETから自動取得するか、手動入力で分析を開始してください。")
                
                # デモ用のサンプルデータ表示
                with st.expander("💡 デモ: サンプルデータで機能確認"):
                    if st.button("トヨタのサンプルデータで分析デモ", key="demo_data"):
                        # トヨタ自動車の概算データ（デモ用）
                        demo_current = {
                            "sales": 31378000,    # 売上高（百万円）
                            "op": 4568000,        # 営業利益
                            "net": 3094000,       # 当期純利益
                            "assets": 54280000,   # 総資産
                            "equity": 23519000,   # 純資産
                            "debt": 12000000,     # 有利子負債
                            "price": float(price_df["close"].iloc[-1]) if price_df is not None and not price_df.empty else 2840,
                            "ocf": 4500000,       # 営業CF
                            "fcf": 2800000,       # フリーCF
                            "ca": 15000000,       # 流動資産
                            "cl": 8000000,        # 流動負債
                            "cogs": 24000000,     # 売上原価
                            "tl": 30000000,       # 総負債
                            "tax": 0.30, "wacc": 0.10
                        }
                        st.write("**デモデータでの分析結果:**")
                        render_quant_tables(demo_current, {})
                        st.info("💡 これはデモ用の概算データです。実際のEDINET連携には有効なAPIキーが必要です。")
                
        except Exception as e:
            st.error(f"財務データの処理に失敗しました: {e}")
            import traceback
            st.code(traceback.format_exc())

    with tabs[2]:
        try:
            st.subheader("簡易レポート（Markdown）")
            md = st.text_area("追記メモ（任意）", height=180, placeholder="所感や注記事項をメモ…", key="report_memo")
            if st.button("Markdownをダウンロード", key="download_report"):
                import datetime as dt
                content = f"# 企業分析レポート\n- 銘柄: {settings.ticker}\n- 期間: 過去{settings.years}年\n\n{md}\n"
                st.download_button("Download report.md",
                                   data=content.encode("utf-8"),
                                   file_name=f"report_{settings.ticker}_{dt.date.today()}.md",
                                   mime="text/markdown",
                                   key="download_report_btn")
        except Exception as e:
            st.error(f"レポート機能でエラーが発生しました: {e}")

if __name__ == "__main__":
    main()