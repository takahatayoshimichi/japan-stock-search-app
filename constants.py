"""
このファイルは、固定の文字列や数値などのデータを変数として一括管理するファイルです。
"""
from dataclasses import dataclass

APP_TITLE = "📈 日本株 企業分析（EDINET v2 × yfinance）"
APP_SUBTITLE = "手入力なし：EDINETから自動で主要KPIを抽出、株価はyfinanceで取得"

DEFAULT_TICKER = "4519.T"  # 中外製薬（製薬会社は報告が頻繁）
DEFAULT_YEARS = 5

# EDINET v2
EDINET_API = "https://api.edinet-fsa.go.jp/api/v2"
# 取得優先：有報 > 四半期 > 半期
EDINET_FORMS = [
    ("010", "030000", "有価証券報告書"),
    ("010", "043000", "四半期報告書"),
    ("010", "053000", "半期報告書"),
]

# 主要勘定のローカル名（IFRS/J-GAAP 横断で候補を列挙）
XBRL_TAGS_LOCAL = {
    "sales": ["Revenue", "NetSales"],
    "cogs": ["CostOfSales"],
    "op": ["OperatingProfitLoss", "OperatingIncome"],
    "ord": ["OrdinaryIncome"],  # 近似的に使う（IFRSは欠落しがち）
    "net": ["ProfitLoss"],
    "assets": ["Assets"],
    "equity": ["Equity", "NetAssets"],
    "tl": ["Liabilities"],  # 総負債
    "ca": ["CurrentAssets"],
    "cl": ["CurrentLiabilities"],
    "inv": ["Inventories"],
    "ar": ["TradeAndOtherReceivablesCurrent", "NotesAndAccountsReceivableTrade"],
    "cash": ["CashAndCashEquivalents", "CashAndDeposits"],
    "stinv": ["Securities", "OtherFinancialAssetsCurrent"],
    "invest": ["InvestmentsAndOtherAssets", "OtherFinancialAssetsNoncurrent"],
    "ppe": ["PropertyPlantAndEquipment"],
    "intan": ["IntangibleAssets"],
    "debt_short": ["ShortTermBorrowings", "BorrowingsCurrent"],
    "debt_long": ["LongTermBorrowings", "BorrowingsNoncurrent"],
    "bonds": ["Bonds", "BondsIssued"],
    "ocf": ["NetCashFlowsFromUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
              "PurchaseOfPropertyPlantAndEquipment"],
    "dep_amort": ["DepreciationAndAmortisationExpense", "DepreciationAndAmortization"],
    "shares": ["NumberOfIssuedShares"],
}

# KPI判定しきい値
HEALTH_THRESHOLDS = dict(
    equity_ratio_min=0.80,     # 自己資本比率 80%以上
    debt_to_equity_max=2.0,    # 負債比率 200%以下
    current_ratio_min=1.0,     # 流動比率 100%以上
    quick_ratio_min=1.0,       # 当座比率 100%以上
    fixed_ratio_max=1.0,       # 固定比率 100%以下
)
PROFIT_GUIDE = dict(
    gross_margin_range=(0.20, 0.40),
    op_margin_good=0.05,
    op_margin_high=0.10,
    net_margin_good=0.05,
    net_margin_thin=0.03,
    roe_excellent=0.10,
    roe_low=0.05,
    roa_efficient=0.05,
)

DEFAULT_WACC = 0.10
BULL_GROWTH = 0.20  # 5年20%
DCF_HORIZON_YEARS = 10

@dataclass
class Settings:
    ticker: str
    years: int
    openai_api_key: str | None
    edinet_api_key: str | None