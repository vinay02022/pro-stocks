'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import TopNav from '@/components/TopNav';
import { Search, Sparkles, ArrowRight } from 'lucide-react';

interface PatternResult {
  type: string;
  signal: string;
  strength: string;
  score: number;
  details: Record<string, unknown>;
  entry_price?: number;
  stop_loss?: number;
  target?: number;
}

interface ScanResult {
  symbol: string;
  current_price: number;
  day_change_percent: number;
  patterns_found: PatternResult[];
  total_score: number;
  dominant_signal: string;
  scan_time: string;
}

interface ScanResponse {
  count: number;
  filters: {
    patterns: string[];
    timeframe: string;
    min_score: number;
    signal_filter: string | null;
  };
  results: ScanResult[];
}

const PATTERNS = [
  { id: 'all', name: 'All' },
  { id: 'breakout', name: 'Breakout' },
  { id: 'momentum', name: 'Momentum' },
  { id: 'volume_spike', name: 'Volume Spike' },
  { id: 'ema_crossover', name: 'EMA Cross' },
  { id: 'rsi_extreme', name: 'RSI Extreme' },
  { id: 'macd_crossover', name: 'MACD Cross' },
  { id: 'sr_bounce', name: 'S/R Bounce' },
  { id: 'bb_squeeze', name: 'BB Squeeze' },
];

const TIMEFRAMES = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1H' },
  { value: '1d', label: 'D' },
];

const LOADING_STEPS = [
  'Connecting to scanner engine…',
  'Server is waking up (free tier)…',
  'Pulling Nifty 50 candles…',
  'Computing technical indicators…',
  'Detecting patterns & breakouts…',
  'Ranking opportunities…',
];

export default function ScannerPage() {
  const [results, setResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const stepTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const [selectedPatterns, setSelectedPatterns] = useState<string[]>(['all']);
  const [timeframe, setTimeframe] = useState('1d');
  const [minScore, setMinScore] = useState(40);
  const [signalFilter, setSignalFilter] = useState<string | null>(null);

  const [sortField, setSortField] = useState<'score' | 'change' | 'symbol'>(
    'score'
  );
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const runScan = async () => {
    setLoading(true);
    setError(null);
    setLoadingStep(0);

    if (stepTimer.current) {
      clearInterval(stepTimer.current);
    }
    stepTimer.current = setInterval(() => {
      setLoadingStep((s) => Math.min(s + 1, LOADING_STEPS.length - 1));
    }, 5000);

    try {
      const patterns = selectedPatterns.includes('all')
        ? 'all'
        : selectedPatterns.join(',');
      let url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/scanner/scan?patterns=${patterns}&timeframe=${timeframe}&min_score=${minScore}`;

      if (signalFilter) {
        url += `&signal=${signalFilter}`;
      }

      const res = await fetch(url);
      if (!res.ok) {
        throw new Error('Scan failed — the server may still be waking up.');
      }

      const data: ScanResponse = await res.json();
      setResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed');
    } finally {
      if (stepTimer.current) {
        clearInterval(stepTimer.current);
      }
      setLoading(false);
    }
  };

  useEffect(() => {
    runScan();
    return () => {
      if (stepTimer.current) {
        clearInterval(stepTimer.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const togglePattern = (pattern: string) => {
    if (pattern === 'all') {
      setSelectedPatterns(['all']);
    } else {
      const newPatterns = selectedPatterns.filter((p) => p !== 'all');
      if (newPatterns.includes(pattern)) {
        const filtered = newPatterns.filter((p) => p !== pattern);
        setSelectedPatterns(filtered.length ? filtered : ['all']);
      } else {
        setSelectedPatterns([...newPatterns, pattern]);
      }
    }
  };

  const sortedResults = [...results].sort((a, b) => {
    let comparison = 0;
    if (sortField === 'score') {
      comparison = a.total_score - b.total_score;
    } else if (sortField === 'change') {
      comparison = a.day_change_percent - b.day_change_percent;
    } else {
      comparison = a.symbol.localeCompare(b.symbol);
    }
    return sortDirection === 'desc' ? -comparison : comparison;
  });

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDirection((p) => (p === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const signalBadge = (signal: string) => {
    if (signal === 'BULLISH') {
      return 'text-spark-emerald bg-spark-emerald/10 border-spark-emerald/20';
    }
    if (signal === 'BEARISH') {
      return 'text-spark-rose bg-spark-rose/10 border-spark-rose/20';
    }
    return 'text-bone-400 bg-white/[0.04] border-white/[0.06]';
  };

  const strengthColor = (strength: string) => {
    if (strength === 'very_strong') {
      return 'text-spark-emerald';
    }
    if (strength === 'strong') {
      return 'text-spark-cyan';
    }
    if (strength === 'moderate') {
      return 'text-spark-amber';
    }
    return 'text-bone-400';
  };

  return (
    <>
      <TopNav />
      <main className="min-h-screen">
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 py-6">
          {/* Title */}
          <div className="flex flex-wrap items-end justify-between gap-3 mb-6 animate-fade-up">
            <div>
              <div className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-bone-400 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-spark-cyan" />
                Market Scanner
              </div>
              <h1 className="text-3xl sm:text-4xl text-display font-semibold text-gradient">
                High-conviction setups, ranked
              </h1>
            </div>
            <Link href="/analyze" className="btn-ghost text-sm">
              Open Analyze
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Filters */}
          <div className="glass rounded-2xl p-4 sm:p-5 mb-5 animate-fade-up">
            {/* Pattern chips */}
            <div className="mb-4">
              <label className="text-[10px] uppercase tracking-[0.18em] text-bone-500 mb-2 block">
                Patterns
              </label>
              <div className="flex flex-wrap gap-1.5">
                {PATTERNS.map((p) => {
                  const active = selectedPatterns.includes(p.id);
                  return (
                    <button
                      key={p.id}
                      onClick={() => togglePattern(p.id)}
                      className={`px-3 py-1.5 text-xs rounded-lg transition-all duration-300 border ${
                        active
                          ? 'bg-spark-violet/15 text-bone-50 border-spark-violet/30 shadow-glow-violet'
                          : 'bg-white/[0.03] text-bone-400 border-white/[0.06] hover:text-bone-100 hover:bg-white/[0.06]'
                      }`}
                    >
                      {p.name}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-wrap items-end gap-4 pt-4 border-t border-white/[0.05]">
              <div>
                <label className="text-[10px] uppercase tracking-[0.18em] text-bone-500 mb-2 block">
                  Timeframe
                </label>
                <div className="flex bg-white/[0.03] border border-white/[0.06] rounded-xl p-1">
                  {TIMEFRAMES.map((tf) => (
                    <button
                      key={tf.value}
                      onClick={() => setTimeframe(tf.value)}
                      className={`px-3 py-1.5 text-xs rounded-lg transition-all ${
                        timeframe === tf.value
                          ? 'bg-white/[0.08] text-bone-50'
                          : 'text-bone-400 hover:text-bone-100'
                      }`}
                    >
                      {tf.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-[0.18em] text-bone-500 mb-2 block">
                  Min score
                </label>
                <input
                  type="number"
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  className="w-20 px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-xl text-bone-50 text-sm focus:bg-white/[0.05] focus:border-white/[0.16] outline-none"
                  min={0}
                  max={100}
                />
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-[0.18em] text-bone-500 mb-2 block">
                  Signal
                </label>
                <div className="flex bg-white/[0.03] border border-white/[0.06] rounded-xl p-1">
                  <button
                    onClick={() => setSignalFilter(null)}
                    className={`px-3 py-1.5 text-xs rounded-lg transition-all ${
                      !signalFilter
                        ? 'bg-white/[0.08] text-bone-50'
                        : 'text-bone-400 hover:text-bone-100'
                    }`}
                  >
                    All
                  </button>
                  <button
                    onClick={() => setSignalFilter('BULLISH')}
                    className={`px-3 py-1.5 text-xs rounded-lg transition-all ${
                      signalFilter === 'BULLISH'
                        ? 'bg-spark-emerald/20 text-spark-emerald'
                        : 'text-bone-400 hover:text-bone-100'
                    }`}
                  >
                    Bullish
                  </button>
                  <button
                    onClick={() => setSignalFilter('BEARISH')}
                    className={`px-3 py-1.5 text-xs rounded-lg transition-all ${
                      signalFilter === 'BEARISH'
                        ? 'bg-spark-rose/20 text-spark-rose'
                        : 'text-bone-400 hover:text-bone-100'
                    }`}
                  >
                    Bearish
                  </button>
                </div>
              </div>

              <div className="ml-auto">
                <button
                  onClick={runScan}
                  disabled={loading}
                  className="btn-accent text-sm"
                >
                  {loading ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white/80 border-t-transparent rounded-full animate-spin" />
                      Scanning…
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      Scan Now
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Cold-start banner */}
          {loading && (
            <div className="glass rounded-2xl p-4 mb-5 animate-fade-in">
              <div className="flex items-center gap-3">
                <div className="relative w-9 h-9 flex-shrink-0">
                  <div className="absolute inset-0 rounded-full border-2 border-white/10" />
                  <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-spark-cyan border-r-spark-violet animate-spin" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-bone-100 text-sm font-medium">
                    {LOADING_STEPS[loadingStep]}
                  </p>
                  <p className="text-xs text-bone-500 mt-0.5">
                    First request after idle can take 30–60 seconds.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && !loading && (
            <div className="rounded-2xl border border-spark-rose/25 bg-spark-rose/[0.06] p-4 mb-5 text-sm text-spark-rose animate-fade-in">
              {error}
            </div>
          )}

          {/* Results table */}
          <div className="glass rounded-2xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-white/[0.05] flex items-center justify-between">
              <span className="text-sm text-bone-400">
                <span className="text-bone-50 font-semibold font-mono">
                  {results.length}
                </span>{' '}
                matching stocks
              </span>
              {!loading && results.length > 0 && (
                <span className="inline-flex items-center gap-1.5 text-xs text-bone-500">
                  <span className="dot-spark bg-spark-emerald" />
                  Updated
                </span>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-white/[0.02]">
                  <tr>
                    <th
                      className="px-4 py-3 text-left text-[10px] font-semibold tracking-[0.16em] text-bone-500 uppercase cursor-pointer hover:text-bone-200"
                      onClick={() => handleSort('symbol')}
                    >
                      Symbol{' '}
                      {sortField === 'symbol' &&
                        (sortDirection === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="px-4 py-3 text-right text-[10px] font-semibold tracking-[0.16em] text-bone-500 uppercase">
                      Price
                    </th>
                    <th
                      className="px-4 py-3 text-right text-[10px] font-semibold tracking-[0.16em] text-bone-500 uppercase cursor-pointer hover:text-bone-200"
                      onClick={() => handleSort('change')}
                    >
                      Change{' '}
                      {sortField === 'change' &&
                        (sortDirection === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="px-4 py-3 text-center text-[10px] font-semibold tracking-[0.16em] text-bone-500 uppercase">
                      Signal
                    </th>
                    <th
                      className="px-4 py-3 text-center text-[10px] font-semibold tracking-[0.16em] text-bone-500 uppercase cursor-pointer hover:text-bone-200"
                      onClick={() => handleSort('score')}
                    >
                      Score{' '}
                      {sortField === 'score' &&
                        (sortDirection === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="px-4 py-3 text-left text-[10px] font-semibold tracking-[0.16em] text-bone-500 uppercase">
                      Patterns
                    </th>
                    <th className="px-4 py-3 text-center text-[10px] font-semibold tracking-[0.16em] text-bone-500 uppercase">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {loading &&
                    results.length === 0 &&
                    Array.from({ length: 8 }).map((_, i) => (
                      <tr key={`s-${i}`}>
                        {Array.from({ length: 7 }).map((__, j) => (
                          <td key={j} className="px-4 py-4">
                            <div
                              className="h-4 rounded skeleton"
                              style={{
                                animationDelay: `${(i + j) * 60}ms`,
                                width:
                                  j === 5 ? '80%' : j === 0 ? '70%' : '60%',
                              }}
                            />
                          </td>
                        ))}
                      </tr>
                    ))}

                  {sortedResults.map((result, i) => (
                    <tr
                      key={result.symbol}
                      className="hover:bg-white/[0.025] transition-colors animate-fade-in"
                      style={{ animationDelay: `${Math.min(i * 30, 600)}ms` }}
                    >
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`dot-spark ${
                              result.dominant_signal === 'BULLISH'
                                ? 'bg-spark-emerald'
                                : result.dominant_signal === 'BEARISH'
                                  ? 'bg-spark-rose'
                                  : 'bg-bone-400'
                            }`}
                          />
                          <span className="font-semibold text-bone-50">
                            {result.symbol}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-right text-bone-100 font-mono text-sm">
                        ₹{result.current_price.toFixed(2)}
                      </td>
                      <td
                        className={`px-4 py-4 text-right font-mono text-sm ${
                          result.day_change_percent >= 0
                            ? 'text-spark-emerald'
                            : 'text-spark-rose'
                        }`}
                      >
                        {result.day_change_percent >= 0 ? '+' : ''}
                        {result.day_change_percent.toFixed(2)}%
                      </td>
                      <td className="px-4 py-4 text-center">
                        <span
                          className={`px-2 py-1 rounded-md text-[10px] font-semibold tracking-wider border ${signalBadge(result.dominant_signal)}`}
                        >
                          {result.dominant_signal}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <div className="w-16 h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                result.dominant_signal === 'BULLISH'
                                  ? 'bg-gradient-to-r from-spark-emerald to-spark-cyan'
                                  : result.dominant_signal === 'BEARISH'
                                    ? 'bg-gradient-to-r from-spark-rose to-spark-amber'
                                    : 'bg-bone-400'
                              }`}
                              style={{
                                width: `${Math.min(result.total_score, 100)}%`,
                              }}
                            />
                          </div>
                          <span className="text-bone-100 text-sm font-mono">
                            {result.total_score.toFixed(0)}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-1">
                          {result.patterns_found
                            .slice(0, 3)
                            .map((pattern, idx) => (
                              <span
                                key={idx}
                                className={`px-2 py-0.5 rounded-md text-[10px] ${strengthColor(pattern.strength)} bg-white/[0.04] border border-white/[0.06]`}
                                title={`Score: ${pattern.score}`}
                              >
                                {pattern.type.replace('_', ' ')}
                              </span>
                            ))}
                          {result.patterns_found.length > 3 && (
                            <span className="px-2 py-0.5 rounded-md text-[10px] text-bone-500 bg-white/[0.04] border border-white/[0.06]">
                              +{result.patterns_found.length - 3}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Link
                            href={`/analyze?symbol=${result.symbol}`}
                            className="px-3 py-1 text-xs bg-white/[0.06] border border-white/[0.08] text-bone-100 rounded-lg hover:bg-spark-violet/15 hover:border-spark-violet/30 transition-all"
                          >
                            Analyze
                          </Link>
                          <Link
                            href={`/chart/${result.symbol}`}
                            className="px-3 py-1 text-xs bg-white/[0.03] border border-white/[0.06] text-bone-400 rounded-lg hover:text-bone-100 transition-all"
                          >
                            Chart
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {results.length === 0 && !loading && (
                <div className="text-center py-12 text-bone-500 text-sm">
                  No stocks matched your filters. Try lowering the min score or
                  selecting more patterns.
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
