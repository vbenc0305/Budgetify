import React, { useState } from "react";
import BasicStats from "../components/BasicStatsComponent.jsx";
import MiniForecast from "../components/MiniForeCastCardComponent.jsx";
import Insights from "../components/Insights";

export default function Statistics({ userId }) {
  const [activeTab, setActiveTab] = useState("basic");

  const renderTab = () => {
    switch (activeTab) {
      case "basic":
        return <BasicStats userId={userId} />;
      case "forecast":
        return <MiniForecast userId={userId} />;
      case "insights":
        return <Insights userId={userId} />;
      default:
        return <BasicStats userId={userId} />;
    }
  };

  return (
    <div className="statistics-container">
      <header className="statistics-header">
        <h1 className="statistics-title">Felhasználói Statisztikák 📊</h1>
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
