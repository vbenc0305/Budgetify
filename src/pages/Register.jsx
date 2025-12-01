// src/pages/Register.jsx
import React, { useState } from "react";
import { setDoc, doc } from "firebase/firestore";
import { auth, db } from "../firebase";
import { createUserWithEmailAndPassword } from "firebase/auth";
import dayjs from "dayjs";
import { useNavigate } from "react-router-dom";
import "./styles/Register.css";
import { getFirebaseErrorMessage } from "../utils/firebaseErrorHandler";
import { useUser } from "../stores/useUser";

export default function Register() {
    const navigate = useNavigate();

    // Zustand selector: csak a függvényeket és szükséges állapotot kérjük le
    const { setUser, fetchProfile } = useUser();

    const [form, setForm] = useState({
        name: "",
        email: "",
        password: "",
        phone: "",
        birthdate: "",
        // opcionális: age, country, gender, stb.
    });
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    };

    const handleRegister = async (e) => {
        e.preventDefault();
        setError("");
        setSuccess("");
        setLoading(true);

        try {
            // 1) Firebase Auth - user létrehozása
            const userCredential = await createUserWithEmailAndPassword(
                auth,
                form.email,
                form.password
            );
            const firebaseUser = userCredential.user;

            // 2) Alap user dokumentum a 'users' kollekcióban
            const userData = {
                name: form.name || "",
                email: form.email || "",
                phone: form.phone || "",
                birthdate: form.birthdate || "",
                role: "user",
                last_login: dayjs().format("YYYY-MM-DD HH:mm:ss"),
                uid: firebaseUser.uid,
            };

            await setDoc(doc(db, "users", firebaseUser.uid), userData);

            // 3) usr_info dokumentum létrehozása (ha szükséges mezők vannak)
            const usrInfoData = {
                user_id: firebaseUser.uid,
                age: form.age ?? null,
                country: form.country ?? "",
                education: form.education ?? "",
                gender: form.gender ?? "",
                housing_status: form.housing_status ?? "",
                marital_status: form.marital_status ?? "",
                occupation: form.occupation ?? "",
            };

            // csak ha van bármilyen értelmes mező, különben létrehozhatunk üres dokumentumot is – döntésed szerint
            await setDoc(doc(db, "usr_info", firebaseUser.uid), usrInfoData);

            // 4) Frissítjük a Zustand store-t: setUser + fetchProfile (ez a store-on belül cached)
            if (typeof setUser === "function") {
                setUser(firebaseUser);
            }

            // fetchProfile belső fetched-check-el védett, így nem kér le kétszer semmit
            if (typeof fetchProfile === "function") {
                try {
                    await fetchProfile();
                } catch (fetchErr) {
                    // Ha a profil-fetch elbukik, továbbra is engedjük a regisztrációt;
                    // a store.error már jelezni fogja a problémát.
                    console.error("Profil lekérése regisztráció után sikertelen:", fetchErr);
                }
            }

            setSuccess("🎉 Sikeres regisztráció! Átirányítunk a kezdőlapra...");
            // kis delay, hogy a user lássa a success üzenetet (opcionális)
            setTimeout(() => navigate("/"), 800);
        } catch (err) {
            console.error("Registration error:", err);
            const friendlyMessage = getFirebaseErrorMessage(err?.code);
            setError(friendlyMessage || "Hiba történt a regisztráció során.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="register-container">
            <form onSubmit={handleRegister} className="register-form" aria-live="polite">
                <h2>Fiók létrehozása</h2>

                <input
                    name="name"
                    placeholder="Név"
                    onChange={handleChange}
                    value={form.name}
                    required
                    autoComplete="name"
                />
                <input
                    type="email"
                    name="email"
                    placeholder="Email"
                    onChange={handleChange}
                    value={form.email}
                    required
                    autoComplete="email"
                />
                <input
                    type="password"
                    name="password"
                    placeholder="Jelszó"
                    onChange={handleChange}
                    value={form.password}
                    required
                    autoComplete="new-password"
                />
                <input
                    name="phone"
                    placeholder="Telefonszám"
                    onChange={handleChange}
                    value={form.phone}
                    autoComplete="tel"
                />
                <input
                    type="date"
                    name="birthdate"
                    onChange={handleChange}
                    value={form.birthdate}
                />

                {/* optional: további mezők, ha szeretnéd regisztrációkor bekérni */}
                {/* <input type="number" name="age" placeholder="Életkor" onChange={handleChange} /> */}

                <button type="submit" disabled={loading}>
                    {loading ? "Regisztráció folyamatban..." : "Regisztráció"}
                </button>

                {error && (
                    <p className="error-text" role="alert">
                        {error}
                    </p>
                )}
                {success && <p className="success-text">{success}</p>}
            </form>
        </div>
    );
}
