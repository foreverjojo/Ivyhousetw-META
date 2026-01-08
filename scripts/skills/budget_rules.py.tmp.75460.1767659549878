"""
Budget Rules Skill (Deterministic)

目的：
  - 提供預算配置決策建議：KILL / SCALE_DOWN / SCALE_UP / HOLD
  - 根據 target_cpa、breakeven_roas 等門檻值自動判定行動
  - 在缺少必要數據時，明確標示警告，避免臆測

輸入：
  - report_summary（report_summary.v1 的 dict）
  - manual_inputs（使用者輸入的 dict，含 target_cpa, breakeven_roas）

輸出（dict）：
  - skill_version, thresholds, actions[], recommendations[], warnings
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class BudgetAction(str, Enum):
    """預算行動類型"""
    KILL = "KILL"             # 立即停止
    SCALE_DOWN = "SCALE_DOWN"  # 降低預算
    SCALE_UP = "SCALE_UP"      # 增加預算
    HOLD = "HOLD"              # 維持觀察


def _to_float(x: Any) -> float:
    """安全轉換為浮點數"""
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def _safe_div(num: float, den: float) -> Optional[float]:
    """安全除法，分母為零時返回 None"""
    if den <= 0:
        return None
    return num / den


@dataclass(frozen=True)
class BudgetThresholds:
    """預算規則門檻值"""
    target_cpa: float = 500.0           # 目標 CPA（預設 500 TWD）
    breakeven_roas: float = 2.0         # 損益平衡 ROAS
    kill_spend_multiplier: float = 1.5  # KILL 門檻：花費 > target_cpa × 此倍數且無單
    scale_up_roas_multiplier: float = 1.2  # SCALE_UP 門檻：ROAS > breakeven × 此倍數
    min_spend_for_decision: float = 100.0  # 最低花費金額（避免樣本過小）
    min_purchases_for_stable: int = 3      # 穩定判定最低購買數


@dataclass
class AdSetBudgetAnalysis:
    """單一廣告組合的預算分析結果"""
    name: str
    id: str = ""
    spend: float = 0.0
    purchases: float = 0.0
    purchase_value: float = 0.0
    roas: Optional[float] = None
    cpa: Optional[float] = None
    action: BudgetAction = BudgetAction.HOLD
    reason: str = ""


def _extract_thresholds_from_inputs(manual_inputs: Dict[str, Any]) -> BudgetThresholds:
    """從 manual_inputs 提取門檻值，缺失時使用預設"""
    target_cpa = _to_float(manual_inputs.get("target_cpa", 500.0))
    breakeven_roas = _to_float(manual_inputs.get("breakeven_roas", 2.0))

    # 確保有合理的預設值
    if target_cpa <= 0:
        target_cpa = 500.0
    if breakeven_roas <= 0:
        breakeven_roas = 2.0

    return BudgetThresholds(
        target_cpa=target_cpa,
        breakeven_roas=breakeven_roas,
    )


def _determine_action(
    spend: float,
    purchases: float,
    roas: Optional[float],
    thresholds: BudgetThresholds,
) -> tuple[BudgetAction, str]:
    """根據規則判定預算行動"""

    # 花費過少，無法判定
    if spend < thresholds.min_spend_for_decision:
        return BudgetAction.HOLD, f"花費 {spend:.0f} < {thresholds.min_spend_for_decision:.0f}，樣本不足，維持觀察"

    kill_threshold = thresholds.target_cpa * thresholds.kill_spend_multiplier

    # KILL: spend > 1.5 × target_cpa 且 purchases = 0
    if spend > kill_threshold and purchases == 0:
        return BudgetAction.KILL, (
            f"花費 {spend:.0f} > {kill_threshold:.0f} (1.5×CPA目標) 且購買數=0，建議立即停止"
        )

    # 若無 ROAS 且有購買，無法精確判定
    if roas is None and purchases > 0:
        return BudgetAction.HOLD, f"有 {int(purchases)} 筆購買但缺少 purchase_value，無法計算 ROAS"

    # SCALE_DOWN: ROAS < breakeven_roas 但有單
    if roas is not None and roas < thresholds.breakeven_roas and purchases > 0:
        return BudgetAction.SCALE_DOWN, (
            f"ROAS {roas:.2f} < 損益平衡 {thresholds.breakeven_roas:.2f}，但有 {int(purchases)} 筆購買，建議降低預算"
        )

    # SCALE_UP: ROAS > breakeven_roas × 1.2 且穩定（購買數>=3）
    scale_up_threshold = thresholds.breakeven_roas * thresholds.scale_up_roas_multiplier
    if (
        roas is not None
        and roas >= scale_up_threshold
        and purchases >= thresholds.min_purchases_for_stable
    ):
        return BudgetAction.SCALE_UP, (
            f"ROAS {roas:.2f} >= {scale_up_threshold:.2f} (1.2×損益平衡) 且購買穩定 ({int(purchases)}筆)，建議增加預算"
        )

    # 其他情況：HOLD
    if roas is not None and roas >= thresholds.breakeven_roas:
        return BudgetAction.HOLD, f"ROAS {roas:.2f} >= 損益平衡 {thresholds.breakeven_roas:.2f}，維持觀察（購買數尚未達穩定標準）"

    return BudgetAction.HOLD, "未符合任何決策規則，維持觀察"


def run_budget_rules(
    report_summary: Dict[str, Any],
    manual_inputs: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    預算配置規則主函式

    Args:
        report_summary: 報表摘要 dict（report_summary.v1 格式）
        manual_inputs: 使用者輸入的 dict，含 target_cpa, breakeven_roas（可選）

    Returns:
        包含預算決策建議的 dict
    """
    manual_inputs = manual_inputs or {}
    warnings: List[str] = []

    # 提取門檻值
    thresholds = _extract_thresholds_from_inputs(manual_inputs)

    # 檢查是否有提供門檻值
    if "target_cpa" not in manual_inputs:
        warnings.append(f"未提供 target_cpa，使用預設值 {thresholds.target_cpa:.0f}")
    if "breakeven_roas" not in manual_inputs:
        warnings.append(f"未提供 breakeven_roas，使用預設值 {thresholds.breakeven_roas:.2f}")

    # 從 report_summary 提取整體指標
    kpi = report_summary.get("kpi", {})
    meta = kpi.get("meta", {})

    total_spend = _to_float(meta.get("spend_twd", 0))
    total_purchases = _to_float(meta.get("purchases", 0))
    purchase_value = _to_float(meta.get("purchase_value_twd", 0))

    # 也嘗試 platform 數據
    platform_purchases = _to_float(meta.get("platform_purchases", 0))
    platform_value = _to_float(meta.get("platform_purchase_value_twd", 0))

    # 選擇主數據源
    if total_purchases == 0 and platform_purchases > 0:
        total_purchases = platform_purchases
        purchase_value = platform_value
        warnings.append("使用 platform 數據（truth 購買為 0）")

    # 計算整體 ROAS 和 CPA
    overall_roas = _safe_div(purchase_value, total_spend)
    overall_cpa = _safe_div(total_spend, total_purchases)

    # 判定整體行動
    overall_action, overall_reason = _determine_action(
        spend=total_spend,
        purchases=total_purchases,
        roas=overall_roas,
        thresholds=thresholds,
    )

    actions: List[Dict[str, Any]] = []
    actions.append({
        "level": "overall",
        "name": "整體帳戶",
        "spend_twd": round(total_spend, 2),
        "purchases": int(total_purchases),
        "purchase_value_twd": round(purchase_value, 2),
        "roas": round(overall_roas, 4) if overall_roas else None,
        "cpa_twd": round(overall_cpa, 2) if overall_cpa else None,
        "action": overall_action.value,
        "reason": overall_reason,
    })

    # 生成建議
    recommendations: List[str] = []

    if overall_action == BudgetAction.KILL:
        recommendations.append(
            "整體花費超過目標 CPA 的 1.5 倍且無購買，建議立即暫停投放並檢視素材/受眾/出價策略。"
        )
    elif overall_action == BudgetAction.SCALE_DOWN:
        recommendations.append(
            f"ROAS 低於損益平衡點 {thresholds.breakeven_roas:.2f}，建議降低日預算 20-30% 或縮減受眾範圍。"
        )
        recommendations.append("檢視轉換漏斗斷點，優化落地頁或結帳流程。")
    elif overall_action == BudgetAction.SCALE_UP:
        recommendations.append(
            f"ROAS 達標且購買穩定（>={thresholds.min_purchases_for_stable}筆），"
            "建議逐步增加預算 10-20%，觀察邊際效益。"
        )
        recommendations.append("可複製成功廣告組合到新受眾，避免單一組合過度飽和。")
    else:
        recommendations.append(
            "目前處於觀察階段，建議累積更多數據後再做預算調整決策。"
        )

    # 補充建議
    if total_spend < thresholds.min_spend_for_decision:
        recommendations.append(
            f"目前花費 {total_spend:.0f} < {thresholds.min_spend_for_decision:.0f}，"
            "建議至少花費 1-2 倍 CPA 目標後再判定成效。"
        )

    if overall_cpa and overall_cpa > thresholds.target_cpa * 2:
        recommendations.append(
            f"CPA {overall_cpa:.0f} 超過目標 {thresholds.target_cpa:.0f} 的 2 倍，"
            "建議重新檢視受眾精準度與素材吸引力。"
        )

    return {
        "skill_version": "budget_rules.v1",
        "thresholds": {
            "target_cpa_twd": thresholds.target_cpa,
            "breakeven_roas": thresholds.breakeven_roas,
            "kill_spend_multiplier": thresholds.kill_spend_multiplier,
            "scale_up_roas_multiplier": thresholds.scale_up_roas_multiplier,
            "min_spend_for_decision": thresholds.min_spend_for_decision,
            "min_purchases_for_stable": thresholds.min_purchases_for_stable,
        },
        "summary": {
            "total_spend_twd": round(total_spend, 2),
            "total_purchases": int(total_purchases),
            "total_purchase_value_twd": round(purchase_value, 2),
            "overall_roas": round(overall_roas, 4) if overall_roas else None,
            "overall_cpa_twd": round(overall_cpa, 2) if overall_cpa else None,
        },
        "actions": actions[:10],  # 最多回傳 10 則
        "recommendations": recommendations[:8],
        "warnings": warnings,
    }
