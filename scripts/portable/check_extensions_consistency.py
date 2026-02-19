#!/usr/bin/env python3
"""
Extensions 三方一致性檢查器

用途：確保 devcontainer / .vscode / idx 三處的 extensions 清單保持同步
目的：在 CI 與本機都可執行，防止 extensions 漂移

使用方法：
  python scripts/portable/check_extensions_consistency.py                # 檢查所有來源
  python scripts/portable/check_extensions_consistency.py --fix          # 嘗試自動修復（覆寫 devcontainer 與 idx）
  python scripts/portable/check_extensions_consistency.py --verbose      # 詳細輸出
"""

import json
import sys
from pathlib import Path

# 定義三個來源
DEVCONTAINER_JSON = ".devcontainer/devcontainer.json"
VSCODE_EXTENSIONS_JSON = ".vscode/extensions.json"
IDX_DEV_NIX = ".idx/dev.nix"


def get_devcontainer_extensions() -> set[str]:
    """從 devcontainer.json 讀取 extensions"""
    path = Path(DEVCONTAINER_JSON)
    if not path.exists():
        return set()

    try:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
        exts = obj.get("customizations", {}).get("vscode", {}).get("extensions", [])
        return set(filter(None, exts))
    except (json.JSONDecodeError, KeyError):
        return set()


def get_vscode_extensions() -> set[str]:
    """從 .vscode/extensions.json 讀取 extensions"""
    path = Path(VSCODE_EXTENSIONS_JSON)
    if not path.exists():
        return set()

    try:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
        exts = obj.get("recommendations", [])
        return set(filter(None, exts))
    except (json.JSONDecodeError, KeyError):
        return set()


def get_idx_extensions() -> set[str]:
    """從 .idx/dev.nix 讀取 extensions"""
    path = Path(IDX_DEV_NIX)
    if not path.exists():
        return set()

    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()

        # 簡單的正則式提取：找 idx.extensions = [ ... ]
        import re

        match = re.search(r"idx\s*=\s*\{[^}]*extensions\s*=\s*\[(.*?)\];", content, re.DOTALL)
        if not match:
            return set()

        ext_block = match.group(1)
        # 提取引號內的字串
        exts = re.findall(r'"([^"]+)"', ext_block)
        return set(filter(None, exts))
    except Exception:
        return set()


def check_consistency() -> tuple[bool, dict]:
    """檢查三個來源是否一致，回傳 (一致否, 詳細資訊)"""
    dev_exts = get_devcontainer_extensions()
    vscode_exts = get_vscode_extensions()
    idx_exts = get_idx_extensions()

    # 找出差異
    only_in_dev = dev_exts - vscode_exts
    only_in_vscode = vscode_exts - dev_exts
    only_in_idx = idx_exts - vscode_exts

    is_consistent = only_in_dev == set() and only_in_vscode == set() and only_in_idx == set()

    info = {
        "devcontainer": {
            "path": DEVCONTAINER_JSON,
            "count": len(dev_exts),
            "extensions": sorted(dev_exts),
        },
        "vscode": {
            "path": VSCODE_EXTENSIONS_JSON,
            "count": len(vscode_exts),
            "extensions": sorted(vscode_exts),
        },
        "idx": {
            "path": IDX_DEV_NIX,
            "count": len(idx_exts),
            "extensions": sorted(idx_exts),
        },
        "differences": {
            "only_in_devcontainer": sorted(only_in_dev),
            "only_in_vscode": sorted(only_in_vscode),
            "only_in_idx": sorted(only_in_idx),
        },
        "is_consistent": is_consistent,
    }

    return is_consistent, info


def print_report(verbose: bool = False) -> bool:
    """列印檢查報告，回傳是否一致"""
    is_consistent, info = check_consistency()

    print("=" * 70)
    print("VS Code Extensions 三方一致性檢查")
    print("=" * 70)

    if verbose:
        print("\n📋 來源清單：")
        for source, details in [
            ("devcontainer", info["devcontainer"]),
            ("vscode", info["vscode"]),
            ("idx", info["idx"]),
        ]:
            print(f"\n  {source.upper()}")
            print(f"    Path: {details['path']}")
            print(f"    Count: {details['count']}")
            if details["extensions"]:
                for ext in details["extensions"][:5]:
                    print(f"      - {ext}")
                if len(details["extensions"]) > 5:
                    print(f"      ... ({len(details['extensions']) - 5} more)")

    print("\n📊 摘要：")
    print(f"  devcontainer: {info['devcontainer']['count']} 個 extensions")
    print(f"  vscode:       {info['vscode']['count']} 個 extensions")
    print(f"  idx:          {info['idx']['count']} 個 extensions")

    diffs = info["differences"]
    has_diff = any([diffs["only_in_devcontainer"], diffs["only_in_vscode"], diffs["only_in_idx"]])

    if has_diff:
        print("\n⚠️  差異檢測：")
        if diffs["only_in_devcontainer"]:
            print(f"  ❌ 僅在 devcontainer 中：{', '.join(diffs['only_in_devcontainer'][:3])}")
            if len(diffs["only_in_devcontainer"]) > 3:
                print(f"     ... 共 {len(diffs['only_in_devcontainer'])} 個")
        if diffs["only_in_vscode"]:
            print(f"  ❌ 僅在 vscode 中：{', '.join(diffs['only_in_vscode'][:3])}")
            if len(diffs["only_in_vscode"]) > 3:
                print(f"     ... 共 {len(diffs['only_in_vscode'])} 個")
        if diffs["only_in_idx"]:
            print(f"  ❌ 僅在 idx 中：{', '.join(diffs['only_in_idx'][:3])}")
            if len(diffs["only_in_idx"]) > 3:
                print(f"     ... 共 {len(diffs['only_in_idx'])} 個")

    if is_consistent:
        print("\n✅ 三方 extensions 清單一致！")
        return True
    else:
        print("\n❌ 三方 extensions 清單不一致")
        print("\n💡 建議：手動更新以下檔案以保持同步，或運行 --fix（覆寫 devcontainer 與 idx）")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細輸出")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="嘗試自動修復（覆寫 devcontainer 與 idx，以 .vscode/extensions.json 為準）",
    )
    args = parser.parse_args()

    is_consistent, info = check_consistency()

    if args.fix:
        print("🔧 嘗試自動修復...")
        vscode_exts = get_vscode_extensions()

        # 更新 devcontainer.json
        try:
            with open(DEVCONTAINER_JSON, encoding="utf-8") as f:
                dev_obj = json.load(f)
            dev_obj.setdefault("customizations", {}).setdefault("vscode", {})["extensions"] = (
                sorted(vscode_exts)
            )
            with open(DEVCONTAINER_JSON, "w", encoding="utf-8") as f:
                json.dump(dev_obj, f, indent=2, ensure_ascii=False)
            print(f"  ✅ 更新 {DEVCONTAINER_JSON}")
        except Exception as e:
            print(f"  ❌ 無法更新 {DEVCONTAINER_JSON}: {e}")

        # 更新 .idx/dev.nix（需要特殊處理）
        try:
            with open(IDX_DEV_NIX, encoding="utf-8") as f:
                nix_content = f.read()

            import re

            ext_list_str = (
                "[\n        "
                + "\n        ".join(f'"{ext}"' for ext in sorted(vscode_exts))
                + "\n      ]"
            )
            nix_content = re.sub(
                r"extensions\s*=\s*\[(.*?)\];",
                f"extensions = {ext_list_str};",
                nix_content,
                flags=re.DOTALL,
            )

            with open(IDX_DEV_NIX, "w", encoding="utf-8") as f:
                f.write(nix_content)
            print(f"  ✅ 更新 {IDX_DEV_NIX}")
        except Exception as e:
            print(f"  ❌ 無法更新 {IDX_DEV_NIX}: {e}")

        print("\n✅ 自動修復完成。請重新執行檢查以驗證。")
        return True

    # 一般檢查
    success = print_report(verbose=args.verbose)

    if not success:
        sys.exit(1)

    return success


if __name__ == "__main__":
    main()
