import AppLayout from "./components/layout/AppLayout";

export default function App() {
  return (
    <AppLayout>
      <div className="space-y-4">
          <div>
              <h1 className="text-5xl font-bold">
                  Good evening 👋
              </h1>

              <p className="mt-2 text-lg text-slate-500">
                  Welcome to AlgoTrade. Explore AI-powered market forecasts
                  designed to support smarter investment decisions.
              </p>
          </div>
      </div>
    </AppLayout>
  );
}