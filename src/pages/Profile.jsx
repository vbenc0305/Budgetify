import React, { useState } from "react";
import { useUser } from "../stores/useUser";
import "../pages/styles/Profile.css";

export default function ProfilePage() {
    const usrInfo = useUser((state) => state.usrInfo);
    const loading = useUser((state) => state.loading);
    const [activeTab, setActiveTab] = useState("basic");

    if (loading) {
        return <div className="profile-container"><h2>Betöltés...</h2></div>;
    }
    if (!usrInfo) {
        return <div className="profile-container"><h2>Nincs profil adat.</h2></div>;
    }

    return (
        <div className="profile-container">
            <h1>Profilom</h1>
            <div className="profile-card">
                {/* Tab menü */}
                <div className="profile-tabs">
                    <button
                        className={`tab-button ${activeTab === "basic" ? "active" : ""}`}
                        onClick={() => setActiveTab("basic")}
                    >
                        Alap adatok
                    </button>
                    <button
                        className={`tab-button ${activeTab === "extra" ? "active" : ""}`}
                        onClick={() => setActiveTab("extra")}
                    >
                        Bővebb adatok
                    </button>
                </div>

                {/* Tab tartalom */}
                {activeTab === "basic" && (
                    <div className="profile-tab-content">
                        <div className="profile-row">
                            <span className="profile-label">Név:</span>
                            <span className="profile-value">{usrInfo.name || "-"}</span>
                        </div>
                        <div className="profile-row">
                            <span className="profile-label">Email:</span>
                            <span className="profile-value">{usrInfo.email || "-"}</span>
                        </div>
                        <div className="profile-row">
                            <span className="profile-label">Nem:</span>
                            <span className="profile-value">{usrInfo.gender || "-"}</span>
                        </div>
                        <div className="profile-row">
                            <span className="profile-label">Ország:</span>
                            <span className="profile-value">{usrInfo.country || "-"}</span>
                        </div>
                        <div className="profile-row">
                            <span className="profile-label">Születési dátum:</span>
                            <span className="profile-value">{usrInfo.birthdate || "-"}</span>
                        </div>
                    </div>
                )}

                {activeTab === "extra" && (
                    <div className="profile-tab-content">
                        <div className="profile-row">
                            <span className="profile-label">Életkor:</span>
                            <span className="profile-value">{usrInfo.age || "-"}</span>
                        </div>
                        <div className="profile-row">
                            <span className="profile-label">Iskolai végzettség:</span>
                            <span className="profile-value">{usrInfo.education || "-"}</span>
                        </div>
                        <div className="profile-row">
                            <span className="profile-label">Lakhatás:</span>
                            <span className="profile-value">{usrInfo.housing_status || "-"}</span>
                        </div>
                        <div className="profile-row">
                            <span className="profile-label">Családi állapot:</span>
                            <span className="profile-value">{usrInfo.marital_status || "-"}</span>
                        </div>
                        <div className="profile-row">
                            <span className="profile-label">Foglalkozás:</span>
                            <span className="profile-value">{usrInfo.occupation || "-"}</span>
                        </div>
                        <div className="profile-row">
                            <span className="profile-label">Telefonszám:</span>
                            <span className="profile-value">{usrInfo.phone || "-"}</span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
