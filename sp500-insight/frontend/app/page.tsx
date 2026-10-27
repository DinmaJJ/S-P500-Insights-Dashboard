export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="text-4xl font-bold tracking-tight">
          S&P 500 Insight
        </h1>
        <p className="mt-4 text-lg text-slate-400 max-w-2xl">
          Daily automated analysis of the S&P 500 — prices, fundamentals,
          technicals, and ranked opportunities. Built as a serious portfolio project.
        </p>

        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
            <h2 className="text-sm font-medium text-slate-400">Universe</h2>
            <p className="mt-2 text-3xl font-semibold">~503</p>
            <p className="mt-1 text-sm text-slate-500">S&P 500 constituents</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
            <h2 className="text-sm font-medium text-slate-400">Status</h2>
            <p className="mt-2 text-3xl font-semibold text-amber-400">Scaffolded</p>
            <p className="mt-1 text-sm text-slate-500">Ready for Phase 1</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
            <h2 className="text-sm font-medium text-slate-400">Next</h2>
            <p className="mt-2 text-lg font-medium">Data Pipeline</p>
            <p className="mt-1 text-sm text-slate-500">ETL + analysis engine</p>
          </div>
        </div>

        <div className="mt-16 rounded-xl border border-slate-800 bg-slate-900/30 p-8">
          <h2 className="text-xl font-semibold">Coming soon</h2>
          <ul className="mt-4 space-y-2 text-slate-400">
            <li>• Live universe browser with sector filters</li>
            <li>• Daily top ranked opportunities</li>
            <li>• Individual stock deep-dives (price + fundamentals + signals)</li>
            <li>• Sector performance heatmaps</li>
            <li>• Historical signal performance tracking</li>
          </ul>
        </div>
      </div>
    </main>
  );
}
