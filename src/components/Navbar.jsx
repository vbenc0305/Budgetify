// src/components/Navbar.jsx
import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import MenuItem from "./MenuItem";
import { useUser } from "../stores/useUser";
import { FaPiggyBank } from "react-icons/fa";
import "./styles/Navbar.css";

export default function Navbar() {
    // Külön hívjuk a store-t user és logout miatt
    const user = useUser((s) => s.user);
    const logout = useUser((s) => s.logout);

    const navigate = useNavigate();

    const handleLogout = async () => {
        try {
            await logout(); // store-ban lévő logout
            navigate("/"); // vissza a Home-ra
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
                    {!user ? (
                        <li>
                            <NavLink
                                to="/login"
                                className={({ isActive }) =>
                                    isActive ? "nav-link active nav-cta" : "nav-link nav-cta"
                                }
                                style={{
                                    background: 'linear-gradient(90deg, #0f172a, #111827)',
                                    backgroundColor: '#0b0b0b',
                                    color: '#fff',
                                    padding: '6px 12px',
                                    borderRadius: '10px',
                                    textDecoration: 'none'
                                }}
                            >
                                Bejelentkezés
                            </NavLink>
                        </li>
                    ) : (
                        <>
                            <MenuItem to="/profile" label="Profilom" />
                            <MenuItem to="/predict" label="Predikció" />
                            <MenuItem to="/transactions" label="Tranzakciók" />

                            <li>
                                <button className="logout-button" onClick={handleLogout}>
                                    Kijelentkezés
                                </button>
                            </li>
                        </>
                    )}
                </ul>
            </div>
        </nav>
    );
}
