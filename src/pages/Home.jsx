// src/components/Home.jsx
import React from "react";
import { useUser } from "../stores/useUser";
import CompleteProfile from "./CompleteProfile";
import NoUserHomePage from "./NoUserHomePage";


export default function Home() {
    // Zustand state: külön hívások, így nincs új objektum probléma
    const user = useUser((s) => s.user);
    const usrInfo = useUser((s) => s.usrInfo);
    const loading = useUser((s) => s.loading);
    const error = useUser((s) => s.error);

    // Ellenőrizzük, hogy hiányzik-e valami a profilból
    const requiredFields = [
        "age",
        "country",
        "education",
        "gender",
        "housing_status",
        "marital_status",
        "occupation",
    ];

    const needsProfile = usrInfo
        ? requiredFields.some((field) => !usrInfo[field])
        : true;

    if (loading) {
        return <p>Betöltés folyamatban...</p>;
    }

    if (error) {
        return <p>Hiba történt: {error}</p>;
    }

    if (!user) {
        return <NoUserHomePage />;
    }

    if (needsProfile) {
        return <CompleteProfile />;
    }

    return (
        <div className="home-root">
            <h1 className="home-title">
                Üdv a Budgetify-ban, {usrInfo?.name || usrInfo?.email || "Felhasználó"}!
            </h1>
            <p className="home-paragraph">Itt ténylegesen megjelenik a Home tartalom.</p>
        </div>
    );
}
