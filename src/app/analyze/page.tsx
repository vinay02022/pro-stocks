'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import StockSearch from '@/components/StockSearch';
import AdvancedChart from '@/components/AdvancedChart';
import NewsWidget from '@/components/NewsWidget';
import { analyzeSymbol, TradeSuggestion } from '@/lib/api';

function AnalyzeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const symbolFromUrl = searchParams.get('symbol');

  const [symbol, setSymbol] = useState(symbolFromUrl || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TradeSuggestion | null>(null);
  const [showChart, setShowChart] = useState(!!symbolFromUrl);
  const [hasAnalyzed, setHasAnalyzed] = useState(false);

  // Auto-analyze if symbol in URL on first load
  useEffect(() => {
    if (symbolFromUrl && !hasAnalyzed) {
      setSymbol(symbolFromUrl);
      setShowChart(true);
      runAnalysis(symbolFromUrl);
    }
  }, [symbolFromUrl, hasAnalyzed]);

  const runAnalysis = async (targetSymbol: string) => {
    if (!targetSymbol.trim()) {
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setHasAnalyzed(true);

    try {
      const data = await analyzeSymbol({ symbol: targetSymbol.trim() });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async (sym?: string) => {
    const targetSymbol = sym || symbol;
    if (!targetSymbol.trim()) {
      return;
    }

    setShowChart(true);

    // Update URL
    router.push(`/analyze?symbol=${targetSymbol}`);

    await runAnalysis(targetSymbol);
  };

  // Stock selection - only load chart, NO automatic analysis
  const handleStockSelect = (sym: string) => {
    setSymbol(sym);
    setShowChart(true);
    setResult(null); // Clear previous results
    // Update URL without triggering analysis
    router.push(`/analyze?symbol=${sym}`, { scroll: false });
    // DO NOT call handleAnalyze - user must click the button
  };

  return (
    <main className="min-h-screen bg-[#0b0e11]">
      {/* Header */}
      <div className="bg-[#131722] border-b border-[#2a2e39]">
        <div className="max-w-[1800px] mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
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
            <div className="flex-1 max-w-xl">
              <StockSearch
                onSelect={handleStockSelect}
                placeholder="Search stocks (e.g., TCS, RELIANCE, INFY)..."
              />
            </div>
            <button
              onClick={() => handleAnalyze()}
              disabled={loading || !symbol.trim()}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Analyzing...
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
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                  AI Analyze
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-[1800px] mx-auto px-4 py-4">
        {/* Error */}
        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg mb-4 flex items-center gap-3">
            <svg
              className="w-5 h-5 text-red-400 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Chart + News */}
        {showChart && symbol && (
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-4 mb-4">
            <div className="xl:col-span-3">
              <AdvancedChart symbol={symbol} />
            </div>
            <div className="xl:col-span-1">
              <NewsWidget symbol={symbol} maxArticles={6} />
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-8 text-center">
            <div className="w-12 h-12 border-3 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-300 text-lg">
              Running AI analysis for{' '}
              <span className="text-white font-semibold">{symbol}</span>
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Calculating indicators, generating trade idea, validating risk...
            </p>
          </div>
        )}

        {/* Results */}
        {result && !loading && <TradeResult data={result} />}

        {/* Empty State */}
        {!symbol && !loading && !result && (
          <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-12 text-center">
            <div className="w-20 h-20 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg
                className="w-10 h-10 text-blue-500"
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
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">
              Search for a stock to analyze
            </h2>
            <p className="text-gray-500">
              Enter a stock symbol like RELIANCE, TCS, INFY, or TATASTEEL
            </p>
            <div className="flex items-center justify-center gap-2 mt-6">
              {['TCS', 'RELIANCE', 'INFY', 'HDFC'].map((s) => (
                <button
                  key={s}
                  onClick={() => handleStockSelect(s)}
                  className="px-4 py-2 bg-[#1e222d] text-gray-300 rounded-lg hover:bg-[#2a2e39] transition-colors text-sm"
                >
                  {s}
                </button>
              ))}
            </div>
            <p className="text-gray-600 text-xs mt-4">
              Click a stock to load chart, then click &ldquo;AI Analyze&rdquo;
              to run analysis
            </p>
          </div>
        )}
      </div>
    </main>
  );
}

function TradeResult({ data }: { data: TradeSuggestion }) {
  const { idea, risk_plan, explanation } = data;
  const isApproved = risk_plan.validation_status === 'APPROVED';

  return (
    <div className="space-y-4">
      {/* Header Card */}
      <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-5">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <span
              className={`px-4 py-2 rounded-lg text-lg font-bold ${
                idea.direction === 'LONG'
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                  : idea.direction === 'SHORT'
                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                    : 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
              }`}
            >
              {idea.direction}
            </span>
            <span className="text-2xl font-bold text-white">{idea.symbol}</span>
            <span
              className={`px-3 py-1 rounded-lg text-sm font-medium ${
                isApproved
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                  : 'bg-red-500/20 text-red-400 border border-red-500/30'
              }`}
            >
              {risk_plan.validation_status}
            </span>
          </div>

          {/* Confidence Badge */}
          <div className="text-right">
            <p className="text-sm text-gray-500">Confidence</p>
            <p className="text-2xl font-bold text-blue-400">
              {(idea.confidence_band.mid * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-gray-500">
              Range: {(idea.confidence_band.low * 100).toFixed(0)}% -{' '}
              {(idea.confidence_band.high * 100).toFixed(0)}%
            </p>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-[#2a2e39]">
          <p className="text-gray-300">{explanation.summary}</p>
        </div>
      </div>

      {/* Entry & Risk Plan */}
      {isApproved && risk_plan.approved_plan && (
        <div className="grid md:grid-cols-2 gap-4">
          {/* Entry Plan */}
          <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-5">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg
                className="w-5 h-5 text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"
                />
              </svg>
              Entry Plan
            </h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center py-2 border-b border-[#2a2e39]">
                <span className="text-gray-400">Entry Price</span>
                <span className="font-semibold text-white">
                  Rs.{idea.suggested_entry.entry_price?.toFixed(2) || 'Market'}
                </span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-[#2a2e39]">
                <span className="text-gray-400">Entry Type</span>
                <span className="font-semibold text-white">
                  {idea.suggested_entry.entry_type}
                </span>
              </div>
            </div>
          </div>

          {/* Risk Plan */}
          <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-5">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg
                className="w-5 h-5 text-amber-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              Risk Plan
            </h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center py-2 border-b border-[#2a2e39]">
                <span className="text-gray-400">Position Size</span>
                <span className="font-semibold text-white">
                  {risk_plan.approved_plan.position_size} shares
                </span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-[#2a2e39]">
                <span className="text-gray-400">Stop Loss</span>
                <span className="font-semibold text-red-400">
                  Rs.{risk_plan.approved_plan.stop_loss.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-[#2a2e39]">
                <span className="text-gray-400">Max Loss</span>
                <span className="font-semibold text-red-400">
                  Rs.{risk_plan.approved_plan.max_loss_amount.toLocaleString()}{' '}
                  ({risk_plan.approved_plan.max_loss_percent}%)
                </span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-gray-400">Risk:Reward</span>
                <span className="font-semibold text-green-400">
                  1:{risk_plan.approved_plan.risk_reward_ratio}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Take Profit Targets */}
      {isApproved && risk_plan.approved_plan?.take_profit && (
        <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-5">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <svg
              className="w-5 h-5 text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Take Profit Targets
          </h2>
          <div className="grid grid-cols-3 gap-4">
            {risk_plan.approved_plan.take_profit.map((tp, i) => (
              <div
                key={i}
                className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 text-center"
              >
                <p className="text-sm text-green-400 mb-1">{tp.label}</p>
                <p className="text-xl font-bold text-green-300">
                  Rs.{tp.price.toFixed(2)}
                </p>
                <p className="text-xs text-green-400/70">
                  Exit {tp.exit_percent}%
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rejection Reasons */}
      {!isApproved &&
        risk_plan.rejection_reasons &&
        risk_plan.rejection_reasons.length > 0 && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-5">
            <h2 className="text-lg font-semibold text-red-400 mb-4 flex items-center gap-2">
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                />
              </svg>
              Why This Trade Was Rejected
            </h2>
            <ul className="space-y-2">
              {risk_plan.rejection_reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-red-300">
                  <span className="text-red-400 mt-0.5">×</span>
                  {r}
                </li>
              ))}
            </ul>
            <p className="mt-4 text-sm text-red-400/70">
              The risk validation engine has blocked this trade to protect your
              capital. Consider adjusting your portfolio settings or waiting for
              a better setup.
            </p>
          </div>
        )}

      {/* Reasoning */}
      <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-5">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <svg
            className="w-5 h-5 text-purple-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          AI Reasoning
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-medium text-green-400 mb-3 flex items-center gap-2 text-sm">
              <span className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center text-xs">
                ✓
              </span>
              Primary Factors
            </h3>
            <ul className="space-y-2">
              {idea.reasoning.primary_factors.map((f, i) => (
                <li
                  key={i}
                  className="text-sm text-gray-300 pl-4 border-l-2 border-green-500/50"
                >
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-medium text-amber-400 mb-3 flex items-center gap-2 text-sm">
              <span className="w-5 h-5 rounded-full bg-amber-500/20 flex items-center justify-center text-xs">
                !
              </span>
              Concerns
            </h3>
            <ul className="space-y-2">
              {idea.reasoning.concerns.map((c, i) => (
                <li
                  key={i}
                  className="text-sm text-gray-300 pl-4 border-l-2 border-amber-500/50"
                >
                  {c}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Risk Disclosure */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-5">
        <h2 className="text-lg font-semibold text-amber-400 mb-2 flex items-center gap-2">
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          Risk Disclosure
        </h2>
        <p className="text-amber-200/80">{explanation.risk_disclosure}</p>
      </div>

      {/* Checklist */}
      <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-5">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <svg
            className="w-5 h-5 text-blue-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
            />
          </svg>
          Before You Trade - Checklist
        </h2>
        <div className="grid md:grid-cols-2 gap-3">
          {explanation.human_checklist.map((item, i) => (
            <label
              key={i}
              className="flex items-start gap-3 cursor-pointer group p-2 rounded hover:bg-[#1e222d] transition-colors"
            >
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-gray-600 bg-[#1e222d] text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span className="text-sm text-gray-400 group-hover:text-gray-200 transition-colors">
                {item}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Confidence Statement */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-5">
        <p className="text-sm text-blue-300">
          <strong className="text-blue-400">Statistical Note:</strong>{' '}
          {explanation.confidence_statement}
        </p>
      </div>
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#0b0e11] flex items-center justify-center">
          <div className="w-10 h-10 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <AnalyzeContent />
    </Suspense>
  );
}
