import ForecastCard from "../components/cards/ForecastCard";
import { useEffect, useState } from "react";
import MarketSummary from "../components/cards/MarketSummary";
import { getMarketForecasts, getMarketSummary } from "../services/marketService";

export default function Home() {
    const [forecasts, setForecasts] = useState([]);
    const [summary, setSummary] = useState(null);

    useEffect(() => {
        async function loadData() {
            const forecastsData = await getMarketForecasts();
            setForecasts(forecastsData);

            const summaryData = await getMarketSummary();
            setSummary(summaryData);
        }

        loadData();
    }, []);
  return (
    <section className="space-y-4">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-emerald-600">
          AI Market Forecast
        </p>

        <h1 className="mt-3 text-5xl font-bold text-slate-950">
          AI Market Forecast
        </h1>

        <p className="mt-3 max-w-2xl text-lg text-slate-500">
          Forecasting the next candle movement for major indices across different time horizons.
        </p>

        <div className="mt-10 grid gap-5 lg:grid-cols-4">
            {forecasts.map((forecast) => (
                <ForecastCard
                key={forecast.symbol}
                {...forecast}
                />
            ))}
        </div>
            {summary && (
                <div className="mt-10 max-w-5xl">
                    <MarketSummary {...summary} />
                </div>
            )}
      </div>
    </section>
  );
}