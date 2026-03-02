import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useTransaction = create(
  persist(
    (set, get) => ({
      transactions: [],
      loading: false,
      error: null,
      fetched: false,

      fetchTransactions: async (user) => {
        if (!user || typeof user.getIdToken !== "function") {
          set({
            transactions: [],
            fetched: false,
            loading: false,
            error: "Nincs bejelentkezett user.",
          });
          return;
        }
        if (get().loading || get().fetched) return;

        set({ loading: true, error: null });

        try {
          const token = await user.getIdToken();
          const res = await fetch("/api/transactions", {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          });

          if (!res.ok) {
            const text = await res.text().catch(() => "");
            throw new Error(`Network response not ok: ${res.status} ${text}`);
          }

          const data = await res.json();
          set({ transactions: data, fetched: true, loading: false });
          console.log("✅ fetchTransactions sikeres", data);
        } catch (err) {
          set({
            error: err.message || "Hiba a tranzakciók lekérésekor",
            loading: false,
          });
        }
      },

      massImport: async (jsonPayload, user) => {
        if (!user || typeof user.getIdToken !== "function") {
          const msg = "Nincs bejelentkezett user.";
          set({ error: msg });
          throw new Error(msg);
        }

        if (get().loading) {
          throw new Error("Már folyamatban van egy művelet.");
        }

        set({ loading: true, error: null });
        try {
          const token = await user.getIdToken();
          const res = await fetch("/api/transactions/mass_import", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            // Backend expects a JSON array in the request body (not an object).
            // Send the parsed rows directly as the top-level array.
            body: JSON.stringify(jsonPayload),
          });

          if (!res.ok) {
            const text = await res.text().catch(() => "");
            throw new Error(`Import sikertelen: ${res.status} ${text}`);
          }

          const result = await res.json();

          if (
            result &&
            Array.isArray(result.imported_transactions) &&
            result.imported_transactions.length > 0
          ) {
            set((state) => ({
              transactions: [
                ...state.transactions,
                ...result.imported_transactions,
              ],
            }));
          }

          // After successful import, force a fresh fetch from backend to get canonical data
          try {
            // mark fetched false so fetchTransactions will actually run
            set({ fetched: false });
            // call the store action to re-fetch; await to ensure transactions updated
            const fetchFn = get().fetchTransactions;
            if (typeof fetchFn === "function") {
              await fetchFn(user);
            }
          } catch (e) {
            // non-fatal: if refetch fails we still return the import result
            console.error("Refetch after massImport failed:", e);
          }

          set({ loading: false });
          return result;
        } catch (err) {
          set({ error: err.message || "Import hiba", loading: false });
          throw err;
        }
      },

      massDeleteTransactions: async (transactionIds, user) => {
        if (!user || typeof user.getIdToken !== "function") {
          const msg = "Nincs bejelentkezett user.";
          set({ error: msg });
          throw new Error(msg);
        }

        if (!Array.isArray(transactionIds) || transactionIds.length === 0) {
          throw new Error("Nincs kiválasztott tranzakció a törléshez.");
        }

        if (get().loading) {
          throw new Error("Már folyamatban van egy művelet.");
        }

        set({ loading: true, error: null });

        try {
          const token = await user.getIdToken();
          const res = await fetch("/api/transactions/mass_delete", {
            method: "DELETE",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ transaction_ids: transactionIds }),
          });

          if (!res.ok) {
            const text = await res.text().catch(() => "");
            throw new Error(`Tömeges törlés sikertelen: ${res.status} ${text}`);
          }

          set((state) => ({
            transactions: state.transactions.filter(
              (tx) => !transactionIds.includes(tx.id),
            ),
            loading: false,
          }));

          return true;
        } catch (err) {
          set({ error: err.message || "Tömeges törlés hiba", loading: false });
          throw err;
        }
      },

      resetTransactions: () =>
        set({ transactions: [], loading: false, error: null, fetched: false }),
    }),
    {
      name: "transaction-storage",
      getStorage: () => localStorage,
      onRehydrateStorage: () => (state) => {
        console.log("Transaction store rehydrated:", state);
        // Clear the error after rehydration because it might be stale
        // (e.g., from a previous session where there was no user)
        if (state && state.error === "Nincs bejelentkezett user.") {
          state.error = null;
          state.fetched = false; // Reset fetched so transactions will be refetched
        }
      },
    },
  ),
);
