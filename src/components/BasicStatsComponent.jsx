// BasicStats.jsx
import React, { useEffect, useMemo, useState } from "react";
import { getAuth } from "firebase/auth";

export default function BasicStats({ userId }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    let isMounted = true;
    const fetchHistory = async () => {
      const auth = getAuth();
      const user = auth.currentUser;

      if (!user && !userId) {
        setError("Nincs bejelentkezett felhasználó");
        setLoading(false);
        return;
      }

      try {
        const token = await user.getIdToken();
        const res = await fetch("/api/predict/transactions", {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) {
          const txt = await res.text();
          throw new Error(`${res.status} ${res.statusText}: ${txt}`);
        }

        const data = await res.json();
        if (!isMounted) return;
        setHistory(Array.isArray(data.history) ? data.history : []);
      } catch (err) {
        if (!isMounted) return;
        setError(err.message || String(err));
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchHistory();
    return () => {
      isMounted = false;
    };
  }, [userId]);

  const stats = useMemo(() => {
    if (!history || !history.length) return null;
    // feltételezem history: [{date: '2025-01', value: 1234}, ...]
    const vals = history
      .map((h) => Number(h.value ?? h.amount ?? 0))
      .filter((v) => !isNaN(v));
    if (!vals.length) return null;

    const sum = vals.reduce((a, b) => a + b, 0);
    const avg = sum / vals.length;
    const sorted = [...vals].sort((a, b) => a - b);
    const min = sorted[0];
    const max = sorted[sorted.length - 1];
    const median =
      sorted.length % 2 === 1
        ? sorted[(sorted.length - 1) / 2]
        : (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2;
    const variance =
      vals.reduce((acc, v) => acc + (v - avg) ** 2, 0) / vals.length;
    const stddev = Math.sqrt(variance);

    // Find months for min/max
    const minIndex = history.findIndex(
      (h) => Number(h.value ?? h.amount ?? 0) === min,
    );
    const maxIndex = history.findIndex(
      (h) => Number(h.value ?? h.amount ?? 0) === max,
    );
    const minMonth = history[minIndex]?.date ?? null;
    const maxMonth = history[maxIndex]?.date ?? null;

    return {
      sum,
      avg,
      min,
      max,
      median,
      stddev,
      minMonth,
      maxMonth,
      points: history.length,
    };
  }, [history]);

  if (loading) return <div className="loading-skeleton" />;
  if (error) return <div className="error-box">Hiba: {error}</div>;
  if (!stats)
    return (
      <div className="chart-card">
        <div style={{ padding: 16 }}>Nincs elérhető történeti adat.</div>
      </div>
    );

  return (
    <section className="cards-section">
      <div className="card-grid">
        <div className="card">
          <div className="card-label">Átlag / hó</div>
          <div className="card-value">
            {Math.round(stats.avg).toLocaleString()} Ft
          </div>
        </div>

        <div className="card">
          <div className="card-label">Legkevesebb</div>
          <div className="card-value small">
            {stats.minMonth
              ? `${stats.minMonth} — ${stats.min.toLocaleString()} Ft`
              : `${stats.min.toLocaleString()} Ft`}
          </div>
        </div>

        <div className="card">
          <div className="card-label">Legtöbb</div>
          <div className="card-value small">
            {stats.maxMonth
              ? `${stats.maxMonth} — ${stats.max.toLocaleString()} Ft`
              : `${stats.max.toLocaleString()} Ft`}
          </div>
        </div>

        <div className="card">
          <div className="card-label">Medián</div>
          <div className="card-value">
            {Math.round(stats.median).toLocaleString()} Ft
          </div>
        </div>

        <div className="card">
          <div className="card-label">Szórás (stddev)</div>
          <div className="card-value">
            {Math.round(stats.stddev).toLocaleString()} Ft
          </div>
        </div>

        <div className="card">
          <div className="card-label">Adatpontok</div>
          <div className="card-value">{stats.points}</div>
        </div>
      </div>
    </section>
  );
}
