import test from "node:test";
import assert from "node:assert/strict";

import {
  normalizeAgeInput,
  toAgePayloadValue,
  validateAge,
} from "../src/utils/profileValidation.js";

test("normalizeAgeInput: removes non-digits and limits to 3 chars", () => {
  assert.equal(normalizeAgeInput("2a7"), "27");
  assert.equal(normalizeAgeInput("  1234  "), "123");
  assert.equal(normalizeAgeInput(""), "");
});

test("validateAge: accepts valid integer age range", () => {
  assert.equal(validateAge("0"), "");
  assert.equal(validateAge("27"), "");
  assert.equal(validateAge("120"), "");
});

test("validateAge: rejects empty and out-of-range values", () => {
  assert.equal(validateAge(""), "Az életkor megadása kötelező.");
  assert.equal(validateAge("121"), "Az életkornak 0 és 120 között kell lennie.");
});

test("toAgePayloadValue: returns number only for valid values", () => {
  assert.equal(toAgePayloadValue("35"), 35);
  assert.equal(toAgePayloadValue("abc"), null);
  assert.equal(toAgePayloadValue("999"), null);
});

