import { create } from "zustand";
import { persist } from "zustand/middleware";
import { getAuth } from "firebase/auth";
import { normalizeTransactionCollection } from "../utils/transactionType";

const hasTokenMethod = (candidate) =>
  !!candidate && typeof candidate.getIdToken === "function";

const resolveActiveUser = (candidateUser) => {
  if (hasTokenMethod(candidateUser)) return candidateUser;
  const current = getAuth().currentUser;
  return hasTokenMethod(current) ? current : null;
};

const fetchWithAuthRetry = async (url, options, user) => {
  const activeUser = resolveActiveUser(user);
  if (!activeUser) {
    throw new Error("Nincs bejelentkezett user.");
  }

  let token = await activeUser.getIdToken();
  let response = await fetch(url, {
    ...options,
    headers: {
      ...(options?.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });

  if (response.status === 401) {
    token = await activeUser.getIdToken(true);
    response = await fetch(url, {
      ...options,
      headers: {
        ...(options?.headers || {}),
        Authorization: `Bearer ${token}`,
      },
    });
  }

  return { response, activeUser };
};

export const useTransaction = create(
  persist(
    (set, get) => ({
      transactions: [],
      loading: false,
      error: null,
      fetched: false,

      fetchTransactions: async (user) => {
        const activeUser = resolveActiveUser(user);
        if (!activeUser) {
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
          const { response } = await fetchWithAuthRetry(
            "/api/transactions",
            {
              method: "GET",
              headers: {
                "Content-Type": "application/json",
              },
            },
            activeUser,
          );

          if (!response.ok) {
            const text = await response.text().catch(() => "");
            throw new Error(
              `Network response not ok: ${response.status} ${text}`,
            );
          }

          const data = await response.json();
          const normalizedTransactions = normalizeTransactionCollection(data);
          set({
            transactions: normalizedTransactions,
            fetched: true,
            loading: false,
          });
          console.log("✅ fetchTransactions sikeres", normalizedTransactions);
        } catch (err) {
          set({
            error: err.message || "Hiba a tranzakciók lekérésekor",
            loading: false,
          });
        }
      },

      massImport: async (jsonPayload, user) => {
        const activeUser = resolveActiveUser(user);
        if (!activeUser) {
          const msg = "Nincs bejelentkezett user.";
          set({ error: msg });
          throw new Error(msg);
        }

        if (get().loading) {
          throw new Error("Már folyamatban van egy művelet.");
        }

        set({ loading: true, error: null });
        try {
          const { response } = await fetchWithAuthRetry(
            "/api/transactions/mass_import",
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              // Backend expects a JSON array in the request body (not an object).
              // Send the parsed rows directly as the top-level array.
              body: JSON.stringify(jsonPayload),
            },
            activeUser,
          );

          if (!response.ok) {
            const text = await response.text().catch(() => "");
            throw new Error(`Import sikertelen: ${response.status} ${text}`);
          }

          const result = await response.json();

          const importedTransactions = normalizeTransactionCollection(
            result?.imported_transactions,
          );

          if (
            result &&
            importedTransactions.length > 0
          ) {
            set((state) => ({
              transactions: [...state.transactions, ...importedTransactions],
            }));
          }

          // After successful import, force a fresh fetch from backend to get canonical data
          try {
            // mark fetched false so fetchTransactions will actually run
            set({ fetched: false });
            // call the store action to re-fetch; await to ensure transactions updated
            const fetchFn = get().fetchTransactions;
            if (typeof fetchFn === "function") {
              await fetchFn(activeUser);
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
        const activeUser = resolveActiveUser(user);
        if (!activeUser) {
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
          const { response } = await fetchWithAuthRetry(
            "/api/transactions/mass_delete",
            {
              method: "DELETE",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({ transaction_ids: transactionIds }),
            },
            activeUser,
          );

          if (!response.ok) {
            const text = await response.text().catch(() => "");
            throw new Error(
              `Tömeges törlés sikertelen: ${response.status} ${text}`,
            );
          }

          const normalizeTxId = (raw) => {
            if (raw === null || raw === undefined) return null;
            const str = String(raw).trim();
            if (!str) return null;
            const normalizedPath = str.startsWith("/") ? str.slice(1) : str;
            const segments = normalizedPath.split("/").filter(Boolean);
            const txIndex = segments.lastIndexOf("transactions");
            if (txIndex >= 0 && segments[txIndex + 1])
              return segments[txIndex + 1];
            return str;
          };

          const idSet = new Set(
            transactionIds.map((id) => normalizeTxId(id)).filter(Boolean),
          );
          set((state) => ({
            transactions: state.transactions.filter((tx) => {
              const txId =
                tx?.id ??
                tx?.transaction_id ??
                tx?.tran_id ??
                tx?._id ??
                tx?.path ??
                tx?.ref_path;
              const normalized = normalizeTxId(txId);
              return !normalized || !idSet.has(normalized);
            }),
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
