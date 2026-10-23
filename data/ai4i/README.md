# AI4I 2020 Predictive Maintenance Dataset

來源：UCI Machine Learning Repository，ID 601。網址：https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset ，DOI：https://doi.org/10.24432/C5HS5C 。授權：CC BY 4.0。

`ai4i2020.zip` 取自 UCI 官方靜態下載，`ai4i2020.csv` 為其原始 CSV，未修改標籤或數值。CSV SHA-256：`dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`。

10,000 筆記錄；二元目標為 `Machine failure`。運作特徵是 `Type`、`Air temperature [K]`、`Process temperature [K]`、`Rotational speed [rpm]`、`Torque [Nm]`、`Tool wear [min]`。`UDI`、`Product ID` 為識別欄；TWF、HDF、PWF、OSF、RNF 是失效模式結果標籤。識別欄與結果標籤不進入主要預測模型。
