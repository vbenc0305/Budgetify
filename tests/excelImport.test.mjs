import test from "node:test";
import assert from "node:assert/strict";
import ExcelJS from "exceljs";

import {
  normalizeExcelCell,
  readExcelRowsFromArrayBuffer,
  worksheetToJsonRows,
} from "../src/utils/excelImport.js";

test("worksheetToJsonRows maps headers, fills missing cells, and skips blank rows", () => {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet("OTP");

  worksheet.addRow(["Tranzakció dátuma", "Típus", "Összeg"]);
  worksheet.addRow(["2026-05-05", "Vásárlás", -1250]);
  worksheet.addRow(["2026-05-06", undefined, -500]);
  worksheet.addRow([]);

  assert.deepEqual(worksheetToJsonRows(worksheet), [
    {
      "Tranzakció dátuma": "2026-05-05",
      Típus: "Vásárlás",
      Összeg: -1250,
    },
    {
      "Tranzakció dátuma": "2026-05-06",
      Típus: "",
      Összeg: -500,
    },
  ]);
});

test("normalizeExcelCell resolves formula and rich text values", () => {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet("OTP");

  worksheet.getCell("A1").value = { formula: "1+1", result: 2 };
  worksheet.getCell("B1").value = {
    richText: [{ text: "OTP" }, { text: " import" }],
  };

  assert.equal(normalizeExcelCell(worksheet.getCell("A1")), 2);
  assert.equal(normalizeExcelCell(worksheet.getCell("B1")), "OTP import");
});

test("readExcelRowsFromArrayBuffer loads the first worksheet from an xlsx buffer", async () => {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet("OTP");

  worksheet.addRow(["Tranzakció dátuma", "Közlemény"]);
  worksheet.addRow(["2026-05-05", "Teszt tranzakció"]);

  const buffer = await workbook.xlsx.writeBuffer();
  const arrayBuffer =
    buffer instanceof ArrayBuffer
      ? buffer
      : buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength);

  const rows = await readExcelRowsFromArrayBuffer(arrayBuffer);

  assert.deepEqual(rows, [
    {
      "Tranzakció dátuma": "2026-05-05",
      Közlemény: "Teszt tranzakció",
    },
  ]);
});

