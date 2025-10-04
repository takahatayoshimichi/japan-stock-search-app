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
    
    with st.spinner(f"株価データを取得中: {ticker}"):
        df = get_price_data(ticker, years)
    
    if df is None or df.empty:
        st.error("📉 株価データが取得できませんでした")
        
        with st.expander("💡 トラブルシューティング"):
            st.write("**よくある原因と解決策:**")
            st.write("1. **ティッカーシンボルの形式**")
            st.write("   - 日本株: `7203.T` (トヨタ), `9984.T` (ソフトバンク)")
            st.write("   - 米国株: `AAPL`, `MSFT`, `GOOGL`")
            st.write("   - 指数: `^N225` (日経平均), `^GSPC` (S&P500)")
            st.write("")
            st.write("2. **推奨テスト用ティッカー**")
            st.code("7203.T  # トヨタ自動車\n9984.T  # ソフトバンクG\n^N225   # 日経平均\nAAPL    # Apple")
            st.write("")
            st.write("3. **ネットワーク問題**")
            st.write("   - 数秒待ってから再試行")
            st.write("   - Yahoo Financeのレート制限の可能性")
            st.write("")
            st.info("💡 4桁の数字のみ入力した場合、自動的に `.T` を追加して日本株として検索します")
        
        return None
    
    # グラフ表示
    c1, c2 = st.columns([3,2])
    with c1:
        if 'close' in df.columns:
            st.line_chart(df.set_index("date")[["close"]], height=280)
        else:
            st.warning("終値データが見つかりません")
    
    with c2:
        if 'volume' in df.columns:
            st.bar_chart(df.set_index("date")[["volume"]], height=280)
        else:
            st.warning("出来高データが見つかりません")
    
    # 現在の株価情報
    if 'close' in df.columns and len(df) > 0:
        latest_close = df['close'].iloc[-1]
        latest_date = df['date'].iloc[-1]
        st.metric(
            "直近終値", 
            f"{latest_close:,.2f}",
            help=f"データ日付: {latest_date}"
        )
        
        # データ統計
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("期間高値", f"{df['close'].max():,.2f}")
        with col2:
            st.metric("期間安値", f"{df['close'].min():,.2f}")
        with col3:
            total_days = len(df)
            st.metric("データ期間", f"{total_days}日")
    
    return df

def render_auto_ingest_section(ticker: str, edinet_api_key: str, price_df: pd.DataFrame):
    st.subheader("2) EDINET 自動取り込み（手入力なし）")
    st.caption("直近の有報/四半期/半期を自動検出→XBRLから主要KPIを抽出します。")
    
    # APIキーの有効性チェック
    if not edinet_api_key:
        st.info("EDINET API Key を .env に設定してください。")
        return None, None, None, None
    
    # APIキー検証
    from utils import validate_edinet_api_key
    is_valid, message = validate_edinet_api_key(edinet_api_key)
    
    if not is_valid:
        st.error(f"❌ EDINET APIキーの問題: {message}")
        
        with st.expander("🔧 EDINET APIキーの解決方法"):
            st.write("**現在のAPIキーは無効です。以下の手順で解決してください：**")
            st.write("")
            st.write("1. **EDINET公式サイトにアクセス**")
            st.write("   - https://disclosure2.edinet-fsa.go.jp/")
            st.write("   - 「API利用」→「ログイン」")
            st.write("")
            st.write("2. **APIキーの状態を確認**")
            st.write("   - マイページ→「API Key管理」")
            st.write("   - 現在のAPIキーの有効期限を確認")
            st.write("   - 必要に応じて新しいAPIキーを生成")
            st.write("")
            st.write("3. **新しいAPIキーを設定**")
            st.code("EDINET_API_KEY=新しい32文字のAPIキー")
            st.write("   - `.env` ファイルを更新")
            st.write("   - アプリケーションを再起動")
            st.write("")
            st.info("💡 **一時的な解決策**: 株価データのみで分析を続行することもできます")
        
        # 手動入力の代替案を提供
        st.write("---")
        st.write("**代替案: 手動で財務データを入力**")
        
        with st.expander("📝 手動入力で分析を続行"):
            st.write("EDINETが利用できない間、以下の数値を手動入力して分析できます：")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**売上高・利益（百万円）**")
                manual_sales = st.number_input("売上高", value=0, min_value=0, key="manual_sales")
                manual_op = st.number_input("営業利益", value=0, key="manual_op")
                manual_net = st.number_input("当期純利益", value=0, key="manual_net")
                
            with col2:
                st.write("**資産・負債（百万円）**")
                manual_assets = st.number_input("総資産", value=0, min_value=0, key="manual_assets")
                manual_equity = st.number_input("純資産", value=0, key="manual_equity")
                manual_debt = st.number_input("有利子負債", value=0, key="manual_debt")
            
            col3, col4 = st.columns(2)
            with col3:
                st.write("**キャッシュフロー（百万円）**")
                manual_ocf = st.number_input("営業CF", value=0, key="manual_ocf")
                manual_fcf = st.number_input("フリーCF", value=0, key="manual_fcf")
            
            with col4:
                st.write("**その他（百万円）**")
                manual_ca = st.number_input("流動資産", value=0, key="manual_ca")
                manual_cl = st.number_input("流動負債", value=0, key="manual_cl")
                
            if st.button("手動データで分析実行", key="manual_analysis"):
                if manual_sales > 0 and manual_assets > 0:
                    current = {
                        "sales": manual_sales, 
                        "op": manual_op, 
                        "net": manual_net,
                        "assets": manual_assets, 
                        "equity": manual_equity, 
                        "debt": manual_debt,
                        "ocf": manual_ocf,
                        "fcf": manual_fcf,
                        "ca": manual_ca,
                        "cl": manual_cl,
                        "price": float(price_df["close"].iloc[-1]) if price_df is not None and not price_df.empty else None,
                        "cogs": None,  # 売上原価
                        "ord": None,   # 経常利益
                        "inv": None,   # 棚卸資産
                        "tl": manual_debt + manual_equity,  # 総負債+純資産=総資産
                        "cash": None,  # 現金
                        "ar": None,    # 売掛金
                        "stinv": None, # 短期投資
                        "invest": None, # 長期投資
                        "ppe": None,   # 有形固定資産
                        "intan": None, # 無形固定資産
                        "shares": None, # 発行済株式数
                        "ebitda": None, # EBITDA
                        "tax": 0.30,   # 税率
                        "wacc": 0.10,  # WACC
                    }
                    
                    st.success("✅ 手動データで分析を実行します")
                    
                    # 即座に分析結果を表示
                    st.markdown("### 📊 分析結果（手動入力データ）")
                    from utils import calc_health, calc_profitability, calc_growth, calc_asset_value, calc_income_value, calc_price_metrics
                    
                    # 健全性分析
                    st.markdown("#### 健全性")
                    st.dataframe(calc_health(current), use_container_width=True, hide_index=True)
                    
                    # 収益性分析
                    st.markdown("#### 収益性")
                    st.dataframe(calc_profitability(current), use_container_width=True, hide_index=True)
                    
                    # 成長性分析
                    st.markdown("#### 成長性")
                    st.dataframe(calc_growth(current, {}), use_container_width=True, hide_index=True)
                    
                    # 企業価値
                    st.markdown("#### 企業価値（資産/収益）")
                    av = calc_asset_value(current)
                    iv = calc_income_value(current)
                    value_metrics = {
                        "修正資産合計": f"{av['adjusted_assets']:,.0f}",
                        "清算価値": f"{av['liquidation_value']:,.0f}",
                        "収益バリュー（弱気/簡易）": f"{iv['weak_simple']:,.0f}",
                        "収益バリュー（強気/簡易）": f"{iv['strong_simple']:,.0f}",
                        "正統DCF（弱気）": f"{iv['weak_dcf']:,.0f}",
                        "正統DCF（強気）": f"{iv['strong_dcf']:,.0f}",
                    }
                    st.json(value_metrics)
                    
                    # 株価指標
                    st.markdown("#### 株価指標")
                    st.dataframe(calc_price_metrics(current, {}), use_container_width=True, hide_index=True)
                    
                    return current, {}, "手動入力", "N/A"
                else:
                    st.warning("売上高と総資産は必須項目です")
        
        # デバッグ用の情報は削除
        return None, None, None, None
    
    # APIキーが有効な場合は通常の処理
    col1, col2 = st.columns([2, 1])
    
    with col1:
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
                        st.write("1. 以下の銘柄で試してみる:")
                        st.write("   - 7203.T (トヨタ自動車)")
                        st.write("   - 9984.T (ソフトバンクグループ)")
                        st.write("   - 8306.T (三菱UFJフィナンシャル・グループ)")
                        st.write("   - 4519.T (中外製薬)")
                        st.write("2. 銘柄コードを4桁で入力してみる（例: 7203）")
                        st.write("3. 数日後に再度試す")
                    
                    return None, None, None, None
    
    with col2:
        if st.button("🔍 EDINET検索テスト", key="edinet_debug_button"):
            with st.spinner("EDINETのAPIキーを検証中..."):
                try:
                    is_valid_test, message_test = validate_edinet_api_key(edinet_api_key)
                    
                    if is_valid_test:
                        st.success(f"✅ {message_test}")
                        st.write("**EDINET APIキーは正常に動作しています。**")
                        st.write("書類検索を実行してください。")
                    else:
                        st.error(f"❌ {message_test}")
                    
                except Exception as e:
                    st.error(f"検証エラー: {e}")
    
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
