# -*- coding: utf-8 -*-
"""
.agent/skills/__init__.py
=====================================
用途：艾薇 Agent Skills 技能庫模組初始化檔案
職責：提供統一的技能匯入接口，方便未來擴充與管理
=====================================
"""

from pathlib import Path

# 定義技能庫根目錄
SKILLS_DIR = Path(__file__).parent

# 技能清單 (供外部查詢)
AVAILABLE_SKILLS = [
    "code_reviewer",
    "doc_generator",
    "test_runner",
    "github_explorer",
    "skill_converter",
    "plan_validator",
    "git_stats_reporter",
    "manifest_updater",
    "skills_evaluator",
]

__all__ = ["SKILLS_DIR", "AVAILABLE_SKILLS"]
