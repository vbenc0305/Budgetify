import ExcelJS from "exceljs";

export function normalizeExcelCell(cell) {
  if (!cell) {
    return "";
  }

  const { value, text } = cell;

  if (value === null || typeof value === "undefined") {
    return "";
  }

  if (value instanceof Date) {
    return text || value.toISOString();
  }

  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map((part) => String(part ?? "")).join("");
  }

  if (typeof value === "object") {
    if (Array.isArray(value.richText)) {
      return value.richText.map((part) => part?.text ?? "").join("");
    }

    if (Object.hasOwn(value, "result")) {
      const result = value.result;
      if (result === null || typeof result === "undefined") {
        return text || "";
      }
      if (result instanceof Date) {
        return text || result.toISOString();
      }
      if (
        typeof result === "string" ||
        typeof result === "number" ||
        typeof result === "boolean"
      ) {
        return result;
      }
      return text || String(result);
    }

    if (typeof value.text === "string" && value.text) {
      return value.text;
    }

    if (typeof value.hyperlink === "string" && value.hyperlink) {
      return text || value.hyperlink;
    }

    if (typeof value.error === "string" && value.error) {
      return value.error;
    }
  }

  return text || String(value);
}

function getWorksheetHeaders(worksheet) {
  const headerRow = worksheet.getRow(1);
  const rowValues = Array.isArray(headerRow.values) ? headerRow.values : [];
  const lastColumnIndex = Math.max(rowValues.length - 1, worksheet.columnCount || 0);
  const headers = [];

  for (let columnIndex = 1; columnIndex <= lastColumnIndex; columnIndex += 1) {
    const normalizedHeader = normalizeExcelCell(headerRow.getCell(columnIndex));
    headers[columnIndex] =
      normalizedHeader === "" ? "" : String(normalizedHeader).trim();
  }

  return headers;
}

export function worksheetToJsonRows(worksheet) {
  if (!worksheet) {
    return [];
  }

  const headers = getWorksheetHeaders(worksheet);
  const rows = [];

  worksheet.eachRow({ includeEmpty: false }, (row, rowNumber) => {
    if (rowNumber === 1) {
      return;
    }

    const rowObject = {};
    let hasData = false;

    for (let columnIndex = 1; columnIndex < headers.length; columnIndex += 1) {
      const header = headers[columnIndex];
      if (!header) {
        continue;
      }

      const value = normalizeExcelCell(row.getCell(columnIndex));
      if (value !== "") {
        hasData = true;
      }
      rowObject[header] = value;
    }

    if (hasData && Object.keys(rowObject).length > 0) {
      rows.push(rowObject);
    }
  });

  return rows;
}

export async function readExcelRowsFromArrayBuffer(arrayBuffer) {
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.load(arrayBuffer);
  return worksheetToJsonRows(workbook.worksheets[0]);
}

export async function readExcelRowsFromFile(file) {
  const arrayBuffer = await file.arrayBuffer();
  return readExcelRowsFromArrayBuffer(arrayBuffer);
}

