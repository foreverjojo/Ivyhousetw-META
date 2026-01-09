# 後續步驟執行清單

**日期**: 2026-01-10
**用途**: 供用戶逐項完成後續工作

---

## ⚡ 立即執行（今天完成）

### 1. ✅ 驗證所有工具已建立

檢查以下檔案是否存在：

```powershell
# 核心工具
ls scripts/check_active_task.py
ls scripts/validate_state_gate.py
ls scripts/task_branch.py
ls scripts/validate_log.py
ls scripts/check_verification_due.py
ls scripts/backup_logs.py

# 配置檔案
ls .pre-commit-config.yaml
ls .gitignore

# 文檔
ls doc/workflow_completion_summary.md
ls doc/workflow_quick_reference.md
ls doc/gcp_key_revocation_guide.md

# 資料夾
ls doc/logs/
ls doc/plans/
ls doc/adr/
```

---

### 2. 🔧 安裝 Pre-commit Hooks

```powershell
# 安裝 pre-commit 套件
pip install pre-commit

# 安裝 Git hooks
pre-commit install

# 安裝 commit-msg hook（用於 State Gate 驗證）
pre-commit install --hook-type commit-msg

# 測試所有 hooks
pre-commit run --all-files
```

**驗收標準**:
- ✅ 無錯誤訊息
- ✅ 顯示所有 hooks 執行結果

---

### 3. 🧪 測試核心工具

#### 3.1 任務鎖管理

```powershell
# 查看狀態
python scripts/check_active_task.py status

# 取得測試鎖
python scripts/check_active_task.py acquire Idx-999

# 再次查看（應顯示鎖定狀態）
python scripts/check_active_task.py status

# 釋放鎖
python scripts/check_active_task.py release Idx-999

# 最後檢查（應無鎖）
python scripts/check_active_task.py status
```

**驗收標準**:
- ✅ 顯示 TTL 和過期時間
- ✅ 防止重複取得鎖
- ✅ 正常釋放鎖

---

#### 3.2 State Gate 驗證

```powershell
# 測試正確格式
python scripts/validate_state_gate.py "feat(Idx-003): 測試功能"

# 測試錯誤格式（應失敗）
python scripts/validate_state_gate.py "feat: 沒有 Index"

# 測試豁免格式
python scripts/validate_state_gate.py "chore: 更新依賴"
```

**驗收標準**:
- ✅ 正確格式通過驗證
- ✅ 錯誤格式被阻擋
- ✅ 豁免格式正常運作

---

#### 3.3 Log 驗證

```powershell
# 驗證所有 Logs（目前應該只有 template）
python scripts/validate_log.py --all
```

**驗收標準**:
- ✅ 腳本正常執行
- ✅ Schema 載入成功

---

#### 3.4 備份工具

```powershell
# 建立第一份備份
python scripts/backup_logs.py

# 列出備份
python scripts/backup_logs.py --list

# 檢查 backups 資料夾
ls backups/
```

**驗收標準**:
- ✅ 備份檔案已建立（.tar.gz）
- ✅ `backups/` 資料夾已建立
- ✅ 可列出備份清單

---

### 4. 🔐 作廢 GCP 私鑰（最重要！）

**詳細步驟**: 參考 `doc/gcp_key_revocation_guide.md`

**快速步驟**:

1. 前往 [GCP Console - Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. 選擇專案：`ivyhouse-ad-analyzer`
3. 找到 Service Account（`firebase-adminsdk-...`）
4. 點擊「金鑰」分頁
5. 找到洩漏的金鑰（Key ID: `e3a920e555a7...`）
6. 點擊「刪除」並確認
7. 建立新金鑰（JSON 格式）
8. 下載並安全儲存新金鑰
9. 更新部署設定（Secret Manager 或環境變數）
10. 測試新金鑰可正常運作

**驗收標準**:
- ✅ 舊金鑰已從 GCP Console 刪除
- ✅ 新金鑰已建立並下載
- ✅ 新金鑰已上傳到 Secret Manager
- ✅ 測試腳本確認新金鑰可用

---

## 📅 短期任務（1-2 週內）

### 5. 🔄 執行完整工作流程測試

建立一個真實任務並走完整流程：

```powershell
# 1. 確認 Index 已在 implementation_plan_index.md 中註冊
# 2. 建立 Plan: doc/plans/Idx-XXX_plan.md

# 3. 建立分支
python scripts/task_branch.py create Idx-XXX

# 4. 取得鎖
python scripts/check_active_task.py acquire Idx-XXX

# 5. 實作功能
# ... 編輯檔案 ...

# 6. 提交變更
git add .
git commit -m "feat(Idx-XXX): 實作功能"
# → Pre-commit hooks 會自動驗證

# 7. QA 審查
# ... QA 測試 ...

# 8. 合併分支
python scripts/task_branch.py merge Idx-XXX

# 9. 釋放鎖
python scripts/check_active_task.py release Idx-XXX

# 10. 完成 Log
# 建立 doc/logs/Idx-XXX_log.md（使用範本）

# 11. 驗證 Log
python scripts/validate_log.py doc/logs/Idx-XXX_log.md

# 12. 更新 Index
# 在 implementation_plan_index.md 中標記為 COMPLETED
```

**驗收標準**:
- ✅ 完整流程無阻礙
- ✅ 所有工具正常運作
- ✅ Log 驗證通過
- ✅ Index 已更新

---

### 6. 📝 補充 ADR

為其他重要技術決策建立 ADR：

```powershell
# 範例：Meta API 選型
# 複製範本
cp doc/adr/0000-template.md doc/adr/0004-meta-api-integration.md

# 編輯並填寫
# ... 編輯檔案 ...

# 更新 ADR 索引
# 編輯 doc/adr/README.md
```

**建議 ADR 主題**:
- Meta API 整合策略
- Cloud Run 部署決策
- 資料庫選型（若有）
- 快取策略（若有）

---

### 7. 🐛 記錄技術債

將現有已知的技術債務記錄到 `doc/tech_debt.md`：

```markdown
| TD-001 | skill_converter.py AST 檢查失敗 | Medium | 2h | - | 2026-01-10 | OPEN |
| TD-002 | debug_pipeline.py docstring 問題 | Low | 1h | - | 2026-01-10 | OPEN |
```

**驗收標準**:
- ✅ 至少記錄 5 個已知技術債
- ✅ 每個都有優先級和預估工作量

---

## 🔄 定期維護設定

### 8. 設定提醒

在您的日曆或任務管理工具中設定：

#### 每週（例如每週一）
- [ ] 執行：`python scripts/check_verification_due.py`
- [ ] 檢視：`doc/tech_debt.md`
- [ ] 檢查：`python scripts/check_active_task.py status`

#### 每月（例如每月 1 日）
- [ ] 執行：`python scripts/backup_logs.py`
- [ ] 執行：`pre-commit autoupdate`
- [ ] 清理合併後的分支：`git branch --merged | grep -v main | xargs git branch -d`

#### 每季（例如 1/4/7/10 月 1 日）
- [ ] 檢視並規劃技術債清償
- [ ] 檢視並補充 ADR
- [ ] 輪換 GCP 金鑰（90 天週期）

---

## 📊 驗收確認

完成上述所有步驟後，確認：

### 立即執行
- [ ] 所有工具檔案已建立
- [ ] Pre-commit hooks 已安裝並測試
- [ ] 任務鎖管理測試通過
- [ ] State Gate 驗證測試通過
- [ ] Log 驗證測試通過
- [ ] 備份工具測試通過
- [ ] **GCP 私鑰已作廢並更新**

### 短期任務
- [ ] 至少執行一次完整工作流程
- [ ] 至少建立一個新 ADR
- [ ] 至少記錄 5 個技術債務

### 定期維護
- [ ] 日曆提醒已設定
- [ ] 了解各項維護任務的執行方式

---

## 🎯 完成標準

當您能夠：

1. ✅ 在不查閱文檔的情況下啟動新任務
2. ✅ Pre-commit hooks 自動運作且無阻礙
3. ✅ 使用備份工具建立定期備份
4. ✅ GCP 私鑰已更新且系統正常運作
5. ✅ 技術債務有明確的追蹤和規劃

**則表示 Workflow 治理框架已完全整合到您的日常工作流程中！**

---

## 📞 需要幫助？

- **工具使用**: 參考 `doc/workflow_quick_reference.md`
- **詳細說明**: 參考 `doc/workflow_implementation_report.md`
- **GCP 操作**: 參考 `doc/gcp_key_revocation_guide.md`

---

**清單建立日期**: 2026-01-10
**預計完成日期**: 2026-01-17
**下次檢視**: 2026-01-24

祝執行順利！🚀
