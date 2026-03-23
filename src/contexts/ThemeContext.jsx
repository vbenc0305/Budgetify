import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const THEME_STORAGE_KEY = "budgetify-theme-preference";
const VALID_THEMES = new Set(["light", "dark", "system"]);

const ThemeContext = createContext(null);

const getSystemTheme = () => {
  if (
    typeof window === "undefined" ||
    typeof window.matchMedia !== "function"
  ) {
    return "light";
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

const sanitizeThemePreference = (value) => {
  if (!value) return "system";
  return VALID_THEMES.has(value) ? value : "system";
};

const applyThemeToDocument = (themePreference) => {
  const resolvedTheme =
    themePreference === "system" ? getSystemTheme() : themePreference;

  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", resolvedTheme);
    document.documentElement.style.colorScheme = resolvedTheme;
  }

  return resolvedTheme;
};

export function ThemeProvider({ children }) {
  const [themePreference, setThemePreference] = useState(() => {
    if (typeof window === "undefined") return "system";

    try {
      return sanitizeThemePreference(
        window.localStorage.getItem(THEME_STORAGE_KEY),
      );
    } catch {
      return "system";
    }
  });

  const [resolvedTheme, setResolvedTheme] = useState(() =>
    applyThemeToDocument(themePreference),
  );

  useEffect(() => {
    const nextResolvedTheme = applyThemeToDocument(themePreference);
    setResolvedTheme(nextResolvedTheme);

    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, themePreference);
    } catch {
      // Ignore persistence failures (private mode / storage restrictions).
    }

    if (themePreference !== "system" || typeof window.matchMedia !== "function")
      return undefined;

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      setResolvedTheme(applyThemeToDocument("system"));
    };

    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }

    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, [themePreference]);

  const value = useMemo(
    () => ({
      themePreference,
      resolvedTheme,
      setThemePreference,
      toggleTheme: () => {
        setThemePreference((previousTheme) => {
          if (previousTheme === "system")
            return getSystemTheme() === "dark" ? "light" : "dark";
          return previousTheme === "dark" ? "light" : "dark";
        });
      },
    }),
    [themePreference, resolvedTheme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }

  return context;
}
