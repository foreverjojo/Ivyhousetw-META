# OAuth Consent Screen 正式發布前置

本文件整理 Ivy House Meta 從 `External / Testing` 走向可送審 brand verification 的最小前置。

## 1. 公開頁面

本 repo 已提供公開頁面來源：`public_site/`，並已掛到既有正式網域的公開 path。

目前 live 公開網址：

- Home: `https://adanalyzer.shincold.com/legal/`
- Privacy: `https://adanalyzer.shincold.com/legal/privacy/`
- Terms: `https://adanalyzer.shincold.com/legal/terms/`

部署方式：

- static source：`public_site/`
- GCS bucket：`gs://ivyhouse-ad-analyzer-public-pages-971489052398/legal/`
- Load Balancer path：`/legal`、`/legal/privacy`、`/legal/terms`

備援方式：

- Workflow: `.github/workflows/public-legal-pages.yml`
- 用途：若日後要切到 GitHub Pages 獨立公開站，可直接沿用

## 2. Google Auth Platform 建議回填值

Branding 頁建議至少更新以下欄位：

- App name: `Ivyhouse Meta Analyzer`
- Homepage: `https://adanalyzer.shincold.com/legal/`
- Privacy policy: `https://adanalyzer.shincold.com/legal/privacy/`
- Terms of service: `https://adanalyzer.shincold.com/legal/terms/`
- Support email: `foreverwow001@gmail.com`

2026-03-07 狀態：Branding draft 已更新並儲存為上述 `/legal/...` live URL。

## 3. Authorized domains

Google 官方要求：

- Homepage / Privacy / Terms 必須公開可見。
- Privacy policy 必須與 homepage 位於同一個網域。
- Authorized domains 需包含 homepage、privacy、terms、redirect URI / JavaScript origin 涉及的網域。
- 若要送 brand verification，需能在 Google Search Console 驗證這些 authorized domains 的所有權。

實務上建議兩條路擇一：

1. 目前 live 路徑已在 `adanalyzer.shincold.com`，可直接作為同網域公開頁方案。
2. 若未來要再拆出獨立 legal site，可改成 `legal.shincold.com`，並在 Search Console 完成驗證。

## 4. 正式發布前的檢查清單

- [x] `adanalyzer.shincold.com/legal/` 已公開可存取。
- [ ] 公開首頁可清楚描述產品功能，不是只有登入入口。
- [ ] 公開首頁已連到 Privacy 與 Terms。
- [ ] Privacy policy 已揭露如何存取、使用、保存與分享 Google user data。
- [ ] Terms 已說明授權、責任與 AI 生成內容限制。
- [x] Branding draft / Developer contact information 已更新為有效聯絡方式。
- [ ] Authorized domains 已與實際公開頁、OAuth client 設定一致。
- [ ] Search Console 已驗證正式送審要使用的網域。
- [ ] 若要顯示正式 app name / logo，已準備送 brand verification。

## 5. 送審注意事項

- 如果仍是少量已知測試使用者，可以維持 `Testing` 狀態，不必急著送審。
- 若要對更多外部 Google 帳號開放，建議改用正式可驗證網域後再送 brand verification。
- Google 官方也建議 testing / staging 與 production 分開專案；若未來要對外正式提供服務，應評估拆出 production project。
