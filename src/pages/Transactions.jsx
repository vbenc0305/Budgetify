// src/components/Transactions.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useTransaction } from "../stores/useTransaction";
import { useUser } from "../stores/useUser";
import "./styles/Transactions.css";
import MassImportModal from "../components/Modals/MassImportModal.jsx";

const getTransactionId = (tx) =>
  tx?.id ?? tx?.transaction_id ?? tx?.tran_id ?? tx?._id ?? null;

const normalizeTransactionId = (id) => (id === null || id === undefined ? null : String(id));

export default function Transactions() {
  const { user, authChecked } = useUser();
  const [showImportModal, setShowImportModal] = useState(false);
  const [bulkDeleteMode, setBulkDeleteMode] = useState(false);
  const [selectedTransactionIds, setSelectedTransactionIds] = useState([]);
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

  const selectedOnScreenCount = useMemo(() => {
    if (!filtered.length || !selectedTransactionIds.length) return 0;
    return filtered.filter((tx) => {
      const id = normalizeTransactionId(getTransactionId(tx));
      return id && selectedTransactionIds.includes(id);
    }).length;
  }, [filtered, selectedTransactionIds]);

  const applyFilter = () => setTypeFilter(pendingFilter);

  const clearFilter = () => {
    setPendingFilter("all");
    setTypeFilter("all");
  };

  const toggleBulkDeleteMode = () => {
    setDeleteError(null);
    setSelectedTransactionIds([]);
    setBulkDeleteMode((prev) => !prev);
  };

  const toggleTransactionSelection = (rawId) => {
    const id = normalizeTransactionId(rawId);
    if (!id) return;

    setDeleteError(null);
    setSelectedTransactionIds((prev) =>
      prev.includes(id) ? prev.filter((txId) => txId !== id) : [...prev, id],
    );
  };

  const cancelBulkDelete = () => {
    setBulkDeleteMode(false);
    setSelectedTransactionIds([]);
    setDeleteError(null);
  };

  const handleBulkDelete = async () => {
    if (!selectedTransactionIds.length) {
      setDeleteError("Válassz ki legalább egy tranzakciót.");
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

  if (loading) return <div>Betöltés...</div>;

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
              const transactionId = getTransactionId(tx);
              const normalizedId = normalizeTransactionId(transactionId);
              const rawType = tx.tran_type ?? tx.type ?? "";
              const norm = normalizeType(rawType);
              const displayType = norm === "outgoing" ? "Kiadás" : norm === "income" ? "Bevétel" : rawType || "-";

              let dateStr;
              try {
                dateStr = tx.date ? new Date(tx.date).toLocaleDateString() : "-";
              } catch {
                dateStr = tx.date || "-";
              }

              const isSelected = normalizedId ? selectedTransactionIds.includes(normalizedId) : false;

              return (
                <tr key={normalizedId || `${tx.description || "tx"}-${idx}`}>
                  {bulkDeleteMode && (
                    <td>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        disabled={!normalizedId}
                        onChange={() => toggleTransactionSelection(normalizedId)}
                        aria-label={`Tranzakció kijelölése: ${tx.description || normalizedId || idx}`}
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
