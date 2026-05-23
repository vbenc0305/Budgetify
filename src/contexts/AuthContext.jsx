import { useEffect, useState } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "../firebase";
import { useUser } from "../stores/useUser";

export const AuthProvider = ({ children }) => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    return onAuthStateChanged(auth, (user) => {
      setLoading(false);
      useUser.setState({ authChecked: true, user: user ?? null });
    });
  }, []);
  return !loading ? children : null;
};

