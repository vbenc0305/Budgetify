// src/components/Transactions.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useTransaction } from "../stores/useTransaction";
import { useUser } from "../stores/useUser";
import "./styles/Transactions.css";
import MassImportModal from "../components/Modals/MassImportModal.jsx";
import Loading from "../components/Loading";

const extractTransactionId = (tx) => {
  const raw = tx?.id ?? tx?.transaction_id ?? tx?.tran_id ?? tx?._id ?? tx?.path ?? tx?.ref_path ?? null;
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

const selectionKeyForTx = (tx, idx) => extractTransactionId(tx) ?? `fallback-${idx}`;

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

  const [typeFilter, setTypeFilter] = useState("all");
  const [pendingFilter, setPendingFilter] = useState("all");

  useEffect(() => {
    const { fetchTransactions } = useTransaction.getState();
    if (authChecked && user && !fetched) {
      fetchTransactions(user);
    }
  }, [user, authChecked, fetched]);

  const normalizeType = (val) => {
    if (val === null || val === undefined) return "";
    const t = String(val).trim().toLowerCase();
    if (["kiadás", "outgoing", "expense", "expenses"].includes(t)) return "outgoing";
    if (["bevétel", "income", "revenue", "incomes", "incoming"].includes(t)) return "income";
    return t;
  };

  const filtered = useMemo(() => {
    if (!transactions) return [];
    if (typeFilter === "all") return transactions;
    return transactions.filter((tx) => {
      const raw = tx.tran_type ?? tx.type ?? "";
      return normalizeType(raw) === typeFilter;
    });
  }, [transactions, typeFilter]);

  const filteredSelectionKeys = useMemo(
    () => filtered.map((tx, idx) => selectionKeyForTx(tx, idx)),
    [filtered],
  );

  const allFilteredSelected =
    filteredSelectionKeys.length > 0 &&
    filteredSelectionKeys.every((key) => selectedKeys.includes(key));

  const selectedOnScreenCount = useMemo(() => {
    if (!filtered.length || !selectedKeys.length) return 0;
    return filtered.filter((tx, idx) => selectedKeys.includes(selectionKeyForTx(tx, idx))).length;
  }, [filtered, selectedKeys]);

  const applyFilter = () => setTypeFilter(pendingFilter);

  const clearFilter = () => {
    setPendingFilter("all");
    setTypeFilter("all");
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
      .map((tx, idx) => ({ key: selectionKeyForTx(tx, idx), id: extractTransactionId(tx) }))
      .filter((item) => selectedKeys.includes(item.key))
      .map((item) => item.id)
      .filter(Boolean);

    if (!selectedTransactionIds.length) {
      setDeleteError("A kijelölt elemekhez nem található törölhető tranzakció azonosító.");
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
            <p style={{ color: "#b91c1c", marginBottom: 12 }}>{String(error)}</p>
          ) : (
            <p>Nincsenek tranzakciók.</p>
          )}

          <button className="importButton" onClick={() => setShowImportModal(true)}>
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
          <label htmlFor="typeFilter" className="filterLabel">
            <strong>Kiadás típusa</strong>
          </label>

          <select
            id="typeFilter"
            value={pendingFilter}
            onChange={(e) => setPendingFilter(e.target.value)}
            className="filterSelect"
            aria-label="Kiadás típusa"
          >
            <option value="all">Minden</option>
            <option value="outgoing">Kiadás</option>
            <option value="income">Bevétel</option>
          </select>

          <button onClick={applyFilter} className="filterApplyButton" aria-label="Szűrő alkalmazása">
            Alkalmaz
          </button>

          <button onClick={clearFilter} className="filterClearButton" aria-label="Szűrő törlése">
            Töröl
          </button>

          {!bulkDeleteMode ? (
            <button
              onClick={toggleBulkDeleteMode}
              className="bulkDeleteToggleButton"
              aria-label="Tömeges törlés mód"
            >
              Tömeges törlés
            </button>
          ) : (
            <div className="bulkDeleteActions">
              <span className="bulkDeleteCount">Kijelölve: {selectedOnScreenCount}</span>
              <button onClick={toggleSelectAllFiltered} className="bulkDeleteSelectAllButton">
                {allFilteredSelected ? "Kijelölés törlése" : "Összes kiválasztása"}
              </button>
              <button onClick={cancelBulkDelete} className="bulkDeleteCancelButton">
                Mégse
              </button>
              <button onClick={handleBulkDelete} className="bulkDeleteConfirmButton">
                Törlés véglegesítése
              </button>
            </div>
          )}

          <div className="resultCount" aria-live="polite">
            Találatok: <strong>{filtered.length}</strong>
          </div>
        </div>

        {deleteError && <p className="bulkDeleteError">{deleteError}</p>}

        {typeFilter !== "all" && (
          <div className="activeFilterInfo">
            Aktív szűrő: <strong>{typeFilter === "outgoing" ? "Kiadás" : "Bevétel"}</strong>
          </div>
        )}
      </div>

      <div className="tableContainer">
        <table className="transactionsTable" role="table" aria-label="Tranzakciók">
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
            {filtered.map((tx, idx) => {
              const txId = extractTransactionId(tx);
              const rowSelectionKey = selectionKeyForTx(tx, idx);
              const rawType = tx.tran_type ?? tx.type ?? "";
              const norm = normalizeType(rawType);
              const displayType = norm === "outgoing" ? "Kiadás" : norm === "income" ? "Bevétel" : rawType || "-";

              let dateStr;
              try {
                dateStr = tx.date ? new Date(tx.date).toLocaleDateString() : "-";
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
                        onChange={() => toggleTransactionSelection(rowSelectionKey)}
                        aria-label={`Tranzakció kijelölése: ${tx.description || txId || idx}`}
                      />
                    </td>
                  )}
                  <td>{dateStr}</td>
                  <td>{tx.amount ?? "-"}</td>
                  <td title={tx.description || "-"}>{tx.description || "-"}</td>
                  <td>{displayType}</td>
                  <td>{tx.category || "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
