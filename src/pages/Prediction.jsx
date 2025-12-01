// Prediction.jsx
import React, { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  Area,
  Brush,
} from "recharts";
import { getAuth } from "firebase/auth";

import "./styles/Prediction.css";

export default function Prediction() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [forecast, setForecast] = useState([]);
  const [ci, setCi] = useState(null);
  const [metrics, setMetrics] = useState({});

  const [showCI, setShowCI] = useState(true);
  const [smoothingWindow, setSmoothingWindow] = useState(0);

  useEffect(() => {
    let isMounted = true;

    const fetchPredictions = async () => {
      const auth = getAuth();
      const user = auth.currentUser;

      if (!user) {
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
        setForecast(Array.isArray(data.forecast) ? data.forecast : []);

        if (Array.isArray(data.ci)) {
          setCi(
            data.ci.map((c) => ({
              date: c.date,
              lower: Number(c.lower ?? c.lo ?? c["lower"] ?? 0),
              upper: Number(c.upper ?? c.hi ?? c["upper"] ?? 0),
            })),
          );
        } else if (data.ci && data.ci.lower && data.ci.upper) {
          const lowerArr = Array.isArray(data.ci.lower) ? data.ci.lower : [];
          const upperArr = Array.isArray(data.ci.upper) ? data.ci.upper : [];
          const mapUpper = new Map(
            upperArr.map((u) => [u.date, Number(u.value)]),
          );
          setCi(
            lowerArr.map((l) => ({
              date: l.date,
              lower: Number(l.value),
              upper: mapUpper.get(l.date) ?? Number(l.value),
            })),
          );
        } else {
          setCi(null);
        }

        setMetrics(data.metrics ?? {});
      } catch (err) {
        if (!isMounted) return;
        setError(err.message || String(err));
      } finally {
        if (!isMounted) return;
        setLoading(false);
      }
    };

    fetchPredictions();

    return () => {
      isMounted = false;
    };
  }, []);

  const merged = useMemo(() => {
    const map = new Map();

    const pushPoint = (p, key) => {
      const d = p.date;
      const existing = map.get(d) || { date: d };
      existing[key] = Number(p.value ?? p["value"] ?? 0);
      map.set(d, existing);
    };

    history.forEach((h) => pushPoint(h, "historyValue"));
    forecast.forEach((f) => pushPoint(f, "forecastValue"));

    if (ci) {
      ci.forEach((c) => {
        const existing = map.get(c.date) || { date: c.date };
        existing.ciLower = Number(c.lower ?? 0);
        existing.ciUpper = Number(c.upper ?? 0);
        map.set(c.date, existing);
      });
    }

    const arr = Array.from(map.values()).sort((a, b) =>
      a.date > b.date ? 1 : -1,
    );

    if (smoothingWindow > 1) {
      const smooth = (key) => {
        const out = [...arr];
        for (let i = 0; i < arr.length; i++) {
          const from = Math.max(0, i - Math.floor(smoothingWindow / 2));
          const to = Math.min(
            arr.length - 1,
            i + Math.floor(smoothingWindow / 2),
          );
          let sum = 0;
          let cnt = 0;
          for (let j = from; j <= to; j++) {
            if (typeof arr[j][key] === "number") {
              sum += arr[j][key];
              cnt++;
            }
          }
          out[i] = { ...out[i], [key]: cnt ? sum / cnt : out[i][key] };
        }
        return out;
      };

      const withHistory = smooth("historyValue");
      const withBoth = smooth("forecastValue");
      return withHistory.map((r, idx) => ({
        ...r,
        forecastValue: withBoth[idx]?.forecastValue,
        ciLower: r.ciLower,
        ciUpper: r.ciUpper,
      }));
    }

    return arr;
  }, [history, forecast, ci, smoothingWindow]);

  const downloadCSV = () => {
    const header =
      ["date", "historyValue", "forecastValue", "ciLower", "ciUpper"].join(
        ",",
      ) + "\n";
    const rows = merged
      .map((r) =>
        [
          r.date,
          r.historyValue ?? "",
          r.forecastValue ?? "",
          r.ciLower ?? "",
          r.ciUpper ?? "",
        ].join(","),
      )
      .join("\n");
    const csv = header + rows;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `prediction_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="prediction-container">
      <header className="prediction-header">
        <div>
          <h1 className="prediction-title">Előrejelzés — jövőbeli kiadások</h1>
          <p className="prediction-subtitle">
            Vizualizáció az API alapján. Interaktív, reszponzív.
          </p>
        </div>

        <div className="controls">
          <button
            onClick={() => setShowCI((s) => !s)}
            className="control-btn"
            title="Confidence interval megjelenítése/elrejtése"
          >
            {showCI ? "CI: on" : "CI: off"}
          </button>

          <select
            value={smoothingWindow}
            onChange={(e) => setSmoothingWindow(Number(e.target.value))}
            className="control-select"
            title="Smoothing (ma)"
          >
            <option value={0}>Sima</option>
            <option value={3}>MA 3</option>
            <option value={7}>MA 7</option>
          </select>

          <button onClick={downloadCSV} className="control-btn">
            Export CSV
          </button>
        </div>
      </header>

      <main>
        <section className="cards-section">
          <div className="card-grid">
            <div className="card">
              <div className="card-label">Status</div>
              <div className="card-value">
                {loading ? "loading..." : "ready"}
              </div>
            </div>

            <div className="card">
              <div className="card-label">Forrás</div>
              <div className="card-value">{loading ? "—" : "API"}</div>
            </div>

            <div className="card">
              <div className="card-label">Metrikák</div>
              <div className="card-value small">
                {Object.keys(metrics).length ? (
                  Object.entries(metrics)
                    .slice(0, 3)
                    .map(([k, v]) => (
                      <div key={k} className="metric-row">
                        {k}: {Number(v).toFixed(3)}
                      </div>
                    ))
                ) : (
                  <div className="muted">—</div>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card-label">Dátumok</div>
              <div className="card-value small">
                {merged.length
                  ? `${merged[0].date} → ${merged[merged.length - 1].date}`
                  : "—"}
              </div>
            </div>
          </div>
        </section>

        {error && <div className="error-box">Hiba: {error}</div>}

        {loading ? (
          <div className="loading-skeleton" />
        ) : (
          <div className="chart-card">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={merged}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" minTickGap={10} />
                <YAxis />
                <Tooltip
                  formatter={(value, name) => [
                    value,
                    name === "historyValue"
                      ? "Történet"
                      : name === "forecastValue"
                        ? "Előrejelzés"
                        : name,
                  ]}
                />
                <Legend />

                {showCI &&
                  merged.some(
                    (r) =>
                      typeof r.ciLower === "number" &&
                      typeof r.ciUpper === "number",
                  ) && (
                    <Area
                      type="monotone"
                      dataKey="ciUpper"
                      stroke="transparent"
                      fillOpacity={0.12}
                      fill="url(#ciGradient)"
                      activeDot={false}
                    />
                  )}

                <defs>
                  <linearGradient id="ciGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopOpacity={0.18} />
                    <stop offset="100%" stopOpacity={0.02} />
                  </linearGradient>
                </defs>

                <Line
                  type="monotone"
                  dataKey="historyValue"
                  name="Történet"
                  stroke="#1f2937"
                  dot={false}
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="forecastValue"
                  name="Előrejelzés"
                  stroke="#e11d48"
                  dot={false}
                  strokeDasharray="5 5"
                  strokeWidth={2}
                />

                <Brush dataKey="date" height={30} stroke="#8884d8" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </main>
    </div>
  );
}
