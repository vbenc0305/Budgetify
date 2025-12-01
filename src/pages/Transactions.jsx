// src/components/Transactions.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useTransaction } from "../stores/useTransaction";
import { useUser } from "../stores/useUser";
import "./styles/Transactions.css";
import MassImportModal from "../components/Modals/MassImportModal.jsx";

export default function Transactions() {
  const { user, authChecked } = useUser();
  const [showImportModal, setShowImportModal] = useState(false);

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

  // Alkalmaz gomb logika: csak ha változott, akkor állítjuk be az aktív szűrőt
  const applyFilter = () => {
    setTypeFilter(pendingFilter);
  };

  // Gyors reset (visszaállítja a pending-et és az aktívot is)
  const clearFilter = () => {
    setPendingFilter("all");
    setTypeFilter("all");
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

          <div className="resultCount" aria-live="polite">
            Találatok: <strong>{filtered.length}</strong>
          </div>
        </div>

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

              return (
                <tr key={tx.id || idx}>
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
