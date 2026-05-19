import React, { useEffect, useMemo, useRef, useState } from "react";
import { canonicalizeCountyName } from "../utils/countyNameNormalizer";

const SVG_WIDTH = 860;
const MAP_PADDING = 18;

const getGeometryPolygons = (geometry) => {
  if (!geometry || !geometry.type || !Array.isArray(geometry.coordinates)) return [];

  if (geometry.type === "Polygon") {
	return [geometry.coordinates];
  }

  if (geometry.type === "MultiPolygon") {
	return geometry.coordinates;
  }

  return [];
};

const flattenCoordinates = (geometry) =>
  getGeometryPolygons(geometry).flatMap((polygon) => polygon.flatMap((ring) => ring));

const getCountyName = (feature) => {
  const rawName = feature?.properties?.name ?? feature?.properties?.NAME ?? "";
  return canonicalizeCountyName(rawName) || String(rawName || "Ismeretlen megye").trim();
};

const buildMapModel = (geoJson) => {
  const sourceFeatures = Array.isArray(geoJson?.features) ? geoJson.features : [];
  if (sourceFeatures.length === 0) return null;

  const allPoints = sourceFeatures.flatMap((feature) => flattenCoordinates(feature.geometry));
  if (allPoints.length === 0) return null;

  const [firstLon, firstLat] = allPoints[0];

  const bounds = allPoints.reduce(
	(accumulator, [lon, lat]) => ({
	  minLon: Math.min(accumulator.minLon, lon),
	  maxLon: Math.max(accumulator.maxLon, lon),
	  minLat: Math.min(accumulator.minLat, lat),
	  maxLat: Math.max(accumulator.maxLat, lat),
	}),
	{
	  minLon: firstLon,
	  maxLon: firstLon,
	  minLat: firstLat,
	  maxLat: firstLat,
	},
  );

  const longitudeSpan = Math.max(bounds.maxLon - bounds.minLon, 0.0001);
  const latitudeSpan = Math.max(bounds.maxLat - bounds.minLat, 0.0001);
  const scale = (SVG_WIDTH - MAP_PADDING * 2) / longitudeSpan;
  const svgHeight = Math.max(520, latitudeSpan * scale + MAP_PADDING * 2);

  const projectPoint = ([lon, lat]) => [
	MAP_PADDING + (lon - bounds.minLon) * scale,
	MAP_PADDING + (bounds.maxLat - lat) * scale,
  ];

  const ringToPath = (ring) => {
	if (!Array.isArray(ring) || ring.length === 0) return "";

	return ring
	  .map((point, index) => {
		const [x, y] = projectPoint(point);
		return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
	  })
	  .join(" ");
  };

  const features = sourceFeatures
	.map((feature, index) => {
	  const polygons = getGeometryPolygons(feature.geometry);
	  const pathData = polygons
		.map((polygon) => polygon.map((ring) => `${ringToPath(ring)} Z`).join(" "))
		.join(" ");

	  if (!pathData) return null;

	  return {
		id: `${getCountyName(feature)}-${index}`,
		name: getCountyName(feature),
		pathData,
	  };
	})
	.filter(Boolean);

  return {
	width: SVG_WIDTH,
	height: svgHeight,
	features,
  };
};

export default function HungaryCountyMap({
  selectedCounty,
  profileCounty,
  onCountySelect,
}) {
  const containerRef = useRef(null);
  const [geoJson, setGeoJson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
	let isCancelled = false;

	const loadGeoJson = async () => {
	  setLoading(true);
	  setError(null);

	  try {
		const response = await fetch("/data/hungary-counties.geojson");

		if (!response.ok) {
		  throw new Error(`A térkép nem tölthető be (${response.status}).`);
		}

		const data = await response.json();
		if (!isCancelled) {
		  setGeoJson(data);
		}
	  } catch (loadError) {
		if (!isCancelled) {
		  setError(loadError?.message || "A térkép betöltése sikertelen.");
		}
	  } finally {
		if (!isCancelled) {
		  setLoading(false);
		}
	  }
	};

	loadGeoJson();

	return () => {
	  isCancelled = true;
	};
  }, []);

  const mapModel = useMemo(() => buildMapModel(geoJson), [geoJson]);

  const updateTooltip = (event, countyName) => {
	const containerBounds = containerRef.current?.getBoundingClientRect();
	if (!containerBounds) return;

	setTooltip({
	  name: countyName,
	  x: event.clientX - containerBounds.left,
	  y: event.clientY - containerBounds.top,
	});
  };

  if (error) {
	return <div className="county-map-error">{error}</div>;
  }

  if (loading || !mapModel) {
	return <div className="county-map-loading">Térkép betöltése folyamatban…</div>;
  }

  return (
	<div className="county-map-shell" ref={containerRef}>
	  <div className="county-map-meta">
		<div>
		  <h2>Interaktív Magyarország-térkép</h2>
		  <p className="county-map-caption">
			Kattints egy megyére a kiválasztáshoz. A térkép billentyűzettel is
			bejárható.
		  </p>
		</div>

		{profileCounty && selectedCounty !== profileCounty ? (
		  <button
			type="button"
			className="county-map-reset"
			onClick={() => onCountySelect?.(profileCounty)}
		  >
			Vissza a profil megyéhez
		  </button>
		) : null}
	  </div>

	  <svg
		className="hungary-county-map"
		viewBox={`0 0 ${mapModel.width} ${mapModel.height}`}
		role="img"
		aria-label="Magyarország kattintható megyetérképe"
	  >
		{mapModel.features.map((feature) => {
		  const isSelected = feature.name === selectedCounty;
		  const isProfileCounty = feature.name === profileCounty;

		  return (
			<path
			  key={feature.id}
			  d={feature.pathData}
			  fillRule="evenodd"
			  className={[
				"county-path",
				isSelected ? "selected" : "",
				isProfileCounty ? "profile" : "",
			  ]
				.filter(Boolean)
				.join(" ")}
			  role="button"
			  tabIndex={0}
			  aria-label={`${feature.name} megye kiválasztása`}
			  aria-pressed={isSelected}
			  onClick={() => onCountySelect?.(feature.name)}
			  onKeyDown={(event) => {
				if (event.key === "Enter" || event.key === " ") {
				  event.preventDefault();
				  onCountySelect?.(feature.name);
				}
			  }}
			  onMouseEnter={(event) => updateTooltip(event, feature.name)}
			  onMouseMove={(event) => updateTooltip(event, feature.name)}
			  onMouseLeave={() => setTooltip(null)}
			/>
		  );
		})}
	  </svg>

	  {tooltip ? (
		<div
		  className="county-map-tooltip"
		  style={{ left: tooltip.x + 12, top: tooltip.y + 12 }}
		>
		  {tooltip.name}
		</div>
	  ) : null}
	</div>
  );
}


