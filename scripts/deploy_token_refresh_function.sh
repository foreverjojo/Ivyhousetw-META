#!/bin/bash
# 部署 Token 刷新 Cloud Function
# 用途：將自動刷新腳本部署到 Google Cloud
# 使用方式：bash scripts/deploy_token_refresh_function.sh <PROJECT_ID> <SERVICE_ACCOUNT_EMAIL>

set -e

if [ -z "$1" ]; then
    echo "❌ 缺少 PROJECT_ID 參數"
    echo "用法：bash scripts/deploy_token_refresh_function.sh <PROJECT_ID> [SERVICE_ACCOUNT_EMAIL]"
    echo "例如：bash scripts/deploy_token_refresh_function.sh ivyhouse-ad-analyzer"
    exit 1
fi

PROJECT_ID="$1"
SERVICE_ACCOUNT="${2:-}"  # 可選，如果未提供則使用預設

echo "=================================================================="
echo "🚀 部署 Token 刷新 Cloud Function"
echo "=================================================================="
echo ""
echo "📌 PROJECT_ID: $PROJECT_ID"
echo "📌 Function 名稱：refresh-oauth-token"
echo "📌 Runtime：python3.11"
echo "📌 區域：asia-east1"
echo ""

# 檢查 gcloud 登入
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ 未登入 gcloud，請先執行："
    echo "   gcloud auth login"
    exit 1
fi

echo "✅ 已登入 gcloud"
echo ""

# 啟用必要的 APIs
echo "=================================================================="
echo "⏳ 啟用 Google Cloud APIs..."
echo "=================================================================="
echo ""

gcloud services enable cloudfunctions.googleapis.com --project="$PROJECT_ID" > /dev/null 2>&1 || true
gcloud services enable cloudscheduler.googleapis.com --project="$PROJECT_ID" > /dev/null 2>&1 || true
gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID" > /dev/null 2>&1 || true
gcloud services enable cloudlogging.googleapis.com --project="$PROJECT_ID" > /dev/null 2>&1 || true
gcloud services enable appengine.googleapis.com --project="$PROJECT_ID" > /dev/null 2>&1 || true

echo "✅ APIs 已啟用"
echo ""

# 創建臨時目錄用於部署
DEPLOY_DIR="/tmp/token_refresh_function"
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

echo "=================================================================="
echo "📦 準備部署内容..."
echo "=================================================================="
echo ""

# 複製必要的文件
cp "scripts/gcp_token_refresh_function.py" "$DEPLOY_DIR/main.py"
cp "scripts/gcp_requirements.txt" "$DEPLOY_DIR/requirements.txt"

echo "✅ 已準備部署文件"
echo ""

# 部署 Cloud Function
echo "=================================================================="
echo "⏳ 部署 Cloud Function..."
echo "=================================================================="
echo ""

gcloud functions deploy refresh-oauth-token \
    --gen2 \
    --runtime python311 \
    --region asia-east1 \
    --source "$DEPLOY_DIR" \
    --entry-point refresh_token \
    --trigger-http \
    --allow-unauthenticated \
    --project "$PROJECT_ID" \
    --set-env-vars "PROJECT_ID=$PROJECT_ID" \
    --memory 256MB \
    --timeout 60s \
    --quiet

echo ""
echo "✅ Cloud Function 已部署"
echo ""

# 獲取 Cloud Function 的 trigger URL
echo "=================================================================="
echo "🔗 Cloud Function URL"
echo "=================================================================="
echo ""

FUNCTION_URL=$(gcloud functions describe refresh-oauth-token \
    --region asia-east1 \
    --project "$PROJECT_ID" \
    --gen2 \
    --format='value(serviceConfig.uri)')

echo "📌 Trigger URL："
echo "   $FUNCTION_URL"
echo ""

# 檢查現有的 Cloud Function
echo "=================================================================="
echo "📋 已部署的 Cloud Functions"
echo "=================================================================="
echo ""

gcloud functions list --project="$PROJECT_ID" --filter="name:refresh-oauth-token" | head -20 || echo "（無結果）"

echo ""
echo "=================================================================="
echo "✅ 部署完成！"
echo "=================================================================="
echo ""
echo "下一步："
echo "1️⃣  設定 Cloud Scheduler 定期執行（見下面的命令）"
echo "2️⃣  驗證 Function 是否可以存取 Secret Manager"
echo "3️⃣  測試手動執行 Function"
echo ""
echo "相關命令："
echo ""
echo "📌 查看部署詳情："
echo "   gcloud functions describe refresh-oauth-token --region=asia-east1 --project=$PROJECT_ID"
echo ""
echo "📌 查看最近的日志："
echo "   gcloud functions logs read refresh-oauth-token --limit 50 --region=asia-east1 --project=$PROJECT_ID"
echo ""
echo "📌 手動測試（觸發 Function）："
echo "   curl \"$FUNCTION_URL\""
echo ""
echo "📌 查看所有 Functions："
echo "   gcloud functions list --project=$PROJECT_ID"
echo ""
