function normalizeText(value) {
  return typeof value === "string" ? value.trim() : "";
}

export function normalizeAgeInput(value) {
  const normalizedValue = normalizeText(String(value ?? ""));
  return normalizedValue.replace(/\D/g, "").slice(0, 3);
}

export function validateAge(ageValue) {
  const normalizedAge = normalizeAgeInput(ageValue);

  if (!normalizedAge) return "Az életkor megadása kötelező.";

  const age = Number(normalizedAge);
  if (!Number.isInteger(age)) return "Az életkor csak szám lehet.";
  if (age < 0 || age > 120) return "Az életkornak 0 és 120 között kell lennie.";

  return "";
}

export function toAgePayloadValue(ageValue) {
  const error = validateAge(ageValue);
  if (error) return null;
  return Number(normalizeAgeInput(ageValue));
}

