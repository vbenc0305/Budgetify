import React from "react";
import "./styles/Loading.css";

export default function Loading({ label = "Betöltés...", className = "" }) {
  return (
    <div className={`loadingContainer ${className}`.trim()} role="status" aria-live="polite">
      <span className="loadingSpinner" aria-hidden="true" />
      <p className="loadingText">{label}</p>
    </div>
  );
}
