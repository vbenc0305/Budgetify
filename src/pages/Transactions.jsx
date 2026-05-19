// src/components/Transactions.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useTransaction } from "../stores/useTransaction";
import { useUser } from "../stores/useUser";
import "./styles/Transactions.css";
import MassImportModal from "../components/Modals/MassImportModal.jsx";
import Loading from "../components/Loading";
import { getTransactionTypeDisplay } from "../utils/transactionType";

const extractTransactionId = (tx) => {
  const raw =
    tx?.id ??
    tx?.transaction_id ??
    tx?.tran_id ??
    tx?._id ??
    tx?.path ??
    tx?.ref_path ??
    null;
  if (raw === null || raw === undefined) return null;

  const str = String(raw).trim();
  if (!str) return null;

  // Firebase path format: users/{uid}/transactions/{txId} (or with leading slash)
  const normalizedPath = str.startsWith("/") ? str.slice(1) : str;
  const segments = normalizedPath.split("/").filter(Boolean);
  const txIndex = segments.lastIndexOf("transactions");
  if (txIndex >= 0 && segments[txIndex + 1]) {
    return segments[txIndex + 1];
  }

  return str;
};

const selectionKeyForTx = (tx, idx) =>
  extractTransactionId(tx) ?? `fallback-${idx}`;

const PAGE_SIZE = 50;
const EMPTY_CATEGORY_VALUE = "__empty_category__";

const normalizeDirection = (value) => {
  if (value === null || value === undefined) return "";

  const normalized = String(value)
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

  if (normalized === "bejovo") {
    return "incoming";
  }

  if (normalized === "kimeno") {
    return "outgoing";
  }

  return normalized;
};

const getTransactionDirectionValue = (transaction) =>
  transaction?.transaction_direction ?? "";

const getTransactionDirectionDisplay = (transaction) => {
  const normalizedDirection = normalizeDirection(
    getTransactionDirectionValue(transaction),
  );

  if (normalizedDirection === "incoming") return "Bejövő";
  if (normalizedDirection === "outgoing") return "Kimenő";

  const rawDirection = getTransactionDirectionValue(transaction);
  return rawDirection || "-";
};

const normalizeCategory = (value) => {
  if (value === null || value === undefined) return "";
  return String(value).trim();
};

const parseTransactionAmount = (value) => {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (value === null || value === undefined) return null;

  const raw = String(value).trim();
  if (!raw) return null;

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
  return Number.isFinite(parsed) ? parsed : null;
};

export default function Transactions() {
  const { user, authChecked } = useUser();
  const [showImportModal, setShowImportModal] = useState(false);
  const [bulkDeleteMode, setBulkDeleteMode] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState([]);
  const [deleteError, setDeleteError] = useState(null);

  const transactions = useTransaction((state) => state.transactions);
  const loading = useTransaction((state) => state.loading);
  const error = useTransaction((state) => state.error);
  const fetched = useTransaction((state) => state.fetched);

  const [directionFilter, setDirectionFilter] = useState("all");
  const [pendingDirectionFilter, setPendingDirectionFilter] = useState("all");
  const [amountOperator, setAmountOperator] = useState("gt");
  const [pendingAmountOperator, setPendingAmountOperator] = useState("gt");
  const [amountFilterValue, setAmountFilterValue] = useState("");
  const [pendingAmountFilterValue, setPendingAmountFilterValue] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [pendingCategoryFilter, setPendingCategoryFilter] = useState("all");

  useEffect(() => {
    const { fetchTransactions } = useTransaction.getState();
    const hasAuthUser = !!user && typeof user.getIdToken === "function";
    if (authChecked && hasAuthUser && !fetched) {
      fetchTransactions(user);
    }
  }, [user, authChecked, fetched]);

  const categoryOptions = useMemo(() => {
    if (!transactions?.length) return [];

    const uniqueCategories = new Set();
    let hasEmptyCategory = false;

    transactions.forEach((tx) => {
      const category = normalizeCategory(tx?.category);
      if (category) {
        uniqueCategories.add(category);
      } else {
        hasEmptyCategory = true;
      }
    });

    const sortedCategories = Array.from(uniqueCategories).sort((a, b) =>
      a.localeCompare(b, "hu"),
    );

    return hasEmptyCategory
      ? [...sortedCategories, EMPTY_CATEGORY_VALUE]
      : sortedCategories;
  }, [transactions]);

  const filtered = useMemo(() => {
    if (!transactions) return [];

    const parsedAmountFilter = parseTransactionAmount(amountFilterValue);

    return transactions.filter((tx) => {
      const rawDirection = getTransactionDirectionValue(tx);
      if (
        directionFilter !== "all" &&
        normalizeDirection(rawDirection) !== directionFilter
      ) {
        return false;
      }

      const normalizedCategory = normalizeCategory(tx?.category);
      if (categoryFilter !== "all") {
        if (categoryFilter === EMPTY_CATEGORY_VALUE) {
          if (normalizedCategory) return false;
        } else if (normalizedCategory !== categoryFilter) {
          return false;
        }
      }

      if (amountFilterValue.trim() && parsedAmountFilter !== null) {
        const transactionAmount = parseTransactionAmount(tx?.amount);
        if (transactionAmount === null) return false;

        if (amountOperator === "lt" && !(transactionAmount < parsedAmountFilter)) {
          return false;
        }

        if (amountOperator === "gt" && !(transactionAmount > parsedAmountFilter)) {
          return false;
        }

        if (amountOperator === "eq" && transactionAmount !== parsedAmountFilter) {
          return false;
        }
      }

      return true;
    });
  }, [
    transactions,
    directionFilter,
    categoryFilter,
    amountFilterValue,
    amountOperator,
  ]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const [currentPage, setCurrentPage] = useState(1);
  const effectiveCurrentPage = Math.min(currentPage, totalPages);

  const currentPageStartIndex = (effectiveCurrentPage - 1) * PAGE_SIZE;
  const currentPageEndIndex = currentPageStartIndex + PAGE_SIZE;

  const pagedRows = useMemo(
    () =>
      filtered
        .slice(currentPageStartIndex, currentPageEndIndex)
        .map((tx, idx) => ({ tx, globalIdx: currentPageStartIndex + idx })),
    [filtered, currentPageStartIndex, currentPageEndIndex],
  );

  const filteredSelectionKeys = useMemo(
    () => filtered.map((tx, idx) => selectionKeyForTx(tx, idx)),
    [filtered],
  );

  const allFilteredSelected =
    filteredSelectionKeys.length > 0 &&
    filteredSelectionKeys.every((key) => selectedKeys.includes(key));

  const selectedInFilteredCount = useMemo(() => {
    if (!filtered.length || !selectedKeys.length) return 0;
    return filtered.filter((tx, idx) =>
      selectedKeys.includes(selectionKeyForTx(tx, idx)),
    ).length;
  }, [filtered, selectedKeys]);

  const pageNumbers = useMemo(
    () => Array.from({ length: totalPages }, (_, idx) => idx + 1),
    [totalPages],
  );

  const applyFilter = () => {
    setDirectionFilter(pendingDirectionFilter);
    setAmountOperator(pendingAmountOperator);
    setAmountFilterValue(pendingAmountFilterValue);
    setCategoryFilter(pendingCategoryFilter);
    setCurrentPage(1);
  };

  const clearFilter = () => {
    setPendingDirectionFilter("all");
    setDirectionFilter("all");
    setPendingAmountOperator("gt");
    setAmountOperator("gt");
    setPendingAmountFilterValue("");
    setAmountFilterValue("");
    setPendingCategoryFilter("all");
    setCategoryFilter("all");
    setCurrentPage(1);
  };

  const toggleBulkDeleteMode = () => {
    setDeleteError(null);
    setSelectedKeys([]);
    setBulkDeleteMode((prev) => !prev);
  };

  const toggleTransactionSelection = (key) => {
    if (!key) return;

    setDeleteError(null);
    setSelectedKeys((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    );
  };

  const toggleSelectAllFiltered = () => {
    setDeleteError(null);

    if (allFilteredSelected) {
      const filteredSet = new Set(filteredSelectionKeys);
      setSelectedKeys((prev) => prev.filter((key) => !filteredSet.has(key)));
      return;
    }

    setSelectedKeys((prev) => {
      const merged = new Set(prev);
      filteredSelectionKeys.forEach((key) => merged.add(key));
      return Array.from(merged);
    });
  };

  const cancelBulkDelete = () => {
    setBulkDeleteMode(false);
    setSelectedKeys([]);
    setDeleteError(null);
  };

  const handleBulkDelete = async () => {
    if (!selectedKeys.length) {
      setDeleteError("Válassz ki legalább egy tranzakciót.");
      return;
    }

    const selectedTransactionIds = filtered
      .map((tx, idx) => ({
        key: selectionKeyForTx(tx, idx),
        id: extractTransactionId(tx),
      }))
      .filter((item) => selectedKeys.includes(item.key))
      .map((item) => item.id)
      .filter(Boolean);

    if (!selectedTransactionIds.length) {
      setDeleteError(
        "A kijelölt elemekhez nem található törölhető tranzakció azonosító.",
      );
      return;
    }

    const confirmed = window.confirm(
      `Biztosan törölni szeretnél ${selectedTransactionIds.length} tranzakciót? Ez a művelet nem visszavonható.`,
    );
    if (!confirmed) return;

    try {
      const { massDeleteTransactions } = useTransaction.getState();
      await massDeleteTransactions(selectedTransactionIds, user);
      cancelBulkDelete();
    } catch (err) {
      setDeleteError(err?.message || "A tömeges törlés sikertelen.");
    }
  };

  if (loading) return <Loading />;

  if (!transactions || transactions.length === 0)
    return (
      <div className="transactionsWrapper noTransactions">
        <MassImportModal
          onClose={() => setShowImportModal(false)}
          onImport={(count) => {
            console.log(`${count} tranzakció importálva`);
            const { fetchTransactions } = useTransaction.getState();
            if (user) fetchTransactions(user);
            setShowImportModal(false);
          }}
          isOpen={showImportModal}
          user={user}
        />
        <div className="noTransactionsCard">
          {error ? (
            <p style={{ color: "#b91c1c", marginBottom: 12 }}>
              {String(error)}
            </p>
          ) : (
            <p>Nincsenek tranzakciók.</p>
          )}

          <button
            className="importButton"
            onClick={() => setShowImportModal(true)}
          >
            Kiadások importálása OTP-ből
          </button>
        </div>
      </div>
    );

  return (
    <div className="transactionsWrapper">
      <MassImportModal
        onClose={() => setShowImportModal(false)}
        onImport={(count) => {
          console.log(`${count} tranzakció importálva`);
          const { fetchTransactions } = useTransaction.getState();
          if (user) fetchTransactions(user);
          setShowImportModal(false);
        }}
        isOpen={showImportModal}
        user={user}
      />

      <div className="filterBox" role="region" aria-label="Tranzakció szűrő">
        <div className="filterRow">
          <label htmlFor="directionFilter" className="filterLabel">
            <strong>Tranzakció iránya</strong>
          </label>

          <select
            id="directionFilter"
            value={pendingDirectionFilter}
            onChange={(e) => setPendingDirectionFilter(e.target.value)}
            className="filterSelect"
            aria-label="Tranzakció iránya"
          >
            <option value="all">Minden</option>
            <option value="incoming">Bejövő</option>
            <option value="outgoing">Kimenő</option>
          </select>

          <label htmlFor="amountOperator" className="filterLabel">
            <strong>Összeg</strong>
          </label>

          <select
            id="amountOperator"
            value={pendingAmountOperator}
            onChange={(e) => setPendingAmountOperator(e.target.value)}
            className="filterSelect"
            aria-label="Összeg összehasonlítás"
          >
            <option value="gt">&gt;</option>
            <option value="lt">&lt;</option>
            <option value="eq">=</option>
          </select>

          <input
            type="text"
            inputMode="decimal"
            value={pendingAmountFilterValue}
            onChange={(e) => setPendingAmountFilterValue(e.target.value)}
            className="filterInput"
            placeholder="Összeg"
            aria-label="Összeg érték"
          />

          <label htmlFor="categoryFilter" className="filterLabel">
            <strong>Kategória</strong>
          </label>

          <select
            id="categoryFilter"
            value={pendingCategoryFilter}
            onChange={(e) => setPendingCategoryFilter(e.target.value)}
            className="filterSelect"
            aria-label="Kategória"
          >
            <option value="all">Minden</option>
            {categoryOptions.map((category) => (
              <option key={category} value={category}>
                {category === EMPTY_CATEGORY_VALUE ? "Nincs kategória" : category}
              </option>
            ))}
          </select>

          <button
            onClick={applyFilter}
            className="filterApplyButton"
            aria-label="Szűrő alkalmazása"
          >
            Filter Alkalmazása
          </button>

          <button
            onClick={clearFilter}
            className="filterClearButton"
            aria-label="Szűrő törlése"
          >
            Filter Törlése
          </button>

          {!bulkDeleteMode ? (
            <button
              onClick={toggleBulkDeleteMode}
              className="bulkDeleteToggleButton"
              aria-label="Tömeges törlés mód"
            >
              Tranzakciók törlése
            </button>
          ) : (
            <div className="bulkDeleteActions">
              <span className="bulkDeleteCount">
                Kijelölve: {selectedInFilteredCount}
              </span>
              <button
                onClick={toggleSelectAllFiltered}
                className="bulkDeleteSelectAllButton"
              >
                {allFilteredSelected
                  ? "Kijelölés törlése"
                  : "Összes kiválasztása"}
              </button>
              <button
                onClick={cancelBulkDelete}
                className="bulkDeleteCancelButton"
              >
                Mégse
              </button>
              <button
                onClick={handleBulkDelete}
                className="bulkDeleteConfirmButton"
              >
                Törlés véglegesítése
              </button>
            </div>
          )}

          <div className="resultCount" aria-live="polite">
            Találatok: <strong>{filtered.length}</strong>
          </div>
        </div>

        {deleteError && <p className="bulkDeleteError">{deleteError}</p>}

        {(directionFilter !== "all" ||
          categoryFilter !== "all" ||
          amountFilterValue.trim()) && (
          <div className="activeFilterInfo">
            Aktív szűrők:{" "}
            {directionFilter !== "all" && (
              <strong>
                Irány: {directionFilter === "incoming" ? "Bejövő" : "Kimenő"}
              </strong>
            )}
            {categoryFilter !== "all" && (
              <strong>
                {directionFilter !== "all" ? " • " : ""}
                Kategória: {categoryFilter === EMPTY_CATEGORY_VALUE ? "Nincs kategória" : categoryFilter}
              </strong>
            )}
            {amountFilterValue.trim() && (
              <strong>
                {directionFilter !== "all" || categoryFilter !== "all" ? " • " : ""}
                Összeg {amountOperator === "gt" ? ">" : amountOperator === "lt" ? "<" : "="} {amountFilterValue}
              </strong>
            )}
          </div>
        )}

        {filtered.length > PAGE_SIZE && (
          <div className="paginationInfo" aria-live="polite">
            Oldal <strong>{effectiveCurrentPage}</strong> / {totalPages}
          </div>
        )}
      </div>

      <div className="tableContainer">
        <table
          className="transactionsTable"
          role="table"
          aria-label="Tranzakciók"
        >
          <thead>
            <tr>
              {bulkDeleteMode && <th scope="col">Kijelölés</th>}
              <th scope="col">Dátum</th>
              <th scope="col">Összeg</th>
              <th scope="col">Leírás</th>
              <th scope="col">Tranzakció típusa</th>
              <th scope="col">Kategória</th>
            </tr>
          </thead>
          <tbody>
            {pagedRows.map(({ tx, globalIdx }) => {
              const txId = extractTransactionId(tx);
              const rowSelectionKey = selectionKeyForTx(tx, globalIdx);
              const displayType = getTransactionTypeDisplay(tx);
              const displayDirection = getTransactionDirectionDisplay(tx);

              let dateStr;
              try {
                dateStr = tx.date
                  ? new Date(tx.date).toLocaleDateString()
                  : "-";
              } catch {
                dateStr = tx.date || "-";
              }

              const isSelected = selectedKeys.includes(rowSelectionKey);

              return (
                <tr key={rowSelectionKey}>
                  {bulkDeleteMode && (
                    <td>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() =>
                          toggleTransactionSelection(rowSelectionKey)
                        }
                        aria-label={`Tranzakció kijelölése: ${tx.description || txId || globalIdx}`}
                      />
                    </td>
                  )}
                  <td>{dateStr}</td>
                  <td>{tx.amount ?? "-"}</td>
                  <td title={tx.description || "-"}>{tx.description || "-"}</td>
                  <td title={`Típus: ${displayType} | Irány: ${displayDirection}`}>
                    {displayType} / {displayDirection}
                  </td>
                  <td>{tx.category || "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filtered.length > PAGE_SIZE && (
        <div
          className="paginationTabs"
          role="tablist"
          aria-label="Tranzakció oldalak"
        >
          <button
            type="button"
            className="paginationTabButton"
            onClick={() =>
              setCurrentPage(Math.max(effectiveCurrentPage - 1, 1))
            }
            disabled={effectiveCurrentPage === 1}
            aria-label="Előző oldal"
          >
            Elozo
          </button>

          {pageNumbers.map((page) => (
            <button
              key={page}
              type="button"
              role="tab"
              aria-selected={effectiveCurrentPage === page}
              className={`paginationTabButton ${effectiveCurrentPage === page ? "active" : ""}`}
              onClick={() => setCurrentPage(page)}
            >
              {page}
            </button>
          ))}

          <button
            type="button"
            className="paginationTabButton"
            onClick={() =>
              setCurrentPage(Math.min(effectiveCurrentPage + 1, totalPages))
            }
            disabled={effectiveCurrentPage === totalPages}
            aria-label="Következő oldal"
          >
            Kovetkezo
          </button>
        </div>
      )}
    </div>
  );
}
