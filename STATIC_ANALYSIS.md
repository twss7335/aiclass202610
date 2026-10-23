# JavaScript 靜態檢查

本專案的 JavaScript 靜態檢查全部由 CLI 執行，不需要編輯器外掛。

## 安裝與執行

```bash
pnpm install --frozen-lockfile
pnpm run check
```

`pnpm run check` 會依序跑完所有工具；即使其中一項發現問題，其餘工具仍會繼續，最後以非零狀態回報待處理項目。也可分別執行：

```bash
pnpm run check:eslint
pnpm run check:duplicates
pnpm run check:deadcode
```

## 範圍與門檻

- ESLint 使用 flat config。`docs/**/*.js` 只宣告 browser globals；`scripts/`、`tests/` 與根目錄設定檔只宣告 Node globals。
- `docs/app.js` 額外只宣告唯讀的 `module`，供既有的條件式 CommonJS 測試匯出使用；沒有把整組 Node globals 套到瀏覽器程式。
- `docs/model-data.js` 完全由 `scripts/export_frontend_models.py` 生成，不視為手寫程式，因此排除於 ESLint 與 jscpd。其正確性由載入順序契約、Python/JavaScript parity tests 與三筆 golden predictions 驗證；不可手動編輯或任意截斷參數。
- Cyclomatic complexity：10。
- 巢狀深度：3。
- 每個函式最多 50 行（忽略空白行與註解）。
- SonarJS cognitive complexity：15。
- jscpd 重複率門檻：0%；JSON 報告輸出到被 Git 忽略的 `reports/static-analysis/jscpd/`。
- Knip 以目前存在的 `docs/*.js` 為執行入口，並由其 ESLint／package scripts 外掛識別工具設定；未來 `scripts/` 或 `tests/` 新增 JS 時，ESLint 的 Node 範圍已預先配置。

套件版本固定在 `package.json`，完整相依解析固定在 `pnpm-lock.yaml`。
