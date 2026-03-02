// src/components/Transactions.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useTransaction } from "../stores/useTransaction";
import { useUser } from "../stores/useUser";
import "./styles/Transactions.css";
import MassImportModal from "../components/Modals/MassImportModal.jsx";

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

  // --- Aktív szűrő amely ténylegesen hat a listára
  const [typeFilter, setTypeFilter] = useState("all");
  // --- Ideiglenes választás a selectben (amíg meg nem nyomod az "Alkalmaz" gombot)
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
    if (["kiadás", "outgoing", "expense", "expenses"].includes(t))
      return "outgoing";
    if (["bevétel", "income", "revenue", "incomes", "incoming"].includes(t))
      return "income";
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

  const selectedOnScreenCount = useMemo(
    () => filtered.filter((tx) => selectedTransactionIds.includes(tx.id)).length,
    [filtered, selectedTransactionIds],
  );

  // Alkalmaz gomb logika: csak ha változott, akkor állítjuk be az aktív szűrőt
  const applyFilter = () => {
    setTypeFilter(pendingFilter);
  };

  // Gyors reset (visszaállítja a pending-et és az aktívot is)
  const clearFilter = () => {
    setPendingFilter("all");
    setTypeFilter("all");
  };

  const toggleBulkDeleteMode = () => {
    setDeleteError(null);
    setSelectedTransactionIds([]);
    setBulkDeleteMode((prev) => !prev);
  };

  const toggleTransactionSelection = (id) => {
    if (id === undefined || id === null) return;
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
  // If loading, show loader. Otherwise, when there are no transactions show the
  // original no-transactions card (and surface any store error inside it).
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
          {/* prefer showing the friendly card; if there's an error show it inline */}
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
      {/* --- Szűrő doboz (kártya) */}
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

          <button
            onClick={applyFilter}
            className="filterApplyButton"
            title="Szűrő alkalmazása"
            aria-label="Szűrő alkalmazása"
          >
            Alkalmaz
          </button>

          <button
            onClick={clearFilter}
            className="filterClearButton"
            title="Szűrő törlése"
            aria-label="Szűrő törlése"
          >
            Töröl
          </button>

          {!bulkDeleteMode ? (
            <button
              onClick={toggleBulkDeleteMode}
              className="bulkDeleteToggleButton"
              title="Tömeges törlés"
              aria-label="Tömeges törlés mód"
            >
              Tömeges törlés
            </button>
          ) : (
            <div className="bulkDeleteActions">
              <span className="bulkDeleteCount">Kijelölve: {selectedOnScreenCount}</span>
              <button
                onClick={cancelBulkDelete}
                className="bulkDeleteCancelButton"
                title="Tömeges törlés megszakítása"
                aria-label="Tömeges törlés megszakítása"
              >
                Mégse
              </button>
              <button
                onClick={handleBulkDelete}
                className="bulkDeleteConfirmButton"
                title="Kijelöltek törlése"
                aria-label="Kijelöltek törlése"
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

        {/* Megmutatjuk melyik szűrő van épp alkalmazva */}
        <div className="appliedInfo">
          {typeFilter !== "all" && (
            <div className="appliedInfo">
              Aktív szűrő:{" "}
              <strong>
                {typeFilter === "outgoing"
                  ? "Kiadás"
                  : typeFilter === "income"
                    ? "Bevétel"
                    : "Ismeretlen"}
              </strong>
            </div>
          )}
        </div>
      </div>

      {/* --- Táblázat konténerrel (lekerekített, fehér háttér) */}
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
            {filtered.map((tx, idx) => {
              const rawType = tx.tran_type ?? tx.type ?? "";
              const norm = normalizeType(rawType);
              const displayType =
                norm === "outgoing"
                  ? "Kiadás"
                  : norm === "income"
                    ? "Bevétel"
                    : rawType || "-";

              let dateStr;
              try {
                dateStr = tx.date
                  ? new Date(tx.date).toLocaleDateString()
                  : "-";
              } catch {
                dateStr = tx.date || "-";
              }

              const isSelected = selectedTransactionIds.includes(tx.id);

              return (
                <tr key={tx.id || idx}>
                  {bulkDeleteMode && (
                    <td>
                      <input
                        type="checkbox"
                        checked={Boolean(isSelected)}
                        disabled={!tx.id}
                        onChange={() => toggleTransactionSelection(tx.id)}
                        aria-label={`Tranzakció kijelölése: ${tx.description || tx.id || idx}`}
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
