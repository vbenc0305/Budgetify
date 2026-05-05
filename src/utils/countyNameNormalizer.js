import { HUNGARIAN_COUNTIES } from "../constants/hungarianCounties";

const normalizeCountyKey = (value) =>
  String(value ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]/g, "");

const canonicalCountyByKey = new Map(
  HUNGARIAN_COUNTIES.map((countyName) => [normalizeCountyKey(countyName), countyName]),
);

const countyAliases = {
  bcskiskun: "Bács-Kiskun",
  bks: "Békés",
  borsodabajzempln: "Borsod-Abaúj-Zemplén",
  csongrd: "Csongrád-Csanád",
  fejr: "Fejér",
  hajdbihar: "Hajdú-Bihar",
  jsznagykunszolnok: "Jász-Nagykun-Szolnok",
  komromesztergom: "Komárom-Esztergom",
  ngrd: "Nógrád",
  szabolcsszatmrbereg: "Szabolcs-Szatmár-Bereg",
  veszprm: "Veszprém",
};

export const canonicalizeCountyName = (rawName) => {
  const key = normalizeCountyKey(rawName);
  if (!key) return "";

  const aliasMatch = countyAliases[key];
  if (aliasMatch) return aliasMatch;

  return canonicalCountyByKey.get(key) || "";
};

export const countyToApiSlug = (countyName) => normalizeCountyKey(countyName);

