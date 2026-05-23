export const showToast = (message, options = {}) => {
  if (typeof window === "undefined") return false;

  const toastFn = window.showToast;
  if (typeof toastFn !== "function") return false;

  try {
    toastFn(message, options);
    return true;
  } catch (error) {
    console.warn("Could not show toast:", error);
    return false;
  }
};

