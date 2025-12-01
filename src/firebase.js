import { initializeApp } from "firebase/app";
import { getAuth, setPersistence, browserLocalPersistence } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
    apiKey: "AIzaSyAYjIk3JC_yZbbXy7VSwTDfZvIX0Av7S0o",
    authDomain: "penzugyielemzo-3ba77.firebaseapp.com",
    projectId: "penzugyielemzo-3ba77",
    storageBucket: "penzugyielemzo-3ba77.firebasestorage.app",
    messagingSenderId: "678708418375",
    appId: "1:678708418375:web:ceb3078ffc6100c18a9e62",
    measurementId: "G-0CXYFRN2R6"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// Export a promise that resolves when persistence is set
const persistencePromise = setPersistence(auth, browserLocalPersistence);

export { auth, db, persistencePromise };
