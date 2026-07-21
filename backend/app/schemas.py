from __future__ import annotations

from pydantic import BaseModel, Field


class BayesRule(BaseModel):
    antecedent: str = Field(..., description="Ana urun")
    consequent: str = Field(..., description="Onerilen urun")
    antecedent_category: str = Field(..., description="Ana urunun kategorisi")
    consequent_category: str = Field(..., description="Onerilen urunun kategorisi")
    prior_probability: float = Field(..., description="Consequent urununun genel support degeri")
    posterior_probability: float = Field(..., description="Antecedent verildiginde consequent olasiligi")
    bayes_factor: float = Field(..., description="Posterior / prior")
    belief_update_pct: float = Field(..., description="On inanc degisimi yuzdesi")
    interpretation: str = Field(..., description="Bayes kanit yorumu")
    support: float = Field(..., description="Kural support degeri")


class MenuPackage(BaseModel):
    package_name: str
    items: list[str]
    antecedent_category: str
    consequent_category: str
    is_cross_category: bool
    package_description: str
    package_total_price: float
    suggested_price_strategy: str
    price_opportunity_score: float
    confidence: float
    bayes_factor: float


class AnalysisSummary(BaseModel):
    total_orders: int
    unique_items: int
    rules_found: int
    packages_generated: int
    date_range: str
    categories_available: list[str]
    active_category_filter: str | None
    filtered_order_count: int
    active_time_filter: str | None
    time_filter_order_count: int
    time_filter_coverage_pct: float


class BaselineComparison(BaseModel):
    top_popular_items: list[str]
    bayes_approach_advantage: str


class MonthlyTopRule(BaseModel):
    antecedent: str
    consequent: str
    bayes_factor: float
    confidence: float


class MonthlyMonthData(BaseModel):
    month_name: str
    order_count: int
    top_rules: list[MonthlyTopRule]


class TrendCombinationChange(BaseModel):
    antecedent: str
    consequent: str
    jan_factor: float
    mar_factor: float
    change_pct: float


class MostConsistentCombination(BaseModel):
    antecedent: str
    consequent: str
    avg_bayes_factor: float


class TrendInsights(BaseModel):
    rising_combinations: list[TrendCombinationChange]
    falling_combinations: list[TrendCombinationChange]
    new_in_march: list[str]
    disappeared_in_march: list[str]
    most_consistent: MostConsistentCombination | None


class MonthlyTrend(BaseModel):
    months: dict[str, MonthlyMonthData]
    trend_insights: TrendInsights


class FullResponse(BaseModel):
    status: str
    analysis_summary: AnalysisSummary
    bayes_rules: list[BayesRule]
    menu_packages: list[MenuPackage]
    baseline_comparison: BaselineComparison
    monthly_trend: MonthlyTrend
