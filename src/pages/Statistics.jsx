import React, { useState } from "react";
import BasicStats from "../components/BasicStatsComponent.jsx";
import MiniForecast from "../components/MiniForeCastCardComponent.jsx";
import Insights from "../components/Insights";
import "./styles/Statistics.css";

export default function Statistics() {
  const [activeTab, setActiveTab] = useState("basic");

  const renderTab = () => {
    switch (activeTab) {
      case "basic":
        return <BasicStats />;
      case "forecast":
        return <MiniForecast />;
      case "insights":
        return <Insights />;
      default:
        return <BasicStats />;
    }
  };

  return (
    <div className="statistics-container">
      <header className="statistics-header">
        <h1>Felhasználói Statisztikák 📊</h1>
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
