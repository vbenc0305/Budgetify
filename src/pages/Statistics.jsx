import React, { useState, useEffect } from "react";
import { getAuth } from "firebase/auth";
import BasicStats from "../components/BasicStatsComponent.jsx";
import MiniForecast from "../components/MiniForeCastCardComponent.jsx";
import Insights from "../components/Insights";

export default function Statistics({ userId }) {
  const [activeTab, setActiveTab] = useState("basic");

  // Shared prediction data — fetched once, passed to all tabs
  const [predData, setPredData] = useState(null);
  const [predLoading, setPredLoading] = useState(true);
  const [predError, setPredError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      const auth = getAuth();
      const user = auth.currentUser;
      if (!user && !userId) {
        if (isMounted) { setPredError("Nincs bejelentkezett felhasználó"); setPredLoading(false); }
        return;
      }
      try {
        let token = await user.getIdToken();
        let res = await fetch("/api/predict/transactions", {
          method: "GET",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        });
        if (res.status === 401) {
          token = await user.getIdToken(true);
          res = await fetch("/api/predict/transactions", {
            method: "GET",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          });
        }
        if (!res.ok) {
          const txt = await res.text();
          if (isMounted) setPredError(`${res.status} ${res.statusText}: ${txt}`);
          return;
        }
        const data = await res.json();
        if (isMounted) setPredData(data);
      } catch (err) {
        if (isMounted) setPredError(err.message || String(err));
      } finally {
        if (isMounted) setPredLoading(false);
      }
    };
    load();
    return () => { isMounted = false; };
  }, [userId]);

  const renderTab = () => {
    switch (activeTab) {
      case "basic":
        return <BasicStats predData={predData} predLoading={predLoading} predError={predError} />;
      case "forecast":
        return <MiniForecast predData={predData} predLoading={predLoading} predError={predError} />;
      case "insights":
        return <Insights userId={userId} predData={predData} predLoading={predLoading} predError={predError} />;
      default:
        return <BasicStats predData={predData} predLoading={predLoading} predError={predError} />;
    }
  };

  return (
    <div className="statistics-container">
      <header className="statistics-header">
        <h1 className="statistics-title">Felhasználói Statisztikák</h1>
        <p className="statistics-subtitle">
          Áttekintés a tranzakciókról és előrejelzések a felhasználóhoz
        </p>

        <div className="tabs">
          <button
            className={activeTab === "basic" ? "tab active" : "tab"}
            onClick={() => setActiveTab("basic")}
          >
            Alap statisztika
          </button>
          <button
            className={activeTab === "forecast" ? "tab active" : "tab"}
            onClick={() => setActiveTab("forecast")}
          >
            Előrejelzés
          </button>
          <button
            className={activeTab === "insights" ? "tab active" : "tab"}
            onClick={() => setActiveTab("insights")}
          >
            Insights
          </button>
        </div>
      </header>

      <main className="tab-content">{renderTab()}</main>
    </div>
  );
}
