import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  getAuth,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  updateProfile as fbUpdateProfile,
} from "firebase/auth";
import { useTransaction } from "./useTransaction";
import isEqual from "lodash/isEqual";

export const useUser = create(
  persist(
    (set, get) => ({
      user: null,
      usrInfo: null,
      loading: false,
      fetchingProfile: false,
      error: null,
      success: null,
      fetched: false,
      authChecked: false, // <-- ide
      listenerAttached: false,

      setUser: (u) => set({ user: u }),

      fetchProfile: async () => {
        const { user, fetched, fetchingProfile } = get();
        if (!user || typeof user.getIdToken !== "function") {
          set({ error: "Nem bejelentkezett vagy hibás user objektum." });
          return null;
        }
        if (fetched && !fetchingProfile) return get().usrInfo;
        if (fetchingProfile) return null;

        set({ loading: true, fetchingProfile: true, error: null });

        try {
          let token = await user.getIdToken();
          let res = await fetch("/api/profile", {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
              Authorization: "Bearer " + token,
            },
          });

          if (res.status === 401) {
            token = await user.getIdToken(true);
            res = await fetch("/api/profile", {
              method: "GET",
              headers: {
                "Content-Type": "application/json",
                Authorization: "Bearer " + token,
              },
            });
          }

          if (res.status === 404) {
            set({ usrInfo: null, fetched: true });
            return null;
          }

          if (!res.ok) {
            const text = await res.text().catch(() => "");
            throw new Error(
              `Profiladatok lekérése sikertelen: ${res.status} ${text}`,
            );
          }

          const data = await res.json();
          const currentUsrInfo = get().usrInfo;
          const isDataContentChanged = !isEqual(data, currentUsrInfo);
          const isFetchedStatusChanged = !get().fetched;

          if (isDataContentChanged || isFetchedStatusChanged) {
            set({
              usrInfo: data,
              fetched: true,
              success: isDataContentChanged ? null : get().success,
            });
          }

          return data;
        } catch (err) {
          set({
            error:
              "Hiba történt a profiladatok lekérésekor: " +
              (err.message || err),
          });
          throw err;
        } finally {
          set({ loading: false, fetchingProfile: false });
        }
      },

      logout: async () => {
        const auth = getAuth();
        await firebaseSignOut(auth);
        set({ user: null, usrInfo: null, fetched: false, authChecked: true });
        useTransaction.getState().resetTransactions();
      },

      initAuthListener: () => {
        if (get().listenerAttached) return;
        set({ listenerAttached: true });

        const auth = getAuth();
        const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
          set({ user: firebaseUser, fetched: false, authChecked: true });

          if (!firebaseUser) {
            useTransaction.getState().resetTransactions();
            set({ usrInfo: null, fetched: false });
          } else {
            setTimeout(() => {
              get().fetchProfile?.().catch(console.error);
            }, 0);
          }
        });

        return unsubscribe;
      },

      updateProfile: async (updateData = {}) => {
        set({ error: null, loading: true, success: null });
        const auth = getAuth();
        const current = auth.currentUser;

        if (!current) {
          const errMsg = "Nincs élő Firebase user a profilfrissítéshez.";
          set({ error: errMsg, loading: false });
          throw new Error(errMsg);
        }

        try {
          // --- 1) Előkészítés: tiltsd el a nem oda való mezőket
          // Ne küldjünk jelszót, email-t stb. a usr_info táblának
          const forbidden = ["password", "email", "last_login", "role", "uid"];
          const payload = {};

          Object.entries(updateData).forEach(([k, v]) => {
            if (forbidden.includes(k)) return;
            // ha üres stringet adnak, ne küldd át, hagyd, hogy a backend kezelje null-ként ha kell
            if (v === "" || v === undefined) return;
            payload[k] = v;
          });

          // --- 2) Ha age csatolva, konvertáld számra vagy null-ra
          if (payload.age !== undefined) {
            const n = Number(payload.age);
            payload.age = Number.isFinite(n)
              ? Math.max(0, Math.floor(n))
              : null;
          }

          function calcAgeFromBirthdate(birthdateStr) {
            if (!birthdateStr) return null;
            const d = new Date(birthdateStr);
            if (Number.isNaN(d.getTime())) return null;
            const now = new Date();
            let age = now.getFullYear() - d.getFullYear();
            const m = now.getMonth() - d.getMonth();
            if (m < 0 || (m === 0 && now.getDate() < d.getDate())) age--;
            return age >= 0 ? age : null;
          }
          // --- 4) Ha van displayName vagy photoURL, frissítsük Firebase user objectet is
          const { displayName, photoURL } = payload;
          if (displayName || photoURL) {
            // csak a szükséges kulcsokat adjuk át a Firebase updateProfile-nek
            await fbUpdateProfile(current, {
              ...(displayName ? { displayName } : {}),
              ...(photoURL ? { photoURL } : {}),
            });
            // ne töröld a payloadból a displayName-t — lehet, hogy a backend is tárolja
          }

          // --- 5) Token és backend hívás
          const token = await current.getIdToken();
          // endpoint: PUT /api/usr_info/:userId  (alakítsd a backend elvárásaihoz)
          const res = await fetch(
            `/api/usr_info/${encodeURIComponent(current.uid)}`,
            {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
                Authorization: "Bearer " + token,
              },
              body: JSON.stringify(payload),
            },
          );

          if (res.status === 401) {
            // próbáljuk újra friss tokennel
            const fresh = await current.getIdToken(true);
            const retry = await fetch(
              `/api/usr_info/${encodeURIComponent(current.uid)}`,
              {
                method: "PUT",
                headers: {
                  "Content-Type": "application/json",
                  Authorization: "Bearer " + fresh,
                },
                body: JSON.stringify(payload),
              },
            );
            if (!retry.ok) {
              const txt = await retry.text().catch(() => "");
              throw new Error(`Backend hibára futott: ${retry.status} ${txt}`);
            }
            const updatedRetry = await retry.json();
            set({
              usrInfo: { ...(get().usrInfo || {}), ...updatedRetry },
              fetched: true,
              success: "Profil sikeresen frissítve.",
              loading: false,
            });
            return updatedRetry;
          }

          if (!res.ok) {
            const txt = await res.text().catch(() => "");
            throw new Error(`Backend hibára futott: ${res.status} ${txt}`);
          }

          const updatedData = await res.json();
          const merged = {
            ...(get().usrInfo || {}),
            ...updatedData.data,
          };
          set({
            usrInfo: merged,
            fetched: true,
            success: "Profil sikeresen frissítve.",
            loading: false,
          });

          return merged;
        } catch (err) {
          console.error("store.updateProfile error:", err);
          set({
            error: "Hiba a profil mentésekor: " + (err.message || err),
            loading: false,
          });
          throw err;
        }
      },
    }),
    {
      name: "user-storage",
      getStorage: () => localStorage,
      partialize: (state) => ({
        user: state.user,
        usrInfo: state.usrInfo,
        fetched: state.fetched,
        authChecked: state.authChecked,
      }),
    },
  ),
);
