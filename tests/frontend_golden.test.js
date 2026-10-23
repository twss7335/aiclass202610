const assert = require("node:assert/strict");
const test = require("node:test");

const { predictIris } = require("../docs/app.js");
const golden = require("./golden.json");

const TOLERANCE = 1e-6;
const FEATURES = [
  "sepal_length_cm",
  "sepal_width_cm",
  "petal_length_cm",
  "petal_width_cm",
];

test("Iris JS predictions match the three Python golden cases", async testContext => {
  assert.equal(golden.model, "iris");
  assert.deepEqual(golden.feature_order, FEATURES);
  assert.equal(golden.cases.length, 3);

  for (const goldenCase of golden.cases) {
    await testContext.test(goldenCase.name, () => {
      const actual = predictIris(goldenCase.input);
      assert.equal(actual.className, goldenCase.expected_class);
      assert.equal(actual.probabilities.length, goldenCase.probabilities.length);
      for (let index = 0; index < actual.probabilities.length; index += 1) {
        const error = Math.abs(
          actual.probabilities[index] - goldenCase.probabilities[index],
        );
        assert.ok(
          error < TOLERANCE,
          `class ${golden.class_order[index]} probability error ${error} must be < ${TOLERANCE}`,
        );
      }
    });
  }
});
