'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Zap, ArrowRight, TrendingUp, TrendingDown } from 'lucide-react';

interface PatternResult {
  type: string;
  signal: string;
  strength: string;
  score: number;
}

interface ScanResult {
  symbol: string;
  current_price: number;
  day_change_percent: number;
  patterns_found: PatternResult[];
  total_score: number;
  dominant_signal: string;
}

const LOADING_STEPS = [
  'Connecting to scanner engine...',
  'Pulling Nifty 50 candles...',
  'Computing technical indicators...',
  'Detecting patterns & breakouts...',
  'Ranking opportunities...',
];

export default function QuickScan() {
  const [results, setResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [scanned, setScanned] = useState(false);

  const runScan = async () => {
    setLoading(true);
    setError(null);
    setStep(0);
    setResults([]);

    const stepTimer = setInterval(() => {
      setStep((s) => (s + 1) % LOADING_STEPS.length);
    }, 4000);

    try {
      const base =
        process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const url = `${base}/scanner/scan?patterns=all&timeframe=1d&min_score=50`;
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error('Scan failed. The server may be waking up.');
      }
      const data = await res.json();
      setResults((data.results || []).slice(0, 5));
      setScanned(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Unable to reach the scanner.'
      );
    } finally {
      clearInterval(stepTimer);
      setLoading(false);
    }
  };

  return (
    <section className="relative">
      {/* Header row */}
      <div className="flex flex-wrap items-end justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-bone-400 mb-2">
            <Zap className="w-3.5 h-3.5 text-spark-cyan" />
            Instant Market Scan
          </div>
          <h2 className="text-2xl sm:text-3xl text-display text-gradient font-semibold">
            Find today&apos;s strongest setups
          </h2>
          <p className="text-sm text-bone-400 mt-1.5">
            One click. We scan Nifty 50 for breakouts, momentum, and
            high-conviction patterns.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {scanned && !loading && (
            <Link
              href="/scanner"
              className="btn-ghost text-sm"
              prefetch={false}
            >
              Full scanner
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
          <button
            onClick={runScan}
            disabled={loading}
            className="btn-accent text-sm"
          >
            {loading ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/70 border-t-transparent rounded-full animate-spin" />
                Scanning…
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                {scanned ? 'Re-scan' : 'Start Scan'}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Loading messages */}
      {loading && (
        <div className="glass rounded-2xl p-5 mb-5 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="relative w-9 h-9 flex-shrink-0">
              <div className="absolute inset-0 rounded-full border-2 border-white/10" />
              <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-spark-cyan border-r-spark-violet animate-spin" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-bone-100 text-sm font-medium truncate">
                {LOADING_STEPS[step]}
              </p>
              <p className="text-xs text-bone-400 mt-0.5">
                First request can take 30–60s on free tier — the server is
                warming up.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="rounded-2xl border border-spark-rose/25 bg-spark-rose/[0.06] p-4 mb-5 text-sm text-spark-rose flex items-start gap-3 animate-fade-in">
          <span className="dot-spark bg-spark-rose mt-1.5" />
          <div>
            <p className="font-medium">{error}</p>
            <p className="text-spark-rose/70 mt-1 text-xs">
              Wait ~30 seconds and click <strong>Start Scan</strong> again. The
              free-tier backend spins down after inactivity.
            </p>
          </div>
        </div>
      )}

      {/* Empty placeholder */}
      {!loading && !scanned && !error && (
        <div className="glass rounded-2xl p-8 sm:p-10 text-center animate-fade-up">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-spark-emerald/15 via-spark-cyan/15 to-spark-violet/15 border border-white/[0.08] mb-4">
            <Zap className="w-6 h-6 text-spark-cyan" />
          </div>
          <h3 className="text-xl text-display text-bone-50 font-semibold mb-1.5">
            Ready when you are
          </h3>
          <p className="text-sm text-bone-400 max-w-md mx-auto">
            Click <strong className="text-bone-100">Start Scan</strong> to
            surface the top 5 stocks with the strongest technical setups right
            now.
          </p>
        </div>
      )}

      {/* Skeleton while loading */}
      {loading && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="glass rounded-2xl p-4 h-32 skeleton"
              style={{ animationDelay: `${i * 100}ms` }}
            />
          ))}
        </div>
      )}

      {/* Results */}
      {!loading && results.length > 0 && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {results.map((r, i) => {
            const up = r.day_change_percent >= 0;
            const bullish = r.dominant_signal === 'BULLISH';
            return (
              <Link
                key={r.symbol}
                href={`/analyze?symbol=${r.symbol}`}
                className="group glass glass-hover rounded-2xl p-4 animate-fade-up relative overflow-hidden"
                style={{ animationDelay: `${i * 70}ms` }}
              >
                <span
                  className={`absolute top-3 right-3 dot-spark ${
                    bullish ? 'bg-spark-emerald' : 'bg-spark-rose'
                  }`}
                />
                <div className="flex items-center justify-between mb-2">
                  <span className="font-display font-semibold text-bone-50 text-sm tracking-tight">
                    {r.symbol}
                  </span>
                  <span
                    className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded ${
                      bullish
                        ? 'text-spark-emerald bg-spark-emerald/10'
                        : 'text-spark-rose bg-spark-rose/10'
                    }`}
                  >
                    {r.dominant_signal}
                  </span>
                </div>
                <div className="text-bone-100 font-mono text-lg leading-tight">
                  ₹{r.current_price.toFixed(2)}
                </div>
                <div
                  className={`flex items-center gap-1 mt-1 text-xs font-medium ${
                    up ? 'text-spark-emerald' : 'text-spark-rose'
                  }`}
                >
                  {up ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                  {up ? '+' : ''}
                  {r.day_change_percent.toFixed(2)}%
                </div>
                <div className="mt-3 pt-3 border-t border-white/[0.05]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-bone-500">Score</span>
                    <span className="text-bone-100 font-mono">
                      {r.total_score.toFixed(0)}
                    </span>
                  </div>
                  <div className="mt-1.5 h-1 bg-white/[0.04] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        bullish
                          ? 'bg-gradient-to-r from-spark-emerald to-spark-cyan'
                          : 'bg-gradient-to-r from-spark-rose to-spark-amber'
                      }`}
                      style={{ width: `${Math.min(r.total_score, 100)}%` }}
                    />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {!loading && scanned && results.length === 0 && !error && (
        <div className="glass rounded-2xl p-6 text-center text-bone-400 text-sm">
          No high-conviction setups detected right now. Try again after the next
          bar closes.
        </div>
      )}
    </section>
  );
}
