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
import {
    normalizePhoneInput,
    sanitizeRegisterForm,
    validateRegisterField,
    validateRegisterForm,
} from "../utils/registerValidation";

const REQUIRED_FIELDS = ["name", "email", "password", "confirmPassword", "phone", "birthdate"];

const PASSWORD_STRENGTH_TEXT = {
    empty: "",
    weak: "Jelszóerősség: gyenge",
    medium: "Jelszóerősség: közepes",
    strong: "Jelszóerősség: erős",
};

const INITIAL_FORM_STATE = {
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    phone: "",
    birthdate: "",
};

export default function Register() {
    const navigate = useNavigate();

    const { setUser, fetchProfile } = useUser();

    const [form, setForm] = useState(INITIAL_FORM_STATE);
    const [touched, setTouched] = useState({});
    const [submitAttempted, setSubmitAttempted] = useState(false);
    const [fieldErrors, setFieldErrors] = useState({});
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [loading, setLoading] = useState(false);

    const validation = validateRegisterForm(form);
    const passwordStrengthText = PASSWORD_STRENGTH_TEXT[validation.passwordStrength] || "";

    const visibleFieldErrors = REQUIRED_FIELDS.reduce((acc, field) => {
        if ((submitAttempted || touched[field]) && fieldErrors[field]) {
            acc[field] = fieldErrors[field];
        }
        return acc;
    }, {});

    const handleChange = (e) => {
        const { name, value } = e.target;
        const nextValue = name === "phone" ? normalizePhoneInput(value) : value;
        const nextForm = { ...form, [name]: nextValue };

        setForm(nextForm);

        if (submitAttempted || touched[name] || (name === "password" && touched.confirmPassword)) {
            const nextValidation = validateRegisterForm(nextForm);
            setFieldErrors(nextValidation.errors);
        }
    };

    const handlePhoneFocus = () => {
        if (!form.phone) {
            setForm((prev) => ({ ...prev, phone: "+" }));
        }
    };

    const handleBlur = (e) => {
        const { name } = e.target;
        const nextTouched = { ...touched, [name]: true };
        setTouched(nextTouched);

        const nextErrors = { ...fieldErrors, [name]: validateRegisterField(name, form) };
        if (name === "password" && (nextTouched.confirmPassword || form.confirmPassword)) {
            nextErrors.confirmPassword = validateRegisterField("confirmPassword", form);
        }
        setFieldErrors(nextErrors);
    };

    const handleRegister = async (e) => {
        e.preventDefault();
        setError("");
        setSuccess("");

        const sanitizedForm = sanitizeRegisterForm(form);
        setForm(sanitizedForm);

        const currentValidation = validateRegisterForm(sanitizedForm);
        setFieldErrors(currentValidation.errors);
        setSubmitAttempted(true);
        setTouched(
            REQUIRED_FIELDS.reduce((acc, field) => {
                acc[field] = true;
                return acc;
            }, {}),
        );

        if (!currentValidation.isValid) {
            return;
        }

        setLoading(true);

        try {
            const userCredential = await createUserWithEmailAndPassword(
                auth,
                sanitizedForm.email,
                sanitizedForm.password
            );
            const firebaseUser = userCredential.user;

            const userData = {
                name: sanitizedForm.name || "",
                email: sanitizedForm.email || "",
                phone: sanitizedForm.phone || "",
                birthdate: sanitizedForm.birthdate || "",
                role: "user",
                last_login: dayjs().format("YYYY-MM-DD HH:mm:ss"),
                uid: firebaseUser.uid,
            };

            await setDoc(doc(db, "users", firebaseUser.uid), userData);

            const usrInfoData = {
                user_id: firebaseUser.uid,
                age: sanitizedForm.age ?? null,
                country: sanitizedForm.country ?? "",
                education: sanitizedForm.education ?? "",
                gender: sanitizedForm.gender ?? "",
                housing_status: sanitizedForm.housing_status ?? "",
                marital_status: sanitizedForm.marital_status ?? "",
                occupation: sanitizedForm.occupation ?? "",
            };

            await setDoc(doc(db, "usr_info", firebaseUser.uid), usrInfoData);

            if (typeof setUser === "function") {
                setUser(firebaseUser);
            }

            if (typeof fetchProfile === "function") {
                try {
                    await fetchProfile();
                } catch (fetchErr) {
                    console.error("Profil lekérése regisztráció után sikertelen:", fetchErr);
                }
            }

            setSuccess("Sikeres regisztráció! Átirányítunk a kezdőlapra...");
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
                <p className="register-required-hint">A * jelölt mezők kitöltése kötelező.</p>

                <div className="register-form-group">
                    <label htmlFor="name">Név *</label>
                    <input
                        id="name"
                        name="name"
                        placeholder="pl. Kiss Péter"
                        onChange={handleChange}
                        onBlur={handleBlur}
                        value={form.name}
                        required
                        autoComplete="name"
                        aria-invalid={Boolean(visibleFieldErrors.name)}
                        aria-describedby={visibleFieldErrors.name ? "name-error" : undefined}
                    />
                    {visibleFieldErrors.name && (
                        <p id="name-error" className="field-error-text" role="alert">
                            {visibleFieldErrors.name}
                        </p>
                    )}
                </div>

                <div className="register-form-group">
                    <label htmlFor="email">E-mail *</label>
                    <input
                        id="email"
                        type="email"
                        name="email"
                        placeholder="pl. valaki@email.com"
                        onChange={handleChange}
                        onBlur={handleBlur}
                        value={form.email}
                        required
                        autoComplete="email"
                        aria-invalid={Boolean(visibleFieldErrors.email)}
                        aria-describedby={visibleFieldErrors.email ? "email-error" : undefined}
                    />
                    {visibleFieldErrors.email && (
                        <p id="email-error" className="field-error-text" role="alert">
                            {visibleFieldErrors.email}
                        </p>
                    )}
                </div>

                <div className="register-form-group">
                    <label htmlFor="password">Jelszó *</label>
                    <input
                        id="password"
                        type="password"
                        name="password"
                        placeholder="Legalább 8 karakter, kis/nagybetű, szám, speciális karakter"
                        onChange={handleChange}
                        onBlur={handleBlur}
                        value={form.password}
                        required
                        autoComplete="new-password"
                        aria-invalid={Boolean(visibleFieldErrors.password)}
                        aria-describedby={`password-helper${visibleFieldErrors.password ? " password-error" : ""}`}
                    />
                    <p id="password-helper" className="field-helper-text">
                        {passwordStrengthText || "A biztonságos jelszó véd az illetéktelen belépés ellen."}
                    </p>
                    {visibleFieldErrors.password && (
                        <p id="password-error" className="field-error-text" role="alert">
                            {visibleFieldErrors.password}
                        </p>
                    )}
                </div>

                <div className="register-form-group">
                    <label htmlFor="confirmPassword">Jelszó újra *</label>
                    <input
                        id="confirmPassword"
                        type="password"
                        name="confirmPassword"
                        placeholder="Írd be újra a jelszót"
                        onChange={handleChange}
                        onBlur={handleBlur}
                        value={form.confirmPassword}
                        required
                        autoComplete="new-password"
                        aria-invalid={Boolean(visibleFieldErrors.confirmPassword)}
                        aria-describedby={
                            visibleFieldErrors.confirmPassword ? "confirm-password-error" : undefined
                        }
                    />
                    {visibleFieldErrors.confirmPassword && (
                        <p id="confirm-password-error" className="field-error-text" role="alert">
                            {visibleFieldErrors.confirmPassword}
                        </p>
                    )}
                </div>

                <div className="register-form-group">
                    <label htmlFor="phone">Telefonszám *</label>
                    <input
                        id="phone"
                        type="tel"
                        name="phone"
                        placeholder="pl. +36301234567"
                        onChange={handleChange}
                        onFocus={handlePhoneFocus}
                        onBlur={handleBlur}
                        value={form.phone}
                        required
                        autoComplete="tel"
                        inputMode="numeric"
                        pattern="\+[0-9]{8,15}"
                        aria-invalid={Boolean(visibleFieldErrors.phone)}
                        aria-describedby={`phone-helper${visibleFieldErrors.phone ? " phone-error" : ""}`}
                    />
                    <p id="phone-helper" className="field-helper-text">
                        Formátum: + és utána 8-15 számjegy (pl. +36301234567).
                    </p>
                    {visibleFieldErrors.phone && (
                        <p id="phone-error" className="field-error-text" role="alert">
                            {visibleFieldErrors.phone}
                        </p>
                    )}
                </div>

                <div className="register-form-group">
                    <label htmlFor="birthdate">Születési dátum *</label>
                    <input
                        id="birthdate"
                        type="date"
                        name="birthdate"
                        onChange={handleChange}
                        onBlur={handleBlur}
                        value={form.birthdate}
                        max={new Date().toISOString().split("T")[0]}
                        required
                        aria-invalid={Boolean(visibleFieldErrors.birthdate)}
                        aria-describedby={visibleFieldErrors.birthdate ? "birthdate-error" : undefined}
                    />
                    {visibleFieldErrors.birthdate && (
                        <p id="birthdate-error" className="field-error-text" role="alert">
                            {visibleFieldErrors.birthdate}
                        </p>
                    )}
                </div>
                <button type="submit" disabled={loading || !validation.isValid}>
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
