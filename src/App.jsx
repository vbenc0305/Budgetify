// src/App.jsx
import React, { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Login from "./pages/Login.jsx";
import { AuthProvider } from "./contexts/AuthContext.jsx";
import Register from "./pages/Register.jsx";
import ProfilePage from "./pages/Profile.jsx";
import { useUser } from "./stores/useUser";
import { useTransaction } from "./stores/useTransaction.js";
import Transactions from "./pages/Transactions.jsx"; // <-- zustand store import
import Statistics from "./pages/Statistics.jsx";
import CountyInsights from "./pages/CountyInsights.jsx";
import ToastContainer from "./components/ToastContainer";

function App() {
  useEffect(() => {
    window.useUser = useUser;
    window.useTransaction = useTransaction;

    // egyszer csatoljuk az auth listener-t, és visszakapjuk az unsubscribe függvényt
    const unsubscribe = useUser.getState().initAuthListener();
    return () => {
      if (typeof unsubscribe === "function") unsubscribe();
    };
  }, []);

  return (
    <Router>
      <AuthProvider>
        <Navbar />
        <ToastContainer />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/predict" element={<Statistics />} />
            <Route path="/county-insights" element={<CountyInsights />} />
          </Routes>
        </main>
      </AuthProvider>
    </Router>
  );
}

export default App;
