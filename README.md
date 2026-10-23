# Iris 資料探索、PCA 與類神經網路分類

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

