import { BarChart3, Home, Info, Star, TrendingUp } from "lucide-react";

export default function AppLayout({ children }) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="h-20 border-b border-slate-200 bg-white px-8 flex items-center justify-between">
        <div className="flex items-center gap-3 font-bold text-2xl text-slate-950">
          <TrendingUp size={30} />
          AlgoTrade
        </div>

        <button className="rounded-2xl border border-slate-200 px-5 py-3 text-base font-semibold text-slate-700 shadow-sm hover:bg-slate-50">
          🌙 Dark
        </button>
      </header>

      <div className="flex">
        <aside className="w-72 min-h-[calc(100vh-5rem)] border-r border-slate-200 bg-white p-6">
          <nav className="space-y-3">
            <NavItem icon={<Home size={30} />} label="Home" active />
            <NavItem icon={<BarChart3 size={30} />} label="Prediction" />
            <NavItem icon={<Star size={30} />} label="Watchlist" />
            <NavItem icon={<Info size={30} />} label="About Model" />
          </nav>
        </aside>

        <main className="flex-1 p-10">{children}</main>
      </div>
    </div>
  );
}

function NavItem({ icon, label, active = false }) {
  return (
    <div
      className={`flex items-center gap-4 rounded-2xl px-5 py-4 text--base font-semibold transition ${
        active
          ? "bg-slate-900 text-white shadow-sm"
          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      }`}
    >
      {icon}
      <span>{label}</span>
    </div>
  );
}