# Google Cloud Run 快速部署腳本
# 使用方式：.\deploy.ps1 -ProjectId "your-project-id" -ServiceName "ivyhouse-meta"

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,

    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "ivyhouse-meta-analyzer",

    [Parameter(Mandatory=$false)]
    [string]$Region = "asia-east1",

    [Parameter(Mandatory=$false)]
    [string]$Memory = "2Gi",

    [Parameter(Mandatory=$false)]
    [int]$Cpu = 2,

    [Parameter(Mandatory=$false)]
    [int]$Timeout = 3600
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ivy House Meta Analyzer 部署工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 檢查 gcloud 是否安裝
Write-Host "檢查 Google Cloud CLI..." -ForegroundColor Yellow
try {
    $gcloudVersion = gcloud version 2>&1 | Select-Object -First 1
    Write-Host "✓ 已安裝: $gcloudVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ 未安裝 Google Cloud CLI" -ForegroundColor Red
    Write-Host "請先安裝: https://cloud.google.com/sdk/docs/install" -ForegroundColor Red
    exit 1
}

# 設定專案
Write-Host ""
Write-Host "設定專案: $ProjectId" -ForegroundColor Yellow
gcloud config set project $ProjectId

# 啟用必要的 API
Write-Host ""
Write-Host "啟用 Cloud Run 和 Cloud Build API..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# 確認部署
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "部署配置:" -ForegroundColor Cyan
Write-Host "  專案 ID: $ProjectId" -ForegroundColor White
Write-Host "  服務名稱: $ServiceName" -ForegroundColor White
Write-Host "  區域: $Region" -ForegroundColor White
Write-Host "  記憶體: $Memory" -ForegroundColor White
Write-Host "  CPU: $Cpu" -ForegroundColor White
Write-Host "  超時: $Timeout 秒" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$confirm = Read-Host "確認部署？(y/n)"
if ($confirm -ne "y") {
    Write-Host "已取消部署" -ForegroundColor Yellow
    exit 0
}

# 開始部署
Write-Host ""
Write-Host "開始部署到 Cloud Run..." -ForegroundColor Yellow
Write-Host ""

try {
    gcloud run deploy $ServiceName `
        --source . `
        --platform managed `
        --region $Region `
        --allow-unauthenticated `
        --memory $Memory `
        --cpu $Cpu `
        --timeout $Timeout `
        --project $ProjectId

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  ✓ 部署成功！" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""

        # 取得服務 URL
        $serviceUrl = gcloud run services describe $ServiceName --region $Region --format="value(status.url)"
        Write-Host "服務 URL: $serviceUrl" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "檢視日誌:" -ForegroundColor Yellow
        Write-Host "  gcloud run services logs read $ServiceName --region $Region --limit 50" -ForegroundColor White
        Write-Host ""
        Write-Host "更新服務:" -ForegroundColor Yellow
        Write-Host "  .\deploy.ps1 -ProjectId $ProjectId" -ForegroundColor White
        Write-Host ""
    } else {
        throw "部署失敗"
    }
} catch {
    Write-Host ""
    Write-Host "✗ 部署失敗: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "常見問題排查:" -ForegroundColor Yellow
    Write-Host "1. 檢查專案 ID 是否正確" -ForegroundColor White
    Write-Host "2. 確認已啟用計費" -ForegroundColor White
    Write-Host "3. 檢查 Dockerfile 語法" -ForegroundColor White
    Write-Host "4. 查看完整錯誤訊息" -ForegroundColor White
    exit 1
}
