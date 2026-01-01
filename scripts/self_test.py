Case 1：正常跑（快篩 / 最終各一次）

events 應該依序看到：B -> C1 -> D(draft) 或 B -> C1 -> E -> F(final)

Case 2：故意改錯 const（你剛做的）

events 應該看到：B(validate_error) 且 details 不為空

Case 3：schema 檔缺失/路徑錯

應該同樣落盤 B(validate_error)（error 會是找不到 schema 檔）

Case 4：關掉 validate_schema

應該不會有 validate_error，流程照舊跑（確保 toggle 有效）