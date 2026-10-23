import eslint from "@eslint/js";
import sonarjs from "eslint-plugin-sonarjs";
import globals from "globals";

const qualityRules = {
  "complexity": ["error", 10],
  "max-depth": ["error", 3],
  "max-lines-per-function": ["error", {
    "max": 50,
    "skipBlankLines": true,
    "skipComments": true,
    "IIFEs": true
  }],
  "sonarjs/cognitive-complexity": ["error", 15]
};

export default [
  {
    ignores: [
      "node_modules/**",
      "reports/static-analysis/**",
      "docs/model-data.js",
      "docs/figures/**",
      "docs/assets/**",
      "docs/artifacts/**"
    ]
  },
  {
    files: ["**/*.{js,mjs,cjs}"],
    plugins: { sonarjs },
    rules: {
      ...eslint.configs.recommended.rules,
      ...sonarjs.configs.recommended.rules,
      ...qualityRules
    }
  },
  {
    files: ["docs/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "script",
      globals: globals.browser
    }
  },
  {
    files: ["docs/app.js"],
    languageOptions: {
      globals: {
        "module": "readonly"
      }
    }
  },
  {
    files: [
      "scripts/**/*.{js,mjs,cjs}",
      "tests/**/*.{js,mjs,cjs}",
      "*.config.{js,mjs,cjs}"
    ],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.node
    }
  }
];
