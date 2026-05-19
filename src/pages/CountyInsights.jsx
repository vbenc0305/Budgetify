import React, { useEffect, useMemo, useState } from "react";
import CountyCategoryRanking from "../components/CountyCategoryRanking";
import HungaryCountyMap from "../components/HungaryCountyMap";
import { useUser } from "../stores/useUser";
import { canonicalizeCountyName } from "../utils/countyNameNormalizer";
import {
  getTopCategoryTotals,
  getTransactionSummary,
} from "../utils/countyAggregation";
import { fetchCountyCategoryAnalytics } from "../utils/predictionApi";
import "./styles/CountyInsights.css";

export default function CountyInsights() {
  const user = useUser((state) => state.user);
  const usrInfo = useUser((state) => state.usrInfo);
  const [selectedCounty, setSelectedCounty] = useState("");
  const [countyTransactions, setCountyTransactions] = useState([]);
  const [matchedUsers, setMatchedUsers] = useState(0);
  const [dataSource, setDataSource] = useState("");
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");

  const profileCounty = useMemo(() => {
    const rawCounty = String(usrInfo?.county ?? "").trim();
    return canonicalizeCountyName(rawCounty) || rawCounty;
  }, [usrInfo]);

  useEffect(() => {
    if (profileCounty && !selectedCounty) {
      setSelectedCounty(profileCounty);
    }
  }, [profileCounty, selectedCounty]);

  useEffect(() => {
    let isCancelled = false;

    const loadCountyAnalytics = async () => {
      const normalizedCounty = String(selectedCounty ?? "").trim();
      if (!normalizedCounty) {
        setCountyTransactions([]);
        setMatchedUsers(0);
        setDataSource("");
        setAnalyticsError("");
        setLoadingAnalytics(false);
        return;
      }

      setLoadingAnalytics(true);
      setAnalyticsError("");

      try {
        const countyData = await fetchCountyCategoryAnalytics(normalizedCounty, user);
        if (isCancelled) return;

        setCountyTransactions(countyData.transactions);
        setMatchedUsers(countyData.matchedUsers);
        setDataSource(countyData.dataSource);
      } catch (error) {
        if (isCancelled) return;

        setCountyTransactions([]);
        setMatchedUsers(0);
        setDataSource("");
        setAnalyticsError(error?.message || "A megyei analitika betöltése sikertelen.");
      } finally {
        if (!isCancelled) {
          setLoadingAnalytics(false);
        }
      }
    };

    loadCountyAnalytics();

    return () => {
      isCancelled = true;
    };
  }, [selectedCounty, user]);

  const topCategories = useMemo(() => {
    return getTopCategoryTotals(countyTransactions, 5);
  }, [countyTransactions]);

  const transactionSummary = useMemo(
    () => getTransactionSummary(countyTransactions),
    [countyTransactions],
  );

  return (
    <section className="county-insights-page">
      <header className="county-insights-header">
        <h1>Megyei betekintés</h1>
        <p>
          Interaktív Magyarország-térkép kattintható megyékkel. A profilban
          megadott megye induláskor ki van emelve, de bármelyik megyére
          rákattinthatsz a részletek megtekintéséhez.
        </p>
      </header>

      <div className="county-insights-grid">
        <HungaryCountyMap
          selectedCounty={selectedCounty}
          profileCounty={profileCounty}
          onCountySelect={setSelectedCounty}
        />

        <CountyCategoryRanking
          selectedCounty={selectedCounty}
          profileCounty={profileCounty}
          loading={loadingAnalytics}
          error={analyticsError}
          matchedUsers={matchedUsers}
          dataSource={dataSource}
          transactionCount={transactionSummary.count}
          totalAmount={transactionSummary.totalAmount}
          topCategories={topCategories}
        />
      </div>
    </section>
  );
}

