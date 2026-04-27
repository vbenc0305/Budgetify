const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const PHONE_STRICT_REGEX = /^\+\d+$/;
const DATE_ONLY_REGEX = /^\d{4}-\d{2}-\d{2}$/;

function normalizeText(value) {
  return typeof value === "string" ? value.trim() : "";
}

function getPasswordStrength(password) {
  const normalizedPassword = String(password || "");
  if (!normalizedPassword) return "empty";

  let score = 0;
  if (normalizedPassword.length >= 8) score += 1;
  if (/[a-z]/.test(normalizedPassword) && /[A-Z]/.test(normalizedPassword)) score += 1;
  if (/\d/.test(normalizedPassword)) score += 1;
  if (/[^A-Za-z0-9]/.test(normalizedPassword)) score += 1;

  if (score <= 1) return "weak";
  if (score <= 3) return "medium";
  return "strong";
}

function validateName(name) {
  const normalizedName = normalizeText(name);
  if (!normalizedName) return "A név megadása kötelező.";
  if (normalizedName.length < 2) return "A név túl rövid.";
  return "";
}

function validateEmail(email) {
  const normalizedEmail = normalizeText(email).toLowerCase();
  if (!normalizedEmail) return "Az e-mail megadása kötelező.";
  if (!EMAIL_REGEX.test(normalizedEmail)) return "Adj meg érvényes e-mail címet.";
  return "";
}

function validatePassword(password, { name, email } = {}) {
  const normalizedPassword = String(password || "");
  if (!normalizedPassword) return "A jelszó megadása kötelező.";
  if (normalizedPassword.length < 8) return "A jelszó legyen legalább 8 karakter hosszú.";
  if (!/[a-z]/.test(normalizedPassword)) return "A jelszó tartalmazzon kisbetűt is.";
  if (!/[A-Z]/.test(normalizedPassword)) return "A jelszó tartalmazzon nagybetűt is.";
  if (!/\d/.test(normalizedPassword)) return "A jelszó tartalmazzon számot is.";
  if (!/[^A-Za-z0-9]/.test(normalizedPassword)) {
    return "A jelszó tartalmazzon speciális karaktert is.";
  }

  const loweredPassword = normalizedPassword.toLowerCase();
  const blockedValues = [
    "password",
    "qwerty",
    "123456",
    normalizeText(name).toLowerCase(),
    normalizeText(email).toLowerCase(),
  ].filter(Boolean);

  if (blockedValues.some((value) => value && loweredPassword.includes(value))) {
    return "A jelszó túl könnyen kitalálható, válassz erősebbet.";
  }

  return "";
}

function validatePasswordConfirmation(password, confirmPassword) {
  const normalizedConfirmPassword = String(confirmPassword || "");
  if (!normalizedConfirmPassword) return "A jelszó megerősítése kötelező.";
  if (String(password || "") !== normalizedConfirmPassword) {
    return "A két jelszó nem egyezik.";
  }
  return "";
}

function validatePhone(phone) {
  const normalizedPhone = normalizeText(phone);
  if (!normalizedPhone || normalizedPhone === "+") {
    return "A telefonszám megadása kötelező.";
  }
  if (!PHONE_STRICT_REGEX.test(normalizedPhone)) {
    return "A telefonszám formátuma: + és utána csak számok.";
  }

  const digitsOnly = normalizedPhone.replace(/\D/g, "");
  if (digitsOnly.length < 8 || digitsOnly.length > 15) {
    return "Adj meg egy valós telefonszámot (8-15 számjegy).";
  }

  return "";
}

export function normalizePhoneInput(value) {
  const normalizedValue = normalizeText(value);
  if (!normalizedValue) return "";

  const digitsOnly = normalizedValue.replace(/\D/g, "");
  return `+${digitsOnly}`;
}

function validateBirthdate(birthdate) {
  const normalizedBirthdate = normalizeText(birthdate);
  if (!normalizedBirthdate) return "A születési dátum megadása kötelező.";
  if (!DATE_ONLY_REGEX.test(normalizedBirthdate)) {
    return "Érvényes dátumot adj meg (ÉÉÉÉ-HH-NN).";
  }

  const date = new Date(`${normalizedBirthdate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return "Érvénytelen születési dátum.";

  const [year, month, day] = normalizedBirthdate.split("-").map(Number);
  if (
    date.getFullYear() !== year ||
    date.getMonth() + 1 !== month ||
    date.getDate() !== day
  ) {
    return "Érvénytelen születési dátum.";
  }

  const today = new Date();
  const todayWithoutTime = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate(),
  );

  if (date > todayWithoutTime) {
    return "A születési dátum nem lehet jövőbeli.";
  }

  return "";
}

export function sanitizeRegisterForm(form) {
  return {
    ...form,
    name: normalizeText(form.name),
    email: normalizeText(form.email).toLowerCase(),
    phone: normalizePhoneInput(form.phone),
    birthdate: normalizeText(form.birthdate),
  };
}

export function validateRegisterField(field, form) {
  switch (field) {
    case "name":
      return validateName(form.name);
    case "email":
      return validateEmail(form.email);
    case "password":
      return validatePassword(form.password, { name: form.name, email: form.email });
    case "confirmPassword":
      return validatePasswordConfirmation(form.password, form.confirmPassword);
    case "phone":
      return validatePhone(form.phone);
    case "birthdate":
      return validateBirthdate(form.birthdate);
    default:
      return "";
  }
}

export function validateRegisterForm(form) {
  const errors = {
    name: validateName(form.name),
    email: validateEmail(form.email),
    password: validatePassword(form.password, { name: form.name, email: form.email }),
    confirmPassword: validatePasswordConfirmation(form.password, form.confirmPassword),
    phone: validatePhone(form.phone),
    birthdate: validateBirthdate(form.birthdate),
  };

  return {
    errors,
    isValid: Object.values(errors).every((value) => !value),
    passwordStrength: getPasswordStrength(form.password),
  };
}


