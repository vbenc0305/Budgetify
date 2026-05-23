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

const unsupportedConsentResponsePattern =
  /analytics_consent|unknown|unexpected|column|schema|not allowed|validation/i;

const clearUserSessionState = (set) => {
  set({
    user: null,
    usrInfo: null,
    fetched: false,
    authChecked: true,
  });
  useTransaction.getState().resetTransactions();
};

const deleteProfileWithToken = async (idToken, uid) => {
  const sendDeleteRequest = (url) =>
    fetch(url, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${idToken}`,
      },
    });

  let primaryResponse = await sendDeleteRequest(
    `/api/usr_info/${encodeURIComponent(uid)}`,
  );

  if (primaryResponse.ok || primaryResponse.status === 404) {
    return true;
  }

  if (![401, 403, 405].includes(primaryResponse.status)) {
    const primaryText = await primaryResponse.text().catch(() => "");
    throw new Error(
      `Profiltörlés sikertelen: ${primaryResponse.status} ${primaryText}`,
    );
  }

  const fallbackResponse = await sendDeleteRequest("/api/profile");

  if (fallbackResponse.ok || fallbackResponse.status === 404) {
    return true;
  }

  const fallbackText = await fallbackResponse.text().catch(() => "");
  throw new Error(
    `Profiltörlés sikertelen: ${fallbackResponse.status} ${fallbackText}`,
  );
};

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
      authChecked: false,
      listenerAttached: false,

      setUser: (u) => set({ user: u }),

      clearStatus: () => set({ error: null, success: null }),

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
          if (
            typeof data.analytics_consent !== "boolean" &&
            typeof get().usrInfo?.analytics_consent === "boolean"
          ) {
            data.analytics_consent = get().usrInfo.analytics_consent;
          }
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
        clearUserSessionState(set);
      },

      deleteAccountProfile: async () => {
        set({ error: null, success: null, loading: true });
        const auth = getAuth();
        const current = auth.currentUser;

        if (!current) {
          const errMsg = "Nincs élő Firebase user a fiók törléséhez.";
          set({ error: errMsg, loading: false });
          throw new Error(errMsg);
        }

        const uid = current.uid;

        try {
          const idToken = await current.getIdToken(true);

          await firebaseSignOut(auth);
          clearUserSessionState(set);
          set({ loading: false, error: null, success: null });

          const deletionPromise = (async () => {
            try {
              await deleteProfileWithToken(idToken, uid);
              set({
                error: null,
                success: "A profil sikeresen törölve lett.",
                loading: false,
              });
              return true;
            } catch (err) {
              console.error("store.deleteAccountProfile error:", err);
              set({
                error: "Hiba a profil törlésekor: " + (err.message || err),
                success: null,
                loading: false,
              });
              throw err;
            }
          })();

          return { deletionPromise };
        } catch (err) {
          console.error("store.deleteAccountProfile bootstrap error:", err);
          set({
            error: "Hiba a fiók törlésekor: " + (err.message || err),
            success: null,
            loading: false,
          });
          throw err;
        }
      },

      initAuthListener: () => {
        if (get().listenerAttached) return;
        set({ listenerAttached: true });

        const auth = getAuth();
        const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
          const effectiveUser =
            firebaseUser && typeof firebaseUser.getIdToken === "function"
              ? firebaseUser
              : auth.currentUser &&
                  typeof auth.currentUser.getIdToken === "function"
                ? auth.currentUser
                : null;

          set({ user: effectiveUser, fetched: false, authChecked: true });

          if (!effectiveUser) {
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
          const forbidden = ["password", "email", "last_login", "role", "uid"];
          const payload = {};

          Object.entries(updateData).forEach(([k, v]) => {
            if (forbidden.includes(k)) return;
            if (v === "" || v === undefined) return;
            payload[k] = v;
          });

          if (payload.age !== undefined) {
            const n = Number(payload.age);
            if (!Number.isInteger(n) || n < 0 || n > 120) {
              delete payload.age;
            } else {
              payload.age = n;
            }
          }

          const sendUpdate = (idToken, bodyPayload) =>
            fetch(`/api/usr_info/${encodeURIComponent(current.uid)}`, {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
                Authorization: "Bearer " + idToken,
              },
              body: JSON.stringify(bodyPayload),
            });

          const { displayName, photoURL } = payload;
          if (displayName || photoURL) {
            await fbUpdateProfile(current, {
              ...(displayName ? { displayName } : {}),
              ...(photoURL ? { photoURL } : {}),
            });
          }

          const token = await current.getIdToken();
          let res = await sendUpdate(token, payload);
          if (res.status === 401) {
            const fresh = await current.getIdToken(true);
            res = await sendUpdate(fresh, payload);
          }

          if (!res.ok) {
            const txt = await res.text().catch(() => "");
            const canRetryWithoutConsent =
              Object.prototype.hasOwnProperty.call(payload, "analytics_consent") &&
              unsupportedConsentResponsePattern.test(txt || "") &&
              [400, 404, 409, 422, 500].includes(res.status);

            if (!canRetryWithoutConsent) {
              throw new Error(`Backend hibára futott: ${res.status} ${txt}`);
            }

            const { analytics_consent, ...fallbackPayload } = payload;

            if (Object.keys(fallbackPayload).length === 0) {
              const localOnly = {
                ...(get().usrInfo || {}),
                analytics_consent,
              };
              set({
                usrInfo: localOnly,
                fetched: true,
                success: "Profil sikeresen frissítve.",
                loading: false,
              });
              return localOnly;
            }

            let retryRes = await sendUpdate(token, fallbackPayload);
            if (retryRes.status === 401) {
              const fresh = await current.getIdToken(true);
              retryRes = await sendUpdate(fresh, fallbackPayload);
            }

            if (!retryRes.ok) {
              const retryTxt = await retryRes.text().catch(() => "");
              throw new Error(
                `Backend hibára futott: ${retryRes.status} ${retryTxt}`,
              );
            }

            const fallbackData = await retryRes.json();
            const mergedFallback = {
              ...(get().usrInfo || {}),
              ...(fallbackData.data || fallbackData),
              analytics_consent,
            };
            set({
              usrInfo: mergedFallback,
              fetched: true,
              success: "Profil sikeresen frissítve.",
              loading: false,
            });
            return mergedFallback;
          }

          const updatedData = await res.json();
          const merged = {
            ...(get().usrInfo || {}),
            ...(updatedData.data || updatedData),
          };
          if (
            typeof merged.analytics_consent !== "boolean" &&
            typeof payload.analytics_consent === "boolean"
          ) {
            merged.analytics_consent = payload.analytics_consent;
          }
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
        usrInfo: state.usrInfo,
        fetched: state.fetched,
      }),
    },
  ),
);
