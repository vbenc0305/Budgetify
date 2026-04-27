import React, { useCallback, useEffect, useRef, useState } from "react";
import ReactDOM from "react-dom";
import "./styles/Toast.css";

export default function ToastContainer() {
  const [toasts, setToasts] = useState([]);
  const timeouts = useRef(new Map());

  const startRemoveToast = useCallback((id) => {
    // mark removing to trigger CSS animation
    setToasts((t) => t.map((x) => (x.id === id ? { ...x, removing: true } : x)));
    // clear scheduled timeout if exists
    const to = timeouts.current.get(id);
    if (to) {
      clearTimeout(to);
      timeouts.current.delete(id);
    }
    // after animation duration, remove it from state
    const ANIM_MS = 260;
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, ANIM_MS);
  }, []);

  useEffect(() => {
    // expose a global helper to show toasts from anywhere
    window.showToast = (message, { type = "info", duration = 3500 } = {}) => {
      const id = Math.random().toString(36).slice(2, 9);
      const toast = { id, message, type, removing: false };
      setToasts((t) => [...t, toast]);

      // schedule auto-dismiss
      const timeoutId = setTimeout(() => {
        startRemoveToast(id);
      }, duration);
      timeouts.current.set(id, timeoutId);
    };

    // capture reference to timeouts map so cleanup uses the same reference
    const timeoutsMap = timeouts.current;

    return () => {
      // remove global helper if it exists
      if (typeof window !== "undefined" && window.showToast) {
        try {
          delete window.showToast;
        } catch (err) {
          // some environments may prevent deletion; ignore
          console.warn("Could not delete window.showToast", err);
        }
      }
      // clear any pending timeouts
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
