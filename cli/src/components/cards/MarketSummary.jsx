export default function MarketSummary({
  sentiment,
  confidence,
  lastUpdate,
  timezone,
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white px-8 py-6 shadow-sm">
    <div className="grid grid-cols-3 divide-x divide-slate-200">
        <div>
          <p className="text-sm font-medium text-slate-500">
            Market Sentiment
          </p>

          <p className="mt-2 text-2xl font-bold text-emerald-600">
            {sentiment}
          </p>
        </div>

        <div>
          <p className="text-sm font-medium text-slate-500">
            AI Confidence Today
          </p>

          <p className="mt-2 text-2xl font-bold text-slate-900">
            {confidence}%
          </p>
        </div>

        <div>
          <p className="text-sm font-medium text-slate-500">
            Last Update
          </p>

          <p className="mt-2 text-2xl font-bold text-slate-900">
            {lastUpdate}
          </p>

          <p className="text-sm text-slate-500">
            {timezone}
          </p>
        </div>
      </div>
    </div>
  );
}