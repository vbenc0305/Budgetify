// src/components/Navbar.jsx
import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { FaMoon, FaSun } from "react-icons/fa";
import MenuItem from "./MenuItem";
import { useUser } from "../stores/useUser";
import { useTheme } from "../contexts/useTheme";
import { FaPiggyBank } from "react-icons/fa";
import "./styles/Navbar.css";

export default function Navbar() {
  const user = useUser((s) => s.user);
  const logout = useUser((s) => s.logout);
  const authChecked = useUser((s) => s.authChecked);
  const { themePreference, resolvedTheme, setThemePreference } = useTheme();

  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      navigate("/");
    } catch (err) {
      console.error("❌ Hiba kijelentkezéskor:", err);
    }
  };

  return (
    <nav className="navbar-root">
      <div className="navbar-container">
        <div className="navbar-logo">
          <NavLink to="/" className="navbar-brand">
            <FaPiggyBank className="navbar-icon" />
            <span style={{ marginLeft: "8px" }}>Budgetify</span>
          </NavLink>
        </div>

        <ul className="navbar-menu">
          <MenuItem to="/" label="Főoldal" />
          {authChecked && !user ? (
            <li>
              <NavLink
                to="/login"
                className={({ isActive }) =>
                  isActive ? "nav-link active nav-cta" : "nav-link nav-cta"
                }
              >
                Bejelentkezés
              </NavLink>
            </li>
          ) : authChecked && user ? (
            <>
              <MenuItem to="/profile" label="Profilom" />
              <MenuItem to="/predict" label="Predikció" />
              <MenuItem to="/transactions" label="Tranzakciók" />
              <MenuItem to="/county-insights" label="Megyei térkép" />

              <li>
                <button className="logout-button" onClick={handleLogout}>
                  Kijelentkezés
                </button>
              </li>
            </>
          ) : null}
          <li className="theme-control-item">
            {resolvedTheme === "dark" ? (
              <FaMoon className="theme-control-icon" aria-hidden="true" />
            ) : (
              <FaSun className="theme-control-icon" aria-hidden="true" />
            )}
            <select
              aria-label="Megjelenés"
              className="theme-control-select"
              value={themePreference}
              onChange={(e) => setThemePreference(e.target.value)}
            >
              <option value="system">Rendszer</option>
              <option value="light">Világos</option>
              <option value="dark">Sötét</option>
            </select>
          </li>
        </ul>
      </div>
    </nav>
  );
}
