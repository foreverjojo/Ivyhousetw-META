#!/bin/bash
# 設定 Cloud Run 的 External HTTPS LB + IAP 入口
# 用途：可重跑地建立或更新 LB、憑證、NEG、IAP 與 ingress 設定
# 用法：bash scripts/setup_cloud_run_iap_entry.sh <PROJECT_ID> <REGION> <SERVICE_NAME> <DOMAIN>

set -euo pipefail

if [ "$#" -lt 4 ]; then
    echo "❌ 缺少必要參數"
    echo "用法：bash scripts/setup_cloud_run_iap_entry.sh <PROJECT_ID> <REGION> <SERVICE_NAME> <DOMAIN>"
    echo ""
    echo "必要環境變數："
    echo "  IAP_OAUTH_CLIENT_ID       IAP custom OAuth client ID"
    echo "  IAP_OAUTH_CLIENT_SECRET   IAP custom OAuth client secret"
    echo ""
    echo "可選環境變數："
    echo "  STATIC_IP_NAME            預設 ivyhouse-meta-iap-ip"
    echo "  MANAGED_CERT_NAME         預設 ivyhouse-meta-iap-managed-cert"
    echo "  NEG_NAME                  預設 ivyhouse-meta-iap-neg"
    echo "  BACKEND_SERVICE_NAME      預設 ivyhouse-meta-iap-backend"
    echo "  URL_MAP_NAME              預設 ivyhouse-meta-iap-map"
    echo "  HTTPS_PROXY_NAME          預設 ivyhouse-meta-iap-proxy"
    echo "  FORWARDING_RULE_NAME      預設 ivyhouse-meta-iap-fr"
    echo "  TEST_CERT_NAME            若存在則一併掛入 HTTPS proxy；預設 ivyhouse-meta-iap-cert"
    echo "  IAP_ACCESS_MEMBERS        完整 allowlist（逗號或換行分隔）；若提供則會移除未列出的既有 accessor"
    echo "  IAP_USER_MEMBER           例如 user:you@example.com"
    echo "  IAP_SERVICE_ACCOUNT_MEMBER 例如 serviceAccount:svc@project.iam.gserviceaccount.com"
    exit 1
fi

PROJECT_ID="$1"
REGION="$2"
SERVICE_NAME="$3"
DOMAIN="$4"

STATIC_IP_NAME="${STATIC_IP_NAME:-ivyhouse-meta-iap-ip}"
MANAGED_CERT_NAME="${MANAGED_CERT_NAME:-ivyhouse-meta-iap-managed-cert}"
NEG_NAME="${NEG_NAME:-ivyhouse-meta-iap-neg}"
BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-ivyhouse-meta-iap-backend}"
URL_MAP_NAME="${URL_MAP_NAME:-ivyhouse-meta-iap-map}"
HTTPS_PROXY_NAME="${HTTPS_PROXY_NAME:-ivyhouse-meta-iap-proxy}"
FORWARDING_RULE_NAME="${FORWARDING_RULE_NAME:-ivyhouse-meta-iap-fr}"
TEST_CERT_NAME="${TEST_CERT_NAME:-ivyhouse-meta-iap-cert}"
IAP_SA="service-$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')@gcp-sa-iap.iam.gserviceaccount.com"

if [ -z "${IAP_OAUTH_CLIENT_ID:-}" ] || [ -z "${IAP_OAUTH_CLIENT_SECRET:-}" ]; then
    echo "❌ 必須提供 IAP_OAUTH_CLIENT_ID 與 IAP_OAUTH_CLIENT_SECRET"
    exit 1
fi

if [ -z "${IAP_ACCESS_MEMBERS:-}" ] && [ -z "${IAP_USER_MEMBER:-}" ] && [ -z "${IAP_SERVICE_ACCOUNT_MEMBER:-}" ]; then
    echo "❌ 至少必須提供一個 IAP allowlist principal（IAP_ACCESS_MEMBERS、IAP_USER_MEMBER 或 IAP_SERVICE_ACCOUNT_MEMBER）"
    exit 1
fi

echo "=================================================================="
echo "🔐 設定 Cloud Run IAP 入口"
echo "=================================================================="
echo "PROJECT_ID            : $PROJECT_ID"
echo "REGION                : $REGION"
echo "SERVICE_NAME          : $SERVICE_NAME"
echo "DOMAIN                : $DOMAIN"
echo "STATIC_IP_NAME        : $STATIC_IP_NAME"
echo "MANAGED_CERT_NAME     : $MANAGED_CERT_NAME"
echo "BACKEND_SERVICE_NAME  : $BACKEND_SERVICE_NAME"
echo "NEG_NAME              : $NEG_NAME"
echo "URL_MAP_NAME          : $URL_MAP_NAME"
echo "HTTPS_PROXY_NAME      : $HTTPS_PROXY_NAME"
echo "FORWARDING_RULE_NAME  : $FORWARDING_RULE_NAME"
echo "IAP Service Agent     : $IAP_SA"
echo "=================================================================="

ensure_iap_enabled() {
    local current_enabled=""
    local current_client_id=""
    local current_secret_sha=""
    local desired_secret_sha=""

    current_enabled="$(gcloud compute backend-services describe "$BACKEND_SERVICE_NAME" --global --project="$PROJECT_ID" --format='value(iap.enabled)' 2>/dev/null || true)"
    current_client_id="$(gcloud compute backend-services describe "$BACKEND_SERVICE_NAME" --global --project="$PROJECT_ID" --format='value(iap.oauth2ClientId)' 2>/dev/null || true)"
    current_secret_sha="$(gcloud compute backend-services describe "$BACKEND_SERVICE_NAME" --global --project="$PROJECT_ID" --format='value(iap.oauth2ClientSecretSha256)' 2>/dev/null || true)"
    desired_secret_sha="$(printf '%s' "$IAP_OAUTH_CLIENT_SECRET" | sha256sum | awk '{print $1}')"

    if [ "$current_enabled" = "True" ] && [ "$current_client_id" = "$IAP_OAUTH_CLIENT_ID" ] && [ "$current_secret_sha" = "$desired_secret_sha" ]; then
        echo "🔄 IAP 已啟用且 OAuth client 設定一致，略過更新"
        return
    fi

    if [ "$current_enabled" = "True" ] && [ -n "$current_client_id" ] && [ "$current_client_id" != "$IAP_OAUTH_CLIENT_ID" ]; then
        echo "ℹ️ 偵測到既有 IAP OAuth client ID，將更新為指定的 client"
    elif [ "$current_enabled" = "True" ] && [ -n "$current_secret_sha" ] && [ "$current_secret_sha" != "$desired_secret_sha" ]; then
        echo "ℹ️ 偵測到 IAP OAuth client secret 已變更，將重新套用 IAP 設定"
    else
        echo "⏳ 啟用 IAP..."
    fi

    gcloud iap web enable \
        --resource-type=backend-services \
        --service="$BACKEND_SERVICE_NAME" \
        --oauth2-client-id="$IAP_OAUTH_CLIENT_ID" \
        --oauth2-client-secret="$IAP_OAUTH_CLIENT_SECRET" \
        --project="$PROJECT_ID" >/dev/null
    echo "✅ IAP 已啟用"
}

ensure_iap_accessor_binding() {
    local member="$1"
    local label="$2"

    echo "⏳ 綁定 $label IAP accessor..."
    gcloud iap web add-iam-policy-binding \
        --resource-type=backend-services \
        --service="$BACKEND_SERVICE_NAME" \
        --member="$member" \
        --role='roles/iap.httpsResourceAccessor' \
        --project="$PROJECT_ID" >/dev/null
    echo "✅ $label IAP accessor 已綁定"
}

reconcile_iap_accessors() {
    local current_members=""
    local current_member=""
    local desired_member=""
    local desired_members=()
    local use_full_allowlist="false"

    if [ -n "${IAP_ACCESS_MEMBERS:-}" ]; then
        use_full_allowlist="true"
        while IFS= read -r desired_member; do
            [ -z "$desired_member" ] && continue
            desired_members+=("$desired_member")
        done <<< "$(printf '%s' "$IAP_ACCESS_MEMBERS" | tr ',' '\n' | sed 's/^ *//;s/ *$//' | sed '/^$/d')"
    fi

    if [ -n "${IAP_USER_MEMBER:-}" ]; then
        desired_members+=("$IAP_USER_MEMBER")
    fi
    if [ -n "${IAP_SERVICE_ACCOUNT_MEMBER:-}" ]; then
        desired_members+=("$IAP_SERVICE_ACCOUNT_MEMBER")
    fi

    current_members="$(gcloud iap web get-iam-policy \
        --resource-type=backend-services \
        --service="$BACKEND_SERVICE_NAME" \
        --project="$PROJECT_ID" \
        --flatten='bindings[].members' \
        --filter='bindings.role:roles/iap.httpsResourceAccessor' \
        --format='value(bindings.members)' 2>/dev/null || true)"

    if [ "$use_full_allowlist" = "true" ]; then
        while IFS= read -r current_member; do
            [ -z "$current_member" ] && continue
            if printf '%s\n' "${desired_members[@]}" | grep -Fxq "$current_member"; then
                continue
            fi

            echo "⏳ 移除不再允許的 IAP accessor：$current_member"
            gcloud iap web remove-iam-policy-binding \
                --resource-type=backend-services \
                --service="$BACKEND_SERVICE_NAME" \
                --member="$current_member" \
                --role='roles/iap.httpsResourceAccessor' \
                --all \
                --project="$PROJECT_ID" >/dev/null
        done <<< "$current_members"
    fi

    for desired_member in "${desired_members[@]}"; do
        ensure_iap_accessor_binding "$desired_member" "$desired_member"
    done
}

remove_drifted_backends() {
    local backend_groups=""
    local backend_group=""
    local backend_neg_name=""
    local backend_neg_region=""

    backend_groups="$(gcloud compute backend-services describe "$BACKEND_SERVICE_NAME" --global --project="$PROJECT_ID" --format='value(backends[].group)' 2>/dev/null || true)"
    if [ -z "$backend_groups" ]; then
        return
    fi

    while IFS= read -r backend_group; do
        [ -z "$backend_group" ] && continue
        if printf '%s' "$backend_group" | grep -q "/networkEndpointGroups/$NEG_NAME$"; then
            continue
        fi

        backend_neg_name="$(printf '%s' "$backend_group" | awk -F'/' '{print $NF}')"
        backend_neg_region="$(printf '%s' "$backend_group" | awk -F'/' '{for (i = 1; i <= NF; i++) if ($i == "regions") {print $(i + 1); exit}}')"
        if [ -z "$backend_neg_name" ] || [ -z "$backend_neg_region" ]; then
            echo "❌ 無法從既有 backend group 解析 NEG 名稱或 region：$backend_group"
            exit 1
        fi

        echo "⏳ 移除漂移的 backend NEG：$backend_neg_name ($backend_neg_region)..."
        gcloud compute backend-services remove-backend "$BACKEND_SERVICE_NAME" \
            --global \
            --network-endpoint-group="$backend_neg_name" \
            --network-endpoint-group-region="$backend_neg_region" \
            --project="$PROJECT_ID" >/dev/null
    done <<< "$(printf '%s' "$backend_groups" | tr ';' '\n')"
}

ensure_forwarding_rule() {
    local current_target=""
    local current_ip=""

    if ! gcloud compute forwarding-rules describe "$FORWARDING_RULE_NAME" --global --project="$PROJECT_ID" >/dev/null 2>&1; then
        echo "✨ 建立 forwarding rule..."
        gcloud compute forwarding-rules create "$FORWARDING_RULE_NAME" \
            --global \
            --load-balancing-scheme=EXTERNAL_MANAGED \
            --network-tier=PREMIUM \
            --address="$STATIC_IP_NAME" \
            --global-address \
            --target-https-proxy="$HTTPS_PROXY_NAME" \
            --global-target-https-proxy \
            --ports=443 \
            --project="$PROJECT_ID" >/dev/null
        return
    fi

    current_target="$(gcloud compute forwarding-rules describe "$FORWARDING_RULE_NAME" --global --project="$PROJECT_ID" --format='value(target)')"
    current_ip="$(gcloud compute forwarding-rules describe "$FORWARDING_RULE_NAME" --global --project="$PROJECT_ID" --format='value(IPAddress)')"

    if [ "$current_ip" = "$STATIC_IP" ] && printf '%s' "$current_target" | grep -q "/targetHttpsProxies/$HTTPS_PROXY_NAME$"; then
        echo "🔄 forwarding rule 已存在且目標 proxy/IP 一致，略過建立"
        return
    fi

    echo "♻️ forwarding rule 與目標 proxy/IP 不一致，將重建"
    gcloud compute forwarding-rules delete "$FORWARDING_RULE_NAME" \
        --global \
        --quiet \
        --project="$PROJECT_ID" >/dev/null
    gcloud compute forwarding-rules create "$FORWARDING_RULE_NAME" \
        --global \
        --load-balancing-scheme=EXTERNAL_MANAGED \
        --network-tier=PREMIUM \
        --address="$STATIC_IP_NAME" \
        --global-address \
        --target-https-proxy="$HTTPS_PROXY_NAME" \
        --global-target-https-proxy \
        --ports=443 \
        --project="$PROJECT_ID" >/dev/null
}

ensure_managed_certificate() {
    local current_domains=""

    if ! gcloud compute ssl-certificates describe "$MANAGED_CERT_NAME" --global --project="$PROJECT_ID" >/dev/null 2>&1; then
        echo "✨ 建立 Google-managed certificate..."
        gcloud compute ssl-certificates create "$MANAGED_CERT_NAME" \
            --domains="$DOMAIN" \
            --global \
            --project="$PROJECT_ID" >/dev/null
        return
    fi

    current_domains="$(gcloud compute ssl-certificates describe "$MANAGED_CERT_NAME" --global --project="$PROJECT_ID" --format='csv[no-heading](managed.domains)')"
    if [ "$current_domains" = "$DOMAIN" ]; then
        echo "🔄 Google-managed certificate 已存在且網域一致，略過建立"
        return
    fi

    echo "ℹ️ 偵測到既有 managed certificate 網域為 $current_domains，將切換為 $DOMAIN"
    if gcloud compute target-https-proxies describe "$HTTPS_PROXY_NAME" --global --project="$PROJECT_ID" >/dev/null 2>&1; then
        if [ "$TEST_CERT_NAME" = "$MANAGED_CERT_NAME" ] || ! gcloud compute ssl-certificates describe "$TEST_CERT_NAME" --global --project="$PROJECT_ID" >/dev/null 2>&1; then
            echo "❌ 現有 managed certificate 與目標網域不一致，且沒有可暫掛的 TEST_CERT_NAME。請先提供測試憑證或改用新的 MANAGED_CERT_NAME。"
            exit 1
        fi

        echo "⏳ 先將 HTTPS proxy 暫時切到測試憑證，避免刪除 in-use certificate 失敗..."
        gcloud compute target-https-proxies update "$HTTPS_PROXY_NAME" \
            --ssl-certificates="$TEST_CERT_NAME" \
            --global-ssl-certificates \
            --global \
            --project="$PROJECT_ID" >/dev/null
    fi

    echo "♻️ 重建 Google-managed certificate..."
    gcloud compute ssl-certificates delete "$MANAGED_CERT_NAME" \
        --global \
        --quiet \
        --project="$PROJECT_ID" >/dev/null
    gcloud compute ssl-certificates create "$MANAGED_CERT_NAME" \
        --domains="$DOMAIN" \
        --global \
        --project="$PROJECT_ID" >/dev/null
}

ensure_serverless_neg() {
    local current_service=""

    if ! gcloud compute network-endpoint-groups describe "$NEG_NAME" --region="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
        echo "✨ 建立 serverless NEG..."
        gcloud compute network-endpoint-groups create "$NEG_NAME" \
            --region="$REGION" \
            --network-endpoint-type=serverless \
            --cloud-run-service="$SERVICE_NAME" \
            --project="$PROJECT_ID" >/dev/null
        return
    fi

    current_service="$(gcloud compute network-endpoint-groups describe "$NEG_NAME" --region="$REGION" --project="$PROJECT_ID" --format='value(cloudRun.service)')"
    if [ "$current_service" = "$SERVICE_NAME" ]; then
        echo "🔄 serverless NEG 已存在且目標服務一致，略過建立"
        return
    fi

    echo "ℹ️ 偵測到既有 NEG 指向 $current_service，將重建為 $SERVICE_NAME"
    if gcloud compute backend-services describe "$BACKEND_SERVICE_NAME" --global --project="$PROJECT_ID" >/dev/null 2>&1; then
        if gcloud compute backend-services describe "$BACKEND_SERVICE_NAME" --global --project="$PROJECT_ID" --format='value(backends[].group)' | grep -q "$NEG_NAME"; then
            echo "⏳ 先將舊 NEG 從 backend service 移除..."
            gcloud compute backend-services remove-backend "$BACKEND_SERVICE_NAME" \
                --global \
                --network-endpoint-group="$NEG_NAME" \
                --network-endpoint-group-region="$REGION" \
                --project="$PROJECT_ID" >/dev/null
        fi
    fi

    gcloud compute network-endpoint-groups delete "$NEG_NAME" \
        --region="$REGION" \
        --quiet \
        --project="$PROJECT_ID" >/dev/null
    gcloud compute network-endpoint-groups create "$NEG_NAME" \
        --region="$REGION" \
        --network-endpoint-type=serverless \
        --cloud-run-service="$SERVICE_NAME" \
        --project="$PROJECT_ID" >/dev/null
}

echo "⏳ 啟用必要 API..."
gcloud services enable \
    run.googleapis.com \
    compute.googleapis.com \
    iap.googleapis.com \
    cloudresourcemanager.googleapis.com \
    --project="$PROJECT_ID" >/dev/null
echo "✅ 必要 API 已啟用"

echo "⏳ 確保 IAP service identity 存在..."
gcloud beta services identity create --service=iap.googleapis.com --project="$PROJECT_ID" >/dev/null 2>&1 || true
echo "✅ IAP service identity 已就緒"

if ! gcloud compute addresses describe "$STATIC_IP_NAME" --global --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "✨ 建立 global static IP..."
    gcloud compute addresses create "$STATIC_IP_NAME" \
        --global \
        --ip-version=IPV4 \
        --network-tier=PREMIUM \
        --project="$PROJECT_ID" >/dev/null
else
    echo "🔄 global static IP 已存在，略過建立"
fi

STATIC_IP="$(gcloud compute addresses describe "$STATIC_IP_NAME" --global --project="$PROJECT_ID" --format='value(address)')"
echo "✅ Load Balancer IP：$STATIC_IP"

ensure_managed_certificate

ensure_serverless_neg

if ! gcloud compute backend-services describe "$BACKEND_SERVICE_NAME" --global --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "✨ 建立 backend service..."
    gcloud compute backend-services create "$BACKEND_SERVICE_NAME" \
        --global \
        --load-balancing-scheme=EXTERNAL_MANAGED \
        --protocol=HTTP \
        --project="$PROJECT_ID" >/dev/null
else
    echo "🔄 backend service 已存在，略過建立"
fi

remove_drifted_backends

if ! gcloud compute backend-services describe "$BACKEND_SERVICE_NAME" --global --project="$PROJECT_ID" --format='value(backends[].group)' | grep -q "$NEG_NAME"; then
    echo "✨ 將 NEG 掛到 backend service..."
    gcloud compute backend-services add-backend "$BACKEND_SERVICE_NAME" \
        --global \
        --network-endpoint-group="$NEG_NAME" \
        --network-endpoint-group-region="$REGION" \
        --project="$PROJECT_ID" >/dev/null
else
    echo "🔄 backend service 已包含目標 NEG，略過"
fi

echo "⏳ 授予 IAP service agent Cloud Run Invoker..."
gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
    --region="$REGION" \
    --member="serviceAccount:$IAP_SA" \
    --role="roles/run.invoker" \
    --project="$PROJECT_ID" >/dev/null
echo "✅ Cloud Run Invoker 已確保"

if ! gcloud compute url-maps describe "$URL_MAP_NAME" --global --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "✨ 建立 URL map..."
    gcloud compute url-maps create "$URL_MAP_NAME" \
        --global \
        --default-service="$BACKEND_SERVICE_NAME" \
        --project="$PROJECT_ID" >/dev/null
else
    echo "🔄 更新 URL map 預設 backend service..."
    gcloud compute url-maps set-default-service "$URL_MAP_NAME" \
        --global \
        --default-service="$BACKEND_SERVICE_NAME" \
        --project="$PROJECT_ID" >/dev/null
fi

proxy_certs="$MANAGED_CERT_NAME"
if [ "$TEST_CERT_NAME" != "$MANAGED_CERT_NAME" ] && gcloud compute ssl-certificates describe "$TEST_CERT_NAME" --global --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "ℹ️ 偵測到測試憑證，將暫時與 managed certificate 共同掛載到 HTTPS proxy"
    proxy_certs="$TEST_CERT_NAME,$MANAGED_CERT_NAME"
fi

if ! gcloud compute target-https-proxies describe "$HTTPS_PROXY_NAME" --global --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "✨ 建立 target HTTPS proxy..."
    gcloud compute target-https-proxies create "$HTTPS_PROXY_NAME" \
        --url-map="$URL_MAP_NAME" \
        --ssl-certificates="$proxy_certs" \
        --global \
        --global-url-map \
        --global-ssl-certificates \
        --project="$PROJECT_ID" >/dev/null
else
    echo "🔄 更新 target HTTPS proxy 的 URL map 與憑證清單..."
    gcloud compute target-https-proxies update "$HTTPS_PROXY_NAME" \
        --url-map="$URL_MAP_NAME" \
        --global-url-map \
        --ssl-certificates="$proxy_certs" \
        --global-ssl-certificates \
        --global \
        --project="$PROJECT_ID" >/dev/null
fi

ensure_forwarding_rule

ensure_iap_enabled

reconcile_iap_accessors

echo "⏳ 收斂 Cloud Run ingress..."
gcloud run services update "$SERVICE_NAME" \
    --region="$REGION" \
    --ingress=internal-and-cloud-load-balancing \
    --project="$PROJECT_ID" >/dev/null
echo "✅ Cloud Run ingress 已收斂"

echo ""
echo "=================================================================="
echo "✅ Cloud Run IAP 入口設定完成"
echo "=================================================================="
echo ""
echo "正式網域：https://$DOMAIN/"
echo "Load Balancer IP：$STATIC_IP"
echo "Managed certificate 狀態："
gcloud compute ssl-certificates describe "$MANAGED_CERT_NAME" \
    --global \
    --project="$PROJECT_ID" \
    --format='yaml(managed.status,managed.domainStatus)'
echo ""
echo "驗收命令："
echo "  curl -I https://$DOMAIN/"
echo ""
echo "若憑證尚未 ACTIVE，請確認 DNS："
echo "  A  $DOMAIN  -> $STATIC_IP"
echo "  並確保 DNS provider 未開啟 proxy"
