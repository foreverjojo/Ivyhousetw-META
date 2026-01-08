"""
Creative Fatigue Diagnostic Skill (Deterministic)

目的：
  - 偵測素材疲乏：高曝光但轉換下降的廣告
  - 找出高潛力素材：Hook Rate/Hold Rate 高但尚未規模化
  - 在缺少影片欄位時，明確標示警告，避免臆測

輸入：
  - report_summary（report_summary.v1 的 dict）
  - ads_df_records（廣告層級資料，list of dict）

輸出（dict）：
  - skill_version, triggered, ads_analyzed, fatigue_ads[], high_potential_ads[],
    recommendations[], warnings
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
class FatigueThresholds:
    """素材疲乏偵測門檻值"""
    frequency_fatigue: float = 2.5          # 頻率超過此值視為疲乏風險
    ctr_below_avg_ratio: float = 0.8        # CTR 低於平均的比例閾值
    hook_rate_min: float = 0.15             # 最低 Hook Rate（3秒觀看/曝光）
    hold_rate_min: float = 0.05             # 最低 Hold Rate（完整觀看/曝光）
    high_potential_hook_rate: float = 0.25  # 高潛力素材 Hook Rate 閾值
    high_potential_hold_rate: float = 0.10  # 高潛力素材 Hold Rate 閾值
    min_impressions: int = 1000             # 最低曝光數（避免樣本過小）


@dataclass
class AdMetrics:
    """單一廣告的計算指標"""
    ad_name: str
    ad_id: str = ""
    impressions: float = 0.0
    frequency: float = 0.0
    ctr: Optional[float] = None
    video_3s: float = 0.0
    thruplays: float = 0.0
    hook_rate: Optional[float] = None
    hold_rate: Optional[float] = None
    spend: float = 0.0
    purchases: float = 0.0


def _extract_ad_metrics(record: Dict[str, Any]) -> AdMetrics:
    """從單一廣告記錄提取指標"""
    ad_name = str(record.get("ad_name", record.get("Ad name", "")))
    ad_id = str(record.get("ad_id", record.get("Ad ID", "")))

    impressions = _to_float(record.get("impressions", 0))
    frequency = _to_float(record.get("frequency", 0))
    video_3s = _to_float(record.get("video_3s", 0))
    thruplays = _to_float(record.get("thruplays", 0))
    spend = _to_float(record.get("spend", 0))
    purchases = _to_float(record.get("purchases", 0))

    # 計算 CTR（若有 link_clicks）
    link_clicks = _to_float(record.get("link_clicks", 0))
    ctr = _safe_div(link_clicks * 100.0, impressions) if impressions > 0 else None

    # 計算 Hook Rate 和 Hold Rate
    hook_rate = _safe_div(video_3s, impressions)
    hold_rate = _safe_div(thruplays, impressions)

    return AdMetrics(
        ad_name=ad_name,
        ad_id=ad_id,
        impressions=impressions,
        frequency=frequency,
        ctr=ctr,
        video_3s=video_3s,
        thruplays=thruplays,
        hook_rate=hook_rate,
        hold_rate=hold_rate,
        spend=spend,
        purchases=purchases,
    )


def _check_missing_video_fields(ads_records: List[Dict[str, Any]]) -> List[str]:
    """檢查是否缺少影片相關欄位"""
    missing = []
    if not ads_records:
        return ["ads_df_records 為空"]

    sample = ads_records[0]
    video_3s_keys = ["video_3s", "3-second video plays", "影片播放 3 秒以上次數"]
    thruplay_keys = ["thruplays", "ThruPlays", "影片完整播放次數"]

    has_video_3s = any(k in sample for k in video_3s_keys)
    has_thruplays = any(k in sample for k in thruplay_keys)

    if not has_video_3s:
        missing.append("video_3s (3-second video plays)")
    if not has_thruplays:
        missing.append("thruplays (ThruPlays)")

    return missing


def run_creative_fatigue_diagnostic(
    report_summary: Dict[str, Any],
    ads_df_records: List[Dict[str, Any]],
    thresholds: FatigueThresholds | None = None,
) -> Dict[str, Any]:
    """
    素材疲乏偵測主函式

    Args:
        report_summary: 報表摘要 dict（report_summary.v1 格式）
        ads_df_records: 廣告層級資料（list of dict）
        thresholds: 門檻值設定（可選）

    Returns:
        包含疲乏分析結果的 dict
    """
    thresholds = thresholds or FatigueThresholds()
    warnings: List[str] = []

    # 檢查缺失欄位
    missing_fields = _check_missing_video_fields(ads_df_records)
    if missing_fields:
        warnings.append(f"missing_fields: {', '.join(missing_fields)}")

    if not ads_df_records:
        return {
            "skill_version": "creative_fatigue.v1",
            "triggered": False,
            "ads_analyzed": 0,
            "fatigue_ads": [],
            "high_potential_ads": [],
            "recommendations": ["請提供廣告層級資料以進行素材疲乏分析"],
            "warnings": warnings,
        }

    # 提取所有廣告指標
    ad_metrics_list: List[AdMetrics] = []
    for record in ads_df_records:
        metrics = _extract_ad_metrics(record)
        if metrics.impressions >= thresholds.min_impressions:
            ad_metrics_list.append(metrics)

    if not ad_metrics_list:
        return {
            "skill_version": "creative_fatigue.v1",
            "triggered": False,
            "ads_analyzed": 0,
            "fatigue_ads": [],
            "high_potential_ads": [],
            "recommendations": [f"沒有曝光數超過 {thresholds.min_impressions} 的廣告可供分析"],
            "warnings": warnings,
        }

    # 計算平均 CTR（僅計入有值的廣告）
    valid_ctrs = [m.ctr for m in ad_metrics_list if m.ctr is not None and m.ctr > 0]
    avg_ctr = sum(valid_ctrs) / len(valid_ctrs) if valid_ctrs else 0.0
    ctr_threshold = avg_ctr * thresholds.ctr_below_avg_ratio

    fatigue_ads: List[Dict[str, Any]] = []
    high_potential_ads: List[Dict[str, Any]] = []

    for metrics in ad_metrics_list:
        # 疲乏判定：frequency > 2.5 且 CTR 低於平均
        is_fatigued = (
            metrics.frequency > thresholds.frequency_fatigue
            and metrics.ctr is not None
            and metrics.ctr < ctr_threshold
        )

        if is_fatigued:
            fatigue_ads.append({
                "ad_name": metrics.ad_name,
                "ad_id": metrics.ad_id,
                "frequency": round(metrics.frequency, 2),
                "ctr_pct": round(metrics.ctr, 4) if metrics.ctr else None,
                "avg_ctr_pct": round(avg_ctr, 4),
                "impressions": int(metrics.impressions),
                "hook_rate": round(metrics.hook_rate, 4) if metrics.hook_rate else None,
                "hold_rate": round(metrics.hold_rate, 4) if metrics.hold_rate else None,
                "reason": f"頻率 {metrics.frequency:.2f} > {thresholds.frequency_fatigue}，CTR {metrics.ctr:.2f}% < 平均 {avg_ctr:.2f}%",
            })

        # 高潛力判定：Hook Rate 或 Hold Rate 高
        has_video_metrics = metrics.hook_rate is not None or metrics.hold_rate is not None
        is_high_potential = has_video_metrics and (
            (metrics.hook_rate is not None and metrics.hook_rate >= thresholds.high_potential_hook_rate)
            or (metrics.hold_rate is not None and metrics.hold_rate >= thresholds.high_potential_hold_rate)
        )

        if is_high_potential and not is_fatigued:
            high_potential_ads.append({
                "ad_name": metrics.ad_name,
                "ad_id": metrics.ad_id,
                "hook_rate": round(metrics.hook_rate, 4) if metrics.hook_rate else None,
                "hold_rate": round(metrics.hold_rate, 4) if metrics.hold_rate else None,
                "impressions": int(metrics.impressions),
                "spend": round(metrics.spend, 2),
                "reason": f"Hook Rate {(metrics.hook_rate or 0)*100:.1f}% / Hold Rate {(metrics.hold_rate or 0)*100:.1f}% 超過門檻",
            })

    # 生成建議
    recommendations: List[str] = []

    if fatigue_ads:
        recommendations.append(
            f"發現 {len(fatigue_ads)} 則疲乏廣告（頻率>{thresholds.frequency_fatigue} 且 CTR<平均）"
            "，建議暫停或更換素材。"
        )
        recommendations.append("疲乏素材可複製成新廣告並更換前 3 秒 Hook 或文案，避免持續消耗預算。")

    if high_potential_ads:
        recommendations.append(
            f"發現 {len(high_potential_ads)} 則高潛力素材（Hook/Hold Rate 高），建議增加預算規模化。"
        )

    if missing_fields:
        recommendations.append(
            "缺少影片指標欄位，無法完整計算 Hook Rate/Hold Rate。"
            "請確認 CSV 匯出包含「3-second video plays」與「ThruPlays」。"
        )

    if not fatigue_ads and not high_potential_ads:
        recommendations.append("目前無明顯疲乏或高潛力素材，建議持續監控並累積更多數據。")

    triggered = len(fatigue_ads) > 0

    return {
        "skill_version": "creative_fatigue.v1",
        "triggered": triggered,
        "ads_analyzed": len(ad_metrics_list),
        "thresholds": {
            "frequency_fatigue": thresholds.frequency_fatigue,
            "ctr_below_avg_ratio": thresholds.ctr_below_avg_ratio,
            "hook_rate_min": thresholds.hook_rate_min,
            "hold_rate_min": thresholds.hold_rate_min,
            "min_impressions": thresholds.min_impressions,
        },
        "avg_ctr_pct": round(avg_ctr, 4) if avg_ctr > 0 else None,
        "fatigue_ads": fatigue_ads[:10],  # 最多回傳 10 則
        "high_potential_ads": high_potential_ads[:10],  # 最多回傳 10 則
        "recommendations": recommendations[:8],
        "warnings": warnings,
    }
