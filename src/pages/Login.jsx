// src/components/Login.jsx
import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useUser } from "../stores/useUser";
import "./styles/Login.css";

export default function Login() {
  const navigate = useNavigate();

  // Zustand store külön hívásokkal, így nincs destructuring hiba
  const user = useUser((s) => s.user);
  const setUser = useUser((s) => s.setUser);
  const fetchProfile = useUser((s) => s.fetchProfile);
  const storeLoading = useUser((s) => s.loading);
  const storeError = useUser((s) => s.error);

  // Lokális state a loginhoz
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState("");
  const [localLoading, setLocalLoading] = useState(false);

  // Ha már be vagyunk jelentkezve, navigáljunk home-ra
  useEffect(() => {
    if (user) {
      navigate("/");
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError("");
    setLocalLoading(true);

    try {
      const { getAuth, signInWithEmailAndPassword } = await import(
        "firebase/auth"
      );
      const auth = getAuth();

      const userCredential = await signInWithEmailAndPassword(
        auth,
        email.trim(),
        password,
      );
      const firebaseUser = userCredential.user;

      if (typeof setUser === "function") setUser(firebaseUser);
      if (typeof fetchProfile === "function") await fetchProfile();

      navigate("/");
    } catch (err) {
      console.error("Login error:", err);
      setLocalError(
        err?.code === "auth/wrong-password" ||
          err?.code === "auth/user-not-found"
          ? "Hibás email vagy jelszó."
          : err?.message || "Hiba történt a bejelentkezés során.",
      );
    } finally {
      setLocalLoading(false);
    }
  };

  const isLoading = localLoading || storeLoading;
  const displayedError = localError || storeError;

  return (
    <div className="login-container">
      <h2>Bejelentkezés</h2>

      <form onSubmit={handleSubmit} className="login-form" aria-live="polite">
        <label>
          Email:
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>

        <label>
          Jelszó:
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>

        <button type="submit" disabled={isLoading}>
          {isLoading ? "Belépés..." : "Belépés"}
        </button>

        {displayedError && (
          <p className="error-text" role="alert">
            {displayedError}
          </p>
        )}
      </form>

      <p className="register-prompt">
        Nincs fiókod?{" "}
        <Link to="/register" className="register-link">
          Regisztrálj itt!
        </Link>
      </p>
    </div>
  );
}
