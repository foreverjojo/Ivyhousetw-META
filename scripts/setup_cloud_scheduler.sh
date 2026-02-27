#!/bin/bash
# 設定 Cloud Scheduler 定期執行 Token 刷新 Task
# 用途：每 6 天執行一次刷新，確保 token 不會過期
# 使用方式：bash scripts/setup_cloud_scheduler.sh <PROJECT_ID> <FUNCTION_URL>

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "❌ 缺少必要參數"
    echo "用法：bash scripts/setup_cloud_scheduler.sh <PROJECT_ID> <FUNCTION_URL>"
    echo ""
    echo "例如："
    echo "  bash scripts/setup_cloud_scheduler.sh ivyhouse-ad-analyzer \\"
    echo "    https://asia-east1-ivyhouse-ad-analyzer.cloudfunctions.net/refresh-oauth-token"
    exit 1
fi

PROJECT_ID="$1"
FUNCTION_URL="$2"
JOB_NAME="refresh-gdrive-token"
SCHEDULE="0 0 * * 0"  # 每週日午夜執行（每 7 天）
TIMEZONE="Asia/Taipei"

echo "=================================================================="
echo "⏰ 設定 Cloud Scheduler 定期任務"
echo "=================================================================="
echo ""
echo "📌 PROJECT_ID: $PROJECT_ID"
echo "📌 Job 名稱：$JOB_NAME"
echo "📌 Function URL：$FUNCTION_URL"
echo "📌 排程：$SCHEDULE (Cron 格式)"
echo "📌 時區：$TIMEZONE"
echo ""

# 檢查 gcloud 登入
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ 未登入 gcloud，請先執行："
    echo "   gcloud auth login"
    exit 1
fi

echo "✅ 已登入 gcloud"
echo ""

# 啟用 Cloud Scheduler API
echo "⏳ 啟用 Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com --project="$PROJECT_ID" > /dev/null 2>&1 || true
echo "✅ API 已啟用"
echo ""

# 檢查 Job 是否已存在
if gcloud scheduler jobs describe "$JOB_NAME" \
    --location=asia-east1 \
    --project="$PROJECT_ID" > /dev/null 2>&1; then

    echo "🔄 已存在的 Scheduler Job，正在更新..."

    gcloud scheduler jobs update http "$JOB_NAME" \
        --location=asia-east1 \
        --schedule="$SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --http-method=GET \
        --uri="$FUNCTION_URL" \
        --project="$PROJECT_ID" \
        --quiet

    echo "✅ Job 已更新"
else
    echo "✨ 建立新的 Scheduler Job..."

    gcloud scheduler jobs create http "$JOB_NAME" \
        --location=asia-east1 \
        --schedule="$SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --http-method=GET \
        --uri="$FUNCTION_URL" \
        --project="$PROJECT_ID" \
        --quiet

    echo "✅ Job 已建立"
fi

echo ""
echo "=================================================================="
echo "✅ Cloud Scheduler 設定完成！"
echo "=================================================================="
echo ""
echo "排程説明："
echo "  • 每週日午夜 (0:00) 執行"
echo "  • 時區：$TIMEZONE (UTC+8)"
echo "  • 執行 Function：refresh-oauth-token"
echo ""
echo "相關命令："
echo ""
echo "📌 查看 Scheduler Job："
echo "   gcloud scheduler jobs describe $JOB_NAME --location=asia-east1 --project=$PROJECT_ID"
echo ""
echo "📌 查看 Job 執行歷史："
echo "   gcloud scheduler jobs describe $JOB_NAME --location=asia-east1 --project=$PROJECT_ID --format='value(status)'"
echo ""
echo "📌 手動執行 Job（立即測試）："
echo "   gcloud scheduler jobs run $JOB_NAME --location=asia-east1 --project=$PROJECT_ID"
echo ""
echo "📌 檢視 Job 日志："
echo "   gcloud functions logs read refresh-oauth-token --limit 100 --region=asia-east1 --project=$PROJECT_ID"
echo ""
echo "📌 刪除 Job（如果不再需要）："
echo "   gcloud scheduler jobs delete $JOB_NAME --location=asia-east1 --project=$PROJECT_ID"
echo ""
