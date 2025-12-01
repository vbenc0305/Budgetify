// src/components/PreviewTable.jsx
import React from "react";
import "./styles/previewTable.css";

export default function PreviewTable({ previewRows }) {
  if (!previewRows || previewRows.length === 0) {
    return (
      <div className="previewSection">
        <p>Nincs még fájl kiválasztva, vagy a fájl üres.</p>
      </div>
    );
  }

  return (
    <div className="previewSection">
      <h4>Előnézet</h4>
      <div className="tableWrapper">
        <table className="previewTable">
          <thead>
            <tr>
              {Object.keys(previewRows[0]).map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {previewRows.map((row, idx) => (
              <tr key={idx}>
                {Object.values(row).map((val, i) => (
                  <td key={i}>{val}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
