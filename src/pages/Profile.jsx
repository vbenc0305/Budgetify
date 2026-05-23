import { useEffect, useState } from "react";
import { updatePassword } from "firebase/auth";
import { useNavigate } from "react-router-dom";
import { useUser } from "../stores/useUser";
import { auth } from "../firebase";
import { getFirebaseErrorMessage } from "../utils/firebaseErrorHandler";
import { validateRegisterField } from "../utils/registerValidation";
import "../pages/styles/Profile.css";

const EDUCATION_OPTIONS = [
  "Általános 8. osztály",
  "Szakiskola / Képesítő bizonyítvány",
  "Érettségi / Gimnázium",
  "Érettségi + Szakképesítés",
  "Technikumi végzettség",
  "Felsőfokú szakképzés (FOKSZ)",
  "Főiskolai diploma / BA, BSc",
  "Egyetemi diploma / MA, MSc",
  "Kétszakos mesterképzés",
  "Egységes, osztatlan mesterképzés",
  "Doktori (Ph.D./DLA) fokozat",
  "Habilitáció",
  "Posztgraduális szakképzés",
  "Nincs befejezett végzettség",
  "Ismeretlen / Nem kíván válaszolni",
];

const INITIAL_PASSWORD_FORM = {
  newPassword: "",
  confirmNewPassword: "",
};

const createProfileFormData = (usrInfo) => ({
  name: usrInfo?.name || "",
  email: usrInfo?.email || "",
  phone: usrInfo?.phone || "",
  birthdate: usrInfo?.birthdate || "",
  age: usrInfo?.age || "",
  country: usrInfo?.country || "",
  education: usrInfo?.education || "",
  gender: usrInfo?.gender || "",
  housing_status: usrInfo?.housing_status || "",
  marital_status: usrInfo?.marital_status || "",
  occupation: usrInfo?.occupation || "",
  analytics_consent: Boolean(usrInfo?.analytics_consent),
});


export default function ProfilePage() {
  const navigate = useNavigate();
  const usrInfo = useUser((state) => state.usrInfo);
  const loading = useUser((state) => state.loading);
  const error = useUser((state) => state.error);
  const success = useUser((state) => state.success);
  const updateProfile = useUser((state) => state.updateProfile);
  const deleteAccountProfile = useUser((state) => state.deleteAccountProfile);

  const [isEditMode, setIsEditMode] = useState(false);
  const [formData, setFormData] = useState({});
  const [countryOptions, setCountryOptions] = useState([]);
  const [showConsentHelp, setShowConsentHelp] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isPasswordFormVisible, setIsPasswordFormVisible] = useState(false);
  const [passwordForm, setPasswordForm] = useState(INITIAL_PASSWORD_FORM);
  const [passwordTouched, setPasswordTouched] = useState({});
  const [passwordErrors, setPasswordErrors] = useState({});
  const [passwordSubmitAttempted, setPasswordSubmitAttempted] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isDeleteConfirmVisible, setIsDeleteConfirmVisible] = useState(false);
  const [deleteAccountError, setDeleteAccountError] = useState("");
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);

  // Initialize form data from usrInfo
  useEffect(() => {
    if (usrInfo) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- preserve the existing store-to-form hydration semantics during profile loading.
      setFormData(createProfileFormData(usrInfo));
    }
  }, [usrInfo]);

  // Fetch country options
  useEffect(() => {
    let mounted = true;

    async function fetchCountries() {
      try {
        const res = await fetch(
          "https://restcountries.com/v3.1/all?fields=translations,name"
        );
        if (!res.ok) throw new Error("Hiba az országlista lekérésekor");
        const data = await res.json();
        const options = data
          .map((c) => c.translations?.hun?.common ?? c.name.common)
          .filter((name) => typeof name === "string")
          .filter((v, i, a) => a.indexOf(v) === i)
          .sort((a, b) => String(a).localeCompare(String(b), "hu"));

        if (mounted) setCountryOptions(options);
      } catch (err) {
        console.error("Hiba a countryOptions lekérésekor:", err);
        if (mounted)
          setCountryOptions(["Magyarország", "USA", "Németország", "Ausztria"]);
      }
    }

    fetchCountries();
    return () => {
      mounted = false;
    };
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const getPasswordValidationErrors = (nextPasswordForm = passwordForm) => {
    const validationSource = {
      name: formData.name || usrInfo?.name || "",
      email: formData.email || usrInfo?.email || "",
      password: nextPasswordForm.newPassword,
      confirmPassword: nextPasswordForm.confirmNewPassword,
    };

    return {
      newPassword: validateRegisterField("password", validationSource),
      confirmNewPassword: validateRegisterField("confirmPassword", validationSource),
    };
  };

  const visiblePasswordErrors = {
    newPassword:
      (passwordSubmitAttempted || passwordTouched.newPassword) && passwordErrors.newPassword
        ? passwordErrors.newPassword
        : "",
    confirmNewPassword:
      (passwordSubmitAttempted || passwordTouched.confirmNewPassword) &&
      passwordErrors.confirmNewPassword
        ? passwordErrors.confirmNewPassword
        : "",
  };

  const resetPasswordFormState = ({ keepSuccess = false } = {}) => {
    setPasswordForm(INITIAL_PASSWORD_FORM);
    setPasswordTouched({});
    setPasswordErrors({});
    setPasswordSubmitAttempted(false);
    setPasswordError("");

    if (!keepSuccess) {
      setPasswordSuccess("");
    }
  };

  const resetDeleteAccountState = () => {
    setIsDeleteConfirmVisible(false);
    setDeleteAccountError("");
    setIsDeletingAccount(false);
  };

  const handleEditClick = () => {
    setIsEditMode(true);
  };

  const handleCancelClick = () => {
    setIsEditMode(false);
    setIsPasswordFormVisible(false);
    resetPasswordFormState();
    resetDeleteAccountState();
    if (usrInfo) {
      setFormData(createProfileFormData(usrInfo));
    }
  };

  const handlePasswordToggle = () => {
    if (isPasswordFormVisible) {
      resetPasswordFormState({ keepSuccess: true });
    } else {
      setPasswordError("");
      setPasswordSuccess("");
    }

    setIsPasswordFormVisible((prev) => !prev);
  };

  const handlePasswordInputChange = (e) => {
    const { name, value } = e.target;
    const nextPasswordForm = {
      ...passwordForm,
      [name]: value,
    };

    setPasswordForm(nextPasswordForm);
    setPasswordError("");
    setPasswordSuccess("");

    if (
      passwordSubmitAttempted ||
      passwordTouched[name] ||
      (name === "newPassword" && passwordTouched.confirmNewPassword)
    ) {
      setPasswordErrors(getPasswordValidationErrors(nextPasswordForm));
    }
  };

  const handlePasswordBlur = (e) => {
    const { name } = e.target;
    setPasswordTouched((prev) => ({
      ...prev,
      [name]: true,
    }));
    setPasswordErrors(getPasswordValidationErrors(passwordForm));
  };

  const handlePasswordCancel = () => {
    resetPasswordFormState({ keepSuccess: true });
    setIsPasswordFormVisible(false);
  };

  const handleDeleteAccountToggle = () => {
    setDeleteAccountError("");
    setIsDeleteConfirmVisible((prev) => !prev);
  };

  const handleDeleteAccountCancel = () => {
    if (isDeletingAccount) {
      return;
    }

    setIsDeleteConfirmVisible(false);
    setDeleteAccountError("");
  };

  const handleDeleteAccountConfirm = async () => {
    setDeleteAccountError("");
    setIsDeletingAccount(true);

    try {
      const { deletionPromise } = await deleteAccountProfile();

      navigate("/login", { replace: true });

      void deletionPromise.catch((err) => {
        console.error("Profiltörlés kijelentkezés után sikertelen:", err);
      });
    } catch (err) {
      console.error("Hiba a fiók törlésekor:", err);
      setDeleteAccountError(
        getFirebaseErrorMessage(err?.code) ||
          err?.message ||
          "A fiók törlése nem sikerült.",
      );
      setIsDeletingAccount(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordError("");
    setPasswordSuccess("");
    setPasswordSubmitAttempted(true);
    setPasswordTouched({
      newPassword: true,
      confirmNewPassword: true,
    });

    const nextErrors = getPasswordValidationErrors(passwordForm);
    setPasswordErrors(nextErrors);

    if (Object.values(nextErrors).some(Boolean)) {
      return;
    }

    setIsChangingPassword(true);

    try {
      const currentUser = auth.currentUser;

      if (!currentUser) {
        setPasswordError("Nem található bejelentkezett felhasználó.");
        return;
      }

      await updatePassword(currentUser, passwordForm.newPassword);
      resetPasswordFormState({ keepSuccess: false });
      setPasswordSuccess("A jelszó sikeresen módosítva lett.");
      setIsPasswordFormVisible(false);
    } catch (err) {
      console.error("Hiba a jelszó módosításakor:", err);
      setPasswordError(
        getFirebaseErrorMessage(err?.code) ||
          err?.message ||
          "A jelszó módosítása nem sikerült.",
      );
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleSaveClick = async () => {
    setIsSaving(true);
    try {
      const updateData = {};
      let hasChanges = false;

      // Only include fields that have actually changed
      Object.keys(formData).forEach((key) => {
        const currentValue = formData[key];
        const originalValue = key === "analytics_consent"
          ? Boolean(usrInfo?.analytics_consent)
          : usrInfo?.[key] || "";

        if (currentValue !== originalValue) {
          if (currentValue !== "" && currentValue !== null) {
            updateData[key] = currentValue;
            hasChanges = true;
          }
        }
      });

      if (hasChanges) {
        await updateProfile(updateData);
      }

      setIsEditMode(false);
      setIsPasswordFormVisible(false);
      resetPasswordFormState();
      resetDeleteAccountState();
    } catch (err) {
      console.error("Hiba a profil mentésekor:", err);
    } finally {
      setIsSaving(false);
    }
  };
  if (loading) {
    return (
      <div className="profile-container">
        <h2>Betöltés...</h2>
      </div>
    );
  }
  if (!usrInfo) {
    return (
      <div className="profile-container">
        <h2>Nincs profil adat.</h2>
      </div>
    );
  }

  return (
    <div className="profile-container">
      <h1>Profilom</h1>

      {/* Error / Success Messages */}
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
      {success && (
        <p className="success-text" role="status">
          {success}
        </p>
      )}

      <div className="profile-card">
        {/* Edit/Cancel/Save Button Group */}
        <div className="profile-button-group">
          {!isEditMode ? (
            <button className="profile-edit-button" onClick={handleEditClick}>
              Szerkesztés
            </button>
          ) : (
            <>
              <button
                className="profile-save-button"
                onClick={handleSaveClick}
                disabled={isSaving || isDeletingAccount}
              >
                {isSaving ? "Mentés..." : "Mentés"}
              </button>
              <button
                className="profile-cancel-button"
                onClick={handleCancelClick}
                disabled={isSaving || isDeletingAccount}
              >
                Mégse
              </button>
            </>
          )}
        </div>

        {/* View Mode */}
        {!isEditMode && (
          <div className="profile-view-mode">
            <div className="profile-section">
              <h3>Alap adatok</h3>
              <div className="profile-row">
                <span className="profile-label">Név:</span>
                <span className="profile-value">{formData.name || "-"}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Email:</span>
                <span className="profile-value">{formData.email || "-"}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Telefonszám:</span>
                <span className="profile-value">{formData.phone || "-"}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Születési dátum:</span>
                <span className="profile-value">{formData.birthdate || "-"}</span>
              </div>
            </div>

            <div className="profile-section">
              <h3>Bővebb adatok</h3>
              <div className="profile-row">
                <span className="profile-label">Életkor:</span>
                <span className="profile-value">{formData.age || "-"}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Ország:</span>
                <span className="profile-value">{formData.country || "-"}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Iskolai végzettség:</span>
                <span className="profile-value">{formData.education || "-"}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Nem:</span>
                <span className="profile-value">{formData.gender || "-"}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Lakhatási státusz:</span>
                <span className="profile-value">{formData.housing_status || "-"}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Családi állapot:</span>
                <span className="profile-value">{formData.marital_status || "-"}</span>
              </div>
              <div className="profile-row">
                <span className="profile-label">Foglalkozás:</span>
                <span className="profile-value">{formData.occupation || "-"}</span>
              </div>
            </div>

            <div className="profile-section">
              <h3>Beállítások</h3>
              <div className="profile-consent-view">
                <label className="consent-status">
                  <span className="consent-label">Anonim statisztika:</span>
                  <span
                    className={`consent-value ${
                      formData.analytics_consent ? "enabled" : "disabled"
                    }`}
                  >
                    {formData.analytics_consent ? "Engedélyezve" : "Letiltva"}
                  </span>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Edit Mode */}
        {isEditMode && (
          <form className="profile-edit-form">
            <div className="profile-section">
              <h3>Alap adatok</h3>

              <div className="form-group">
                <label htmlFor="name">Név:</label>
                <input
                  id="name"
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="email">Email:</label>
                <input
                  id="email"
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  disabled
                />
              </div>

              <div className="form-group">
                <label htmlFor="phone">Telefonszám:</label>
                <input
                  id="phone"
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="birthdate">Születési dátum:</label>
                <input
                  id="birthdate"
                  type="date"
                  name="birthdate"
                  value={formData.birthdate}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div className="profile-section">
              <h3>Bővebb adatok</h3>

              <div className="form-group">
                <label htmlFor="age">Életkor:</label>
                <input
                  id="age"
                  type="number"
                  name="age"
                  value={formData.age}
                  onChange={handleChange}
                  min={0}
                />
              </div>

              <div className="form-group">
                <label htmlFor="country">Ország:</label>
                <input
                  id="country"
                  type="text"
                  name="country"
                  list="countries"
                  value={formData.country}
                  onChange={handleChange}
                  placeholder="Kezdd el gépelni az ország nevét..."
                />
                <datalist id="countries">
                  {countryOptions.map((country) => (
                    <option key={country} value={country} />
                  ))}
                </datalist>
              </div>

              <div className="form-group">
                <label htmlFor="education">Iskolai végzettség:</label>
                <select
                  id="education"
                  name="education"
                  value={formData.education}
                  onChange={handleChange}
                >
                  <option value="">Válassz végzettségi szintet...</option>
                  {EDUCATION_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="gender">Nem:</label>
                <select
                  id="gender"
                  name="gender"
                  value={formData.gender}
                  onChange={handleChange}
                >
                  <option value="">Válassz…</option>
                  <option value="Férfi">Férfi</option>
                  <option value="Nő">Nő</option>
                  <option value="Egyéb">Egyéb</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="housing_status">Lakhatási státusz:</label>
                <select
                  id="housing_status"
                  name="housing_status"
                  value={formData.housing_status}
                  onChange={handleChange}
                >
                  <option value="">Válassz…</option>
                  <option value="Saját tulajdonú lakás">Saját tulajdonú lakás</option>
                  <option value="Bérlakás">Bérlakás</option>
                  <option value="Albérlet">Albérlet</option>
                  <option value="Önálló ház">Önálló ház</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="marital_status">Családi állapot:</label>
                <select
                  id="marital_status"
                  name="marital_status"
                  value={formData.marital_status}
                  onChange={handleChange}
                >
                  <option value="">Válassz…</option>
                  <option value="Egyedülálló">Egyedülálló</option>
                  <option value="Házas">Házas</option>
                  <option value="Élettársi kapcsolat">Élettársi kapcsolat</option>
                  <option value="Elvált">Elvált</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="occupation">Foglalkozás:</label>
                <input
                  id="occupation"
                  type="text"
                  name="occupation"
                  value={formData.occupation}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div className="profile-section">
              <h3>Beállítások</h3>

              <fieldset className="profile-consent-edit-block">
                <legend>Anonim statisztika</legend>

                <label
                  className="profile-consent-checkbox-label"
                  htmlFor="analytics-consent-edit"
                >
                  <input
                    id="analytics-consent-edit"
                    type="checkbox"
                    name="analytics_consent"
                    checked={formData.analytics_consent}
                    onChange={handleChange}
                    aria-describedby="consent-helper-edit"
                  />
                  <span>Engedélyezem, hogy a kiadási adataimból anonim statisztika készüljön.</span>
                </label>

                <p id="consent-helper-edit" className="profile-consent-helper-text">
                  Ez segít a szolgáltatás fejlesztésében, és később bármikor visszavonható.
                </p>

                <button
                  type="button"
                  className="profile-consent-help-toggle"
                  onClick={() => setShowConsentHelp((prev) => !prev)}
                  aria-expanded={showConsentHelp}
                  aria-controls="consent-extra-edit"
                >
                  Miért kérjük ezt?
                </button>

                {showConsentHelp && (
                  <p id="consent-extra-edit" className="profile-consent-extra-info" role="status">
                    A hozzájárulás csak összesített, anonim trendekhez használható, személyes
                    azonosítás nélkül.
                  </p>
                )}
              </fieldset>
            </div>
          </form>
        )}

        {isEditMode && (
          <div className="profile-section profile-password-section">
            <div className="profile-password-header">
              <div>
                <h3>Jelszó módosítása</h3>
                <p className="profile-password-description">
                  Add meg kétszer az új jelszavad a módosításhoz.
                </p>
              </div>

              {!isPasswordFormVisible ? (
                <button
                  type="button"
                  className="profile-password-toggle-button"
                  onClick={handlePasswordToggle}
                  disabled={isChangingPassword || isDeletingAccount}
                >
                  Jelszó cseréje
                </button>
              ) : null}
            </div>

            {passwordError && (
              <p className="profile-inline-error-text" role="alert">
                {passwordError}
              </p>
            )}

            {passwordSuccess && (
              <p className="profile-inline-success-text" role="status">
                {passwordSuccess}
              </p>
            )}

            {isPasswordFormVisible && (
              <form className="profile-password-form" onSubmit={handlePasswordSubmit} noValidate>
                <div className="form-group">
                  <label htmlFor="newPassword">Új jelszó:</label>
                  <input
                    id="newPassword"
                    type="password"
                    name="newPassword"
                    value={passwordForm.newPassword}
                    onChange={handlePasswordInputChange}
                    onBlur={handlePasswordBlur}
                    autoComplete="new-password"
                    placeholder="Adj meg egy új, erős jelszót"
                    aria-invalid={Boolean(visiblePasswordErrors.newPassword)}
                    aria-describedby={`new-password-helper${
                      visiblePasswordErrors.newPassword ? " new-password-error" : ""
                    }`}
                  />
                  <p id="new-password-helper" className="profile-password-helper-text">
                    Legalább 8 karakter, kis- és nagybetű, szám, valamint speciális karakter.
                  </p>
                  {visiblePasswordErrors.newPassword && (
                    <p id="new-password-error" className="profile-field-error-text" role="alert">
                      {visiblePasswordErrors.newPassword}
                    </p>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="confirmNewPassword">Új jelszó újra:</label>
                  <input
                    id="confirmNewPassword"
                    type="password"
                    name="confirmNewPassword"
                    value={passwordForm.confirmNewPassword}
                    onChange={handlePasswordInputChange}
                    onBlur={handlePasswordBlur}
                    autoComplete="new-password"
                    placeholder="Írd be újra az új jelszót"
                    aria-invalid={Boolean(visiblePasswordErrors.confirmNewPassword)}
                    aria-describedby={
                      visiblePasswordErrors.confirmNewPassword
                        ? "confirm-new-password-error"
                        : undefined
                    }
                  />
                  {visiblePasswordErrors.confirmNewPassword && (
                    <p
                      id="confirm-new-password-error"
                      className="profile-field-error-text"
                      role="alert"
                    >
                      {visiblePasswordErrors.confirmNewPassword}
                    </p>
                  )}
                </div>

                <div className="profile-password-actions">
                  <button
                    type="submit"
                    className="profile-save-button"
                    disabled={isChangingPassword || isDeletingAccount}
                  >
                    {isChangingPassword ? "Jelszó mentése..." : "Új jelszó mentése"}
                  </button>
                  <button
                    type="button"
                    className="profile-secondary-button"
                    onClick={handlePasswordCancel}
                    disabled={isChangingPassword || isDeletingAccount}
                  >
                    Mégse
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {isEditMode && (
          <div className="profile-section profile-danger-section">
            <div className="profile-danger-header">
              <div>
                <h3>Fiók törlése</h3>
                <p className="profile-danger-description">
                  A megerősítés után kijelentkeztetünk, átirányítunk a bejelentkezéshez,
                  majd töröljük a profilodat.
                </p>
              </div>

              {!isDeleteConfirmVisible ? (
                <button
                  type="button"
                  className="profile-danger-button"
                  onClick={handleDeleteAccountToggle}
                  disabled={isSaving || isChangingPassword || isDeletingAccount}
                >
                  Fiók törlése
                </button>
              ) : null}
            </div>

            {deleteAccountError && (
              <p className="profile-inline-error-text" role="alert">
                {deleteAccountError}
              </p>
            )}

            {isDeleteConfirmVisible && (
              <div className="profile-danger-confirmation" role="alert">
                <p className="profile-danger-confirmation-text">
                  Biztosan törölni szeretnéd a fiókodat? Ez a művelet nem vonható vissza.
                </p>

                <div className="profile-password-actions">
                  <button
                    type="button"
                    className="profile-danger-button"
                    onClick={handleDeleteAccountConfirm}
                    disabled={isDeletingAccount}
                  >
                    {isDeletingAccount ? "Fiók törlése..." : "Igen, törlöm a fiókom"}
                  </button>
                  <button
                    type="button"
                    className="profile-secondary-button"
                    onClick={handleDeleteAccountCancel}
                    disabled={isDeletingAccount}
                  >
                    Mégsem
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
