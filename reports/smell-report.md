# docs/ 與 scripts/ 靜態檢查報告

執行日期：2026-10-23  
範圍：`docs/`、`scripts/`  
整合指令：`pnpm run check`

## 執行摘要

整合檢查依序執行 ESLint（含 SonarJS）、jscpd 與 Knip。三項工具皆有完成；整體結束碼為 1，原因是 ESLint 找到 23 個 error。沒有修改任何既有推論或資料處理程式。

| 工具 | 結果 | 發現數 |
| --- | --- | ---: |
| ESLint + SonarJS | 未通過 | 23 errors、0 warnings |
| jscpd | 通過 | 0 個重複片段 |
| Knip | 通過 | 0 個未使用項目 |

## 1. 各項警告總數（依規則分組）

| 規則 | 等級 | 數量 | 設定門檻 |
| --- | --- | ---: | --- |
| `no-loss-of-precision` | error | 23 | ESLint recommended |
| `complexity` | error | 0 | 10 |
| `max-depth` | error | 0 | 3 |
| `max-lines-per-function` | error | 0 | 50 |
| `sonarjs/cognitive-complexity` | error | 0 | 15 |
| 其他 ESLint／SonarJS 規則 | error / warning | 0 | 依目前設定 |

23 個 `no-loss-of-precision` 都在 `docs/app.js` 第 2 行的內嵌模型資料：

`2:10030`、`2:57623`、`2:86391`、`2:94008`、`2:99682`、`2:106676`、`2:127891`、`2:143737`、`2:173826`、`2:219887`、`2:290285`、`2:340139`、`2:403466`、`2:412542`、`2:480945`、`2:575350`、`2:588816`、`2:629346`、`2:636051`、`2:669575`、`2:733901`、`2:748346`、`2:791651`。

這些位置均為 JavaScript 數值字面量在執行時可能失去精度；本次僅記錄，未調整或截斷任何模型參數。追蹤單：[GitHub Issue #10](https://github.com/twss7335/aiclass202610/issues/10)。

## 2. 重複率與重複片段位置

jscpd 依 `.jscpd.json` 掃描 JavaScript：

| 格式 | 檔案 | 行數 | Tokens | 重複片段 | 重複行 | 重複 Tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| JavaScript | 2 | 148 | 350,262 | 0 | 0（0.00%） | 0（0.00%） |

沒有重複片段，因此沒有可列出的重複位置。原始機器可讀結果位於 `reports/static-analysis/jscpd/jscpd-report.json`（此執行產物依 `.gitignore` 不納入版本控制）。

## 3. 未使用的檔案與函式

Knip 回傳 `{"issues":[]}`：

- 未使用檔案：0
- 未使用函式／匯出：0
- 未使用相依套件：0

覆蓋說明：目前 Knip 專案範圍是 JavaScript，入口為 `docs/*.js`。`scripts/` 目前只有 Python 檔，並無 JavaScript 可供 ESLint、Knip 或目前限定 JavaScript pattern 的 jscpd 檢查。因此「0 項」不應解讀為已由 Knip 證明 Python 程式沒有死碼；本次沒有安裝額外 Python 靜態分析器，也沒有修改工具設定。

## 4. 前端推論程式規模

前端推論集中在 `docs/app.js`，計數方式採實體行（含空白、註解與內嵌模型資料行），函式數包含具名 `function` 與箭頭函式。

| 範圍 | 行數 | 函式數 | 說明 |
| --- | ---: | ---: | --- |
| `docs/app.js` 全檔 | 93 | 16 | 5 個具名函式、11 個箭頭函式；包含表單互動與結果呈現 |
| 核心推論 `docs/app.js:4-58` | 55 | 11 | 3 個具名函式、8 個計算用箭頭函式 |

核心具名函式為 `numeric`、`predictIris`、`predictAI4I`。第 2 行是單行內嵌模型資料（926,188 個字元），因此實體行數很小，但 token 數很高。

`docs/site.js` 負責載入與展示既有實驗指標，不計入「前端推論」核心；整體 JavaScript 重複率統計仍包含它。

## 5. 工具涵蓋與重現方式

```bash
PATH=/path/to/node/bin:$PATH pnpm run check
```

- ESLint 實際檢查 `docs/**/*.js`；`scripts/**/*.{js,mjs,cjs}` 目前沒有匹配檔案。
- jscpd 設定掃描 `docs/`、`scripts/`、`tests/`，但 pattern 限定 JavaScript。
- Knip 檢查目前 JavaScript entry/project。
- 在沒有把 `node` 放入 `PATH` 的乾淨 shell 中，pnpm 的工具啟動器會回報 `node: not found`；加入專案使用的 Node runtime 後可正常執行。

## 結論

目前可量化的 code smell 是 `docs/app.js` 內嵌模型資料的 23 個浮點精度警告。沒有偵測到 JavaScript 重複片段或未使用項目，所有指定複雜度門檻均為 0 違規。Python 腳本不在現有 JavaScript 靜態工具的有效涵蓋範圍內，應避免把此報告的零項結果外推為 Python 死碼檢查結論。
