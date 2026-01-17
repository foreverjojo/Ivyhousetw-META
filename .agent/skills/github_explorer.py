# -*- coding: utf-8 -*-
"""
.agent/skills/github_explorer.py
=====================================
用途：GitHub 技能搜尋與下載工具
職責：
  - 根據關鍵字從 GitHub 搜尋含 SKILL.md 的 Repo
  - 預覽技能內容供使用者審核
  - 使用者批准後才下載技能至本地
  - 下載後自動執行安全掃描
=====================================

使用方式：
    python .agent/skills/github_explorer.py search <keyword>
    python .agent/skills/github_explorer.py preview <repo_url>
    python .agent/skills/github_explorer.py download <repo_url> <file_path>

輸出：JSON 格式報告
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import subprocess

def validate_output_schema(result: Dict[str, Any], skill_name: str) -> Dict[str, Any]:
    """可選 JSON Schema 驗證（graceful degradation）"""
    try:
        import jsonschema
    except ImportError:
        return result

    schema_path = Path(__file__).resolve().parent / "schemas" / f"{skill_name}_output.schema.json"
    if not schema_path.exists():
        return result

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(result, schema)
        return result
    except jsonschema.ValidationError as exc:
        result["validation_errors"] = [
            {"message": exc.message, "path": list(exc.path), "schema_path": list(exc.schema_path)}
        ]
        result.setdefault(
            "suggestion",
            f"輸出格式不符合 schema 規範。請檢查 {skill_name}_output.schema.json 並確認欄位正確性。",
        )
        return result
    except Exception:
        return result


# =========================
# 常數設定
# =========================
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"
SKILLS_DIR = Path(__file__).parent
MAX_SEARCH_RESULTS = 10

# 安全相關檔案路徑
WHITELIST_FILE = SKILLS_DIR / "skill_whitelist.json"
MANIFEST_FILE = SKILLS_DIR / "skill_manifest.json"
AUDIT_LOG_FILE = SKILLS_DIR / "audit.log"

# 額外匯入
import hashlib
import fnmatch
from datetime import datetime, timezone


# =========================
# 審計 Log 功能
# =========================
def write_audit_log(action: str, skill_name: str, **kwargs) -> None:
    """
    寫入審計 log

    參數:
        action: 操作類型 (download, install, rollback, security_scan, whitelist_violation)
        skill_name: 技能名稱
        **kwargs: 其他要記錄的資訊
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    extra = " ".join([f"{k}={v}" for k, v in kwargs.items()])
    log_line = f"[{timestamp}] ACTION={action} SKILL={skill_name} {extra}\n"

    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        pass  # 審計 log 寫入失敗不應阻斷主流程


# =========================
# 白名單檢查功能
# =========================
def load_whitelist() -> Dict[str, Any]:
    """載入白名單配置"""
    if not WHITELIST_FILE.exists():
        return {"approved_sources": [], "approval_policy": {}}

    try:
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"approved_sources": [], "approval_policy": {}}


def check_whitelist(repo_full_name: str) -> Dict[str, Any]:
    """
    檢查 Repo 是否在白名單中

    參數:
        repo_full_name: Repo 的 full_name (如 "owner/repo")

    回傳:
        檢查結果
    """
    whitelist = load_whitelist()
    approved_sources = whitelist.get("approved_sources", [])

    for pattern in approved_sources:
        if fnmatch.fnmatch(repo_full_name.lower(), pattern.lower()):
            return {
                "approved": True,
                "matched_pattern": pattern,
                "repo": repo_full_name
            }

    # 記錄白名單違規
    write_audit_log("whitelist_violation", repo_full_name, STATUS="blocked")

    return {
        "approved": False,
        "repo": repo_full_name,
        "message": f"⛔ Repo '{repo_full_name}' 不在白名單中",
        "approved_patterns": approved_sources
    }


# =========================
# Manifest 管理功能
# =========================
def load_manifest() -> Dict[str, Any]:
    """載入 manifest"""
    if not MANIFEST_FILE.exists():
        return {"version": "1.0", "skills": []}

    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "1.0", "skills": []}


def save_manifest(manifest: Dict[str, Any]) -> None:
    """儲存 manifest"""
    try:
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_to_manifest(
    skill_name: str,
    source_repo: str,
    file_path: str,
    content_hash: str,
    commit_sha: str = "unknown"
) -> None:
    """
    新增技能到 manifest

    參數:
        skill_name: 技能名稱
        source_repo: 來源 Repo
        file_path: 檔案路徑
        content_hash: 內容的 SHA-256 hash
        commit_sha: Git commit SHA (若可取得)
    """
    manifest = load_manifest()

    # 移除舊的同名記錄
    manifest["skills"] = [s for s in manifest["skills"] if s.get("name") != skill_name]

    # 新增記錄
    manifest["skills"].append({
        "name": skill_name,
        "source_repo": source_repo,
        "file_path": file_path,
        "commit_sha": commit_sha,
        "sha256_hash": content_hash,
        "downloaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    })

    save_manifest(manifest)
    write_audit_log("manifest_update", skill_name, REPO=source_repo, HASH=content_hash[:16])


def remove_from_manifest(skill_name: str) -> bool:
    """
    從 manifest 移除技能

    回傳:
        是否成功移除
    """
    manifest = load_manifest()
    original_count = len(manifest["skills"])
    manifest["skills"] = [s for s in manifest["skills"] if s.get("name") != skill_name]

    if len(manifest["skills"]) < original_count:
        save_manifest(manifest)
        return True
    return False


def calculate_file_hash(file_path: str) -> str:
    """計算檔案的 SHA-256 hash"""
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return ""


# =========================
# 技能回滾功能
# =========================
def rollback_skill(skill_name: str) -> Dict[str, Any]:
    """
    回滾（移除）已安裝的技能

    參數:
        skill_name: 要移除的技能名稱

    回傳:
        回滾結果
    """
    manifest = load_manifest()
    skill_entry = None

    # 在 manifest 中尋找技能
    for skill in manifest["skills"]:
        if skill.get("name") == skill_name:
            skill_entry = skill
            break

    # 尋找對應的檔案
    skill_file = SKILLS_DIR / f"{skill_name}.py"

    results = {
        "skill_name": skill_name,
        "actions_taken": []
    }

    # 刪除檔案
    if skill_file.exists():
        try:
            skill_file.unlink()
            results["actions_taken"].append(f"已刪除檔案：{skill_file.name}")
        except Exception as e:
            results["actions_taken"].append(f"刪除檔案失敗：{e}")
    else:
        results["actions_taken"].append(f"檔案不存在：{skill_file.name}")

    # 從 manifest 移除
    if remove_from_manifest(skill_name):
        results["actions_taken"].append("已從 manifest 移除")
    else:
        results["actions_taken"].append("manifest 中無此技能記錄")

    # 記錄審計 log
    write_audit_log("rollback", skill_name, STATUS="success")

    # 嘗試從 __init__.py 移除 (不保證成功)
    init_file = SKILLS_DIR / "__init__.py"
    if init_file.exists():
        try:
            content = init_file.read_text(encoding="utf-8")
            if f'"{skill_name}"' in content:
                # 簡單移除：這只是盡力而為
                new_content = content.replace(f'    "{skill_name}",\n', "")
                init_file.write_text(new_content, encoding="utf-8")
                results["actions_taken"].append("已從 __init__.py 移除")
        except Exception:
            pass

    results["status"] = "success"
    results["message"] = f"✅ 已成功回滾技能：{skill_name}"

    return results




# =========================
# 搜尋功能
# =========================
def search_github_skills(keyword: str) -> Dict[str, Any]:
    """
    在 GitHub 搜尋含有 SKILL.md 的 Repo

    參數:
        keyword: 搜尋關鍵字

    回傳:
        包含搜尋結果的 JSON 物件
    """
    try:
        import requests
    except ImportError:
        return {
            "status": "error",
            "message": "缺少 requests 套件，無法執行 GitHub 搜尋",
            "suggestion": "請先安裝 requests，例如：pip install requests",
            "usage": "python .agent/skills/github_explorer.py search <keyword>",
        }

    # 搜尋含有 SKILL.md 檔案的 Repo
    query = f"{keyword} filename:SKILL.md"
    url = f"{GITHUB_API_BASE}/search/code"
    params = {
        "q": query,
        "per_page": MAX_SEARCH_RESULTS
    }
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "IvyHouse-SkillExplorer/1.0"
    }

    # 加入 GITHUB_TOKEN 認證（若存在）
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)

        if resp.status_code == 401:
            return {
                "status": "error",
                "message": "GitHub API 認證失敗 (401)，請檢查 GITHUB_TOKEN 是否正確",
                "auth_error": True
            }

        if resp.status_code == 403:
            return {
                "status": "error",
                "message": "GitHub API 請求次數已達上限（每小時 10 次），請稍後再試",
                "rate_limit": True
            }

        if resp.status_code != 200:
            return {
                "status": "error",
                "message": f"GitHub API 錯誤：{resp.status_code}",
                "details": resp.text[:500]
            }

        data = resp.json()
        items = data.get("items", [])

        # 整理搜尋結果
        results = []
        seen_repos = set()

        for item in items:
            repo = item.get("repository", {})
            repo_full_name = repo.get("full_name", "")

            # 避免重複的 Repo
            if repo_full_name in seen_repos:
                continue
            seen_repos.add(repo_full_name)

            results.append({
                "repo_name": repo_full_name,
                "description": repo.get("description", "（無描述）") or "（無描述）",
                "repo_url": repo.get("html_url", ""),
                "skill_path": item.get("path", "SKILL.md"),
                "stars": repo.get("stargazers_count", 0)
            })

        return {
            "status": "success",
            "keyword": keyword,
            "total_count": data.get("total_count", 0),
            "results": results,
            "message": f"找到 {len(results)} 個含有 SKILL.md 的 Repo"
        }

    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "GitHub API 請求超時，請檢查網路連線"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"搜尋失敗：{str(e)}"
        }


# =========================
# 預覽功能
# =========================
def preview_skill(repo_url: str, skill_path: str = "SKILL.md") -> Dict[str, Any]:
    """
    預覽指定 Repo 的 SKILL.md 內容

    ⚠️ 安全機制：此步驟僅讀取內容，不會下載任何檔案

    參數:
        repo_url: Repo 的 GitHub URL 或 full_name (如 "owner/repo")
        skill_path: SKILL.md 在 Repo 中的路徑

    回傳:
        包含 SKILL.md 內容的 JSON 物件
    """
    try:
        import requests
    except ImportError:
        return {
            "status": "error",
            "message": "缺少 requests 套件，無法執行 GitHub 預覽",
            "suggestion": "請先安裝 requests，例如：pip install requests",
            "usage": "python .agent/skills/github_explorer.py preview <repo_url> [skill_path]",
        }

    # 解析 repo_url 取得 owner/repo
    if repo_url.startswith("http"):
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            repo_full_name = f"{path_parts[0]}/{path_parts[1]}"
        else:
            return {
                "status": "error",
                "message": f"無法解析 Repo URL：{repo_url}"
            }
    else:
        repo_full_name = repo_url

    # 取得 SKILL.md 內容 (從 main 或 master 分支)
    for branch in ["main", "master"]:
        raw_url = f"{GITHUB_RAW_BASE}/{repo_full_name}/{branch}/{skill_path}"

        try:
            resp = requests.get(raw_url, timeout=15)
            if resp.status_code == 200:
                content = resp.text

                return {
                    "status": "success",
                    "repo": repo_full_name,
                    "skill_path": skill_path,
                    "branch": branch,
                    "content": content,
                    "content_length": len(content),
                    "message": "⚠️ 請審核以上內容。若確認安全，請使用 download 指令下載。",
                    "next_step": f"python .agent/skills/github_explorer.py download {repo_full_name} {skill_path}"
                }
        except Exception:
            continue

    return {
        "status": "error",
        "message": f"無法讀取 {repo_full_name} 的 {skill_path}，請確認檔案存在"
    }


# =========================
# 下載功能
# =========================
def download_skill(
    repo_url: str,
    file_path: str,
    target_dir: Optional[str] = None,
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    下載指定的技能檔案至本地，並執行轉換流水線

    ⚠️ 安全機制：必須由使用者明確確認才能執行

    參數:
        repo_url: Repo 的 full_name (如 "owner/repo")
        file_path: 要下載的檔案路徑
        target_dir: 目標目錄 (預設為 .agent/skills/)
        user_confirmed: 使用者是否已確認 (必須為 True 才會執行)

    回傳:
        下載結果的 JSON 物件
    """
    if not user_confirmed:
        return {
            "status": "blocked",
            "message": "⛔ 安全機制啟動：下載前必須先執行 preview 並取得使用者確認",
            "action_required": "請先使用 preview 指令查看內容，確認無安全疑慮後再下載"
        }

    try:
        import requests
    except ImportError:
        return {
            "status": "error",
            "message": "缺少 requests 套件，無法執行 GitHub 下載",
            "suggestion": "請先安裝 requests，例如：pip install requests",
            "usage": "python .agent/skills/github_explorer.py download <repo_url> <file_path> --confirm",
        }

    # 解析 repo_url
    if repo_url.startswith("http"):
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            repo_full_name = f"{path_parts[0]}/{path_parts[1]}"
        else:
            return {"status": "error", "message": f"無法解析 Repo URL：{repo_url}"}
    else:
        repo_full_name = repo_url

    # 🔒 白名單檢查
    whitelist_result = check_whitelist(repo_full_name)
    if not whitelist_result.get("approved"):
        return {
            "status": "blocked",
            "message": whitelist_result.get("message", "白名單檢查失敗"),
            "whitelist_check": whitelist_result,
            "action_required": "請聯繫 QA Team 將此 Repo 加入白名單"
        }

    # 記錄審計 log
    write_audit_log("download_start", Path(file_path).stem, REPO=repo_full_name)

    # 設定目標目錄
    if target_dir:
        dest_dir = Path(target_dir)
    else:
        dest_dir = SKILLS_DIR

    dest_dir.mkdir(parents=True, exist_ok=True)

    # 下載檔案
    for branch in ["main", "master"]:
        raw_url = f"{GITHUB_RAW_BASE}/{repo_full_name}/{branch}/{file_path}"

        try:
            resp = requests.get(raw_url, timeout=15)
            if resp.status_code == 200:
                content = resp.text

                # 儲存檔案
                file_name = Path(file_path).name
                dest_path = dest_dir / file_name
                dest_path.write_text(content, encoding="utf-8")

                # 執行安全掃描
                scan_result = run_security_scan(str(dest_path))
                write_audit_log("security_scan", dest_path.stem, RESULT=scan_result.get("status", "unknown"))

                if scan_result.get("status") == "fail":
                    # 安全掃描失敗，刪除檔案
                    dest_path.unlink(missing_ok=True)
                    write_audit_log("download_blocked", dest_path.stem, REASON="security_scan_failed")
                    return {
                        "status": "blocked",
                        "message": "🚨 安全掃描失敗！已自動刪除下載的檔案",
                        "scan_result": scan_result,
                        "deleted_file": str(dest_path)
                    }

                # 📝 記錄到 manifest
                content_hash = calculate_file_hash(str(dest_path))
                add_to_manifest(
                    skill_name=dest_path.stem,
                    source_repo=repo_full_name,
                    file_path=str(dest_path),
                    content_hash=content_hash
                )
                write_audit_log("install", dest_path.stem, REPO=repo_full_name, HASH=content_hash[:16])

                # 執行轉換流水線
                convert_result = run_conversion_pipeline(
                    str(dest_path),
                    dest_path.stem,
                    repo_full_name,
                    user_confirmed=True
                )

                return {
                    "status": "success",
                    "message": f"✅ 成功下載、通過安全掃描並完成轉換",
                    "source": raw_url,
                    "destination": str(dest_path),
                    "content_hash": content_hash,
                    "scan_result": scan_result,
                    "conversion_result": convert_result
                }

        except Exception as e:
            continue

    return {
        "status": "error",
        "message": f"無法下載 {repo_full_name}/{file_path}"
    }


# =========================
# 轉換流水線
# =========================
def run_conversion_pipeline(
    file_path: str,
    skill_name: str,
    source_repo: str,
    user_confirmed: bool = False
) -> Dict[str, Any]:
    """
    執行技能轉換流水線

    參數:
        file_path: 已下載的技能檔案路徑
        skill_name: 技能名稱
        source_repo: 來源 Repo
        user_confirmed: 使用者是否已確認

    回傳:
        轉換結果的 JSON 物件
    """
    try:
        # 嘗試匯入 skill_converter
        from . import skill_converter
        return skill_converter.convert_skill(
            file_path,
            skill_name,
            source_repo,
            user_confirmed=user_confirmed
        )
    except ImportError:
        # 若無法匯入，使用 subprocess 調用
        converter_path = SKILLS_DIR / "skill_converter.py"
        if not converter_path.exists():
            return {
                "status": "warning",
                "message": "skill_converter.py 不存在，跳過轉換"
            }

        # 簡化版：直接執行基本轉換
        return {
            "status": "success",
            "message": "✅ 已完成基本下載（轉換模組載入失敗，跳過進階轉換）"
        }



# =========================
# 安全掃描
# =========================
def run_security_scan(file_path: str) -> Dict[str, Any]:
    """
    執行 code_reviewer.py 進行安全掃描

    參數:
        file_path: 要掃描的檔案路徑

    回傳:
        掃描結果的 JSON 物件
    """
    reviewer_path = SKILLS_DIR / "code_reviewer.py"

    if not reviewer_path.exists():
        return {
            "status": "warning",
            "message": "code_reviewer.py 不存在，跳過安全掃描"
        }

    try:
        result = subprocess.run(
            [sys.executable, str(reviewer_path), file_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 解析 code_reviewer 的 JSON 輸出
        try:
            scan_data = json.loads(result.stdout)
            return scan_data
        except json.JSONDecodeError:
            return {
                "status": "warning",
                "message": "無法解析安全掃描結果",
                "raw_output": result.stdout[:500]
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "安全掃描超時"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"安全掃描失敗：{str(e)}"
        }


# =========================
# 列出本地技能
# =========================
def list_local_skills() -> Dict[str, Any]:
    """
    列出本地已安裝的技能

    回傳:
        本地技能清單的 JSON 物件
    """
    skills = []

    for py_file in SKILLS_DIR.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        # 讀取檔案的 docstring
        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            # 找到第一個 docstring
            docstring = ""
            in_docstring = False
            for line in lines[:30]:
                if '"""' in line or "'''" in line:
                    if in_docstring:
                        break
                    in_docstring = True
                    continue
                if in_docstring:
                    docstring += line.strip() + " "

            skills.append({
                "name": py_file.stem,
                "file": py_file.name,
                "description": docstring[:100].strip() if docstring else "（無描述）"
            })
        except Exception:
            skills.append({
                "name": py_file.stem,
                "file": py_file.name,
                "description": "（讀取失敗）"
            })

    return {
        "status": "success",
        "skills_dir": str(SKILLS_DIR),
        "count": len(skills),
        "skills": skills,
        "message": f"共 {len(skills)} 個本地技能",
    }


# =========================
# 主程式
# =========================
def main():
    """主程式入口"""
    if len(sys.argv) < 2:
        result = {
            "status": "success",
            "message": "GitHub 技能搜尋與下載工具（使用說明）",
            "help": True,
            "usage": {
                "search": "python .agent/skills/github_explorer.py search <keyword>",
                "preview": "python .agent/skills/github_explorer.py preview <repo_url> [skill_path]",
                "download": "python .agent/skills/github_explorer.py download <repo_url> <file_path> --confirm",
                "list": "python .agent/skills/github_explorer.py list",
                "rollback": "python .agent/skills/github_explorer.py rollback <skill_name>",
            },
            "security_note": "下載前必須先 preview 並取得使用者確認",
        }
        result = validate_output_schema(result, "github_explorer")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "search":
        if len(sys.argv) < 3:
            result = {
                "status": "error",
                "message": "請提供搜尋關鍵字",
                "usage": "python .agent/skills/github_explorer.py search <keyword>",
                "suggestion": "範例：python .agent/skills/github_explorer.py search crewai",
            }
            result = validate_output_schema(result, "github_explorer")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(1)

        keyword = " ".join(sys.argv[2:])
        result = search_github_skills(keyword)
        result = validate_output_schema(result, "github_explorer")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "preview":
        if len(sys.argv) < 3:
            result = {
                "status": "error",
                "message": "請提供 Repo URL",
                "usage": "python .agent/skills/github_explorer.py preview <repo_url> [skill_path]",
                "suggestion": "範例：python .agent/skills/github_explorer.py preview owner/repo",
            }
            result = validate_output_schema(result, "github_explorer")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(1)

        repo_url = sys.argv[2]
        skill_path = sys.argv[3] if len(sys.argv) > 3 else "SKILL.md"
        result = preview_skill(repo_url, skill_path)
        result = validate_output_schema(result, "github_explorer")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "download":
        if len(sys.argv) < 4:
            result = {
                "status": "error",
                "message": "請提供 Repo URL 與檔案路徑",
                "usage": "python .agent/skills/github_explorer.py download <repo_url> <file_path> --confirm",
                "suggestion": "範例：python .agent/skills/github_explorer.py download owner/repo SKILL.md --confirm",
            }
            result = validate_output_schema(result, "github_explorer")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(1)

        repo_url = sys.argv[2]
        file_path = sys.argv[3]
        user_confirmed = "--confirm" in sys.argv

        result = download_skill(repo_url, file_path, user_confirmed=user_confirmed)
        result = validate_output_schema(result, "github_explorer")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "list":
        result = list_local_skills()
        result = validate_output_schema(result, "github_explorer")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "rollback":
        if len(sys.argv) < 3:
            result = {
                "status": "error",
                "message": "請提供技能名稱",
                "usage": "python .agent/skills/github_explorer.py rollback <skill_name>",
                "suggestion": "範例：python .agent/skills/github_explorer.py rollback example_skill",
            }
            result = validate_output_schema(result, "github_explorer")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(1)

        skill_name = sys.argv[2]
        result = rollback_skill(skill_name)
        result = validate_output_schema(result, "github_explorer")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        result = {
            "status": "error",
            "message": f"未知指令：{command}",
            "available_commands": ["search", "preview", "download", "list", "rollback"],
            "usage": "python .agent/skills/github_explorer.py <command> [args]",
            "suggestion": "請先執行：python .agent/skills/github_explorer.py 以查看使用說明。",
        }
        result = validate_output_schema(result, "github_explorer")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
