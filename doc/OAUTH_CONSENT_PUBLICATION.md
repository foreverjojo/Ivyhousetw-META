# OAuth Consent Screen 正式發布前置

本文件整理 Ivy House Meta 從 `External / Testing` 走向可送審 brand verification 的最小前置。

## 1. 公開頁面

本 repo 已提供 GitHub Pages 用的公開頁面來源：`public_site/`。

預設公開網址：

- Home: `https://foreverjojo.github.io/Ivyhousetw-META/`
- Privacy: `https://foreverjojo.github.io/Ivyhousetw-META/privacy/`
- Terms: `https://foreverjojo.github.io/Ivyhousetw-META/terms/`

部署方式：

- Workflow: `.github/workflows/public-legal-pages.yml`
- 觸發條件：push 到 `main` 或 `chore/cloudbuild-cloudrun`，或手動 `workflow_dispatch`

## 2. Google Auth Platform 建議回填值

Branding 頁建議至少更新以下欄位：

- App name: `Ivyhouse Meta Analyzer`
- Homepage: `https://foreverjojo.github.io/Ivyhousetw-META/`
- Privacy policy: `https://foreverjojo.github.io/Ivyhousetw-META/privacy/`
- Terms of service: `https://foreverjojo.github.io/Ivyhousetw-META/terms/`
- Support email: `foreverwow001@gmail.com`

## 3. Authorized domains

Google 官方要求：

- Homepage / Privacy / Terms 必須公開可見。
- Privacy policy 必須與 homepage 位於同一個網域。
- Authorized domains 需包含 homepage、privacy、terms、redirect URI / JavaScript origin 涉及的網域。
- 若要送 brand verification，需能在 Google Search Console 驗證這些 authorized domains 的所有權。

實務上建議兩條路擇一：

1. 臨時公開頁：先使用 GitHub Pages 預設網址，讓公開文件先上線。
2. 正式送審：改用你可驗證所有權的正式網域，例如 `legal.shincold.com`，並在 Search Console 完成驗證。

## 4. 正式發布前的檢查清單

- [ ] GitHub Pages workflow 已成功部署公開頁。
- [ ] 公開首頁可清楚描述產品功能，不是只有登入入口。
- [ ] 公開首頁已連到 Privacy 與 Terms。
- [ ] Privacy policy 已揭露如何存取、使用、保存與分享 Google user data。
- [ ] Terms 已說明授權、責任與 AI 生成內容限制。
- [ ] Branding / Developer contact information 已更新為有效聯絡方式。
- [ ] Authorized domains 已與實際公開頁、OAuth client 設定一致。
- [ ] Search Console 已驗證正式送審要使用的網域。
- [ ] 若要顯示正式 app name / logo，已準備送 brand verification。

## 5. 送審注意事項

- 如果仍是少量已知測試使用者，可以維持 `Testing` 狀態，不必急著送審。
- 若要對更多外部 Google 帳號開放，建議改用正式可驗證網域後再送 brand verification。
- Google 官方也建議 testing / staging 與 production 分開專案；若未來要對外正式提供服務，應評估拆出 production project。
