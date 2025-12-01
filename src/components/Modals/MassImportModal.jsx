// src/components/MassImportModal.jsx
import React, { useState, useEffect } from "react";
import * as XLSX from "xlsx";
import PreviewTable from "../PreviewTable.jsx"; // külön komponens a previewhoz
import "../styles/MassImportModal.css";
import { useTransaction } from "../../stores/useTransaction";

const EXPECTED_COLUMNS = [
  "Tranzakció dátuma",
  "Könyvelés dátuma",
  "Típus",
  "Bejövő/Kimenő",
  "Partner neve",
  "Partner számlaszáma/azonosítója",
  "Költési kategória",
  "Közlemény",
  "Számla név",
  "Számla szám",
  "Összeg",
  "Pénznem",
];

export default function MassImportModal({ onClose, onImport, isOpen, user }) {
  const [file, setFile] = useState(null);
  const [previewRows, setPreviewRows] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // We'll obtain the massImport function at call time from the store to avoid
  // selector/timing issues that can cause `undefined` during initial render.
  // (useTransaction.getState() is safe to call outside render.)

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    setFile(f);
    setError("");
    setPreviewRows([]);

    if (!f) return;
    if (!f.name.endsWith(".xlsx")) {
      setError("Csak .xlsx fájl feltöltése engedélyezett!");
      return;
    }

    const reader = new FileReader();
    reader.onload = (evt) => {
      const data = evt.target.result;
      const workbook = XLSX.read(data, { type: "binary" });
      const sheetName = workbook.SheetNames[0];
      const sheet = workbook.Sheets[sheetName];
      const json = XLSX.utils.sheet_to_json(sheet, { defval: "" });

      if (!json.length) {
        setError("A fájl üres.");
        return;
      }

      const sheetColumns = Object.keys(json[0]);
      const missingCols = EXPECTED_COLUMNS.filter(
        (col) => !sheetColumns.includes(col),
      );
      if (missingCols.length > 0) {
        setError("Hiányzó oszlopok: " + missingCols.join(", "));
        return;
      }

      setPreviewRows(json.slice(0, 5)); // preview az első 5 sor
    };
    reader.readAsBinaryString(f);
  };

  const handleImport = async () => {
    if (!file || error) return;

    // get the function at runtime
    const massImportFn = useTransaction.getState().massImport;
    if (typeof massImportFn !== "function") {
      setError("Import nem elérhető - frissítse az oldalt.");
      return;
    }

    setLoading(true);
    try {
      // Use async File API instead of FileReader callbacks so errors bubble to this try/catch
      const arrayBuffer = await file.arrayBuffer();
      const workbook = XLSX.read(new Uint8Array(arrayBuffer), {
        type: "array",
      });
      const sheetName = workbook.SheetNames[0];
      const sheet = workbook.Sheets[sheetName];
      const json = XLSX.utils.sheet_to_json(sheet, { defval: "" });

      // use store action to perform the network request with auth
      const result = await massImportFn(json, user);
      const importedCount =
        result && typeof result.imported_count !== "undefined"
          ? result.imported_count
          : Array.isArray(result && result.imported_transactions)
            ? result.imported_transactions.length
            : 0;

      // show a success toast if available
      try {
        if (
          typeof window !== "undefined" &&
          typeof window.showToast === "function"
        ) {
          const msg =
            importedCount > 0
              ? `Siker: ${importedCount} tranzakció importálva.`
              : `Importálás sikeres.`;
          window.showToast(msg, { type: "success", duration: 4000 });
        }
      } catch (toastErr) {
        // log toast errors to help debugging (avoid unused var eslint error)
         
        console.warn("Could not show toast:", toastErr);
      }

      if (result && typeof result.imported_count !== "undefined") {
        onImport(result.imported_count);
      } else {
        onImport(0);
      }
      onClose();
    } catch (err) {
      setError(err && err.message ? err.message : String(err));
      // show an error toast if available
      try {
        if (
          typeof window !== "undefined" &&
          typeof window.showToast === "function"
        ) {
          const msg =
            err && err.message ? err.message : "Importálás sikertelen.";
          window.showToast(msg, { type: "error", duration: 6000 });
        }
      } catch (toastErr) {
         
        console.warn("Could not show error toast:", toastErr);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`modalOverlay ${isOpen ? "open" : ""}`}
      onClick={(e) => {
        // close only when clicking on the overlay itself (not the modal content)
        if (e.target === e.currentTarget) onClose();
      }}
      aria-hidden={!isOpen}
    >
      <aside
        className={`modalContent rightSlide ${isOpen ? "open" : ""}`}
        role="dialog"
        aria-modal="true"
      >
        <div className="modalHeader">
          <h2>Kiadások importálása OTP-ből</h2>
          <button
            className="modalCloseButton"
            onClick={onClose}
            aria-label="Bezárás"
            title="Bezárás"
          >
            ×
          </button>
        </div>

        <div className="modalBody">
          <p>
            Válassz egy Excel fájlt az OTP exportból, hogy importáljuk a
            tranzakciókat.
          </p>

          <div className="fileInputWrapper">
            <label htmlFor="mass-import-file" className="fileInputLabel">
              Fájl kiválasztása
            </label>
            <input
              id="mass-import-file"
              type="file"
              accept=".xlsx"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
            <div className="fileName">
              {file ? file.name : "Nincs kiválasztva fájl"}
            </div>
          </div>

          {!user && (
            <p className="error" style={{ marginTop: 10 }}>
              Importáláshoz bejelentkezés szükséges.
            </p>
          )}

          {error && <p className="error">{error}</p>}

          <PreviewTable previewRows={previewRows} />
        </div>

        <div className="modalActions">
          <button onClick={onClose}>Mégse</button>
          <button
            onClick={handleImport}
            disabled={!file || !!error || loading || !user}
          >
            {loading ? "Importálás..." : "Importálás"}
          </button>
        </div>
      </aside>
    </div>
  );
}
