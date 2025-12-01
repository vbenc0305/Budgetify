// src/utils/firebaseErrorHandler.js
export function getFirebaseErrorMessage(errorCode) {
    switch (errorCode) {
        // Auth hibakódok:
        case "auth/email-already-in-use":
            return "Ez az email már használatban van.";
        case "auth/invalid-email":
            return "A megadott email cím formátuma helytelen.";
        case "auth/operation-not-allowed":
            return "A regisztráció jelenleg nem engedélyezett.";
        case "auth/weak-password":
            return "A jelszó túl gyenge. Legalább 6 karakter legyen.";
        case "auth/network-request-failed":
            return "Hálózati hiba: ellenőrizd az internetkapcsolatot!";
        case "auth/user-disabled":
            return "A felhasználó fiókja le van tiltva. Fordulj az ügyfélszolgálathoz.";
        case "auth/user-not-found":
            return "Ilyen email-címmel nem található felhasználó.";
        case "auth/wrong-password":
            return "Hibás jelszó.";
        case "auth/too-many-requests":
            return "Túl sok sikertelen próbálkozás. Kérlek, próbáld később.";

        // Firestore hibák:
        case "permission-denied":
            return "Nincs jogosultság az adatbázis művelethez.";
        case "unavailable":
            return "Adatbázis jelenleg nem elérhető, próbáld később!";
        case "deadline-exceeded":
            return "Az adatbázis-kérés túl sokáig tartott, próbáld újra.";
        case "internal":
            return "Belső hiba történt, kérlek próbáld később!";

        // Alapértelmezett hibaüzenet
        default:
            return "Valami hiba történt: " + errorCode;
    }
}
