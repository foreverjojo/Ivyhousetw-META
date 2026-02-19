---
description: 在執行 /dev（或 /dev-team）或 dev-team workflow 時應用此規則
alwaysApply: false
---

當執行 /dev（或 /dev-team）工作流程時，必須在以下兩個點停頓等待用戶確認：

1. **Planner Spec 確認**：展示完整的開發規格書後，必須明確詢問「請確認此 Spec 是否正確？」並等待用戶回應。

2. **執行模式選擇**：進入 Engineer 步驟前，必須詢問：
   - 「模式 A (直接實作)：由我直接修改檔案」
   - 「模式 B (Codex 代理)：產出 codex edit 指令」
   並等待用戶選擇。

**禁止行為**：不得自行假設用戶選擇並直接執行。
