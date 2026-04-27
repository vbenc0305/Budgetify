import test from "node:test";
import assert from "node:assert/strict";

import {
  normalizePhoneInput,
  sanitizeRegisterForm,
  validateRegisterField,
  validateRegisterForm,
} from "../src/utils/registerValidation.js";

const validForm = {
  name: "Teszt Elek",
  email: "teszt@example.com",
  password: "Abcd1234!",
  confirmPassword: "Abcd1234!",
  phone: "+36301234567",
  birthdate: "1995-05-20",
};

test("validateRegisterForm: valid form passes", () => {
  const result = validateRegisterForm(validForm);
  assert.equal(result.isValid, true);
  assert.equal(Object.values(result.errors).every((value) => !value), true);
});

test("validateRegisterForm: empty required fields fail", () => {
  const result = validateRegisterForm({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    phone: "",
    birthdate: "",
  });

  assert.equal(result.isValid, false);
  assert.ok(result.errors.name);
  assert.ok(result.errors.email);
  assert.ok(result.errors.password);
  assert.ok(result.errors.confirmPassword);
  assert.ok(result.errors.phone);
  assert.ok(result.errors.birthdate);
});

test("validateRegisterField: invalid email is rejected", () => {
  const error = validateRegisterField("email", {
    ...validForm,
    email: "rossz-email-format",
  });

  assert.equal(error, "Adj meg érvényes e-mail címet.");
});

test("validateRegisterField: weak password is rejected", () => {
  const error = validateRegisterField("password", {
    ...validForm,
    password: "abcd1234",
  });

  assert.equal(error, "A jelszó tartalmazzon nagybetűt is.");
});

test("validateRegisterField: password mismatch is rejected", () => {
  const error = validateRegisterField("confirmPassword", {
    ...validForm,
    confirmPassword: "Abcd1234?",
  });

  assert.equal(error, "A két jelszó nem egyezik.");
});

test("validateRegisterField: invalid phone is rejected", () => {
  const error = validateRegisterField("phone", {
    ...validForm,
    phone: "+36abc",
  });

  assert.equal(error, "A telefonszám formátuma: + és utána csak számok.");
});

test("validateRegisterField: phone without plus is rejected", () => {
  const error = validateRegisterField("phone", {
    ...validForm,
    phone: "36301234567",
  });

  assert.equal(error, "A telefonszám formátuma: + és utána csak számok.");
});

test("validateRegisterField: future birthdate is rejected", () => {
  const nextYear = new Date().getFullYear() + 1;
  const error = validateRegisterField("birthdate", {
    ...validForm,
    birthdate: `${nextYear}-01-01`,
  });

  assert.equal(error, "A születési dátum nem lehet jövőbeli.");
});

test("sanitizeRegisterForm: trims relevant values", () => {
  const sanitized = sanitizeRegisterForm({
    ...validForm,
    name: "  Teszt Elek  ",
    email: "  TESZT@EXAMPLE.COM ",
    phone: "  +36 30 123 4567  ",
    birthdate: " 1995-05-20 ",
  });

  assert.equal(sanitized.name, "Teszt Elek");
  assert.equal(sanitized.email, "teszt@example.com");
  assert.equal(sanitized.phone, "+36301234567");
  assert.equal(sanitized.birthdate, "1995-05-20");
});

test("normalizePhoneInput: keeps plus and digits only", () => {
  assert.equal(normalizePhoneInput("+36 30 abc-12"), "+363012");
  assert.equal(normalizePhoneInput("36301234567"), "+36301234567");
  assert.equal(normalizePhoneInput(""), "");
});

