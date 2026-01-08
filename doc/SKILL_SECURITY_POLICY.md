# Skills 供應鏈安全政策

**版本**：1.0  
**最後更新**：2026-01-04  
**負責人**：QA Team

---

## 📋 目的

本政策定義 Ivy House Agent Skills 的**供應鏈安全管理規範**，確保從 GitHub 下載的外部技能：
1. 來源可信
2. 內容安全
3. 可追溯審計
4. 可快速回滾

---

## 🔒 安全原則

### 1. 來源白名單制度

所有技能下載必須來自**預先批准的 GitHub 組識或使用者**。

**白名單檔案**：`.agent/skills/skill_whitelist.json`

**白名單格式**：
```json
{
  "version": "1.0",
  "approved_sources": [
    "openai/*",
    "google/*",
    "anthropic/*",
    "ivyhouse-tw/*"
  ],
  "last_updated": "2026-01-04T00:00:00Z"
}
```

**檢查邏輯**：
- ✅ 允許：`github.com/openai/crewai-skills`
- ❌ 拒絕：`github.com/random-user/untrusted-script`

---

### 2. 版本固定與 Hash 驗證

**禁止浮動版本**：不允許「latest」或「main」，必須固定 commit SHA。

**Manifest 記錄檔案**：`.agent/skills/skill_manifest.json`

**Manifest 格式**：
```json
{
  "skills": [
    {
      "name": "example_skill",
      "source_repo": "openai/crewai-skills",
      "commit_sha": "abc123def456...",
      "file_path": "skills/example.py",
      "downloaded_at": "2026-01-04T01:30:00Z",
      "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "license": "MIT",
      "approved_by": "user@ivyhouse.tw"
    }
  ]
}
```

**驗證流程**：
1. 下載後立即計算 SHA-256
2. 記錄到 manifest
3. 每次載入時重新驗證 hash
4. 若 hash 不符，拒絕執行並告警

---

### 3. 審計追蹤

所有操作記錄到：`.agent/skills/audit.log`

**審計 Log 格式**：
```
[2026-01-04T01:30:00Z] ACTION=download SKILL=example_skill REPO=openai/crewai-skills COMMIT=abc123 STATUS=success USER=antigravity
[2026-01-04T01:30:05Z] ACTION=security_scan SKILL=example_skill RESULT=pass ISSUES=0
[2026-01-04T01:30:10Z] ACTION=install SKILL=example_skill LOCATION=.agent/skills/example_skill.py
```

**必須記錄的事件**：
- `download`：技能下載
- `security_scan`：安全掃描結果
- `install`：安裝到檔案系統
- `rollback`：回滾操作
- `whitelist_violation`：白名單違規嘗試

---

### 4. 安全掃描

每個下載的技能必須通過：
1. **靜態掃描**：`code_reviewer.py` 檢查 API Key 洩漏
2. **Hash 驗證**：確認檔案完整性
3. **語法檢查**：Python 語法正確性

**掃描失敗處理**：
- 自動刪除已下載檔案
- 記錄到 audit.log
- 通知使用者

---

### 5. 權限隔離與 Sandbox (未來)

**當前限制**：
- Skills 在主 Python 程序中執行
- 無檔案系統隔離

**未來計畫** (Phase 4)：
- [ ] 使用 Docker 容器隔離
- [ ] 限制網路存取
- [ ] 限制檔案寫入範圍
- [ ] 資源配額 (CPU/Memory)

---

## 🔄 快速審批流程

若需要新增白名單 Repo：

1. **提交申請**：說明 Repo 用途與信任來源
2. **安全審查**：QA 檢查 Repo 歷史、維護者、Star 數
3. **批准記錄**：更新 `skill_whitelist.json`
4. **通知團隊**：更新 Implementation Plan

**審批標準**：
- ✅ 官方組織 (OpenAI, Google, Anthropic)
- ✅ Star > 1000 且活躍維護
- ✅ 有明確 LICENSE
- ❌ 個人帳號 (除非特別批准)
- ❌ 近期無更新 (>6個月)

---

## 🆘 技能回滾

**指令**：
```bash
python .agent/skills/github_explorer.py rollback <skill_name>
```

**回滾流程**：
1. 檢查 manifest 是否存在該技能
2. 刪除對應的 `.py` 檔案
3. 從 `__init__.py` 移除
4. 從 `SKILL.md` 移除
5. 記錄到 audit.log

---

## 📊 定期審計

**每月審計清單**：
- [ ] 檢查所有已安裝技能的來源 Repo 是否仍然活躍
- [ ] 檢查是否有新版本 (commit 更新)
- [ ] 檢查 license 變更
- [ ] 檢查白名單是否需要更新
- [ ] 檢查 audit.log 是否有異常活動

---

## ⚠️ 違規處理

**自動阻止**：
- 非白名單 Repo → 拒絕下載
- Hash 驗證失敗 → 自動刪除
- 安全掃描失敗 → 拒絕安裝

**人工介入**：
- 發現惡意代碼 → 立即回滾並封鎖來源
- 重複違規嘗試 → 審查使用者權限

---

## 📚 參考文件

- [工程補強計畫](file:///C:/Users/forev/.gemini/antigravity/brain/943d9e5e-52e6-4be3-965f-1193d4130cb0/engineering_reinforcement_plan.md)
- [工程待辦清單](file:///C:/Users/forev/.gemini/antigravity/brain/943d9e5e-52e6-4be3-965f-1193d4130cb0/engineering_backlog.md)
- [Ivy House Rules](file:///c:/Users/forev/OneDrive/4-管理專用/Jonas/AI生成/廣告數據報告/ivyhousetw%20ad%20analyzer/Ivyhousetw-META/ivy_house_rules.md)
