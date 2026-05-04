export default function App() {
  return (
    <main className="min-h-screen bg-slate-50 text-ink">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-5xl px-6 py-5">
          <h1 className="text-2xl font-semibold tracking-tight">PriorArt Pal</h1>
          <p className="mt-1 text-sm text-slate-500">
            RAG-powered prior-art patent search · phase 1 scaffold
          </p>
        </div>
      </header>

      <section className="mx-auto max-w-5xl px-6 py-10">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Coming soon</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            <li>· Phase 2 — patent corpus ingest + first retrieval pass</li>
            <li>· Phase 3 — Cohere reranking + Claude streaming generation</li>
            <li>· Phase 4 — Cognito auth, observability, admin metrics</li>
          </ul>
        </div>
      </section>
    </main>
  );
}
