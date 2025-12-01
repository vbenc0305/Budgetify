import React, { useState, useEffect } from "react";
import { useUser } from "../stores/useUser";
import { useNavigate } from "react-router-dom";
import "./styles/CompleteProfile.css";

export default function CompleteProfile() {
  const navigate = useNavigate();
  const user = useUser((s) => s.user);
  const usrInfo = useUser((s) => s.usrInfo);
  const loading = useUser((s) => s.loading);
  const error = useUser((s) => s.error);
  const success = useUser((s) => s.success);
  const updateProfile = useUser((s) => s.updateProfile);

  const requiredFields = [
    "age",
    "country",
    "education",
    "gender",
    "housing_status",
    "marital_status",
    "occupation",
  ];

  const [form, setForm] = useState({});
  const [missingFields, setMissingFields] = useState(requiredFields);
  const [countryOptions, setCountryOptions] = useState([]);

  // Betöltjük a formot a store-ból
  useEffect(() => {
    if (!usrInfo) {
      setForm({});
      setMissingFields(requiredFields);
      return;
    }

    const initialForm = {};
    requiredFields.forEach((f) => {
      initialForm[f] = usrInfo[f] ?? "";
    });
    setForm(initialForm);

    const missing = requiredFields.filter(
        (f) => !usrInfo[f] || usrInfo[f] === ""
    );
    setMissingFields(missing);

    if (missing.length === 0) {
      navigate("/");
    }
  }, [usrInfo, navigate]);

  // Országlista betöltése
  useEffect(() => {
    let mounted = true;

    async function fetchCountries() {
      try {
        const res = await fetch(
            "https://restcountries.com/v3.1/all?fields=translations,name"
        );
        if (!res.ok) throw new Error("Hiba az országlista lekérésekor");
        const data = await res.json();
        const options = data
            // Lekérés, magyar fordítás preferálása
            .map((c) => c.translations?.hun?.common ?? c.name.common)
            // 💡 JAVÍTÁS 1: Kiszűrjük azokat az elemeket, amelyek nem stringek.
            .filter(name => typeof name === 'string')
            // Duplikátumok eltávolítása (a filter megvédi ezt a lépést a nem-stringektől)
            .filter((v, i, a) => a.indexOf(v) === i)
            // 💡 JAVÍTÁS 2: A sort-ban mindkét elemet stringgé kényszerítjük.
            .sort((a, b) => String(a).localeCompare(String(b), "hu"));

        if (mounted) setCountryOptions(options);
      } catch (err) {
        console.error("Hiba a countryOptions lekérésekor:", err);
        if (mounted)
          setCountryOptions(["Magyarország", "USA", "Németország", "Ausztria"]);
      }
    }

    fetchCountries();
    return () => {
      mounted = false;
    };
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!user || typeof user.getIdToken !== "function") {
      console.error("Még nincs bejelentkezett user vagy hibás user objektum.");
      alert("Kérlek, jelentkezz be, mielőtt mentenéd a profilodat.");
      return;
    }

    const updateData = {};
    let hasUpdates = false;

    // Csak a hiányzó és kitöltött mezőket mentjük el
    missingFields.forEach((f) => {
      if (form[f] && form[f] !== "") {
        updateData[f] = form[f];
        hasUpdates = true;
      }
    });

    if (!hasUpdates) return;

    try {
      const updatedUsr = await updateProfile(updateData);

      const newMissing = requiredFields.filter(
          (f) => !updatedUsr[f] || updatedUsr[f] === ""
      );
      setMissingFields(newMissing);

      if (newMissing.length === 0) {
        navigate("/");
      }
    } catch (err) {
      console.error("Hiba a profil mentésekor:", err);
    }
  };

  if (!user) {
    return <p>Betöltés vagy bejelentkezés folyamatban...</p>;
  }

  return (
      <div className="complete-profile-container">
        <h2>Hiányzó profiladatok kitöltése</h2>

        {/* Hibák és sikerüzenet */}
        {error && (
            <p className="error-text" role="alert">
              {error}
            </p>
        )}
        {success && (
            <p className="success-text" role="status">
              {success}
            </p>
        )}

        <form onSubmit={handleSubmit} className="complete-profile-form">
          {missingFields.includes("age") && (
              <label>
                Életkor:
                <input
                    type="number"
                    name="age"
                    value={form.age}
                    onChange={handleChange}
                    required
                    min={0}
                />
              </label>
          )}

          {missingFields.includes("country") && (
              <label>
                Ország:
                <input
                    type="text"
                    name="country"
                    list="countries"
                    value={form.country}
                    onChange={handleChange}
                    required
                    placeholder="Kezdd el gépelni az ország nevét..."
                />
                <datalist id="countries">
                  {countryOptions.map((country) => (
                      <option key={country} value={country} />
                  ))}
                </datalist>
              </label>
          )}

          {missingFields.includes("education") && (
              <label>
                Végzettség:
                <select
                    name="education"
                    value={form.education}
                    onChange={handleChange}
                    required
                >
                  <option value="">Válassz végzettségi szintet...</option>
                  <option value="Általános 8. osztály">Általános 8. osztály</option>
                  <option value="Szakiskola / Képesítő bizonyítvány">
                    Szakiskola / Képesítő bizonyítvány
                  </option>
                  <option value="Érettségi / Gimnázium">Érettségi / Gimnázium</option>
                  <option value="Érettségi + Szakképesítés">
                    Érettségi + Szakképesítés
                  </option>
                  <option value="Technikumi végzettség">Technikumi végzettség</option>
                  <option value="Felsőfokú szakképzés (FOKSZ)">
                    Felsőfokú szakképzés (FOKSZ)
                  </option>
                  <option value="Főiskolai diploma / BA, BSc">
                    Főiskolai diploma / BA, BSc
                  </option>
                  <option value="Egyetemi diploma / MA, MSc">
                    Egyetemi diploma / MA, MSc
                  </option>
                  <option value="Kétszakos mesterképzés">Kétszakos mesterképzés</option>
                  <option value="Egységes, osztatlan mesterképzés">
                    Egységes, osztatlan mesterképzés
                  </option>
                  <option value="Doktori (Ph.D./DLA) fokozat">
                    Doktori (Ph.D./DLA) fokozat
                  </option>
                  <option value="Habilitáció">Habilitáció</option>
                  <option value="Posztgraduális szakképzés">Posztgraduális szakképzés</option>
                  <option value="Nincs befejezett végzettség">
                    Nincs befejezett végzettség
                  </option>
                  <option value="Ismeretlen / Nem kíván válaszolni">
                    Ismeretlen / Nem kíván válaszolni
                  </option>
                </select>
              </label>
          )}

          {missingFields.includes("gender") && (
              <label>
                Nem:
                <select
                    name="gender"
                    value={form.gender}
                    onChange={handleChange}
                    required
                >
                  <option value="">Válassz…</option>
                  <option value="Férfi">Férfi</option>
                  <option value="Nő">Nő</option>
                  <option value="Egyéb">Egyéb</option>
                </select>
              </label>
          )}

          {missingFields.includes("housing_status") && (
              <label>
                Lakhatási státusz:
                <select
                    name="housing_status"
                    value={form.housing_status}
                    onChange={handleChange}
                    required
                >
                  <option value="">Válassz…</option>
                  <option value="Saját tulajdonú lakás">Saját tulajdonú lakás</option>
                  <option value="Bérlakás">Bérlakás</option>
                  <option value="Albérlet">Albérlet</option>
                  <option value="Önálló ház">Önálló ház</option>
                </select>
              </label>
          )}

          {missingFields.includes("marital_status") && (
              <label>
                Családi állapot:
                <select
                    name="marital_status"
                    value={form.marital_status}
                    onChange={handleChange}
                    required
                >
                  <option value="">Válassz…</option>
                  <option value="Egyedülálló">Egyedülálló</option>
                  <option value="Házas">Házas</option>
                  <option value="Élettársi kapcsolat">Élettársi kapcsolat</option>
                  <option value="Elvált">Elvált</option>
                </select>
              </label>
          )}

          {missingFields.includes("occupation") && (
              <label>
                Foglalkozás:
                <input
                    type="text"
                    name="occupation"
                    value={form.occupation}
                    onChange={handleChange}
                    required
                />
              </label>
          )}

          <button type="submit" disabled={loading}>
            {loading ? "Mentés..." : "Mentés"}
          </button>
        </form>
      </div>
  );
}