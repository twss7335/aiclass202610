/* Read-only presentation of the published Python metrics; no hard-coded result values. */
const metricFields = {
  iris: [
    ["accuracy", "Accuracy", "percent"],
    ["macro_f1", "Macro F1", "percent"],
    ["train_samples", "訓練資料", "count"],
    ["test_samples", "測試資料", "count"],
  ],
  ai4i: [
    ["pr_auc", "PR-AUC", "decimal"],
    ["precision", "故障 Precision", "percent"],
    ["recall", "故障 Recall", "percent"],
    ["f1", "故障 F1", "percent"],
    ["test_samples", "測試資料", "count"],
  ],
};

function formatMetric(value, kind) {
  if (kind === "percent") return `${(value * 100).toFixed(2)}%`;
  if (kind === "count") return value.toLocaleString("zh-TW");
  return value.toFixed(4);
}

function displayMetrics(target, payload, fields) {
  const list = document.createElement("dl");
  for (const [key, label, kind] of fields) {
    if (typeof payload.metrics[key] !== "number") throw new Error(`缺少指標：${key}`);
    const term = document.createElement("dt");
    term.textContent = label;
    const value = document.createElement("dd");
    value.textContent = formatMetric(payload.metrics[key], kind);
    list.append(term, value);
  }
  const source = document.createElement("p");
  source.className = "source";
  source.textContent = `數字來源：${payload.source}`;
  target.replaceChildren(list, source);
}

fetch("results.json")
  .then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(results => {
    for (const [name, fields] of Object.entries(metricFields)) {
      displayMetrics(document.getElementById(`${name}-metrics`), results[name], fields);
    }
  })
  .catch(error => {
    for (const name of Object.keys(metricFields)) {
      document.getElementById(`${name}-metrics`).textContent =
        `無法載入 results.json（${error.message}）。請透過本機 HTTP 伺服器開啟此頁。`;
    }
  });
