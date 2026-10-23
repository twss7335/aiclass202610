# Iris 資料探索、PCA 與類神經網路分類

> 本儲存庫也包含 [AI4I 2020 設備故障分析](paper/ai4i_study.md)。兩項研究的資料、測試與結果分開保存。

本專案以 UCI Iris Dataset 完成資料品質檢查、探索性資料分析、標準化後的 3D PCA，以及以多層感知器（MLP）進行三分類。開發採用 TDD：先建立資料契約與模型管線測試，再實作、執行實驗，最後以產出物測試驗證結果。

## 實驗摘要

- 150 筆資料、4 個連續特徵、3 個平衡類別（各 50 筆）
- 無缺失值；原始資料包含 1 筆完整重複列，為忠實保留官方資料而未刪除
- 分層切分：訓練 120 筆、測試 30 筆，`random_state=42`
- 測試集 Accuracy：`0.9667`
- Macro Precision / Recall / F1：`0.9697 / 0.9667 / 0.9666`
- PCA 前三主成分解釋變異：`72.96% / 22.85% / 3.67%`，合計 `99.48%`

完整討論請見 [`paper/iris_study.md`](paper/iris_study.md)。

## 專案結構

```text
data/                       UCI 原始檔、整理後 CSV 與資料說明
src/iris_workflow.py        可重現的分析與建模流程
tests/test_iris_workflow.py TDD 測試
results/                    指標、分類報告、統計表與圖表
paper/iris_study.md         小論文
run_analysis.py             一鍵執行入口
requirements.txt            固定版相依套件
```

## 重現方式

需要 Python 3.13（其他近期 Python 3 版本亦可能適用）。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run_analysis.py
python -m unittest discover -s tests -v
```

第一次測試時，產出物測試在 `results/metrics.json` 尚不存在時會跳過；執行分析後再次測試，5 個測試應全部通過。

若執行環境無法寫入預設 Matplotlib cache，可使用：

```bash
MPLCONFIGDIR=.matplotlib python run_analysis.py
```

## 模型設定

- 前處理：`StandardScaler`，只在訓練資料內由 Pipeline 擬合
- 模型：`MLPClassifier`
- 隱藏層：16、8 個神經元
- 啟用函數：ReLU
- 最佳化器：Adam
- 損失函數：多類別 log loss（scikit-learn 內部實作）
- Batch size：16
- 初始學習率：0.01
- L2 regularization (`alpha`)：0.001
- 最大 epoch：1000
- Early stopping：啟用，驗證比例 20%，40 個 epoch 未改善即停止
- 隨機種子：42

## 資料來源與授權

R. A. Fisher, *Iris* [Dataset], UCI Machine Learning Repository, 1936. DOI: https://doi.org/10.24432/C56C76 。資料採 CC BY 4.0 授權；詳見 [`data/README.md`](data/README.md)。

## AI4I 2020：設備故障分析

此研究以 UCI AI4I 2020 的 10,000 筆合成設備資料，預測當筆資料的 `Machine failure`。僅用六項運作特徵及由其推導的物理特徵；識別欄和五種失效模式標籤不進入模型。原始資料及來源見 [`data/ai4i/README.md`](data/ai4i/README.md)，詳細方法、圖表與限制見 [`paper/ai4i_study.md`](paper/ai4i_study.md)。

在已安裝上述 `requirements.txt` 的環境中，可離線重建 AI4I 結果：

```bash
MPLCONFIGDIR=.matplotlib python run_ai4i.py
MPLCONFIGDIR=.matplotlib python -m unittest discover -s tests -v
```

`run_ai4i.py` 會從專案內的原始 CSV 生成 `results/ai4i/` 的資料稽核、EDA／PCA 圖、模型比較、驗證分數、門檻分析、最終測試指標與錯誤案例。第二個指令包含完整流程的端到端整合測試。預設固定亂數種子 42、80/20 分層切分、訓練集內 3 折交叉驗證，按故障類別 PR-AUC（Average Precision）選模型。驗證資料上選擇達到至少 90% Recall 且 Precision 最高的門檻，測試集只做最後評估。唯一的不平衡處理是訓練折內的類別加權；MLP 使用等價的樣本權重，沒有重採樣。

完整實驗在獨立測試集的結果：PR-AUC `0.8737`、故障 Recall `0.8824`、Precision `0.4380`。68 筆故障中偵測 60 筆，漏報 8 筆，誤報 77 筆。驗證集的 90% Recall 目標沒有保證測試集也達到相同數值。模型與門檻是依驗證資料選出；測試集指標並非調參目標。

主要成果：[模型比較](results/ai4i/model_comparison.csv) · [完整指標](results/ai4i/metrics.json) · [PR 曲線](results/ai4i/figures/precision_recall.png) · [驗證門檻取捨](results/ai4i/figures/validation_threshold_tradeoff.png) · [PCA](results/ai4i/eda/pca.png)。

## 純前端互動推論

開啟 [`docs/index.html`](docs/index.html) 即可在瀏覽器試用 Iris 與 AI4I 表單。兩者共用一個結果區，推論只執行 [`docs/app.js`](docs/app.js)，不會向後端傳送輸入。Iris 使用原本的 4→16→8→3 MLP；AI4I 使用選出的 120 棵樹隨機森林及相同的工程特徵。AI4I 顯示的風險門檻為驗證資料選出的 `0.11311298759413635`，不是設備安全標準。

前端參數由訓練集重新擬合後匯出。安裝 Python 相依套件後，可重建並驗證：

```bash
PYTHONPATH=. python scripts/export_frontend_models.py
python -m unittest tests.test_frontend_inference -v
```

第二步需有 Node.js，用於將前端預測機率與 Python 模型逐筆比較；整體測試仍可用 `python -m unittest discover -s tests -v`。匯出步驟僅在開發時需要，使用網頁時不需 Python、Node.js 或 API。

