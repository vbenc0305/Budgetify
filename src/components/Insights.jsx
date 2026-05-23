// Insights.jsx
import React, { useState, Suspense } from "react";
import MiniForecastCard from "./MiniForeCastCardComponent.jsx";
import BasicStats from "./BasicStatsComponent.jsx";

export default function Insights({ predData, predLoading, predError }) {
  const tabs = [
    { id: "basic", label: "Alap statisztika" },
    { id: "quarter", label: "Negyedéves bontás" },
    { id: "category", label: "Kategória-elemzés" },
    { id: "timeseries", label: "Idősor" },
    { id: "forecast", label: "Előrejelzés (mini)" },
  ];

  const [active, setActive] = useState("basic");

  return (
    <div className="prediction-container">
      <header className="prediction-header">
        <div>
          <h1 className="prediction-title">Statisztika & Insights</h1>
          <p className="prediction-subtitle">
            A felhasználó tranzakcióiból számított kimutatások — kattints a
            fülekre.
          </p>
        </div>
      </header>

      <nav
        className="insights-tabs"
        style={{ marginTop: 12, marginBottom: 12 }}
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActive(t.id)}
            className={`tab-btn ${active === t.id ? "tab-active" : ""}`}
            style={{
              marginRight: 8,
              padding: "8px 12px",
              borderRadius: 6,
              border: "1px solid #e5e7eb",
              background: active === t.id ? "#0ea5e9" : "#fff",
              color: active === t.id ? "#fff" : "#111827",
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        <Suspense fallback={<div>Betöltés…</div>}>
          {active === "basic" && <BasicStats predData={predData} predLoading={predLoading} predError={predError} />}
          {active === "quarter" && (
            <div className="chart-card">
              <div style={{ padding: 20 }}>
                <strong>Negyedéves bontás</strong>
                <p className="muted">(Placeholder — implementálható később)</p>
              </div>
            </div>
          )}
          {active === "category" && (
            <div className="chart-card">
              <div style={{ padding: 20 }}>
                <strong>Kategória-elemzés</strong>
                <p className="muted">
                  (Placeholder — kategória breakdown és donut chart javasolt)
                </p>
              </div>
            </div>
          )}
          {active === "timeseries" && (
            <div className="chart-card">
              <div style={{ padding: 20 }}>
                <strong>Idősor</strong>
                <p className="muted">
                  (Placeholder — itt lehet multi-year line chart, rolling avg
                  stb.)
                </p>
              </div>
            </div>
          )}
          {active === "forecast" && <MiniForecastCard predData={predData} predLoading={predLoading} predError={predError} />}
        </Suspense>
      </main>
    </div>
  );
}
