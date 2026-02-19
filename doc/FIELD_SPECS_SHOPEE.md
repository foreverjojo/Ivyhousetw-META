<!-- 檔案用途：定義蝦皮廣告報表欄位規格與 Unified Schema 對應關係 -->

# 蝦皮廣告報表欄位規格 (FIELD_SPECS_SHOPEE)

## 1. 平台特性

| 項目 | 蝦皮 | Meta | 備註 |
|------|------|------|------|
| **「直接」口徑** | ✅ 有 | ✅ 有 | 等同 Meta「網站直接購買」 |
| **廣告層級 ID** | ❌ 無 | ✅ 有 | 需使用 fallback ID 策略 |
| **漏斗事件 (ATC/IC)** | ❌ 無 | ✅ 有 | 設為 0 |

## 2. 欄位對應表

### 必選欄位 (7 個核心)

| 蝦皮欄位名稱 | Unified Schema 路徑 | 型別 | 說明 |
|-------------|---------------------|------|------|
| 花費 / 廣告金額 | `metrics.spend` | float | 廣告花費 (TWD) |
| 瀏覽數 | `metrics.impressions` | int | 曝光次數 |
| 點擊數 | `metrics.clicks` | int | 點擊次數 |
| 銷售金額 | `metrics.conversions.platform.value` | float | 平台口徑轉換金額 |
| 轉換數 | `metrics.conversions.platform.count` | int | 平台口徑轉換次數 |
| 直接銷售金額 | `metrics.conversions.truth.value` | float | 真值口徑轉換金額 |
| 直接轉換數 | `metrics.conversions.truth.count` | int | 真值口徑轉換次數 |

### 建議選取欄位 (驗算用)

| 蝦皮欄位名稱 | 計算公式 | 說明 |
|-------------|----------|------|
| 投入產出比 (ROAS) | 銷售金額 / 花費 | 可驗算 |
| 點擊率 (CTR) | 點擊數 / 瀏覽數 × 100% | 可驗算 |
| 每次轉換成本 (CPA) | 花費 / 轉換數 | 可驗算 |

### 無對應欄位 (設為預設值)

| Unified Schema 路徑 | 預設值 | 原因 |
|---------------------|--------|------|
| `metrics.funnel.atc` | 0 | 蝦皮無此欄位 |
| `metrics.funnel.ic` | 0 | 蝦皮無此欄位 |
| `metrics.funnel.lpv` | 0 | 蝦皮無此欄位 |

## 3. ID 生成策略

由於蝦皮報表無廣告層級 ID，採用 **Fallback ID** 策略：

```python
# 使用 name + time_range + salt 產生穩定 hash ID
id = f"shopee_{level}_{sha1(name|start|end|salt)[:12]}"
```

## 4. 最終勾選清單

請在蝦皮廣告成效報表匯出時勾選以下欄位：

- [x] 花費 (廣告金額)
- [x] 瀏覽數
- [x] 點擊數
- [x] 銷售金額
- [x] 轉換數
- [x] 直接銷售金額
- [x] 直接轉換數
- [x] 投入產出比 (ROAS) - 驗算用
- [x] 點擊率 (CTR) - 驗算用
- [x] 每次轉換成本 (CPA) - 驗算用

**不需勾選：**
- 成本收入比
- 轉換率
- 直接轉換率
- 每次直接轉換成本
