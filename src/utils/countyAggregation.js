export const parseTransactionAmount = (value) => {
  if (typeof value === "number") {
	return Number.isFinite(value) ? value : 0;
  }

  if (value === null || value === undefined) return 0;

  const raw = String(value).trim();
  if (!raw) return 0;

  let normalized = raw
	.replace(/\s+/g, "")
	.replace(/Ft/gi, "")
	.replace(/[^\d,.-]/g, "");

  const hasComma = normalized.includes(",");
  const hasDot = normalized.includes(".");

  if (hasComma && hasDot) {
	if (normalized.lastIndexOf(",") > normalized.lastIndexOf(".")) {
	  normalized = normalized.replace(/\./g, "").replace(",", ".");
	} else {
	  normalized = normalized.replace(/,/g, "");
	}
  } else if (hasComma) {
	normalized = normalized.replace(",", ".");
  }

  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
};

export const normalizeTransactionCategory = (value) => {
  if (value === null || value === undefined) return "Nincs kategória";
  const normalized = String(value).trim();
  return normalized || "Nincs kategória";
};

export const aggregateTransactionsByCategory = (transactions) => {
  if (!Array.isArray(transactions) || transactions.length === 0) return [];

  const totalsByCategory = new Map();

  transactions.forEach((transaction) => {
	const category = normalizeTransactionCategory(transaction?.category);
	const amount = Math.abs(parseTransactionAmount(transaction?.amount));
	totalsByCategory.set(category, (totalsByCategory.get(category) ?? 0) + amount);
  });

  return Array.from(totalsByCategory.entries())
	.map(([category, total]) => ({ category, total }))
	.sort((a, b) => b.total - a.total);
};

export const getTopCategoryTotals = (transactions, limit = 5) =>
  aggregateTransactionsByCategory(transactions).slice(0, Math.max(0, limit));

export const getTransactionSummary = (transactions) => {
  if (!Array.isArray(transactions) || transactions.length === 0) {
	return {
	  count: 0,
	  totalAmount: 0,
	};
  }

  return transactions.reduce(
	(summary, transaction) => ({
	  count: summary.count + 1,
	  totalAmount: summary.totalAmount + Math.abs(parseTransactionAmount(transaction?.amount)),
	}),
	{
	  count: 0,
	  totalAmount: 0,
	},
  );
};


