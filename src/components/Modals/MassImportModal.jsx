// src/components/MassImportModal.jsx
import React, { useState, useEffect } from "react";
import PreviewTable from "../PreviewTable.jsx"; // külön komponens a previewhoz
import "../styles/MassImportModal.css";
import { useTransaction } from "../../stores/useTransaction";
import { readExcelRowsFromFile } from "../../utils/excelImport";

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
  const [parsedRows, setParsedRows] = useState([]);
  const [previewRows, setPreviewRows] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const hasAuthUser = !!user && typeof user.getIdToken === "function";

  const getImportValidationError = (rows) => {
    if (!rows.length) {
      return "A fájl üres.";
    }

    const sheetColumns = Object.keys(rows[0]);
    const missingCols = EXPECTED_COLUMNS.filter(
      (col) => !sheetColumns.includes(col),
    );

    if (missingCols.length > 0) {
      return "Hiányzó oszlopok: " + missingCols.join(", ");
    }

    return "";
  };

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

  const handleFileChange = async (e) => {
    const f = e.target.files[0];
    setFile(f);
    setParsedRows([]);
    setError("");
    setPreviewRows([]);

    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".xlsx")) {
      setError("Csak .xlsx fájl feltöltése engedélyezett!");
      return;
    }

    try {
      const rows = await readExcelRowsFromFile(f);
      const validationError = getImportValidationError(rows);
      if (validationError) {
        setError(validationError);
        return;
      }

      setParsedRows(rows);
      setPreviewRows(rows.slice(0, 5)); // preview az első 5 sor
    } catch (err) {
      setError(
        err && err.message
          ? err.message
          : "A fájl feldolgozása sikertelen.",
      );
    }
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
      const json =
        parsedRows.length > 0 ? parsedRows : await readExcelRowsFromFile(file);
      const validationError = getImportValidationError(json);
      if (validationError) {
        setError(validationError);
        return;
      }

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
      className={`massImportModalOverlay modalOverlay ${isOpen ? "open" : ""}`}
      onClick={(e) => {
        // close only when clicking on the overlay itself (not the modal content)
        if (e.target === e.currentTarget) onClose();
      }}
      aria-hidden={!isOpen}
    >
      <aside
        className={`massImportModalContent modalContent rightSlide ${isOpen ? "open" : ""}`}
        role="dialog"
        aria-modal="true"
      >
        <div className="massImportModalHeader modalHeader">
          <h2>Kiadások importálása OTP-ből</h2>
          <button
            className="massImportModalCloseButton modalCloseButton"
            onClick={onClose}
            aria-label="Bezárás"
            title="Bezárás"
          >
            ×
          </button>
        </div>

        <div className="massImportModalBody modalBody">
          <p>
            Válassz egy Excel fájlt az OTP exportból, hogy importáljuk a
            tranzakciókat.
          </p>

          <div className="massImportFileInputWrapper fileInputWrapper">
            <label
              htmlFor="mass-import-file"
              className="massImportFileInputLabel fileInputLabel"
            >
              Fájl kiválasztása
            </label>
            <input
              id="mass-import-file"
              type="file"
              accept=".xlsx"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
            <div className="massImportFileName fileName">
              {file ? file.name : "Nincs kiválasztva fájl"}
            </div>
          </div>

          {!hasAuthUser && (
            <p className="massImportError" style={{ marginTop: 10 }}>
              Importáláshoz bejelentkezés szükséges.
            </p>
          )}

          {error && <p className="massImportError">{error}</p>}

          <PreviewTable previewRows={previewRows} />
        </div>

        <div className="massImportModalActions modalActions">
          <button className="massImportCancelButton" onClick={onClose}>
            Mégse
          </button>
          <button
            className="massImportImportButton"
            onClick={handleImport}
            disabled={!file || !!error || loading || !hasAuthUser}
          >
            {loading ? "Importálás..." : "Importálás"}
          </button>
        </div>
      </aside>
    </div>
  );
}
