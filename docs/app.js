/* Static, self-contained inference. Regenerate model-data.js with scripts/export_frontend_models.py. */
const MODEL_DATA = globalThis.MODEL_DATA ||
  (typeof module !== "undefined" ? module.require("./model-data.js") : null);
if (!MODEL_DATA) throw new Error("model-data.js must load before app.js");

function numeric(row, name) {
  const value = Number(row[name]);
  if (row[name] === "" || row[name] == null || !Number.isFinite(value)) {
    throw new Error(`請輸入有效的${name}數值。`);
  }
  return value;
}

function predictIris(row) {
  const model = MODEL_DATA.iris;
  let layer = model.features.map((name, i) =>
    (numeric(row, name) - model.mean[i]) / model.scale[i]);
  for (let layerIndex = 0; layerIndex < model.weights.length; layerIndex += 1) {
    const weights = model.weights[layerIndex];
    const bias = model.biases[layerIndex];
    const next = bias.map((offset, outputIndex) =>
      offset + layer.reduce((sum, input, inputIndex) =>
        sum + input * weights[inputIndex][outputIndex], 0));
    layer = layerIndex < model.weights.length - 1
      ? next.map(value => Math.max(0, value)) : next;
  }
  const maximum = Math.max(...layer);
  const exponentials = layer.map(value => Math.exp(value - maximum));
  const total = exponentials.reduce((sum, value) => sum + value, 0);
  const probabilities = exponentials.map(value => value / total);
  const winner = probabilities.indexOf(Math.max(...probabilities));
  return { className: model.classes[winner], probabilities };
}

function predictAI4I(row) {
  const model = MODEL_DATA.ai4i;
  const air = numeric(row, "Air temperature [K]");
  const process = numeric(row, "Process temperature [K]");
  const speed = numeric(row, "Rotational speed [rpm]");
  const torque = numeric(row, "Torque [Nm]");
  const wear = numeric(row, "Tool wear [min]");
  const type = row.Type;
  if (!model.types.includes(type)) throw new Error("請選擇有效的產品等級。");
  const raw = [air, process, speed, torque, wear,
    process - air, torque * speed * (2 * Math.PI / 60), wear * torque];
  // scikit-learn's forest converts the preprocessed matrix to float32 before tree traversal.
  const features = raw.map((value, i) => Math.fround((value - model.mean[i]) / model.scale[i]));
  for (const category of model.types) features.push(type === category ? 1 : 0);
  let total = 0;
  for (const tree of model.trees) {
    let node = 0;
    while (tree.l[node] !== -1) {
      node = features[tree.f[node]] <= tree.t[node] ? tree.l[node] : tree.r[node];
    }
    total += tree.p[node];
  }
  const failureProbability = total / model.trees.length;
  return { failureProbability, threshold: model.threshold,
    highRisk: failureProbability >= model.threshold };
}

function percent(value) { return `${(value * 100).toFixed(2)}%`; }

function collect(form) {
  const values = {};
  for (const [name, value] of new FormData(form)) values[name] = value;
  return values;
}

if (typeof document !== "undefined") {
  const result = document.getElementById("result");
  document.getElementById("iris-form").addEventListener("submit", event => {
    event.preventDefault();
    try {
      const prediction = predictIris(collect(event.currentTarget));
      const labels = MODEL_DATA.iris.classes;
      result.innerHTML = `<h2>Iris 推論結果</h2><p>預測類別：<strong>${prediction.className}</strong></p>` +
        `<table class="probabilities"><thead><tr><th>類別</th><th>機率</th><th>比例</th></tr></thead><tbody>` +
        prediction.probabilities.map((value, i) => `<tr><td>${labels[i]}</td><td>${percent(value)}</td>` +
          `<td><span class="bar" style="width:${(value * 100).toFixed(2)}%"></span></td></tr>`).join("") +
        `</tbody></table>`;
    } catch (error) { result.innerHTML = `<h2>輸入錯誤</h2><p>${error.message}</p>`; }
  });
  document.getElementById("ai4i-form").addEventListener("submit", event => {
    event.preventDefault();
    try {
      const prediction = predictAI4I(collect(event.currentTarget));
      result.innerHTML = `<h2>AI4I 推論結果</h2><p>故障機率：<strong>${percent(prediction.failureProbability)}</strong></p>` +
        `<p class="${prediction.highRisk ? "warning" : ""}">${prediction.highRisk ? "超過" : "未達"}實驗決策門檻 ${percent(prediction.threshold)}。</p>` +
        `<p class="footnote">此門檻來自實驗驗證集，不代表工業現場的安全標準。</p>`;
    } catch (error) { result.innerHTML = `<h2>輸入錯誤</h2><p>${error.message}</p>`; }
  });
}

if (typeof module !== "undefined") module.exports = { predictIris, predictAI4I };
