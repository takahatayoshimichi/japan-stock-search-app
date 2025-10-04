"""
このファイルは、画面表示以外の様々な関数定義のファイルです。
"""

# utils.py
import datetime as dt
import io
import zipfile
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import requests
import yfinance as yf
try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    import xml.etree.ElementTree as etree
    LXML_AVAILABLE = False

from constants import (
    EDINET_API, EDINET_FORMS, XBRL_TAGS_LOCAL,
    HEALTH_THRESHOLDS, PROFIT_GUIDE,
    DEFAULT_WACC, BULL_GROWTH, DCF_HORIZON_YEARS,
)

# ---------- 共通 ----------
def _safe_div(a, b):
    try:
        if a is None or b in (None, 0):
            return None
        return float(a) / float(b)
    except Exception:
        return None

def fmt_pct(x, digits=1):
    return None if x is None else f"{x*100:.{digits}f}%"

def fmt_num(x, digits=0):
    return None if x is None else f"{x:,.{digits}f}"

# ---------- 株価 ----------
def get_price_data(ticker: str, years: int) -> pd.DataFrame:
    end = dt.date.today()
    start = end - dt.timedelta(days=365*years + 7)
    df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(), auto_adjust=True)
    if isinstance(df, pd.DataFrame) and not df.empty:
        # MultiIndex列の場合は最初のレベル（Price）を使用
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        # 列名を小文字に変換
        df.columns = [col.lower() for col in df.columns]
    return df

# ---------- EDINET API ----------
def edinet_list_documents(date: str, api_key: str) -> dict:
    params = {"date": date, "type": 2, "Subscription-Key": api_key}
    headers = {"X-API-KEY": api_key}
    r = requests.get(f"{EDINET_API}/documents.json", params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def edinet_pick_latest_doc_debug(results: list, sec_code_4: Optional[str], search_date: str) -> Optional[dict]:
    """デバッグ情報付きのドキュメント検索関数"""
    def match_sec(r):
        if not sec_code_4:
            return True
        
        # より柔軟なマッチング
        doc_sec_code = r.get("secCode") or ""
        doc_title = r.get("title") or ""
        doc_description = r.get("docDescription") or ""
        
        # 検索候補となる文字列
        search_targets = [doc_sec_code, doc_title, doc_description]
        
        # 様々なパターンでマッチング
        patterns_to_check = [
            sec_code_4,                    # 7203
            sec_code_4.zfill(4),          # 7203
            f"{sec_code_4}.T",            # 7203.T
            f"{sec_code_4}0",             # 72030（EDINETで使われることがある）
        ]
        
        for pattern in patterns_to_check:
            for target in search_targets:
                if pattern in target:
                    return True
        
        return False
    
    # 該当する証券コードのドキュメントを全て収集
    matching_docs = [r for r in results if match_sec(r)]
    print(f"日付 {search_date}: 証券コード {sec_code_4} に一致するドキュメント: {len(matching_docs)}件")
    
    # マッチしない場合は、類似する証券コードを表示
    if not matching_docs and sec_code_4:
        similar_codes = set()
        for r in results[:50]:  # 最初の50件をチェック
            sec_code = r.get("secCode")
            if sec_code and sec_code.startswith(sec_code_4[0]):  # 最初の数字が同じもの
                similar_codes.add(sec_code)
        
        if similar_codes:
            print(f"  類似する証券コード例: {sorted(list(similar_codes))[:10]}")
        
        # 企業名での検索も試す
        company_names = {
            "7203": ["トヨタ", "TOYOTA"],
            "8306": ["三菱UFJ", "MUFG"],
            "9984": ["ソフトバンク", "SoftBank"],
            "6758": ["ソニー", "SONY"],
        }
        
        if sec_code_4 in company_names:
            for name in company_names[sec_code_4]:
                name_matches = [r for r in results if name in (r.get("title") or "") or name in (r.get("docDescription") or "")]
                if name_matches:
                    print(f"  企業名 '{name}' での検索: {len(name_matches)}件")
                    # 企業名でマッチした場合は、最初のものを返す
                    for ord_code, form_code, form_name in EDINET_FORMS:
                        tier = [r for r in name_matches if r.get("ordinanceCode")==ord_code and r.get("formCode")==form_code]
                        if tier:
                            tier.sort(key=lambda x: (x.get("submitDateTime") or x.get("periodEnd") or ""), reverse=True)
                            print(f"  企業名で見つかった書類: {form_name} - {tier[0].get('docDescription', 'N/A')}")
                            return tier[0]
    
    if matching_docs:
        for i, doc in enumerate(matching_docs[:3]):  # 最初の3件を表示
            print(f"  {i+1}. {doc.get('docDescription', 'N/A')} (証券コード: {doc.get('secCode', 'N/A')}, 書類コード: {doc.get('formCode', 'N/A')})")
    
    # 優先度順に絞り込み
    for ord_code, form_code, form_name in EDINET_FORMS:
        tier = [r for r in matching_docs if r.get("ordinanceCode")==ord_code and r.get("formCode")==form_code]
        if tier:
            tier.sort(key=lambda x: (x.get("submitDateTime") or x.get("periodEnd") or ""), reverse=True)
            print(f"見つかった書類: {form_name} - {tier[0].get('docDescription', 'N/A')}")
            return tier[0]
    
    return None

def edinet_pick_latest_doc(results: list, sec_code_4: Optional[str]) -> Optional[dict]:
    def match_sec(r):
        if not sec_code_4:
            return True
        
        # より柔軟なマッチング
        doc_sec_code = r.get("secCode") or ""
        doc_title = r.get("title") or ""
        
        # 完全一致
        if doc_sec_code == sec_code_4:
            return True
        
        # タイトルに含まれているかチェック
        if sec_code_4 in doc_title:
            return True
        
        # 証券コードが4桁でない場合の処理
        if len(sec_code_4) < 4:
            padded_code = sec_code_4.zfill(4)
            if doc_sec_code == padded_code or padded_code in doc_title:
                return True
        
        return False
    
    # 優先度順に絞り込み
    all_matches = []
    for ord_code, form_code, form_name in EDINET_FORMS:
        tier = [r for r in results if r.get("ordinanceCode")==ord_code and r.get("formCode")==form_code and match_sec(r)]
        if tier:
            tier.sort(key=lambda x: (x.get("submitDateTime") or x.get("periodEnd") or ""), reverse=True)
            print(f"見つかった書類: {form_name} - {tier[0].get('docDescription', 'N/A')}")
            return tier[0]
    
    # マッチしない場合のデバッグ情報
    if sec_code_4:
        matching_docs = [r for r in results if match_sec(r)]
        print(f"証券コード {sec_code_4} に一致する書類: {len(matching_docs)}件")
        if matching_docs:
            for doc in matching_docs[:3]:  # 最初の3件を表示
                print(f"  - {doc.get('docDescription', 'N/A')} (証券コード: {doc.get('secCode', 'N/A')})")
    
    return None

def edinet_download_zip(doc_id: str, api_key: str) -> bytes:
    params = {"type": 1, "Subscription-Key": api_key}
    headers = {"X-API-KEY": api_key}
    r = requests.get(f"{EDINET_API}/documents/{doc_id}", params=params, headers=headers, timeout=60)
    r.raise_for_status()
    return r.content

# ---------- XBRL（lxmlで軽量パース） ----------
def _localname(tag: str) -> str:
    try:
        if LXML_AVAILABLE:
            return etree.QName(tag).localname
        else:
            # 標準ライブラリでの代替実装
            if "}" in tag:
                return tag.split("}", 1)[1]
            if ":" in tag:
                return tag.split(":", 1)[1]
            return tag
    except Exception:
        # fallback
        if "}" in tag:
            return tag.split("}", 1)[1]
        if ":" in tag:
            return tag.split(":", 1)[1]
        return tag

def _parse_contexts(root) -> Dict[str, dt.date]:
    ns = {}  # 名前空間は localname で見るので未使用
    ctx = {}
    for el in root.iter():
        if _localname(el.tag) != "context":
            continue
        ctx_id = el.get("id")
        if not ctx_id:
            continue
        end_date = None
        for child in el.iter():
            ln = _localname(child.tag)
            if ln == "endDate" or ln == "instant":
                try:
                    end_date = dt.date.fromisoformat((child.text or "").strip()[:10])
                except Exception:
                    pass
        if end_date:
            ctx[ctx_id] = end_date
    return ctx

def parse_xbrl_series(zip_bytes: bytes) -> Dict[str, Dict[dt.date, float]]:
    """
    指定ZIP内のXBRLから、各キー（sales等）→{日付: 値} の辞書を返す
    """
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    xbrl_files = [n for n in zf.namelist() if n.lower().endswith(".xbrl") or n.lower().endswith(".xml")]
    series: Dict[str, Dict[dt.date, float]] = {k: {} for k in XBRL_TAGS_LOCAL.keys()}
    for name in xbrl_files:
        with zf.open(name) as f:
            try:
                if LXML_AVAILABLE:
                    root = etree.parse(f).getroot()
                else:
                    # 標準ライブラリの場合はバイトデータを文字列に変換
                    content = f.read().decode('utf-8', errors='ignore')
                    root = etree.fromstring(content)
            except Exception:
                continue
        ctx = _parse_contexts(root)
        desired = {local for tags in XBRL_TAGS_LOCAL.values() for local in tags}
        # 事実を走査
        for fact in root.iter():
            ln = _localname(fact.tag)
            if ln not in desired:
                continue
            ctx_id = fact.get("contextRef")
            if not ctx_id or ctx_id not in ctx:
                continue
            try:
                val = float((fact.text or "").replace(",", "").strip())
            except Exception:
                continue
            end_date = ctx[ctx_id]
            # どのキーに属するかを逆引き
            for key, tags in XBRL_TAGS_LOCAL.items():
                if ln in tags:
                    # 最新値で上書き（同日複数は最後を優先）
                    series[key][end_date] = val
                    break
    # 合成項目（dateごと）
    # 有利子負債 = 短期 + 長期 + 社債
    for d in set().union(*[set(v.keys()) for v in series.values()]):
        debt = (series.get("debt_short", {}).get(d, 0.0)
                + series.get("debt_long", {}).get(d, 0.0)
                + series.get("bonds", {}).get(d, 0.0))
        if debt != 0.0:
            series.setdefault("debt", {})[d] = debt
        # FCF ≒ OCF - CAPEX
        if d in series.get("ocf", {}) and d in series.get("capex", {}):
            series.setdefault("fcf", {})[d] = series["ocf"][d] - abs(series["capex"][d])
        # EBITDA ≒ 営業利益 + 減価償却
        if d in series.get("op", {}) and d in series.get("dep_amort", {}):
            series.setdefault("ebitda", {})[d] = series["op"][d] + abs(series["dep_amort"][d])
    return series

def pick_current_previous(series: Dict[str, Dict[dt.date, float]]) -> Tuple[Dict, Dict, Optional[dt.date], Optional[dt.date]]:
    # 全キーの「観測日」集合
    dates = set()
    for dmap in series.values():
        dates |= set(dmap.keys())
    if not dates:
        return {}, {}, None, None
    latest = max(dates)
    older = max([d for d in dates if d < latest], default=None)

    def at_date(d: Optional[dt.date]) -> Dict[str, Optional[float]]:
        if d is None:
            return {}
        out = {}
        for k in series.keys():
            out[k] = series[k].get(d)
        return out

    cur = at_date(latest)
    prev = at_date(older)
    return cur, prev, latest, older

def debug_edinet_codes(api_key: str) -> dict:
    """EDINETに存在する証券コードを調査するデバッグ関数"""
    today = dt.date.today()
    all_codes = set()
    matching_companies = []
    
    # 最近の平日を探して調査
    for i in range(1, 10):
        d = (today - dt.timedelta(days=i)).isoformat()
        try:
            idx = edinet_list_documents(d, api_key)
            results = idx.get("results", [])
            
            if results:  # データがある日を見つけた
                print(f"調査日: {d}, ドキュメント数: {len(results)}")
                
                for r in results:
                    sec_code = r.get("secCode")
                    if sec_code:
                        all_codes.add(sec_code)
                    
                    # トヨタ関連を探す
                    title = r.get("title") or ""
                    description = r.get("docDescription") or ""
                    if any(keyword in title.upper() or keyword in description.upper() 
                           for keyword in ["TOYOTA", "トヨタ", "豊田"]):
                        matching_companies.append(f"{description} (証券コード: {sec_code})")
                
                break  # 1日分で十分
                
        except Exception as e:
            print(f"日付 {d} でエラー: {e}")
            continue
    
    return {
        "sample_codes": sorted(list(all_codes)),
        "matching_companies": matching_companies
    }

def autofill_financials_from_edinet(ticker: str, api_key: str) -> Tuple[Dict, Dict, Optional[dt.date], Optional[dt.date]]:
    # 銘柄コードの抽出を改善
    ticker_clean = ticker.split(".")[0]  # "6758.T" -> "6758"
    sec4 = ticker_clean.zfill(4) if ticker_clean.isdigit() else None  # "6758" -> "6758"
    
    today = dt.date.today()
    chosen = None
    search_days = 90  # 3ヶ月まで拡張
    
    # デバッグ情報
    print(f"銘柄コード検索: {ticker} -> {sec4}")
    
    # まず最近の数日間で詳細にチェック
    test_results = []
    for i in range(0, min(10, search_days)):  # 最初の10日をチェック
        d = (today - dt.timedelta(days=i)).isoformat()
        try:
            idx = edinet_list_documents(d, api_key)
            results = idx.get("results", [])
            test_results.append((d, len(results)))
            
            # その日のドキュメントから証券コードをサンプル表示
            if i == 1 and results:  # 2日目（平日の可能性が高い）で詳細表示
                sample_codes = []
                for r in results[:30]:  # 最初の30件をチェック
                    sec_code = r.get("secCode")
                    if sec_code:
                        sample_codes.append(sec_code)
                print(f"日付 {d}: 証券コードの例: {sample_codes[:15]}")
            
            # 実際の検索を実行
            doc = edinet_pick_latest_doc_debug(results, sec4, d)
            if doc:
                chosen = doc
                print(f"ドキュメント発見: {doc.get('docDescription', 'N/A')} (日付: {d})")
                break
                
        except Exception as e:
            print(f"日付 {d} でエラー: {e}")
            continue
    
    # 検索結果のサマリー
    print(f"検索結果サマリー:")
    for date, count in test_results:
        print(f"  {date}: {count}件")
    
    if not chosen:
        # より詳細なエラーメッセージ
        error_msg = f"EDINETで該当ドキュメントが見つかりませんでした。\n"
        error_msg += f"検索した銘柄コード: {sec4}\n"
        error_msg += f"検索期間: {search_days}日間\n"
        error_msg += f"銘柄コードが正しいか確認してください（例: 7203.T）\n\n"
        error_msg += "検索結果:\n"
        for date, count in test_results:
            error_msg += f"  {date}: {count}件のドキュメント\n"
        raise RuntimeError(error_msg)
    
    zipb = edinet_download_zip(chosen["docID"], api_key)
    series = parse_xbrl_series(zipb)
    cur, prev, cur_date, prev_date = pick_current_previous(series)

    # current/previous をアプリ内部のキーに整形
    def build_payload(src: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
        return dict(
            sales=src.get("sales"), cogs=src.get("cogs"), op=src.get("op"), ord=src.get("ord"),
            net=src.get("net"), ocf=src.get("ocf"), fcf=src.get("fcf"),
            assets=src.get("assets"), equity=src.get("equity"),
            ca=src.get("ca"), inv=src.get("inv"), cl=src.get("cl"), tl=src.get("tl"),
            debt=src.get("debt"), cash=src.get("cash"), ar=src.get("ar"),
            stinv=src.get("stinv"), invest=src.get("invest"),
            ppe=src.get("ppe"), intan=src.get("intan"),
            shares=src.get("shares"),  # 取れない会社もあります
            price=None, ebitda=src.get("ebitda"),
            tax=0.30, wacc=0.10,
        )
    current = build_payload(cur)
    previous = build_payload(prev) if prev else {}
    return current, previous, cur_date, prev_date

# ---------- KPI計算 ----------
def calc_health(current: Dict[str, float]) -> pd.DataFrame:
    equity_ratio = _safe_div(current.get("equity"), current.get("assets"))
    debt_to_equity = _safe_div(current.get("tl") or None, current.get("equity"))
    current_ratio = _safe_div(current.get("ca"), current.get("cl"))
    quick_assets = (current.get("ca") or 0) - (current.get("inv") or 0)
    quick_ratio = _safe_div(quick_assets, current.get("cl"))
    fixed_assets = (current.get("ppe") or 0) + (current.get("intan") or 0) + (current.get("invest") or 0)
    fixed_ratio = _safe_div(fixed_assets, current.get("equity"))

    rows = [
        ("自己資本比率", equity_ratio, f">= {fmt_pct(HEALTH_THRESHOLDS['equity_ratio_min'])}", "OK" if (equity_ratio or 0) >= HEALTH_THRESHOLDS["equity_ratio_min"] else "NG"),
        ("負債比率", debt_to_equity, f"<= {HEALTH_THRESHOLDS['debt_to_equity_max']:.2f}x", "OK" if (debt_to_equity or 1e9) <= HEALTH_THRESHOLDS["debt_to_equity_max"] else "NG"),
        ("流動比率", current_ratio, f">= {HEALTH_THRESHOLDS['current_ratio_min']:.2f}x", "OK" if (current_ratio or 0) >= HEALTH_THRESHOLDS["current_ratio_min"] else "NG"),
        ("当座比率", quick_ratio, f">= {HEALTH_THRESHOLDS['quick_ratio_min']:.2f}x", "OK" if (quick_ratio or 0) >= HEALTH_THRESHOLDS["quick_ratio_min"] else "NG"),
        ("固定比率", fixed_ratio, f"<= {HEALTH_THRESHOLDS['fixed_ratio_max']:.2f}x", "OK" if (fixed_ratio or 1e9) <= HEALTH_THRESHOLDS["fixed_ratio_max"] else "NG"),
    ]
    df = pd.DataFrame(rows, columns=["指標","当期","基準","判定"])
    df["当期(%)"] = df["当期"].apply(lambda x: fmt_pct(x) if x is not None else None)
    return df[["指標","当期(%)","基準","判定"]]

def calc_profitability(current: Dict[str, float]) -> pd.DataFrame:
    sales = current.get("sales") or 0
    gross = (current.get("sales") or 0) - (current.get("cogs") or 0)
    op = current.get("op"); ord_ = current.get("ord"); net = current.get("net")

    gm = _safe_div(gross, sales) if sales else None
    opm = _safe_div(op, sales) if sales else None
    orm = _safe_div(ord_, sales) if (sales and ord_ is not None) else None
    nm = _safe_div(net, sales) if sales else None
    roe = _safe_div(net, current.get("equity"))
    roa = _safe_div(net, current.get("assets"))

    def judge_opm(x):
        if x is None: return ""
        if x >= PROFIT_GUIDE["op_margin_high"]: return "高い"
        if x >= PROFIT_GUIDE["op_margin_good"]: return "健全"
        return "低い"

    def judge_nm(x):
        if x is None: return ""
        if x >= PROFIT_GUIDE["net_margin_good"]: return "優良"
        if x <= PROFIT_GUIDE["net_margin_thin"]: return "薄利"
        return "中間"

    def judge_roe(x):
        if x is None: return ""
        if x >= PROFIT_GUIDE["roe_excellent"]: return "優秀"
        if x <= PROFIT_GUIDE["roe_low"]: return "低"
        return "中"

    def judge_roa(x):
        if x is None: return ""
        return "良" if x >= PROFIT_GUIDE["roa_efficient"] else "普"

    rows = [
        ("売上総利益率", gm, "20%〜40%", "OK" if (gm is not None and PROFIT_GUIDE["gross_margin_range"][0] <= gm <= PROFIT_GUIDE["gross_margin_range"][1]) else "CHK"),
        ("営業利益率", opm, "5%以上/10%以上高収益", judge_opm(opm)),
        ("経常利益率", orm, "営業と大乖離なし", "" if orm is None else "OK"),
        ("純利益率", nm, "5%以上優良/3%以下薄利", judge_nm(nm)),
        ("ROE", roe, "10%以上優秀/5%以下低", judge_roe(roe)),
        ("ROA", roa, "5%以上で効率", judge_roa(roa)),
    ]
    df = pd.DataFrame(rows, columns=["指標","当期","目安","判定"])
    df["当期(%)"] = df["当期"].apply(lambda x: fmt_pct(x) if x is not None else None)
    return df[["指標","当期(%)","目安","判定"]]

def calc_growth(current: Dict[str, float], previous: Dict[str, float]) -> pd.DataFrame:
    def g(cur, prev): return _safe_div((cur or 0) - (prev or 0), prev) if prev not in (None, 0) else None
    sales_g = g(current.get("sales"), previous.get("sales"))
    op_g = g(current.get("op"), previous.get("op"))
    net_g = g(current.get("net"), previous.get("net"))

    avg_assets = None
    if current.get("assets") and previous.get("assets"):
        avg_assets = np.mean([current["assets"], previous["assets"]])
    asset_turn = _safe_div(current.get("sales"), avg_assets)

    avg_ar = None
    if current.get("ar") and previous.get("ar"):
        avg_ar = np.mean([current["ar"], previous["ar"]])
    ar_turn = _safe_div(current.get("sales"), avg_ar)

    rows = [
        ("売上成長率", sales_g, "（当期−前期）/前期"),
        ("営業利益成長率", op_g, "プラス成長が望ましい"),
        ("純利益成長率", net_g, "安定した成長が理想"),
        ("総資産回転率(回)", asset_turn, "一般に 0.3〜2.0回/年が多い"),
        ("売上債権回転率(回)", ar_turn, "回転が多いほど資金繰り良"),
    ]
    out = []
    for nm, val, note in rows:
        if "回)" in nm:
            disp = f"{val:.1f}" if val is not None else None
        else:
            disp = fmt_pct(val) if val is not None else None
        out.append((nm, disp, note))
    return pd.DataFrame(out, columns=["指標","表示","コメント"])

def calc_asset_value(current: Dict[str, float]) -> dict:
    adj_assets = (
        (current.get("cash") or 0) +
        (current.get("stinv") or 0) +
        0.85 * (current.get("ar") or 0) +
        0.50 * (current.get("inv") or 0) +
        0.50 * (current.get("ppe") or 0) +
        0.00 * (current.get("intan") or 0) +
        0.50 * (current.get("invest") or 0)
    )
    liquidation = adj_assets - (current.get("tl") or 0)
    return dict(adjusted_assets=adj_assets, liquidation_value=liquidation)

def calc_income_value(current: Dict[str, float]) -> dict:
    wacc = current.get("wacc") or DEFAULT_WACC
    fcf = current.get("fcf") or 0.0
    netcash = (current.get("cash") or 0) + (current.get("stinv") or 0) - (current.get("debt") or 0)
    weak = netcash + (fcf / wacc if wacc else 0)
    strong = netcash + (fcf * (1 + BULL_GROWTH) ** 5) / wacc if wacc else netcash

    def pv_cf(cf, r, t): return cf / ((1 + r) ** t)
    weak_pv = sum(pv_cf(fcf, wacc, t) for t in range(1, DCF_HORIZON_YEARS + 1)) + (fcf / wacc) / ((1 + wacc) ** DCF_HORIZON_YEARS)
    strong_fcf5 = fcf * (1 + BULL_GROWTH) ** 5
    strong_pv = (sum(pv_cf(fcf * (1 + BULL_GROWTH) ** t, wacc, t) for t in range(1, 6))
                 + sum(pv_cf(strong_fcf5, wacc, t) for t in range(6, DCF_HORIZON_YEARS + 1))
                 + (strong_fcf5 / wacc) / ((1 + wacc) ** DCF_HORIZON_YEARS))
    return dict(weak_simple=weak, strong_simple=strong, weak_dcf=netcash + weak_pv, strong_dcf=netcash + strong_pv)

def calc_price_metrics(current: Dict[str, float], previous: Dict[str, float]) -> pd.DataFrame:
    price = current.get("price") or 0
    shares = current.get("shares") or None
    mktcap = (price * shares) if (price and shares) else None
    ev = None
    if mktcap is not None:
        ev = mktcap + (current.get("debt") or 0) - ((current.get("cash") or 0) + (current.get("stinv") or 0))
    ni = current.get("net"); ocf = current.get("ocf"); sales = current.get("sales")
    equity = current.get("equity"); ebitda = current.get("ebitda"); tax = current.get("tax") or 0.0
    op = current.get("op")
    invested = (current.get("debt") or 0) + (current.get("equity") or 0) - ((current.get("cash") or 0) + (current.get("stinv") or 0))
    nopat = (op or 0) * (1 - tax) if op is not None else None

    per = _safe_div(mktcap, ni) if mktcap is not None else None
    pcfr = _safe_div(mktcap, ocf) if mktcap is not None else None
    psr = _safe_div(mktcap, sales) if mktcap is not None else None
    pbr = _safe_div(mktcap, equity) if mktcap is not None else None
    ey = _safe_div(ni, mktcap) if mktcap is not None else None
    ev_ebitda = _safe_div(ev, ebitda) if (ev is not None) else None
    roic = _safe_div(nopat, invested) if nopat is not None else None
    accruals = None
    if (current.get("assets") and previous.get("assets")):
        avg_assets = np.mean([current["assets"], previous["assets"]])
        accruals = _safe_div((ni or 0) - (ocf or 0), avg_assets)

    rows = [
        ("株価（直近終値）", price),
        ("近似PER", per),
        ("PCFR", pcfr),
        ("PSR", psr),
        ("PBR", pbr),
        ("予想収益率", ey),
        ("PER×PBR", (per * pbr) if (per is not None and pbr is not None) else None),
        ("EV/EBITDA", ev_ebitda),
        ("ROIC", roic),
        ("アクルーアル/総資産", accruals),
        ("時価総額", mktcap),
    ]
    df = pd.DataFrame(rows, columns=["指標","当期"])
    def _fmt(nm, v):
        if v is None:
            return None
        if nm in ("近似PER","PCFR","PSR","PBR","EV/EBITDA","PER×PBR"):
            return f"{v:.2f}"
        if nm in ("予想収益率","ROIC","アクルーアル/総資産"):
            return fmt_pct(v, 1)
        if nm in ("株価（直近終値）","時価総額"):
            return fmt_num(v, 0)
        return fmt_num(v, 2)
    df["表示"] = df.apply(lambda r: _fmt(r["指標"], r["当期"]), axis=1)
    return df