import React, { useCallback, useEffect, useRef, useState } from "react";
import ReactDOM from "react-dom";
import "./styles/Toast.css";

export default function ToastContainer() {
  const [toasts, setToasts] = useState([]);
  const timeouts = useRef(new Map());

  const startRemoveToast = useCallback((id) => {
    setToasts((t) => t.map((x) => (x.id === id ? { ...x, removing: true } : x)));
    const to = timeouts.current.get(id);
    if (to) {
      clearTimeout(to);
      timeouts.current.delete(id);
    }
    const ANIM_MS = 260;
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, ANIM_MS);
  }, []);

  useEffect(() => {
    window.showToast = (message, { type = "info", duration = 3500 } = {}) => {
      const id = Math.random().toString(36).slice(2, 9);
      const toast = { id, message, type, removing: false };
      setToasts((t) => [...t, toast]);

      const timeoutId = setTimeout(() => {
        startRemoveToast(id);
      }, duration);
      timeouts.current.set(id, timeoutId);
    };

    const timeoutsMap = timeouts.current;

    return () => {
      if (typeof window !== "undefined" && window.showToast) {
        try {
          delete window.showToast;
        } catch (err) {
          console.warn("Could not delete window.showToast", err);
        }
      }
      timeoutsMap.forEach((to) => clearTimeout(to));
      timeoutsMap.clear();
    };
     
  }, [startRemoveToast]);

  if (!toasts.length) return null;

  return ReactDOM.createPortal(
    <div className="toastRoot" aria-live="polite" aria-atomic="true">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`toast ${t.type} ${t.removing ? "removing" : ""}`}
          role="status"
        >
          <div className="toastMessage">{t.message}</div>
          <button
            className="toastClose"
            onClick={() => startRemoveToast(t.id)}
            aria-label="Bezárás"
            title="Bezárás"
          >
            ×
          </button>
        </div>
      ))}
    </div>,
    document.body
  );
}
