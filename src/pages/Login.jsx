// src/components/Login.jsx
import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useUser } from "../stores/useUser";
import { getFirebaseErrorMessage } from "../utils/firebaseErrorHandler";
import "./styles/Login.css";

export default function Login() {
  const navigate = useNavigate();

  // Zustand store külön hívásokkal, így nincs destructuring hiba
  const user = useUser((s) => s.user);
  const setUser = useUser((s) => s.setUser);
  const fetchProfile = useUser((s) => s.fetchProfile);
  const clearStatus = useUser((s) => s.clearStatus);
  const storeLoading = useUser((s) => s.loading);
  const storeError = useUser((s) => s.error);
  const storeSuccess = useUser((s) => s.success);

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

  useEffect(() => {
    return () => {
      clearStatus();
    };
  }, [clearStatus]);

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
        getFirebaseErrorMessage(err?.code) ||
          "Hiba történt a bejelentkezés során.",
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
        <div className="login-form-group">
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            placeholder="pl. valaki@email.com"
            aria-invalid={Boolean(displayedError)}
          />
        </div>

        <div className="login-form-group">
          <label htmlFor="login-password">Jelszó</label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            placeholder="Add meg a jelszavad"
            aria-invalid={Boolean(displayedError)}
          />
        </div>

        <button type="submit" disabled={isLoading}>
          {isLoading ? "Belépés..." : "Belépés"}
        </button>

        {displayedError && (
          <p className="error-text" role="alert">
            {displayedError}
          </p>
        )}
        {!displayedError && storeSuccess && (
          <p className="success-text" role="status">
            {storeSuccess}
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
