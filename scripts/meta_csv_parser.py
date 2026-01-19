from core import validation as core_validation

REQUIRED_ZH_ADSET = [...]  # 直接用 FIELD_SPECS_META.md YAML 那份清單
REQUIRED_ZH_AD = [...]


def guard_export_language(df, required_cols, report_kind: str):
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        # 你們已經有 SchemaValidationError(details=list[str]) 的慣例
        details = [
            f"[LANG_MISMATCH] {report_kind} CSV 欄位不完整（疑似英文介面匯出或匯出模板不同）",
            f"Missing columns ({len(missing)}): "
            + ", ".join(missing[:12])
            + (" ..." if len(missing) > 12 else ""),
            "Fix: 請切換 Meta 介面語言為「中文(繁體)」並用固定模板重新匯出（欄位需與 FIELD_SPECS_META.md 一致）",
        ]
        raise core_validation.SchemaValidationError(step="A(lang_mismatch)", details=details)
