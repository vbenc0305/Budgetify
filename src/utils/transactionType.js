const normalizeText = (value) => {
  if (value === null || value === undefined) return "";

  return String(value)
	.trim()
	.toLowerCase()
	.normalize("NFD")
	.replace(/[\u0300-\u036f]/g, "");
};

const firstNonEmptyString = (...values) => {
  for (const value of values) {
	if (value === null || value === undefined) continue;
	const text = String(value).trim();
	if (text) return text;
  }

  return "";
};

export const getTransactionTypeValue = (transaction) => {
  const directType = firstNonEmptyString(
	transaction?.type,
    transaction?.tran_type,
  );

  return directType;
};

export const normalizeTransactionType = (value) => {
  const normalized = normalizeText(value);

  if (["kiadas", "outgoing", "expense", "expenses", "debit"].includes(normalized)) {
	return "outgoing";
  }

  if (["bevetel", "income", "revenue", "incomes", "incoming", "credit"].includes(normalized)) {
	return "income";
  }

  if (["transfer", "atvezetes", "atutalas"].includes(normalized)) {
	return "transfer";
  }

  return normalized;
};

export const getTransactionTypeDisplay = (transaction) => {
  const rawType = getTransactionTypeValue(transaction);
  const normalizedType = normalizeTransactionType(rawType);

  if (normalizedType === "outgoing") return "Kiadás";
  if (normalizedType === "income") return "Bevétel";
  if (normalizedType === "transfer") return "Transfer";

  return rawType || "-";
};

export const normalizeTransactionRecord = (transaction) => {
  if (!transaction || typeof transaction !== "object") {
	return transaction;
  }

  const normalizedForWho = normalizeText(transaction?.for_who);
  const resolvedType =
    getTransactionTypeValue(transaction) ||
    (normalizedForWho === "kimeno" ? "Transfer" : "");

  return {
	...transaction,
    ...(resolvedType ? { type: resolvedType } : {}),
  };
};

export const normalizeTransactionCollection = (transactions) => {
  if (!Array.isArray(transactions)) return [];
  return transactions.map((transaction) => normalizeTransactionRecord(transaction));
};

