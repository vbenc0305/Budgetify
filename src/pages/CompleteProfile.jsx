import React, { useState, useEffect } from "react";
import { useUser } from "../stores/useUser";
import { useNavigate } from "react-router-dom";
import "./styles/CompleteProfile.css";
import {
  normalizeAgeInput,
  toAgePayloadValue,
  validateAge,
} from "../utils/profileValidation";

const REQUIRED_FIELDS = [
  "age",
  "country",
  "education",
  "gender",
  "housing_status",
  "marital_status",
  "occupation",
];

export default function CompleteProfile() {
  const navigate = useNavigate();
  const user = useUser((s) => s.user);
  const usrInfo = useUser((s) => s.usrInfo);
  const loading = useUser((s) => s.loading);
  const error = useUser((s) => s.error);
  const success = useUser((s) => s.success);
  const updateProfile = useUser((s) => s.updateProfile);

  const [form, setForm] = useState({});
  const [missingFields, setMissingFields] = useState(REQUIRED_FIELDS);
  const [countryOptions, setCountryOptions] = useState([]);
  const [showConsentHelp, setShowConsentHelp] = useState(false);
  const [ageError, setAgeError] = useState("");
  const hasStoredConsent = typeof usrInfo?.analytics_consent === "boolean";

  // Betöltjük a formot a store-ból
  useEffect(() => {
    if (!usrInfo) {
      setForm({});
      setMissingFields(REQUIRED_FIELDS);
      return;
    }

    const initialForm = {};
    REQUIRED_FIELDS.forEach((f) => {
      initialForm[f] = usrInfo[f] ?? "";
    });
    initialForm.analytics_consent = Boolean(usrInfo.analytics_consent);
    setForm(initialForm);

    const missing = REQUIRED_FIELDS.filter(
        (f) => !usrInfo[f] || usrInfo[f] === ""
    );
    setMissingFields(missing);

    if (missing.length === 0 && hasStoredConsent) {
      navigate("/");
    }
  }, [usrInfo, navigate, hasStoredConsent]);

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
    const { name, value, type, checked } = e.target;
    const nextValue =
      name === "age" ? normalizeAgeInput(value) : type === "checkbox" ? checked : value;

    setForm((prev) => ({
      ...prev,
      [name]: nextValue,
    }));

    if (name === "age") {
      if (!nextValue) {
        setAgeError("");
        return;
      }
      setAgeError(validateAge(nextValue));
    }
  };

  const handleAgeBlur = () => {
    setAgeError(validateAge(form.age));
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

    if (missingFields.includes("age")) {
      const nextAgeError = validateAge(form.age);
      setAgeError(nextAgeError);
      if (nextAgeError) return;
    }

    // Csak a hiányzó és kitöltött mezőket mentjük el
    missingFields.forEach((f) => {
      if (form[f] && form[f] !== "") {
        if (f === "age") {
          const ageValue = toAgePayloadValue(form[f]);
          if (ageValue === null) return;
          updateData[f] = ageValue;
        } else {
          updateData[f] = form[f];
        }
        hasUpdates = true;
      }
    });

    if (!hasStoredConsent) {
      updateData.analytics_consent = Boolean(form.analytics_consent);
      hasUpdates = true;
    }

    if (!hasUpdates) return;

    try {
      const updatedUsr = await updateProfile(updateData);

      const newMissing = REQUIRED_FIELDS.filter(
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
                    type="text"
                    name="age"
                    value={form.age ?? ""}
                    onChange={handleChange}
                    onBlur={handleAgeBlur}
                    required
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={3}
                    placeholder="pl. 27"
                    aria-invalid={Boolean(ageError)}
                    aria-describedby={ageError ? "age-error" : undefined}
                />
                {ageError && (
                    <span id="age-error" className="complete-profile-field-error" role="alert">
                      {ageError}
                    </span>
                )}
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

          {!hasStoredConsent && (
              <fieldset className="consent-block">
                <legend>Anonim statisztika</legend>

                <label className="consent-checkbox-row" htmlFor="analytics_consent">
                  <input
                      id="analytics_consent"
                      type="checkbox"
                      name="analytics_consent"
                      checked={Boolean(form.analytics_consent)}
                      onChange={handleChange}
                      aria-describedby="consent-helper-text"
                  />
                  <span>
                    Engedélyezem, hogy a kiadási adataimból anonim statisztika készüljön.
                  </span>
                </label>

                <p id="consent-helper-text" className="consent-helper-text">
                  Ez segít a szolgáltatás fejlesztésében, és később bármikor visszavonható.
                </p>

                <button
                    type="button"
                    className="consent-help-toggle"
                    onClick={() => setShowConsentHelp((prev) => !prev)}
                    aria-expanded={showConsentHelp}
                    aria-controls="consent-extra-info"
                >
                  Miért kérjük ezt?
                </button>

                {showConsentHelp && (
                    <p id="consent-extra-info" className="consent-extra-info" role="status">
                      A hozzájárulás csak összesített, anonim trendekhez használható,
                      személyes azonosítás nélkül.
                    </p>
                )}
              </fieldset>
          )}

          <button type="submit" disabled={loading}>
            {loading ? "Mentés..." : "Mentés"}
          </button>
        </form>
      </div>
  );
}