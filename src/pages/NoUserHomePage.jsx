import React from "react";
import { NavLink } from "react-router-dom";
import "./styles/NoUserHomePage.css";

export default function NoUserHomePage() {
  const projectHighlights = [
    "Kiadások és bevételek átlátható követése egy helyen",
    "OTP exportból történő gyors tranzakcióimport",
    "Predikciók, statisztikák és megyei betekintések",
  ];

  const loginBenefits = [
    "Saját profil és személyre szabott pénzügyi nézetek",
    "Tranzakciók mentése, importálása és szűrése",
    "Megyei és kategóriaalapú analitikák elérése",
    "Predikciós és statisztikai funkciók használata",
  ];

  return (
    <section className="no-user-home-container">
      <div className="no-user-hero">
        <span className="no-user-badge">Személyes pénzügyek egyszerűbben</span>
        <h1>Üdvözöl a Budgetify!</h1>
        <p className="no-user-lead">
          A Budgetify egy modern pénzügyi menedzsment alkalmazás, amely segít
          átlátni a költéseidet, felismerni a pénzügyi szokásaidat, és jobb
          döntéseket hozni a mindennapi költségvetésedben.
        </p>

        <div className="no-user-home-cta">
          <NavLink to="/register" className="button-primary">
            Regisztráció
          </NavLink>
          <NavLink to="/login" className="button-ghost">
            Bejelentkezés
          </NavLink>
        </div>
      </div>

      <div className="no-user-content-grid">
        <article className="no-user-card">
          <h2>Miről szól a projekt?</h2>
          <p>
            A célja, hogy ne csak listázza a tranzakcióidat, hanem értelmezhető
            képet is adjon a pénzügyeidről. A rendszer támogatja a tranzakciók
            kezelését, az elemzéseket és a vizuális betekintéseket is.
          </p>

          <ul className="no-user-list">
            {projectHighlights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="no-user-card">
          <h2>Miért jobb bejelentkezve?</h2>
          <p>
            Bejelentkezés után a Budgetify személyes munkafelületté válik: a
            saját adataid, tranzakcióid és elemzéseid alapján működik.
          </p>

          <ul className="no-user-list">
            {loginBenefits.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  );
}
