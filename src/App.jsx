import { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Login from "./pages/Login.jsx";
import { AuthProvider } from "./contexts/AuthContext.jsx";
import Register from "./pages/Register.jsx";
import ProfilePage from "./pages/Profile.jsx";
import { useUser } from "./stores/useUser";
import Transactions from "./pages/Transactions.jsx";
import Statistics from "./pages/Statistics.jsx";
import CountyInsights from "./pages/CountyInsights.jsx";
import ToastContainer from "./components/ToastContainer";

function App() {
  useEffect(() => {
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
