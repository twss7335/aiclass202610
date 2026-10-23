# 測試總清單

執行日期：2026-10-23

## Python 測試（26 tests，全數通過）

| 檔案 | 對應範圍 | 測試數 | 狀態 |
| --- | --- | ---: | --- |
| `tests/test_ai4i_workflow.py` | AI4I 資料契約、切分、前處理、評估與整合流程 | 9 | 9 passed |
| `tests/test_experiment_conclusions.py` | 上午實驗的四項結論契約 | 4 | 4 passed |
| `tests/test_frontend_inference.py` | Python 與前端 Iris／AI4I 推論一致性 | 3 | 3 passed |
| `tests/test_iris_workflow.py` | Iris 資料、切分、模型與產出契約 | 5 | 5 passed |
| `tests/test_static_site.py` | 靜態網站、報告、圖檔與結果來源 | 5 | 5 passed |

執行結果：`Ran 26 tests in 10.294s — OK`。

## JavaScript 前端測試（7 tests，全數通過）

| 檔案 | 內容 | 測試數 | 狀態 |
| --- | --- | ---: | --- |
| `tests/docs_smoke.test.js` | 固定 results 顯示、Iris 表單、fetch 失敗訊息 | 3 | 3 passed |
| `tests/frontend_golden.test.js` | Python golden 主測試與 3 筆 Iris 子案例 | 4 | 4 passed |

執行結果：`tests 7 — pass 7 — fail 0`。

## 總覽

| 類別 | 數量 | 狀態 |
| --- | ---: | --- |
| Python unittest | 26 | 26 passed |
| JavaScript Node test | 7 | 7 passed |
| 總計 | 33 | 33 passed |

## 實驗結論的故障注入證明

四項實驗結論不只測函式；每項都曾故意破壞並確認測試會失敗，之後已完整還原：

| 結論 | 注入的錯誤 | 紅燈摘要 |
| --- | --- | --- |
| 特徵不得包含失效模式或目標 | 將 `TWF` 加入特徵 | `Target leakage in feature list: ['TWF']` |
| 不得只預測多數類 | Recall 改為 0 | `Failure recall must be greater than zero` |
| 不得全部預測同一類 | 將所有預測設為 0 | `Predictions collapsed to a single class` |
| 網頁數字需吻合來源結果 | Iris accuracy 改為 0.5 | `Published iris numbers differ from results/metrics.json` |
| 保存的前處理需重現預測 | 第一個 mean 改為 0 | 6/6 機率不一致，最大差異 0.11237381 |

## 其他品質檢查

| 工具 | 結果 |
| --- | --- |
| 新增的 JavaScript 測試 ESLint | 0 violations |
| jscpd | 0 clones、0.00% 重複率 |
| Knip | 0 unused issues |
| 全專案 ESLint | 23 個既知 `no-loss-of-precision` errors，集中於 `docs/app.js` 的生成模型資料；追蹤於 Issue #10 |

因此「33 項測試全數通過」與「全專案靜態檢查仍有 23 個既知錯誤」是兩個不同狀態，不應合併宣稱所有品質檢查全綠。

## 重現指令

```bash
# Python
python -m unittest discover -s tests -v

# JavaScript
pnpm run test:frontend

# 靜態檢查
pnpm run check
```
