import test from "node:test";
import assert from "node:assert/strict";

import { getFirebaseErrorMessage } from "../src/utils/firebaseErrorHandler.js";

test("getFirebaseErrorMessage: invalid credential uses friendly login text", () => {
  assert.equal(
    getFirebaseErrorMessage("auth/invalid-credential"),
    "Hibás email vagy jelszó.",
  );
});

test("getFirebaseErrorMessage: wrong password and unknown user use the same generic login text", () => {
  assert.equal(
    getFirebaseErrorMessage("auth/wrong-password"),
    "Hibás email vagy jelszó.",
  );
  assert.equal(
    getFirebaseErrorMessage("auth/user-not-found"),
    "Hibás email vagy jelszó.",
  );
});

test("getFirebaseErrorMessage: recent login requirement uses password change guidance", () => {
  assert.equal(
    getFirebaseErrorMessage("auth/requires-recent-login"),
    "A jelszó módosításához biztonsági okból jelentkezz be újra.",
  );
});

test("getFirebaseErrorMessage: unknown codes do not expose raw Firebase internals", () => {
  assert.equal(
    getFirebaseErrorMessage("auth/some-new-error"),
    "Valami hiba történt. Kérlek, próbáld újra később.",
  );
});

