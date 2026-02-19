#!/usr/bin/env python3
"""
性能基準測試工具

對應 P2 改進：性能基準測試（Performance Benchmark）

功能：
1. 測試核心函數的執行時間
2. 設定性能閾值，超過則警告
3. 輸出性能報告

使用方式：
    # 執行所有 benchmark
    python scripts/benchmark.py

    # 只執行特定 benchmark
    python scripts/benchmark.py --only kpi

    # 輸出 JSON 格式
    python scripts/benchmark.py --json

    # 設定迭代次數
    python scripts/benchmark.py --iterations 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# === 設定 ===
# 性能閾值（秒）
THRESHOLDS = {
    "kpi_calc": 5.0,  # KPI 計算應在 5 秒內完成
    "json_parse": 1.0,  # JSON 解析應在 1 秒內
    "file_io": 0.5,  # 檔案讀寫應在 0.5 秒內
    "adapter_meta": 2.0,  # Meta 適配器應在 2 秒內
    "adapter_shopee": 2.0,  # Shopee 適配器應在 2 秒內
    "adapter_momo": 2.0,  # Momo 適配器應在 2 秒內
}


@dataclass
class BenchmarkResult:
    """Benchmark 結果"""

    name: str
    elapsed: float
    threshold: float
    passed: bool
    iterations: int = 1
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


def timer(func: Callable, *args, **kwargs) -> tuple[float, Any]:
    """計時執行函數"""
    start = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return elapsed, result
    except Exception as e:
        elapsed = time.perf_counter() - start
        return elapsed, e


def benchmark_json_parse() -> BenchmarkResult:
    """測試 JSON 解析性能"""
    name = "json_parse"
    threshold = THRESHOLDS.get(name, 1.0)

    # 生成測試數據
    test_data = {
        "kpi": {f"metric_{i}": i * 1.5 for i in range(1000)},
        "insights": [{"id": i, "text": f"Insight {i}" * 10} for i in range(100)],
    }
    json_str = json.dumps(test_data)

    # 執行測試
    elapsed, result = timer(json.loads, json_str)

    if isinstance(result, Exception):
        return BenchmarkResult(
            name=name,
            elapsed=elapsed,
            threshold=threshold,
            passed=False,
            error=str(result),
        )

    return BenchmarkResult(
        name=name,
        elapsed=elapsed,
        threshold=threshold,
        passed=elapsed < threshold,
        details={"json_size": len(json_str)},
    )


def benchmark_file_io() -> BenchmarkResult:
    """測試檔案讀寫性能"""
    name = "file_io"
    threshold = THRESHOLDS.get(name, 0.5)

    test_file = Path("_benchmark_test.tmp")
    test_content = "x" * (1024 * 100)  # 100 KB

    try:
        # 寫入
        start = time.perf_counter()
        test_file.write_text(test_content)
        write_time = time.perf_counter() - start

        # 讀取
        start = time.perf_counter()
        _ = test_file.read_text()
        read_time = time.perf_counter() - start

        elapsed = write_time + read_time

        return BenchmarkResult(
            name=name,
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={"write_time": write_time, "read_time": read_time},
        )
    except Exception as e:
        return BenchmarkResult(
            name=name,
            elapsed=0,
            threshold=threshold,
            passed=False,
            error=str(e),
        )
    finally:
        if test_file.exists():
            test_file.unlink()


def benchmark_kpi_calc() -> BenchmarkResult:
    """測試 KPI 計算性能（需要 golden test 數據）"""
    name = "kpi_calc"
    threshold = THRESHOLDS.get(name, 5.0)

    # 檢查是否有測試數據
    golden_dir = Path("tests/golden")
    meta_sample = golden_dir / "meta_sample_input.csv"

    if not meta_sample.exists():
        return BenchmarkResult(
            name=name,
            elapsed=0,
            threshold=threshold,
            passed=True,  # 跳過，不算失敗
            error="Golden test data not found (skipped)",
        )

    try:
        # 嘗試匯入
        from scripts.kpi_calc import build_report_summary

        # 讀取測試數據
        csv_bytes = meta_sample.read_bytes()

        # 執行測試（使用相同數據作為 adset 和 ad）
        elapsed, result = timer(
            build_report_summary,
            csv_bytes,
            csv_bytes,
            None,  # 無 web excel
        )

        if isinstance(result, Exception):
            return BenchmarkResult(
                name=name,
                elapsed=elapsed,
                threshold=threshold,
                passed=False,
                error=str(result),
            )

        return BenchmarkResult(
            name=name,
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={"input_size": len(csv_bytes)},
        )

    except ImportError as e:
        return BenchmarkResult(
            name=name,
            elapsed=0,
            threshold=threshold,
            passed=True,
            error=f"Import error (skipped): {e}",
        )
    except Exception as e:
        return BenchmarkResult(
            name=name,
            elapsed=0,
            threshold=threshold,
            passed=False,
            error=str(e),
        )


def benchmark_adapter(adapter_name: str) -> BenchmarkResult:
    """測試適配器性能"""
    name = f"adapter_{adapter_name}"
    threshold = THRESHOLDS.get(name, 2.0)

    golden_dir = Path("tests/golden")

    # 根據適配器類型選擇測試檔案
    test_files = {
        "meta": golden_dir / "meta_sample_input.csv",
        "shopee": golden_dir / "shopee_sample_input.csv",
        "momo": golden_dir / "momo_sample_input.csv",
    }

    test_file = test_files.get(adapter_name)
    if not test_file or not test_file.exists():
        return BenchmarkResult(
            name=name,
            elapsed=0,
            threshold=threshold,
            passed=True,
            error=f"Test file not found: {test_file} (skipped)",
        )

    try:
        # 嘗試匯入對應適配器
        if adapter_name == "meta":
            from scripts.adapters.meta_adapter import parse_meta_csv as parse_func
        elif adapter_name == "shopee":
            from scripts.adapters.shopee_adapter import parse_shopee_csv as parse_func
        elif adapter_name == "momo":
            from scripts.adapters.momo_adapter import parse_momo_csv as parse_func
        else:
            return BenchmarkResult(
                name=name,
                elapsed=0,
                threshold=threshold,
                passed=True,
                error=f"Unknown adapter: {adapter_name}",
            )

        # 讀取測試數據
        csv_content = test_file.read_text(encoding="utf-8")

        # 執行測試
        elapsed, result = timer(parse_func, csv_content)

        if isinstance(result, Exception):
            return BenchmarkResult(
                name=name,
                elapsed=elapsed,
                threshold=threshold,
                passed=False,
                error=str(result),
            )

        return BenchmarkResult(
            name=name,
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={"input_size": len(csv_content)},
        )

    except ImportError as e:
        return BenchmarkResult(
            name=name,
            elapsed=0,
            threshold=threshold,
            passed=True,
            error=f"Import error (skipped): {e}",
        )
    except Exception as e:
        return BenchmarkResult(
            name=name,
            elapsed=0,
            threshold=threshold,
            passed=False,
            error=str(e),
        )


def run_all_benchmarks(
    only: str | None = None,
    iterations: int = 1,
) -> list[BenchmarkResult]:
    """執行所有 benchmark"""
    benchmarks = {
        "json": benchmark_json_parse,
        "file": benchmark_file_io,
        "kpi": benchmark_kpi_calc,
        "meta": lambda: benchmark_adapter("meta"),
        "shopee": lambda: benchmark_adapter("shopee"),
        "momo": lambda: benchmark_adapter("momo"),
    }

    if only:
        if only not in benchmarks:
            print(f"❌ 未知的 benchmark：{only}")
            print(f"   可用：{', '.join(benchmarks.keys())}")
            return []
        benchmarks = {only: benchmarks[only]}

    results = []

    for name, func in benchmarks.items():
        print(f"⏱️  執行 {name}...", end=" ", flush=True)

        # 多次迭代取平均
        times = []
        last_result = None
        for _ in range(iterations):
            result = func()
            times.append(result.elapsed)
            last_result = result

        avg_time = sum(times) / len(times)
        last_result = BenchmarkResult(
            name=last_result.name,
            elapsed=avg_time,
            threshold=last_result.threshold,
            passed=avg_time < last_result.threshold,
            iterations=iterations,
            error=last_result.error,
            details=last_result.details,
        )

        results.append(last_result)

        if last_result.error and "skipped" in last_result.error.lower():
            print("⏭️  跳過")
        elif last_result.passed:
            print(f"✅ {avg_time:.3f}s")
        else:
            print(f"❌ {avg_time:.3f}s (閾值: {last_result.threshold}s)")

    return results


def print_report(results: list[BenchmarkResult], as_json: bool = False) -> None:
    """輸出報告"""
    if as_json:
        output = [
            {
                "name": r.name,
                "elapsed": r.elapsed,
                "threshold": r.threshold,
                "passed": r.passed,
                "iterations": r.iterations,
                "error": r.error,
                "details": r.details,
            }
            for r in results
        ]
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    print("\n" + "=" * 60)
    print("📊 性能基準測試報告")
    print("=" * 60)

    passed = sum(1 for r in results if r.passed)
    failed = sum(
        1 for r in results if not r.passed and not (r.error and "skipped" in r.error.lower())
    )
    skipped = sum(1 for r in results if r.error and "skipped" in r.error.lower())

    print(f"\n結果：✅ {passed} 通過 | ❌ {failed} 失敗 | ⏭️  {skipped} 跳過\n")

    print(f"{'Benchmark':<20} {'時間':>10} {'閾值':>10} {'狀態':>10}")
    print("-" * 50)

    for r in results:
        if r.error and "skipped" in r.error.lower():
            status = "⏭️  跳過"
        elif r.passed:
            status = "✅ 通過"
        else:
            status = "❌ 失敗"

        print(f"{r.name:<20} {r.elapsed:>8.3f}s {r.threshold:>8.1f}s {status:>10}")

    if failed > 0:
        print("\n⚠️  有 benchmark 超過閾值，請檢查性能退化")


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="性能基準測試工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  執行所有 benchmark：
    python scripts/benchmark.py

  只執行特定 benchmark：
    python scripts/benchmark.py --only kpi

  多次迭代：
    python scripts/benchmark.py --iterations 5

  輸出 JSON：
    python scripts/benchmark.py --json
        """,
    )

    parser.add_argument(
        "--only",
        "-o",
        choices=["json", "file", "kpi", "meta", "shopee", "momo"],
        help="只執行特定 benchmark",
    )
    parser.add_argument(
        "--iterations",
        "-n",
        type=int,
        default=1,
        help="迭代次數（預設 1）",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="輸出 JSON 格式",
    )

    args = parser.parse_args()

    print("🚀 性能基準測試\n")

    results = run_all_benchmarks(args.only, args.iterations)

    if not results:
        return 1

    print_report(results, args.json)

    # 有失敗則返回 1
    failed = any(not r.passed and not (r.error and "skipped" in r.error.lower()) for r in results)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
