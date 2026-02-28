'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface PatternResult {
  type: string;
  signal: string;
  strength: string;
  score: number;
  details: Record<string, any>;
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
  { id: 'all', name: 'All Patterns' },
  { id: 'breakout', name: 'Breakout' },
  { id: 'momentum', name: 'Momentum' },
  { id: 'volume_spike', name: 'Volume Spike' },
  { id: 'ema_crossover', name: 'EMA Crossover' },
  { id: 'rsi_extreme', name: 'RSI Extreme' },
  { id: 'macd_crossover', name: 'MACD Crossover' },
  { id: 'sr_bounce', name: 'S/R Bounce' },
  { id: 'bb_squeeze', name: 'BB Squeeze' },
];

const TIMEFRAMES = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1H' },
  { value: '1d', label: 'Daily' },
];

export default function ScannerPage() {
  const [results, setResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

    try {
      const patterns = selectedPatterns.includes('all')
        ? 'all'
        : selectedPatterns.join(',');
      let url = `http://localhost:8000/api/v1/scanner/scan?patterns=${patterns}&timeframe=${timeframe}&min_score=${minScore}`;

      if (signalFilter) {
        url += `&signal=${signalFilter}`;
      }

      const res = await fetch(url);
      if (!res.ok) {
        throw new Error('Scan failed');
      }

      const data: ScanResponse = await res.json();
      setResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runScan();
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
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BULLISH':
        return 'text-green-400 bg-green-500/20';
      case 'BEARISH':
        return 'text-red-400 bg-red-500/20';
      default:
        return 'text-gray-400 bg-gray-500/20';
    }
  };

  const getStrengthColor = (strength: string) => {
    switch (strength) {
      case 'very_strong':
        return 'text-green-400';
      case 'strong':
        return 'text-green-500';
      case 'moderate':
        return 'text-yellow-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <main className="min-h-screen bg-[#0b0e11]">
      {/* Header */}
      <div className="bg-[#131722] border-b border-[#2a2e39]">
        <div className="max-w-[1800px] mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="text-xl font-bold text-white hover:text-blue-400 transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-8 h-8 text-blue-500"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                  />
                </svg>
                StockPro
              </Link>
              <span className="text-gray-500">|</span>
              <h1 className="text-lg font-semibold text-white">
                Market Scanner
              </h1>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/analyze"
                className="px-4 py-2 text-sm text-gray-300 hover:text-white bg-[#1e222d] rounded-lg transition-colors"
              >
                Analyze
              </Link>
              <Link
                href="/backtest"
                className="px-4 py-2 text-sm text-gray-300 hover:text-white bg-[#1e222d] rounded-lg transition-colors"
              >
                Backtest
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-[1800px] mx-auto px-4 py-6">
        {/* Filters */}
        <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            {/* Pattern Selector */}
            <div className="flex-1">
              <label className="text-xs text-gray-500 uppercase mb-2 block">
                Patterns
              </label>
              <div className="flex flex-wrap gap-2">
                {PATTERNS.map((pattern) => (
                  <button
                    key={pattern.id}
                    onClick={() => togglePattern(pattern.id)}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      selectedPatterns.includes(pattern.id)
                        ? 'bg-blue-600 text-white'
                        : 'bg-[#1e222d] text-gray-400 hover:text-white'
                    }`}
                  >
                    {pattern.name}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-[#2a2e39]">
            {/* Timeframe */}
            <div>
              <label className="text-xs text-gray-500 uppercase mb-2 block">
                Timeframe
              </label>
              <div className="flex bg-[#1e222d] rounded-lg p-1">
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf.value}
                    onClick={() => setTimeframe(tf.value)}
                    className={`px-3 py-1.5 text-sm rounded transition-colors ${
                      timeframe === tf.value
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    {tf.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Min Score */}
            <div>
              <label className="text-xs text-gray-500 uppercase mb-2 block">
                Min Score
              </label>
              <input
                type="number"
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="w-20 px-3 py-2 bg-[#1e222d] border border-[#2a2e39] rounded-lg text-white text-sm"
                min={0}
                max={100}
              />
            </div>

            {/* Signal Filter */}
            <div>
              <label className="text-xs text-gray-500 uppercase mb-2 block">
                Signal
              </label>
              <div className="flex bg-[#1e222d] rounded-lg p-1">
                <button
                  onClick={() => setSignalFilter(null)}
                  className={`px-3 py-1.5 text-sm rounded transition-colors ${
                    !signalFilter
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setSignalFilter('BULLISH')}
                  className={`px-3 py-1.5 text-sm rounded transition-colors ${
                    signalFilter === 'BULLISH'
                      ? 'bg-green-600 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  Bullish
                </button>
                <button
                  onClick={() => setSignalFilter('BEARISH')}
                  className={`px-3 py-1.5 text-sm rounded transition-colors ${
                    signalFilter === 'BEARISH'
                      ? 'bg-red-600 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  Bearish
                </button>
              </div>
            </div>

            {/* Scan Button */}
            <div className="ml-auto">
              <label className="text-xs text-gray-500 uppercase mb-2 block">
                &nbsp;
              </label>
              <button
                onClick={runScan}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 transition-colors flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                      />
                    </svg>
                    Scan Now
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg mb-4 text-red-400">
            {error}
          </div>
        )}

        {/* Results */}
        <div className="bg-[#131722] rounded-lg border border-[#2a2e39] overflow-hidden">
          {/* Results Header */}
          <div className="px-4 py-3 border-b border-[#2a2e39] flex items-center justify-between">
            <span className="text-gray-400">
              Found{' '}
              <span className="text-white font-semibold">{results.length}</span>{' '}
              stocks matching criteria
            </span>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#1e222d]">
                <tr>
                  <th
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-white"
                    onClick={() => handleSort('symbol')}
                  >
                    Symbol{' '}
                    {sortField === 'symbol' &&
                      (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Price
                  </th>
                  <th
                    className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-white"
                    onClick={() => handleSort('change')}
                  >
                    Change{' '}
                    {sortField === 'change' &&
                      (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Signal
                  </th>
                  <th
                    className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-white"
                    onClick={() => handleSort('score')}
                  >
                    Score{' '}
                    {sortField === 'score' &&
                      (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Patterns
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2a2e39]">
                {sortedResults.map((result) => (
                  <tr
                    key={result.symbol}
                    className="hover:bg-[#1e222d] transition-colors"
                  >
                    <td className="px-4 py-4">
                      <span className="font-semibold text-white">
                        {result.symbol}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-right text-white font-mono">
                      ₹{result.current_price.toFixed(2)}
                    </td>
                    <td
                      className={`px-4 py-4 text-right font-mono ${
                        result.day_change_percent >= 0
                          ? 'text-green-400'
                          : 'text-red-400'
                      }`}
                    >
                      {result.day_change_percent >= 0 ? '+' : ''}
                      {result.day_change_percent.toFixed(2)}%
                    </td>
                    <td className="px-4 py-4 text-center">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${getSignalColor(result.dominant_signal)}`}
                      >
                        {result.dominant_signal}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 h-2 bg-[#1e222d] rounded-full overflow-hidden">
                          <div
                            className={`h-full ${result.dominant_signal === 'BULLISH' ? 'bg-green-500' : result.dominant_signal === 'BEARISH' ? 'bg-red-500' : 'bg-gray-500'}`}
                            style={{
                              width: `${Math.min(result.total_score, 100)}%`,
                            }}
                          />
                        </div>
                        <span className="text-white text-sm font-mono">
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
                              className={`px-2 py-0.5 rounded text-xs ${getStrengthColor(pattern.strength)} bg-[#1e222d]`}
                              title={`Score: ${pattern.score}`}
                            >
                              {pattern.type.replace('_', ' ')}
                            </span>
                          ))}
                        {result.patterns_found.length > 3 && (
                          <span className="px-2 py-0.5 rounded text-xs text-gray-500 bg-[#1e222d]">
                            +{result.patterns_found.length - 3}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <Link
                          href={`/analyze?symbol=${result.symbol}`}
                          className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                        >
                          Analyze
                        </Link>
                        <Link
                          href={`/chart/${result.symbol}`}
                          className="px-3 py-1 text-xs bg-[#1e222d] text-gray-300 rounded hover:text-white transition-colors"
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
              <div className="text-center py-12 text-gray-500">
                No stocks found matching the criteria. Try adjusting filters.
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
