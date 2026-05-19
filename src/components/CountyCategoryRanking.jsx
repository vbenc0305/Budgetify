import React from "react";

const formatCurrency = (value) => `${Math.round(value).toLocaleString("hu-HU")} Ft`;

export default function CountyCategoryRanking({
  selectedCounty,
  profileCounty,
  loading,
  error,
  matchedUsers,
  dataSource,
  transactionCount,
  totalAmount,
  topCategories,
}) {
  const hasTransactions = Array.isArray(topCategories) && topCategories.length > 0;
  const selectionLabel = selectedCounty || "Még nincs kiválasztott megye";
  const isProfileCounty = !!selectedCounty && selectedCounty === profileCounty;

  return (
	<aside className="county-ranking-card" aria-labelledby="county-ranking-heading">
	  <h2 id="county-ranking-heading">{selectionLabel}</h2>
	  <p className="county-ranking-source">
		Kattints a térképre egy megyére. Az alábbi analitika mindig az éppen
		kiválasztott megyéhez tartozó backend adatokból készül.
	  </p>

	  <dl className="county-selection-summary">
		<div>
		  <dt>Profil megye</dt>
		  <dd>{profileCounty || "Nincs beállítva"}</dd>
		</div>
		<div>
		  <dt>Kiválasztás állapota</dt>
		  <dd>{isProfileCounty ? "Egyezik a profillal" : "Egyedi kiválasztás"}</dd>
		</div>
		<div>
		  <dt>Talált felhasználók</dt>
		  <dd>{matchedUsers.toLocaleString("hu-HU")}</dd>
		</div>
		<div>
		  <dt>Megyei tranzakciók</dt>
		  <dd>{transactionCount.toLocaleString("hu-HU")}</dd>
		</div>
		<div>
		  <dt>Összes elemzett összeg</dt>
		  <dd>{formatCurrency(totalAmount)}</dd>
		</div>
		<div>
		  <dt>Adatforrás</dt>
		  <dd>{dataSource || "-"}</dd>
		</div>
	  </dl>

	  <h3 className="county-ranking-subheading">Legnagyobb kategóriák</h3>

	  {loading ? (
		<p className="county-ranking-empty">Megyei analitika betöltése…</p>
	  ) : null}

	  {!loading && error ? <p className="county-ranking-error">{error}</p> : null}

	  {!loading && !error && !hasTransactions ? (
		<p className="county-ranking-empty">
		  Ehhez a megyéhez jelenleg nincs megjeleníthető tranzakciós adat.
		</p>
	  ) : null}

	  {!loading && !error && hasTransactions ? (
		<table className="county-ranking-table">
		  <thead>
			<tr>
			  <th>Kategória</th>
			  <th>Összeg</th>
			</tr>
		  </thead>
		  <tbody>
			{topCategories.map(({ category, total }) => (
			  <tr key={category}>
				<td>{category}</td>
				<td>{formatCurrency(total)}</td>
			  </tr>
			))}
		  </tbody>
		</table>
	  ) : null}
	</aside>
  );
}


