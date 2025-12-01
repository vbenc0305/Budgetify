// src/components/MenuItem.jsx
import React from "react";
import { NavLink } from "react-router-dom";

/**
 * MenuItem komponens
 * Props:
 *  - to: string          // a routoláshoz szükséges útvonal (pl. "/why")
 *  - label: string       // a megjelenítendő szöveg (pl. "Miért kövess?")
 */
export default function MenuItem({ to, label }) {
    return (
        <li>
            <NavLink
                to={to}
                className={({ isActive }) =>
                    isActive ? "nav-link active" : "nav-link"
                }
            >
                {label}
            </NavLink>
        </li>
    );
}
