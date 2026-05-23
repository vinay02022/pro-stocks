'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import StockSearch from '@/components/StockSearch';
import AdvancedChart from '@/components/AdvancedChart';
import NewsWidget from '@/components/NewsWidget';
import TopNav from '@/components/TopNav';
import { analyzeSymbol, TradeSuggestion } from '@/lib/api';
import {
  Brain,
  Search,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  Target,
  AlertTriangle,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

const LOADING_STEPS = [
  { label: 'Fetching market data…', hint: 'Pulling latest candles' },
  { label: 'Computing indicators…', hint: '15+ technical signals' },
  { label: 'Reasoning with Gemini AI…', hint: 'Building trade thesis' },
  { label: 'Validating risk gate…', hint: 'Position size & stop-loss' },
  { label: 'Preparing your trade plan…', hint: 'Final assembly' },
];

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
  const [loadingStep, setLoadingStep] = useState(0);
  const stepTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (symbolFromUrl && !hasAnalyzed) {
      setSymbol(symbolFromUrl);
      setShowChart(true);
      runAnalysis(symbolFromUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbolFromUrl, hasAnalyzed]);

  const runAnalysis = async (targetSymbol: string) => {
    if (!targetSymbol.trim()) {
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setHasAnalyzed(true);
    setLoadingStep(0);

    if (stepTimer.current) {
      clearInterval(stepTimer.current);
    }
    stepTimer.current = setInterval(() => {
      setLoadingStep((s) => Math.min(s + 1, LOADING_STEPS.length - 1));
    }, 3500);

    try {
      const data = await analyzeSymbol({ symbol: targetSymbol.trim() });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      if (stepTimer.current) {
        clearInterval(stepTimer.current);
      }
      setLoading(false);
    }
  };

  const handleAnalyze = async (sym?: string) => {
    const targetSymbol = sym || symbol;
    if (!targetSymbol.trim()) {
      return;
    }

    setShowChart(true);
    router.push(`/analyze?symbol=${targetSymbol}`);
    await runAnalysis(targetSymbol);
  };

  const handleStockSelect = (sym: string) => {
    setSymbol(sym);
    setShowChart(true);
    setResult(null);
    router.push(`/analyze?symbol=${sym}`, { scroll: false });
  };

  return (
    <>
      <TopNav />
      <main className="min-h-screen">
        {/* Search bar */}
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 pt-6 pb-4">
          <div className="glass rounded-2xl p-3 flex flex-wrap items-center gap-3 animate-fade-up">
            <div className="flex-1 min-w-[240px]">
              <StockSearch
                onSelect={handleStockSelect}
                placeholder="Search stocks — TCS, RELIANCE, INFY…"
              />
            </div>
            <button
              onClick={() => handleAnalyze()}
              disabled={loading || !symbol.trim()}
              className="btn-accent text-sm"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/80 border-t-transparent rounded-full animate-spin" />
                  Analyzing…
                </>
              ) : (
                <>
                  <Brain className="w-4 h-4" />
                  AI Analyze
                </>
              )}
            </button>
          </div>
        </div>

        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 pb-12">
          {/* Error */}
          {error && (
            <div className="rounded-2xl border border-spark-rose/25 bg-spark-rose/[0.06] p-4 mb-4 flex items-start gap-3 animate-fade-in">
              <AlertTriangle className="w-5 h-5 text-spark-rose flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-spark-rose font-medium">{error}</p>
                <p className="text-spark-rose/70 text-xs mt-1">
                  The server may be waking up. Wait ~30 seconds and try again.
                </p>
              </div>
            </div>
          )}

          {/* Chart + News */}
          {showChart && symbol && (
            <div
              className="grid grid-cols-1 xl:grid-cols-4 gap-4 mb-4 animate-fade-up"
              style={{ animationDelay: '80ms' }}
            >
              <div className="xl:col-span-3">
                <AdvancedChart symbol={symbol} />
              </div>
              <div className="xl:col-span-1">
                <NewsWidget symbol={symbol} maxArticles={6} />
              </div>
            </div>
          )}

          {/* Loading state — progressive */}
          {loading && (
            <div className="glass rounded-2xl p-8 sm:p-10 animate-fade-in">
              <div className="flex items-center gap-4 mb-6">
                <div className="relative w-12 h-12 flex-shrink-0">
                  <div className="absolute inset-0 rounded-full border-2 border-white/10" />
                  <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-spark-cyan border-r-spark-violet animate-spin" />
                  <Sparkles className="absolute inset-0 m-auto w-4 h-4 text-spark-violet" />
                </div>
                <div className="min-w-0">
                  <p className="text-bone-50 text-lg font-semibold">
                    Running AI analysis for{' '}
                    <span className="text-gradient-spark">{symbol}</span>
                  </p>
                  <p className="text-sm text-bone-400 mt-0.5">
                    First request may take 30–60s as the server wakes up.
                  </p>
                </div>
              </div>

              <div className="space-y-2.5">
                {LOADING_STEPS.map((s, i) => {
                  const done = i < loadingStep;
                  const active = i === loadingStep;
                  return (
                    <div
                      key={s.label}
                      className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-500 ${
                        active
                          ? 'bg-spark-violet/10 border-spark-violet/25'
                          : done
                            ? 'bg-spark-emerald/[0.06] border-spark-emerald/15'
                            : 'bg-white/[0.02] border-white/[0.05] opacity-60'
                      }`}
                    >
                      <span className="flex-shrink-0">
                        {done ? (
                          <CheckCircle2 className="w-4 h-4 text-spark-emerald" />
                        ) : active ? (
                          <span className="block w-4 h-4 rounded-full border-2 border-spark-violet border-t-transparent animate-spin" />
                        ) : (
                          <span className="block w-4 h-4 rounded-full border-2 border-white/15" />
                        )}
                      </span>
                      <div className="flex-1 flex items-center justify-between gap-3 min-w-0">
                        <span
                          className={`text-sm font-medium ${
                            active
                              ? 'text-bone-50'
                              : done
                                ? 'text-bone-200'
                                : 'text-bone-400'
                          }`}
                        >
                          {s.label}
                        </span>
                        <span className="text-xs text-bone-500 truncate">
                          {s.hint}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Results */}
          {result && !loading && <TradeResult data={result} />}

          {/* Empty */}
          {!symbol && !loading && !result && (
            <div className="glass rounded-2xl p-12 text-center animate-fade-up">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-spark-violet/15 via-spark-cyan/15 to-spark-emerald/15 border border-white/[0.08] mb-5">
                <Search className="w-7 h-7 text-spark-violet" />
              </div>
              <h2 className="text-2xl text-display font-semibold text-gradient mb-2">
                Search for a stock to analyze
              </h2>
              <p className="text-bone-400 mb-6">
                Try RELIANCE, TCS, INFY, or TATASTEEL.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-2">
                {['TCS', 'RELIANCE', 'INFY', 'HDFC'].map((s) => (
                  <button
                    key={s}
                    onClick={() => handleStockSelect(s)}
                    className="btn-ghost text-xs"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  );
}

function TradeResult({ data }: { data: TradeSuggestion }) {
  const { idea, risk_plan, explanation } = data;
  const isApproved = risk_plan.validation_status === 'APPROVED';
  const dirColor =
    idea.direction === 'LONG'
      ? 'from-spark-emerald to-spark-cyan'
      : idea.direction === 'SHORT'
        ? 'from-spark-rose to-spark-amber'
        : 'from-bone-400 to-bone-500';

  return (
    <div className="space-y-4 animate-fade-up">
      {/* Header card */}
      <div className="glass rounded-2xl p-5 sm:p-6 relative overflow-hidden">
        <span className="absolute top-4 right-4 dot-spark bg-spark-violet" />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-wrap">
            <span
              className={`px-3.5 py-1.5 rounded-xl text-base font-bold text-ink-950 bg-gradient-to-r ${dirColor}`}
            >
              {idea.direction}
            </span>
            <span className="text-2xl font-display font-bold text-bone-50 tracking-tight">
              {idea.symbol}
            </span>
            <span
              className={`px-3 py-1 rounded-lg text-xs font-semibold tracking-wider border ${
                isApproved
                  ? 'bg-spark-emerald/10 text-spark-emerald border-spark-emerald/20'
                  : 'bg-spark-rose/10 text-spark-rose border-spark-rose/20'
              }`}
            >
              {isApproved ? (
                <span className="inline-flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" />{' '}
                  {risk_plan.validation_status}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3" />{' '}
                  {risk_plan.validation_status}
                </span>
              )}
            </span>
          </div>

          <div className="text-right">
            <p className="text-xs uppercase tracking-[0.16em] text-bone-500">
              Confidence
            </p>
            <p className="text-3xl font-display font-bold text-gradient-spark">
              {(idea.confidence_band.mid * 100).toFixed(0)}%
            </p>
            <p className="text-[10px] text-bone-500 font-mono">
              {(idea.confidence_band.low * 100).toFixed(0)}% –{' '}
              {(idea.confidence_band.high * 100).toFixed(0)}%
            </p>
          </div>
        </div>

        <div className="mt-5 pt-5 border-t border-white/[0.05]">
          <p className="text-bone-200 leading-relaxed">{explanation.summary}</p>
        </div>
      </div>

      {/* Entry & Risk */}
      {isApproved && risk_plan.approved_plan && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="glass rounded-2xl p-5">
            <h2 className="text-base font-semibold text-bone-50 mb-4 flex items-center gap-2">
              <Target className="w-4 h-4 text-spark-cyan" />
              Entry Plan
            </h2>
            <div className="space-y-2.5">
              <Row
                label="Entry price"
                value={`₹${idea.suggested_entry.entry_price?.toFixed(2) || 'Market'}`}
              />
              <Row label="Entry type" value={idea.suggested_entry.entry_type} />
            </div>
          </div>

          <div className="glass rounded-2xl p-5">
            <h2 className="text-base font-semibold text-bone-50 mb-4 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-spark-amber" />
              Risk Plan
            </h2>
            <div className="space-y-2.5">
              <Row
                label="Position size"
                value={`${risk_plan.approved_plan.position_size} shares`}
              />
              <Row
                label="Stop loss"
                value={`₹${risk_plan.approved_plan.stop_loss.toFixed(2)}`}
                valueClass="text-spark-rose"
              />
              <Row
                label="Max loss"
                value={`₹${risk_plan.approved_plan.max_loss_amount.toLocaleString()} (${risk_plan.approved_plan.max_loss_percent}%)`}
                valueClass="text-spark-rose"
              />
              <Row
                label="Risk : Reward"
                value={`1 : ${risk_plan.approved_plan.risk_reward_ratio}`}
                valueClass="text-spark-emerald"
              />
            </div>
          </div>
        </div>
      )}

      {/* Take-profit targets */}
      {isApproved && risk_plan.approved_plan?.take_profit && (
        <div className="glass rounded-2xl p-5">
          <h2 className="text-base font-semibold text-bone-50 mb-4 flex items-center gap-2">
            <Target className="w-4 h-4 text-spark-emerald" />
            Take Profit Targets
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {risk_plan.approved_plan.take_profit.map((tp, i) => (
              <div
                key={i}
                className="rounded-xl p-4 text-center border border-spark-emerald/20 bg-spark-emerald/[0.06] relative overflow-hidden"
              >
                <span className="absolute top-2 right-2 dot-spark bg-spark-emerald" />
                <p className="text-xs text-spark-emerald/80 mb-1">{tp.label}</p>
                <p className="text-xl font-display font-bold text-spark-emerald">
                  ₹{tp.price.toFixed(2)}
                </p>
                <p className="text-[10px] text-spark-emerald/60 mt-0.5">
                  Exit {tp.exit_percent}%
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rejection */}
      {!isApproved &&
        risk_plan.rejection_reasons &&
        risk_plan.rejection_reasons.length > 0 && (
          <div className="rounded-2xl border border-spark-rose/25 bg-spark-rose/[0.06] p-5">
            <h2 className="text-base font-semibold text-spark-rose mb-3 flex items-center gap-2">
              <XCircle className="w-4 h-4" />
              Why this trade was blocked
            </h2>
            <ul className="space-y-2">
              {risk_plan.rejection_reasons.map((r, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-spark-rose/90 text-sm"
                >
                  <span className="text-spark-rose mt-0.5">×</span>
                  {r}
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs text-spark-rose/60">
              The risk gate protects your capital. Adjust portfolio settings or
              wait for a better setup.
            </p>
          </div>
        )}

      {/* Reasoning */}
      <div className="glass rounded-2xl p-5">
        <h2 className="text-base font-semibold text-bone-50 mb-4 flex items-center gap-2">
          <Brain className="w-4 h-4 text-spark-violet" />
          AI Reasoning
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-xs uppercase tracking-[0.18em] text-spark-emerald mb-3 flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Primary factors
            </h3>
            <ul className="space-y-2">
              {idea.reasoning.primary_factors.map((f, i) => (
                <li
                  key={i}
                  className="text-sm text-bone-200 pl-3 border-l-2 border-spark-emerald/40"
                >
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-xs uppercase tracking-[0.18em] text-spark-amber mb-3 flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5" />
              Concerns
            </h3>
            <ul className="space-y-2">
              {idea.reasoning.concerns.map((c, i) => (
                <li
                  key={i}
                  className="text-sm text-bone-200 pl-3 border-l-2 border-spark-amber/40"
                >
                  {c}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Risk disclosure */}
      <div className="rounded-2xl border border-spark-amber/20 bg-spark-amber/[0.05] p-5">
        <h2 className="text-base font-semibold text-spark-amber mb-2 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          Risk disclosure
        </h2>
        <p className="text-sm text-spark-amber/85">
          {explanation.risk_disclosure}
        </p>
      </div>

      {/* Checklist */}
      <div className="glass rounded-2xl p-5">
        <h2 className="text-base font-semibold text-bone-50 mb-4 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-spark-cyan" />
          Before you trade — checklist
        </h2>
        <div className="grid md:grid-cols-2 gap-2">
          {explanation.human_checklist.map((item, i) => (
            <label
              key={i}
              className="flex items-start gap-3 cursor-pointer group p-2.5 rounded-lg hover:bg-white/[0.04] transition-colors"
            >
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 rounded border-white/15 bg-white/[0.05] text-spark-violet focus:ring-spark-violet focus:ring-offset-0"
              />
              <span className="text-sm text-bone-300 group-hover:text-bone-100 transition-colors">
                {item}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Confidence statement */}
      <div className="rounded-2xl border border-spark-violet/20 bg-spark-violet/[0.05] p-5">
        <p className="text-sm text-bone-200">
          <strong className="text-spark-violet">Statistical note: </strong>
          {explanation.confidence_statement}
        </p>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  valueClass = 'text-bone-50',
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04] last:border-b-0">
      <span className="text-bone-400 text-sm">{label}</span>
      <span className={`font-semibold font-mono text-sm ${valueClass}`}>
        {value}
      </span>
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="w-10 h-10 border-2 border-spark-violet border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <AnalyzeContent />
    </Suspense>
  );
}
