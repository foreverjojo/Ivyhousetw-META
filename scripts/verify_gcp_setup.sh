#!/bin/bash

#
# GCP + OAuth 環境驗證腳本
#
# 用途：檢查本機和 Google Cloud 環境是否已正確設置，
#      用於在部署前驗證。
#
# 用法：bash scripts/verify_gcp_setup.sh [PROJECT_ID]
#

set -e

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 預設 project ID
PROJECT_ID="${1:-ivyhouse-ad-analyzer}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Google Cloud OAuth Token 自動化 - 環境驗證                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 計數器
CHECKS_PASSED=0
CHECKS_FAILED=0

# ==================== 1. 檢查本機前置條件 ====================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔍 第 1 部分：本機前置條件${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# 檢查 gcloud CLI
printf "[檢查] gcloud CLI 已安裝... "
if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud --version | head -1)
    echo -e "${GREEN}✓${NC} $GCLOUD_VERSION"
    ((++CHECKS_PASSED))
else
    echo -e "${RED}✗ 缺失${NC} (安裝：https://cloud.google.com/sdk/docs/install)"
    ((++CHECKS_FAILED))
fi

# 檢查 curl
printf "[檢查] curl 已安裝... "
if command -v curl &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
    ((++CHECKS_PASSED))
else
    echo -e "${RED}✗ 缺失${NC}"
    ((++CHECKS_FAILED))
fi

# 檢查 jq
printf "[檢查] jq 已安裝... "
if command -v jq &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
    ((++CHECKS_PASSED))
else
    echo -e "${YELLOW}⚠${NC} 缺失（非必需，但建議安裝）"
    ((++CHECKS_FAILED))
fi

# 檢查 Python
printf "[檢查] Python 3.11+ 已安裝... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} $PYTHON_VERSION"
    ((++CHECKS_PASSED))
else
    echo -e "${RED}✗ 缺失${NC}"
    ((++CHECKS_FAILED))
fi

echo ""

# ==================== 2. 檢查本地檔案和環境 ====================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔍 第 2 部分：本地檔案和環境${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# 檢查 ifp.env
printf "[檢查] ifp.env 存在... "
if [ -f "ifp.env" ]; then
    echo -e "${GREEN}✓${NC}"
    ((++CHECKS_PASSED))

    # 檢查 GOOGLE_DRIVE_ 環境變數
    printf "       ├─ GOOGLE_DRIVE_ACCESS_TOKEN 已設定... "
    if grep -q "GOOGLE_DRIVE_ACCESS_TOKEN=" ifp.env; then
        echo -e "${GREEN}✓${NC}"
        ((++CHECKS_PASSED))
    else
        echo -e "${YELLOW}⚠${NC} 缺失"
        ((++CHECKS_FAILED))
    fi

    printf "       ├─ GOOGLE_DRIVE_FOLDER_ID 已設定... "
    if grep -q "GOOGLE_DRIVE_FOLDER_ID=" ifp.env; then
        echo -e "${GREEN}✓${NC}"
        ((++CHECKS_PASSED))
    else
        echo -e "${YELLOW}⚠${NC} 缺失"
        ((++CHECKS_FAILED))
    fi

    printf "       └─ GOOGLE_DRIVE_CLIENT_SECRET 已設定... "
    if grep -q "GOOGLE_DRIVE_CLIENT_SECRET=" ifp.env; then
        echo -e "${GREEN}✓${NC}"
        ((++CHECKS_PASSED))
    else
        echo -e "${YELLOW}⚠${NC} 缺失"
        ((++CHECKS_FAILED))
    fi
else
    echo -e "${YELLOW}⚠${NC} 缺失"
    ((++CHECKS_FAILED))
fi

# 檢查 client secret JSON
printf "[檢查] client_secret*.json 檔案存在... "
if ls secrets/client_secret_*.json &> /dev/null; then
    SECRET_FILE=$(ls secrets/client_secret_*.json | head -1)
    echo -e "${GREEN}✓${NC} ($SECRET_FILE)"
    ((++CHECKS_PASSED))
else
    echo -e "${YELLOW}⚠${NC} 缺失"
    ((++CHECKS_FAILED))
fi

# 檢查 .gitignore
printf "[檢查] .gitignore 包含 secrets/、ifp.env、.env... "
GITIGNORE_OK=true
for pattern in "secrets/" "ifp.env" ".env"; do
    if ! grep -q "$pattern" .gitignore 2>/dev/null; then
        GITIGNORE_OK=false
        break
    fi
done

if [ "$GITIGNORE_OK" = true ]; then
    echo -e "${GREEN}✓${NC}"
    ((++CHECKS_PASSED))
else
    echo -e "${RED}✗ 未找到所有必要的模式${NC}"
    ((++CHECKS_FAILED))
fi

# 檢查部署腳本
printf "[檢查] 部署腳本存在... "
SCRIPTS_OK=true
for script in "scripts/setup_gcp_secrets.sh" "scripts/deploy_token_refresh_function.sh" "scripts/setup_cloud_scheduler.sh" "scripts/gcp_token_refresh_function.py"; do
    if [ ! -f "$script" ]; then
        SCRIPTS_OK=false
        break
    fi
done

if [ "$SCRIPTS_OK" = true ]; then
    echo -e "${GREEN}✓${NC}"
    ((++CHECKS_PASSED))
else
    echo -e "${RED}✗ 缺少部分腳本${NC}"
    ((++CHECKS_FAILED))
fi

echo ""

# ==================== 3. 檢查 GCP 連線 ====================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔍 第 3 部分：Google Cloud 連線${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# 檢查 gcloud 登入狀態
printf "[檢查] gcloud 已登入... "
if gcloud auth list 2>/dev/null | grep -q ACTIVE; then
    ACTIVE_ACCOUNT=$(gcloud config get-value account)
    echo -e "${GREEN}✓${NC} ($ACTIVE_ACCOUNT)"
    ((++CHECKS_PASSED))
else
    echo -e "${RED}✗ 未登入${NC} (執行：gcloud auth login)"
    ((++CHECKS_FAILED))
fi

# 檢查 GCP Project
printf "[檢查] GCP Project 已設定... "
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [ -z "$CURRENT_PROJECT" ]; then
    echo -e "${RED}✗ 未設定${NC}"
    echo "       執行：gcloud config set project $PROJECT_ID"
    ((++CHECKS_FAILED))
else
    if [ "$CURRENT_PROJECT" = "$PROJECT_ID" ]; then
        echo -e "${GREEN}✓${NC} ($CURRENT_PROJECT)"
        ((++CHECKS_PASSED))
    else
        echo -e "${YELLOW}⚠${NC} 當前：$CURRENT_PROJECT，期望：$PROJECT_ID"
        echo "       執行：gcloud config set project $PROJECT_ID"
        ((++CHECKS_FAILED))
    fi
fi

echo ""

# ==================== 4. 檢查 GCP APIs ====================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔍 第 4 部分：Google Cloud APIs 啟用狀態${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# 需要的 APIs
REQUIRED_APIS=(
    "secretmanager.googleapis.com"
    "cloudfunctions.googleapis.com"
    "cloudscheduler.googleapis.com"
    "cloudlogging.googleapis.com"
    "appengine.googleapis.com"
    "drive.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    printf "[檢查] $api... "
    if gcloud services list --enabled --project="$PROJECT_ID" 2>/dev/null | grep -q "$api"; then
        echo -e "${GREEN}✓${NC}"
        ((++CHECKS_PASSED))
    else
        echo -e "${YELLOW}⚠${NC} 未啟用（部署時自動啟用）"
        ((++CHECKS_FAILED))
    fi
done

echo ""

# ==================== 5. 檢查 Secret Manager ====================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔍 第 5 部分：Google Cloud Secret Manager${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# 檢查 secrets 是否存在
SECRETS_OK=true
REQUIRED_SECRETS=(
    "GOOGLE_DRIVE_CLIENT_ID"
    "GOOGLE_DRIVE_CLIENT_SECRET"
    "GOOGLE_DRIVE_ACCESS_TOKEN"
    "GOOGLE_DRIVE_FOLDER_ID"
    "GOOGLE_DRIVE_REFRESH_TOKEN"
)

printf "[檢查] Secret Manager 中的 Secrets... "
echo ""

for secret in "${REQUIRED_SECRETS[@]}"; do
    printf "       ├─ $secret... "
    if gcloud secrets describe "$secret" --project="$PROJECT_ID" &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        ((++CHECKS_PASSED))
    else
        echo -e "${YELLOW}○${NC} 未建立（可在初始化時建立）"
        ((++CHECKS_FAILED))
    fi
done

echo ""

# ==================== 6. 檢查 Cloud Function ====================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔍 第 6 部分：Cloud Function${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

printf "[檢查] Cloud Function 'refresh-oauth-token'... "
if gcloud functions describe refresh-oauth-token --gen2 --region=asia-east1 --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
    ((++CHECKS_PASSED))

    # 取得 Function URL
    printf "       ├─ Trigger URL... "
    FUNC_URL=$(gcloud functions describe refresh-oauth-token --gen2 --region=asia-east1 --project="$PROJECT_ID" --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
    if [ -n "$FUNC_URL" ]; then
        echo -e "${GREEN}✓${NC}"
        echo "           $FUNC_URL"
        ((++CHECKS_PASSED))
    else
        echo -e "${YELLOW}⚠${NC} 無法取得 URL"
        ((++CHECKS_FAILED))
    fi

    # 檢查最近的日志
    printf "       └─ 最近執行日志... "
    if gcloud functions logs read refresh-oauth-token --limit 1 --region=asia-east1 --project="$PROJECT_ID" &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        ((++CHECKS_PASSED))
    else
        echo -e "${YELLOW}○${NC} 無執行歷史"
        ((++CHECKS_FAILED))
    fi
else
    echo -e "${YELLOW}○${NC} 未部署（可執行部署腳本建立）"
    ((++CHECKS_FAILED))
fi

echo ""

# ==================== 7. 檢查 Cloud Scheduler ====================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔍 第 7 部分：Cloud Scheduler${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

printf "[檢查] Cloud Scheduler Job 'refresh-gdrive-token'... "
if gcloud scheduler jobs describe refresh-gdrive-token --location=asia-east1 --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
    ((++CHECKS_PASSED))

    # 檢查排程
    printf "       ├─ 排程設定... "
    SCHEDULE=$(gcloud scheduler jobs describe refresh-gdrive-token --location=asia-east1 --project="$PROJECT_ID" --format='value(schedule)' 2>/dev/null || echo "")
    if [ -n "$SCHEDULE" ]; then
        echo -e "${GREEN}✓${NC} (Cron: $SCHEDULE)"
        ((++CHECKS_PASSED))
    else
        echo -e "${YELLOW}⚠${NC} 無法取得排程"
        ((++CHECKS_FAILED))
    fi

    # 檢查狀態
    printf "       └─ Job 狀態... "
    JOB_STATE=$(gcloud scheduler jobs describe refresh-gdrive-token --location=asia-east1 --project="$PROJECT_ID" --format='value(state)' 2>/dev/null || echo "")
    if [ "$JOB_STATE" = "ENABLED" ]; then
        echo -e "${GREEN}✓${NC} (已啟用)"
        ((++CHECKS_PASSED))
    else
        echo -e "${YELLOW}⚠${NC} 狀態：$JOB_STATE"
        ((++CHECKS_FAILED))
    fi
else
    echo -e "${YELLOW}○${NC} 未配置（可執行 scheduler 設定腳本建立）"
    ((++CHECKS_FAILED))
fi

echo ""

# ==================== 8. 測試結果摘要 ====================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📊 驗證結果摘要${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

TOTAL_CHECKS=$((CHECKS_PASSED + CHECKS_FAILED))
PASS_PERCENTAGE=$((CHECKS_PASSED * 100 / TOTAL_CHECKS))

echo -e "✓ 通過檢查：${GREEN}$CHECKS_PASSED${NC}/$TOTAL_CHECKS"
echo -e "✗ 缺失/警告：${YELLOW}$CHECKS_FAILED${NC}/$TOTAL_CHECKS"
echo -e "完成度：${BLUE}$PASS_PERCENTAGE%${NC}"
echo ""

# ==================== 9. 建議和後續步驟 ====================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}💡 後續建議${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

if [ ${CHECKS_FAILED} -gt 0 ]; then
    if [ $PASS_PERCENTAGE -lt 50 ]; then
        echo -e "${RED}❌ 環境設置不完整，請先完成以下操作：${NC}"
        echo ""
        echo "1. 確保 gcloud 已正確登入："
        echo "   $ gcloud auth login"
        echo ""
        echo "2. 設定 GCP project："
        echo "   $ gcloud config set project $PROJECT_ID"
        echo ""
        echo "3. 檢查 ifp.env 和 client_secret*.json 檔案："
        echo "   $ ls -la ifp.env secrets/client_secret_*.json"
        echo ""
    elif [ $PASS_PERCENTAGE -lt 80 ]; then
        echo -e "${YELLOW}⚠️  環境設置大部分完成，建議執行以下操作：${NC}"
        echo ""
        echo "1. 初始化 Secret Manager："
        echo "   $ bash scripts/setup_gcp_secrets.sh $PROJECT_ID"
        echo ""
        echo "2. 部署 Cloud Function："
        echo "   $ bash scripts/deploy_token_refresh_function.sh $PROJECT_ID"
        echo ""
        echo "3. 配置 Cloud Scheduler："
        echo "   $ bash scripts/setup_cloud_scheduler.sh $PROJECT_ID <FUNCTION_URL>"
        echo ""
    else
        echo -e "${GREEN}✓ 環境設置幾乎完成！${NC}"
        echo ""
        echo "下一步：手動執行剩餘部署步驟或測試現有設置"
        echo ""
    fi
else
    echo -e "${GREEN}✓ 環境檢查全部通過！${NC}"
    echo ""
    echo "系統已準備好運行。"
    echo ""
    if [ -n "$FUNC_URL" ]; then
        echo "可選：手動測試 Cloud Function："
        echo "   $ curl '$FUNC_URL'"
        echo ""
        echo "或立即執行 Scheduler Job："
        echo "   $ gcloud scheduler jobs run refresh-gdrive-token --location=asia-east1 --project=$PROJECT_ID"
        echo ""
    fi
fi

echo ""

# ==================== 10. 詳細使用指南 ====================

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📚 快速參考${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

echo "相關文件："
echo "  • 完整部署指南：doc/GCP_TOKEN_AUTOMATION.md"
echo "  • 快速命令參考：doc/GCP_QUICK_REFERENCE.md"
echo ""

echo "常見命令："
echo "  # 檢查所有 secrets"
echo "  $ gcloud secrets list --project=$PROJECT_ID"
echo ""
echo "  # 查看 Function 日志"
echo "  $ gcloud functions logs read refresh-oauth-token --region=asia-east1 --project=$PROJECT_ID"
echo ""
echo "  # 手動執行 Scheduler"
echo "  $ gcloud scheduler jobs run refresh-gdrive-token --location=asia-east1 --project=$PROJECT_ID"
echo ""
echo "  # 重新執行此驗證"
echo "  $ bash scripts/verify_gcp_setup.sh $PROJECT_ID"
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo ""

# 結束狀態碼
if [ ${CHECKS_FAILED} -eq 0 ]; then
    exit 0
else
    exit 1
fi
