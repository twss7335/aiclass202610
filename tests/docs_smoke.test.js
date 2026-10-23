const assert = require("node:assert/strict");
const test = require("node:test");


class FakeElement {
  constructor(id = "") {
    this.id = id;
    this.children = [];
    this.innerHTML = "";
    this.textContent = "";
    this.listeners = {};
    this.entries = [];
  }

  addEventListener(type, listener) {
    this.listeners[type] = listener;
  }

  append(...children) {
    this.children.push(...children);
  }

  replaceChildren(...children) {
    this.children = children;
  }

  submit() {
    this.listeners.submit({ preventDefault() {}, currentTarget: this });
  }
}


function createDocument(ids) {
  const elements = Object.fromEntries(ids.map(id => [id, new FakeElement(id)]));
  return {
    elements,
    createElement: () => new FakeElement(),
    getElementById: id => elements[id],
  };
}


function loadSite(globals) {
  Object.assign(globalThis, globals);
  delete require.cache[require.resolve("../docs/site.js")];
  require("../docs/site.js");
}


function loadApp(globals) {
  Object.assign(globalThis, globals);
  delete require.cache[require.resolve("../docs/app.js")];
  require("../docs/app.js");
}


async function settlePromises() {
  await new Promise(resolve => setImmediate(resolve));
  await new Promise(resolve => setImmediate(resolve));
}


test("fixed results.json renders at least three homepage metrics", async () => {
  const document = createDocument(["iris-metrics", "ai4i-metrics"]);
  const fixedResults = {
    iris: { source: "fixed-iris.json", metrics: {
      accuracy: 0.96, macro_f1: 0.95, train_samples: 120, test_samples: 30,
    } },
    ai4i: { source: "fixed-ai4i.json", metrics: {
      pr_auc: 0.87, precision: 0.44, recall: 0.88, f1: 0.59, test_samples: 2000,
    } },
  };
  loadSite({
    document,
    fetch: async () => ({ ok: true, json: async () => fixedResults }),
  });
  await settlePromises();

  const metricValues = document.elements["iris-metrics"].children[0].children
    .filter((_, index) => index % 2 === 1);
  assert.ok(metricValues.length >= 3, "Homepage must render at least three metrics");
  assert.equal(metricValues[0].textContent, "96.00%");
  assert.equal(metricValues[1].textContent, "95.00%");
  assert.equal(metricValues[2].textContent, "120");
});


test("known Iris form values render the predicted class in the shared result", () => {
  const document = createDocument(["iris-form", "ai4i-form", "result"]);
  document.elements["iris-form"].entries = [
    ["sepal_length_cm", "5.1"],
    ["sepal_width_cm", "3.5"],
    ["petal_length_cm", "1.4"],
    ["petal_width_cm", "0.2"],
  ];
  class FakeFormData {
    constructor(form) {
      this.entries = form.entries;
    }

    [Symbol.iterator]() {
      return this.entries[Symbol.iterator]();
    }
  }
  loadApp({
    console,
    document,
    FormData: FakeFormData,
  });
  document.elements["iris-form"].submit();

  assert.match(document.elements.result.innerHTML, /Iris-setosa/);
});


test("failed results.json fetch renders an error instead of a blank region", async () => {
  const document = createDocument(["iris-metrics", "ai4i-metrics"]);
  loadSite({
    document,
    fetch: async () => { throw new Error("network unavailable"); },
  });
  await settlePromises();

  for (const id of ["iris-metrics", "ai4i-metrics"]) {
    assert.match(document.elements[id].textContent, /無法載入 results\.json/);
    assert.match(document.elements[id].textContent, /network unavailable/);
  }
});
