import { indexStyles, recommendationStyles } from "../../theme/forecastStyles";

export default function ForecastCard({
  symbol,
  name,
  recommendation,
  range,
  confidence,
}) {
    const recommendationStyle = recommendationStyles[recommendation];
    const indexStyle = indexStyles[symbol];
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={`flex h-11 w-11 items-center justify-center rounded-full ${indexStyle.circle} text-sm font-bold text-white`}>
            {symbol}
          </div>

          <div>
            <h3 className="text-lg font-bold text-slate-950">{symbol}</h3>
            <p className="text-sm text-slate-500">{name}</p>
          </div>
        </div>

        <span className={`rounded-full px-3 py-1 text-xs font-bold ${recommendationStyle.badge}`}>
          {recommendation}
        </span>
      </div>

      <p className={`mt-7 text-2xl font-bold ${recommendationStyle.text}`}>
        {range}
      </p>

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="text-slate-600">Confidence</span>
          <span className="font-semibold text-slate-700">{confidence}%</span>
        </div>

        <div className="h-2 rounded-full bg-slate-100">
          <div
            className={`h-2 rounded-full ${
              recommendation === "SHORT"
                ? "bg-red-500"
                : recommendation === "STAY OUT"
                ? "bg-amber-400"
                : "bg-emerald-500"
            }`}
            style={{ width: `${confidence}%` }}
          />
        </div>
      </div>
    </div>
  );
}