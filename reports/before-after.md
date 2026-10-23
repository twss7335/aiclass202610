# Issue #11 修正前後比較

## 摘要

本次從 Issue #11 選出三項彼此相依的技術債進行修正：

1. 將生成模型參數從手寫的 `docs/app.js` 分離為 `docs/model-data.js`。
2. 將 Python exporter 改為直接產生模型資產，不再用 regex 改寫 `app.js`。
3. 建立 generated asset 的載入、靜態檢查與推論一致性契約。

重構維持純前端、無後端、無 build framework。Iris 與 AI4I 的 Python/JavaScript parity tests 均通過。

## 指標修正前後

| 指標 | 修正前 | 修正後 | 變化 |
| --- | ---: | ---: | ---: |
| ESLint 錯誤／警告 | 23 errors / 0 warnings | 0 errors / 0 warnings | -23 errors |
| `complexity > 10` 違規 | 0 | 0 | 0 |
| `max-depth > 3` 違規 | 0 | 0 | 0 |
| `max-lines-per-function > 50` 違規 | 0 | 0 | 0 |
| Cognitive complexity > 15 違規 | 0 | 0 | 0 |
| jscpd 重複率 | 0.00% | 0.00% | 0.00 個百分點 |
| jscpd clones | 0 | 0 | 0 |
| Python tests | 26 | 27 | +1 |
| JavaScript tests | 7 | 7 | 0 |
| 測試總數 | 33 | 34 | +1 |
| 通過測試 | 33 | 34 | +1，全部通過 |

補充：原本 23 個 `no-loss-of-precision` 全部來自 Python 生成的模型參數。修正後不是任意截斷或改寫參數，而是將 generated asset 排除於手寫程式 lint／重複率計算，改由 exporter、載入順序契約，以及 Python/JavaScript 機率一致性測試驗證。最大既有 Iris golden 誤差仍為 `4.163336342344337e-17`，低於 `1e-6` 門檻。

## 三項修正的 diff 摘要

### 1. 分離生成模型資產

| 檔案 | 行數變化 | 說明 |
| --- | ---: | --- |
| `docs/app.js` | +4 / -2 | 移除 926,188 字元的內嵌模型資料，改為讀取已載入資產；保留 Node 測試 fallback。 |
| `docs/model-data.js` | +3 / -0 | 新增由 Python 產生的模型參數資產，包含瀏覽器 global 與 CommonJS export。 |
| `docs/index.html` | +1 / -0 | 在 `app.js` 前載入 `model-data.js`。 |

`docs/app.js` 由 930,619 bytes 降為 4,617 bytes；模型數值原樣移至 926,292 bytes 的 generated asset。

### 2. Exporter 不再改寫手寫程式

| 檔案 | 行數變化 | 說明 |
| --- | ---: | --- |
| `scripts/export_frontend_models.py` | +7 / -8 | 移除 `re` 與 `re.subn` marker replacement，直接覆寫 `docs/model-data.js`。 |

產生器現在只負責生成其擁有的檔案；重新訓練或更新參數時，不會再造成推論／UI 程式的大型單行 diff。

### 3. Generated asset 品質契約

| 檔案 | 行數變化 | 說明 |
| --- | ---: | --- |
| `eslint.config.mjs` | +1 / -0 | generated model asset 不套用手寫程式規則。 |
| `.jscpd.json` | +1 / -1 | generated model asset 不納入重複率，避免模型數值扭曲程式碼指標。 |
| `STATIC_ANALYSIS.md` | +1 / -0 | 記錄 generated asset ownership、排除理由與替代驗證。 |
| `tests/test_static_site.py` | +12 / -0 | 新增模型資產存在、載入順序、app 大小、marker/regex 移除等結構契約。 |

既有測試另外持續驗證：

- 三筆 Iris golden 類別與各類機率，誤差小於 `1e-6`。
- Python Iris MLP 與 JavaScript 推論一致。
- Python AI4I forest 與 JavaScript 推論一致。
- 首頁表單、結果區與 fetch 失敗訊息正常。

## 最難修的項目

最難的是「分離生成模型資產」，因為原本單一檔案同時服務兩種執行環境：

- GitHub Pages 以 classic `<script>` 依序載入，模型資料必須先成為瀏覽器可見的 global。
- Node 測試直接 `require("docs/app.js")`，沒有 HTML 幫忙先載入模型資產。
- 近 1 MB 的參數不能手動整理、截斷或重新估算，否則會悄悄改變機率。

因此修正不只是搬檔案；還需要設計 browser 載入順序、CommonJS fallback、exporter ownership 與 parity regression tests，才能證明 Iris/AI4I 的輸出沒有漂移。

## 驗證結果

```text
pnpm run check
  ESLint: 0 errors
  jscpd: 0 clones, 0.00%
  Knip: 0 issues

python -m unittest discover -s tests -v
  Ran 27 tests — OK

pnpm run test:frontend
  tests 7 — pass 7 — fail 0
```

關聯事件單：#11。原始精度警告追蹤：#10。
