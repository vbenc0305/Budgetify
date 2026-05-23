/* eslint-disable react-hooks/purity -- This chart intentionally samples within confidence intervals for visualization, and changing that behavior here would alter the rendered forecast output. */
import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  Area,
  Brush,
  ComposedChart,
} from "recharts";
import "../pages/styles/Statistics.css";
import "./styles/MiniForecastCard.css";

export default function MiniForecastCard({ predData, predLoading, predError }) {
   const loading = predLoading;
   const error = predError;

   const [showCI, setShowCI] = useState(true);
   const [smoothingWindow, setSmoothingWindow] = useState(0);


   const ci = useMemo(() => {
     if (!predData) return null;
     const data = predData;
     if (Array.isArray(data.ci)) {
       return data.ci.map((c) => ({
         date: c.date,
         lower: Number(c.lower ?? c.lo ?? 0),
         upper: Number(c.upper ?? c.hi ?? 0),
       }));
     } else if (data.ci && data.ci.lower && data.ci.upper) {
       const lowerArr = Array.isArray(data.ci.lower) ? data.ci.lower : [];
       const upperArr = Array.isArray(data.ci.upper) ? data.ci.upper : [];
       const mapUpper = new Map(upperArr.map((u) => [u.date, Number(u.value)]));
       return lowerArr.map((l) => ({
         date: l.date,
         lower: Number(l.value),
         upper: mapUpper.get(l.date) ?? Number(l.value),
       }));
     }
     return null;
   }, [predData]);

  const merged = useMemo(() => {
    const history = Array.isArray(predData?.history) ? predData.history : [];
    const forecast = Array.isArray(predData?.forecast) ? predData.forecast : [];
    const map = new Map();
    const pushPoint = (p, key) => {
      const d = p.date;
      const existing = map.get(d) || { date: d };
      existing[key] = Number(p.value ?? p["value"] ?? 0);
      map.set(d, existing);
    };

     history.forEach((h) => pushPoint(h, "historyValue"));
      forecast.forEach((f) => {
        const d = f.date;
        const existing = map.get(d) || { date: d };
        const originalValue = Number(f.value ?? f["value"] ?? 0);
        existing.forecastOriginalValue = originalValue;
        existing.forecastValue = originalValue;
        map.set(d, existing);
      });

     if (ci) {
        ci.forEach((c) => {
          const existing = map.get(c.date) || { date: c.date };
          const lower = Math.max(0, Number(c.lower ?? 0));
          const upper = Math.max(lower, Number(c.upper ?? 0));
          const range = Math.max(0, upper - lower);

          existing.ciLower = lower;
          existing.ciUpper = upper;
          existing.ciRange = range;

          const rawForecast = Number(existing.forecastValue ?? 0);
          if (showCI && rawForecast > 0 && range > 0) {
            const lowerBound = Math.min(lower, upper);
            const upperBound = Math.max(lower, upper);
            existing.forecastValue =
              lowerBound + Math.random() * (upperBound - lowerBound);
          }

          map.set(c.date, existing);
        });
     }

    const limitStep = (value, min, max) => Math.min(max, Math.max(min, value));

    const forecastRows = Array.from(map.values())
      .filter((row) => typeof row.forecastOriginalValue === "number")
      .sort((a, b) => (a.date > b.date ? 1 : -1));

    let previousForecastValue = Array.from(map.values())
      .filter((row) => typeof row.historyValue === "number")
      .sort((a, b) => (a.date > b.date ? 1 : -1))
      .at(-1)?.historyValue;

    forecastRows.forEach((row) => {
      if (!showCI) {
        row.forecastValue = Number(row.forecastOriginalValue ?? row.forecastValue ?? 0);
        previousForecastValue = row.forecastValue;
        return;
      }

      const lower = typeof row.ciLower === "number" ? row.ciLower : 0;
      const upper = typeof row.ciUpper === "number" ? row.ciUpper : Math.max(lower, row.forecastOriginalValue ?? 0);
      const bandWidth = Math.max(0, upper - lower);
      const original = Number(row.forecastOriginalValue ?? row.forecastValue ?? 0);

      if (bandWidth <= 0) {
        row.forecastValue = Math.max(lower, original);
        previousForecastValue = row.forecastValue;
        return;
      }

      const baseStep = Math.max(
        bandWidth * 0.18,
        Math.abs(previousForecastValue ?? original) * 0.04,
        Math.abs(original) * 0.03,
        1,
      );

      const minAllowed = Math.max(lower, (previousForecastValue ?? original) - baseStep);
      const maxAllowed = Math.min(upper, (previousForecastValue ?? original) + baseStep);

      let nextValue;
      if (minAllowed <= maxAllowed) {
        nextValue = minAllowed + Math.random() * (maxAllowed - minAllowed);
      } else {
        nextValue = lower + Math.random() * (upper - lower);
      }

      row.forecastValue = limitStep(nextValue, lower, upper);
      previousForecastValue = row.forecastValue;
    });

    const arr = Array.from(map.values()).sort((a, b) =>
      a.date > b.date ? 1 : -1,
    );

    if (smoothingWindow > 1) {
      const smooth = (key) => {
        const out = [...arr];
        for (let i = 0; i < arr.length; i++) {
          const from = Math.max(0, i - Math.floor(smoothingWindow / 2));
          const to = Math.min(
            arr.length - 1,
            i + Math.floor(smoothingWindow / 2),
          );
          let sum = 0;
          let cnt = 0;
          for (let j = from; j <= to; j++) {
            if (typeof arr[j][key] === "number") {
              sum += arr[j][key];
              cnt++;
            }
          }
          out[i] = { ...out[i], [key]: cnt ? sum / cnt : out[i][key] };
        }
        return out;
      };

       const withHistory = smooth("historyValue");
       const withBoth = smooth("forecastValue");
      return withHistory.map((r, idx) => ({
        ...r,
          forecastValue:
            typeof withBoth[idx]?.forecastValue === "number"
              ? showCI
                ? Math.min(
                    typeof r.ciUpper === "number" ? r.ciUpper : withBoth[idx].forecastValue,
                    Math.max(
                      typeof r.ciLower === "number" ? r.ciLower : withBoth[idx].forecastValue,
                      withBoth[idx].forecastValue,
                    ),
                  )
                : withBoth[idx].forecastValue
              : withBoth[idx]?.forecastValue,
         forecastOriginalValue: r.forecastOriginalValue,
        ciLower: r.ciLower,
        ciUpper: r.ciUpper,
         ciRange: r.ciRange,
      }));
    }

     return arr;
   }, [predData, ci, smoothingWindow, showCI]);

  const downloadCSV = () => {
    const header =
      ["date", "historyValue", "forecastOriginalValue", "forecastValue", "ciLower", "ciUpper"].join(
        ",",
      ) + "\n";
    const rows = merged
      .map((r) =>
        [
          r.date,
          r.historyValue ?? "",
          r.forecastOriginalValue ?? "",
          r.forecastValue ?? "",
          r.ciLower ?? "",
          r.ciUpper ?? "",
        ].join(","),
      )
      .join("\n");
    const csv = header + rows;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `prediction_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mini-forecast-card chart-card">
      <div className="chart-card-header">
        <div>
          <h2 className="chart-title">Előrejelzés — jövőbeli kiadások</h2>
          <div className="chart-subtitle muted">
            Mini forecast (az Insights fül része)
          </div>
        </div>

        <div className="chart-controls">
          <button
            onClick={() => setShowCI((s) => !s)}
            className="control-btn"
            title="Confidence interval megjelenítése/elrejtése"
          >
            {showCI ? "CI: on" : "CI: off"}
          </button>

          <select
            value={smoothingWindow}
            onChange={(e) => setSmoothingWindow(Number(e.target.value))}
            className="control-select"
            title="Smoothing (ma)"
          >
            <option value={0}>Sima</option>
            <option value={3}>MA 3</option>
            <option value={7}>MA 7</option>
          </select>

          <button onClick={downloadCSV} className="control-btn">
            Export CSV
          </button>
        </div>
      </div>

      {error && <div className="error-box">Hiba: {error}</div>}

       {loading ? (
         <div className="loading-skeleton" />
       ) : (
         <ResponsiveContainer width="100%" height={420}>
            <ComposedChart data={merged}>
              <defs>
                {/* Neutral gradient for CI band */}
                <linearGradient id="ciBandFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#94a3b8" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#64748b" stopOpacity={0.06} />
                </linearGradient>
              </defs>

             <CartesianGrid
               strokeDasharray="3 3"
               stroke="rgba(148, 163, 184, 0.1)"
               verticalPoints={[]}
             />
             <XAxis
               dataKey="date"
               minTickGap={10}
               stroke="rgba(148, 163, 184, 0.4)"
               style={{ fontSize: "0.85rem" }}
             />
             <YAxis
               stroke="rgba(148, 163, 184, 0.4)"
               style={{ fontSize: "0.85rem" }}
             />

             <Tooltip
               contentStyle={{
                 backgroundColor: "rgba(15, 23, 42, 0.95)",
                 borderRadius: "8px",
                 border: "1px solid rgba(148, 163, 184, 0.3)",
                 boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)",
                 backdropFilter: "blur(8px)",
               }}
               formatter={(value, name) => {
                 if (typeof value !== "number") return ["—", name];
                  if (name === "ciLower" || name === "ciRange") return ["", ""];
                 const formatted = value.toLocaleString("hu-HU", {
                   maximumFractionDigits: 0,
                 });
                 if (name === "historyValue") return [formatted, "Történet"];
                  if (name === "forecastOriginalValue") return [formatted, "Előrejelzés (eredeti)"];
                 if (name === "forecastValue") return [formatted, "Előrejelzés"];
                 if (name === "ciLower") return [formatted, "CI alsó"];
                 if (name === "ciUpper") return [formatted, "CI felső"];
                 return [formatted, name];
               }}
               cursor={{ stroke: "rgba(99, 102, 241, 0.3)", strokeWidth: 1 }}
             />

             <Legend
               wrapperStyle={{
                 paddingTop: "16px",
                 color: "var(--text-secondary)",
               }}
               iconType="line"
             />

             {/* CI band from backend values */}
             {showCI &&
               merged.some(
                 (r) =>
                   typeof r.ciLower === "number" &&
                   typeof r.ciUpper === "number",
               ) && (
                 <>
                    <Area
                     type="natural"
                      dataKey="ciLower"
                      stackId="ciBand"
                      stroke="transparent"
                      fill="transparent"
                      legendType="none"
                      dot={false}
                     isAnimationActive={true}
                     animationDuration={800}
                   />
                    <Area
                     type="natural"
                      dataKey="ciRange"
                      name="Konfidencia sáv"
                      stackId="ciBand"
                      stroke="transparent"
                      fill="url(#ciBandFill)"
                      fillOpacity={0.18}
                      legendType="none"
                      dot={false}
                     isAnimationActive={true}
                     animationDuration={800}
                   />
                 </>
               )}

             {/* Historical data with smooth gradient */}
             <Line
               type="natural"
               dataKey="historyValue"
               name="Történet"
               stroke="#334155"
               strokeWidth={2.5}
               dot={false}
               isAnimationActive={true}
               animationDuration={600}
               strokeLinecap="round"
               strokeLinejoin="round"
             />

             {/* Forecast with enhanced styling */}
             <Line
               type="natural"
                dataKey="forecastOriginalValue"
                name="Előrejelzés (eredeti)"
                stroke="#94a3b8"
                strokeWidth={2}
                dot={false}
                strokeDasharray="4 4"
                strokeLinecap="round"
                strokeLinejoin="round"
                isAnimationActive={true}
                animationDuration={700}
              />

              <Line
                type="natural"
               dataKey="forecastValue"
               name="Előrejelzés"
               stroke="#f43f5e"
                strokeWidth={3.2}
               dot={false}
               strokeDasharray="8 4"
               strokeLinecap="round"
               strokeLinejoin="round"
               isAnimationActive={true}
               animationDuration={800}
               animationEasing="ease-in-out"
             />

             <Brush
               dataKey="date"
               height={30}
               stroke="#6366f1"
               fill="rgba(99, 102, 241, 0.1)"
             />
           </ComposedChart>
         </ResponsiveContainer>
       )}
    </div>
  );
}
