#!/bin/bash
# GCP Secret Manager 初始化腳本
# 用途：初次設定時，將本地 secrets 上傳到 Google Cloud Secret Manager
# 使用方式：bash scripts/setup_gcp_secrets.sh <PROJECT_ID>

set -e

if [ -z "$1" ]; then
    echo "❌ 缺少 PROJECT_ID 參數"
    echo "用法：bash scripts/setup_gcp_secrets.sh <PROJECT_ID>"
    echo "例如：bash scripts/setup_gcp_secrets.sh ivyhouse-ad-analyzer"
    exit 1
fi

PROJECT_ID="$1"

echo "=================================================================="
echo "🔐 Google Cloud Secret Manager 初始化"
echo "=================================================================="
echo ""
echo "📌 PROJECT_ID: $PROJECT_ID"
echo ""

# 檢查 gcloud 登入
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ 未登入 gcloud，請先執行："
    echo "   gcloud auth login"
    exit 1
fi

echo "✅ 已登入 gcloud"
echo ""

# 檢查本地 secrets
echo "=================================================================="
echo "📁 檢查本地 secrets..."
echo "=================================================================="

# 使用 glob 展開來檢查檔案是否存在
if ! ls secrets/client_secret_*.json &>/dev/null; then
    echo "❌ 找不到 client_secret_*.json"
    echo "   請確保已下載 OAuth credentials 到 secrets/ 目錄"
    exit 1
fi

CLIENT_SECRET_FILE=$(ls secrets/client_secret_*.json | head -1)
echo "✅ 找到：$CLIENT_SECRET_FILE"

if [ ! -f "ifp.env" ]; then
    echo "❌ 找不到 ifp.env"
    exit 1
fi

echo "✅ 找到：ifp.env"
echo ""

# 抽取 tokens
echo "=================================================================="
echo "🔑 抽取 tokens..."
echo "=================================================================="

CLIENT_ID=$(grep "client_id" "$CLIENT_SECRET_FILE" | sed 's/.*"client_id": "\([^"]*\)".*/\1/' | head -1)
CLIENT_SECRET=$(grep "client_secret" "$CLIENT_SECRET_FILE" | sed 's/.*"client_secret": "\([^"]*\)".*/\1/' | head -1)
ACCESS_TOKEN=$(grep "GOOGLE_DRIVE_ACCESS_TOKEN=" ifp.env | cut -d'=' -f2)
FOLDER_ID=$(grep "GOOGLE_DRIVE_FOLDER_ID=" ifp.env | cut -d'=' -f2)

# 由於我們已經有了 access_token，但沒有存儲 refresh_token 在 ifp.env
# 我們需要要求用戶提供 refresh_token，或提醒需要重新授權
echo "📌 CLIENT_ID: ${CLIENT_ID:0:30}..."
echo "📌 CLIENT_SECRET: ${CLIENT_SECRET:0:20}..."
echo "📌 ACCESS_TOKEN: ${ACCESS_TOKEN:0:30}..."
echo "📌 FOLDER_ID: $FOLDER_ID"
echo ""

# 詢問 refresh_token
echo "=================================================================="
echo "🔑 Refresh Token"
echo "=================================================================="
echo ""
echo "⚠️  我們需要 refresh_token（用於無限期更新 access_token）"
echo ""
echo "你可能需要重新執行授權流程來獲取 refresh_token。"
echo "從之前的授權響應中，你應該收到類似的："
echo '  "refresh_token": "1//0eEc2IUWr2r00..."'
echo ""

read -p "🔑 請輸入 Refresh Token（或按 Enter 跳過）: " REFRESH_TOKEN

if [ -z "$REFRESH_TOKEN" ]; then
    echo "⚠️  未提供 refresh_token，將於後續手動添加"
    REFRESH_TOKEN="PLACEHOLDER_REFRESH_TOKEN_PLEASE_UPDATE"
fi

echo ""
echo "=================================================================="
echo "📤 上傳到 Google Cloud Secret Manager..."
echo "=================================================================="
echo ""

# Enable Secret Manager API
echo "⏳ 啟用 Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID" > /dev/null 2>&1 || true

# 建立或更新 secrets
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2

    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" > /dev/null 2>&1; then
        echo "  🔄 更新：$secret_name"
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
            --data-file=- --project="$PROJECT_ID" > /dev/null
    else
        echo "  ✨ 建立：$secret_name"
        echo -n "$secret_value" | gcloud secrets create "$secret_name" \
            --data-file=- --project="$PROJECT_ID" \
            --replication-policy="automatic" > /dev/null
    fi
}

create_or_update_secret "GOOGLE_DRIVE_CLIENT_ID" "$CLIENT_ID"
create_or_update_secret "GOOGLE_DRIVE_CLIENT_SECRET" "$CLIENT_SECRET"
create_or_update_secret "GOOGLE_DRIVE_ACCESS_TOKEN" "$ACCESS_TOKEN"
create_or_update_secret "GOOGLE_DRIVE_REFRESH_TOKEN" "$REFRESH_TOKEN"
create_or_update_secret "GOOGLE_DRIVE_FOLDER_ID" "$FOLDER_ID"

echo ""
echo "=================================================================="
echo "🔐 列出已建立的 Secrets..."
echo "=================================================================="
echo ""

gcloud secrets list --project="$PROJECT_ID" | grep GOOGLE_DRIVE || echo "（無）"

echo ""
echo "=================================================================="
echo "✅ Secret Manager 設定完成！"
echo "=================================================================="
echo ""
echo "下一步："
echo "1️⃣  部署 token 刷新 Cloud Function"
echo "2️⃣  設定 Cloud Scheduler 定期執行"
echo "3️⃣  驗證權限"
echo ""
echo "相關命令："
echo "  gcloud secrets list --project=$PROJECT_ID"
echo "  gcloud secrets describe GOOGLE_DRIVE_ACCESS_TOKEN --project=$PROJECT_ID"
echo ""
