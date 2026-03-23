import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";
import { persistencePromise } from "./firebase";
import { ThemeProvider } from "./contexts/ThemeContext.jsx";

persistencePromise.then(() => {
  createRoot(document.getElementById("root")).render(
    <StrictMode>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </StrictMode>,
  );
});
