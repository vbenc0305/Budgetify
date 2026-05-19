import { getAuth } from "firebase/auth";
import { countyToApiSlug } from "./countyNameNormalizer";

const hasTokenMethod = (candidate) =>
  !!candidate && typeof candidate.getIdToken === "function";

const resolveActiveUser = (candidateUser) => {
  if (hasTokenMethod(candidateUser)) return candidateUser;

  const currentUser = getAuth().currentUser;
  return hasTokenMethod(currentUser) ? currentUser : null;
};

const fetchWithAuthRetry = async (url, user) => {
  const activeUser = resolveActiveUser(user);
  if (!activeUser) {
	throw new Error("Nincs bejelentkezett user.");
  }

  let token = await activeUser.getIdToken();
  let response = await fetch(url, {
	method: "GET",
	headers: {
	  "Content-Type": "application/json",
	  Authorization: `Bearer ${token}`,
	},
  });

  if (response.status === 401) {
	token = await activeUser.getIdToken(true);
	response = await fetch(url, {
	  method: "GET",
	  headers: {
		"Content-Type": "application/json",
		Authorization: `Bearer ${token}`,
	  },
	});
  }

  return response;
};

export const fetchCountyCategoryAnalytics = async (county, user) => {
  const normalizedCounty = String(county ?? "").trim();
  if (!normalizedCounty) {
	throw new Error("A megye megadása kötelező.");
  }

  const countySlug = countyToApiSlug(normalizedCounty);
  const candidateUrls = [
	`/api/stats/counties/${encodeURIComponent(normalizedCounty)}/categories`,
	countySlug
	  ? `/api/stats/counties/${encodeURIComponent(countySlug)}/categories`
	  : null,
	`/stats/counties/${encodeURIComponent(normalizedCounty)}/categories`,
	countySlug
	  ? `/stats/counties/${encodeURIComponent(countySlug)}/categories`
	  : null,
  ].filter(Boolean);

  let response = null;

  for (const url of candidateUrls) {
	const candidateResponse = await fetchWithAuthRetry(url, user);
	if (candidateResponse.status === 404) {
	  continue;
	}

	response = candidateResponse;
	break;
  }

  if (!response) {
	throw new Error(
	  `Megyei adatok lekérése sikertelen: 404 Nem található a megyei statisztika végpont (${normalizedCounty}).`,
	);
	}

  if (!response.ok) {
	const text = await response.text().catch(() => "");
	throw new Error(`Megyei adatok lekérése sikertelen: ${response.status} ${text}`);
  }

  const data = await response.json();

  return {
	county: data?.county ?? normalizedCounty,
	matchedUsers: Number(data?.matched_users ?? 0),
	transactionCount: Number(data?.transaction_count ?? 0),
	transactions: Array.isArray(data?.transactions) ? data.transactions : [],
	dataSource: data?.data_source ?? "ismeretlen",
  };
};


