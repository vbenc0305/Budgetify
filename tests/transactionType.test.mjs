import test from "node:test";
import assert from "node:assert/strict";

import {
  getTransactionTypeDisplay,
  getTransactionTypeValue,
  normalizeTransactionCollection,
  normalizeTransactionType,
} from "../src/utils/transactionType.js";

test("getTransactionTypeValue uses the normalized type field", () => {
  assert.equal(getTransactionTypeValue({ type: "Transfer" }), "Transfer");
  assert.equal(getTransactionTypeValue({ tran_type: "Kiadás" }), "Kiadás");
});

test("getTransactionTypeValue prefers normalized type over raw tran_type", () => {
  assert.equal(
    getTransactionTypeValue({ type: "Transfer", tran_type: "VÁSÁRLÁS KÁRTYÁVAL" }),
    "Transfer",
  );
});

test("normalizeTransactionType recognizes transfer values", () => {
  assert.equal(normalizeTransactionType("Transfer"), "transfer");
  assert.equal(normalizeTransactionType("Átvezetés"), "transfer");
});

test("normalizeTransactionCollection injects derived type into returned records", () => {
  assert.deepEqual(normalizeTransactionCollection([{ id: 1, for_who: "Kimenő" }]), [
    { id: 1, for_who: "Kimenő", type: "Transfer" },
  ]);
});

test("normalizeTransactionCollection converts Kimenő to Transfer even when tran_type exists", () => {
  assert.deepEqual(
    normalizeTransactionCollection([
      { id: 1, for_who: "Kimenő", tran_type: "VÁSÁRLÁS KÁRTYÁVAL" },
    ]),
    [
      {
        id: 1,
        for_who: "Kimenő",
        tran_type: "VÁSÁRLÁS KÁRTYÁVAL",
        type: "VÁSÁRLÁS KÁRTYÁVAL",
      },
    ],
  );
});

test("getTransactionTypeDisplay renders Transfer label from the normalized type field", () => {
  assert.equal(getTransactionTypeDisplay({ type: "Transfer" }), "Transfer");
});

