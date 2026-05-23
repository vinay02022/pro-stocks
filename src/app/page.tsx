'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import StockSearch from '@/components/StockSearch';
import Recommendations from '@/components/Recommendations';
import QuickScan from '@/components/QuickScan';
import TopNav from '@/components/TopNav';
import {
  Search,
  Newspaper,
  History,
  BarChart3,
  Sparkles,
  Shield,
  Brain,
  Zap,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';

const STEPS = [
  {
    icon: Search,
    title: 'Search any stock',
    body: 'Type RELIANCE, TCS, INFY — anything on NSE.',
    accent: 'from-spark-cyan to-spark-violet',
  },
  {
    icon: Brain,
    title: 'AI reads the tape',
    body: '15+ indicators feed a Gemini reasoning loop.',
    accent: 'from-spark-violet to-spark-rose',
  },
  {
    icon: Shield,
    title: 'Deterministic risk gate',
    body: 'Position sizing, stop-loss, and exposure caps.',
    accent: 'from-spark-emerald to-spark-cyan',
  },
  {
    icon: TrendingUp,
    title: 'You decide & execute',
    body: 'No auto-trading. The human stays in command.',
    accent: 'from-spark-amber to-spark-emerald',
  },
];

const QUICK_ACTIONS = [
  {
    href: '/analyze',
    label: 'Analyze',
    icon: BarChart3,
    color: 'text-spark-cyan',
    dotColor: 'bg-spark-cyan',
  },
  {
    href: '/scanner',
    label: 'Scanner',
    icon: Search,
    color: 'text-spark-emerald',
    dotColor: 'bg-spark-emerald',
  },
  {
    href: '/backtest',
    label: 'Backtest',
    icon: History,
    color: 'text-spark-amber',
    dotColor: 'bg-spark-amber',
  },
  {
    href: '/news',
    label: 'News',
    icon: Newspaper,
    color: 'text-spark-violet',
    dotColor: 'bg-spark-violet',
  },
];

export default function Home() {
  const router = useRouter();

  const handleStockSelect = (symbol: string) => {
    router.push(`/analyze?symbol=${symbol}`);
  };

  return (
    <>
      <TopNav />

      <main className="relative min-h-screen">
        {/* Hero */}
        <section className="relative overflow-hidden">
          {/* Hero ambient glow */}
          <div
            aria-hidden
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                'radial-gradient(ellipse 60% 50% at 50% 0%, rgba(167,139,250,0.18), transparent 60%)',
            }}
          />

          <div className="relative max-w-[1400px] mx-auto px-4 sm:px-6 pt-12 sm:pt-20 pb-8 sm:pb-14 text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs text-bone-300 animate-fade-up">
              <Sparkles className="w-3.5 h-3.5 text-spark-violet" />
              <span>AI-assisted trading for Indian markets</span>
              <span className="text-bone-500">·</span>
              <span className="text-spark-emerald font-medium">Beta</span>
            </div>

            <h1
              className="mt-6 text-display font-bold text-5xl sm:text-6xl md:text-7xl tracking-[-0.02em] leading-[1.05] animate-fade-up"
              style={{ animationDelay: '80ms' }}
            >
              <span className="text-gradient">Trade with</span>{' '}
              <span className="text-gradient-spark">conviction</span>
              <span className="inline-block ml-1 w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full bg-spark-emerald align-middle animate-pulse-glow" />
            </h1>

            <p
              className="mt-5 text-base sm:text-lg text-bone-400 max-w-2xl mx-auto animate-fade-up"
              style={{ animationDelay: '160ms' }}
            >
              A precision toolkit that pairs{' '}
              <span className="text-bone-100">Gemini reasoning</span> with a
              deterministic risk engine — so every idea you see has already
              passed the gate.
            </p>

            {/* Primary CTAs */}
            <div
              className="mt-8 flex flex-wrap items-center justify-center gap-3 animate-fade-up"
              style={{ animationDelay: '240ms' }}
            >
              <button
                onClick={() => {
                  document
                    .getElementById('quick-scan')
                    ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }}
                className="btn-accent"
              >
                <Zap className="w-4 h-4" />
                Start a scan
              </button>
              <Link href="/analyze" className="btn-primary">
                <Brain className="w-4 h-4" />
                Analyze a stock
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {/* Search */}
            <div
              className="mt-10 max-w-2xl mx-auto animate-fade-up"
              style={{ animationDelay: '320ms' }}
            >
              <StockSearch
                onSelect={handleStockSelect}
                placeholder="Or jump straight in — search RELIANCE, TCS, TATASTEEL…"
              />
            </div>

            {/* Quick action chips */}
            <div
              className="mt-6 flex flex-wrap items-center justify-center gap-2 animate-fade-up"
              style={{ animationDelay: '400ms' }}
            >
              {QUICK_ACTIONS.map(
                ({ href, label, icon: Icon, color, dotColor }) => (
                  <Link
                    key={href}
                    href={href}
                    className="group inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full glass glass-hover text-xs text-bone-300"
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${dotColor} animate-sparkle`}
                    />
                    <Icon className={`w-3.5 h-3.5 ${color}`} />
                    <span className="font-medium">{label}</span>
                  </Link>
                )
              )}
            </div>
          </div>
        </section>

        {/* Quick Scan — inline */}
        <section
          id="quick-scan"
          className="max-w-[1400px] mx-auto px-4 sm:px-6 py-10 scroll-mt-20"
        >
          <QuickScan />
        </section>

        <div className="max-w-[1400px] mx-auto px-4 sm:px-6">
          <div className="divider-spark" />
        </div>

        {/* How it works */}
        <section className="max-w-[1400px] mx-auto px-4 sm:px-6 py-14">
          <div className="text-center mb-10 animate-fade-up">
            <div className="text-xs uppercase tracking-[0.18em] text-bone-400 mb-2">
              How it works
            </div>
            <h2 className="text-3xl sm:text-4xl text-display font-semibold text-gradient">
              From symbol to a trade plan in seconds
            </h2>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {STEPS.map(({ icon: Icon, title, body, accent }, i) => (
              <div
                key={title}
                className="group glass glass-hover rounded-2xl p-5 relative overflow-hidden animate-fade-up"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <div className="flex items-start justify-between mb-4">
                  <span
                    className={`inline-flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br ${accent} text-ink-950 shadow-glow-violet`}
                  >
                    <Icon className="w-5 h-5" strokeWidth={2.4} />
                  </span>
                  <span className="text-xs font-mono text-bone-500">
                    0{i + 1}
                  </span>
                </div>
                <h3 className="text-bone-50 font-semibold text-base mb-1">
                  {title}
                </h3>
                <p className="text-sm text-bone-400 leading-relaxed">{body}</p>
                <span
                  aria-hidden
                  className="absolute -bottom-10 -right-10 w-32 h-32 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{
                    background:
                      'radial-gradient(circle, rgba(167,139,250,0.12), transparent 60%)',
                  }}
                />
              </div>
            ))}
          </div>
        </section>

        {/* Stats / Targets */}
        <section className="max-w-[1400px] mx-auto px-4 sm:px-6 pb-14">
          <div className="grid sm:grid-cols-3 gap-4">
            {[
              {
                label: 'Target win rate',
                value: '60–70%',
                hint: 'over rolling windows',
                dot: 'bg-spark-emerald',
              },
              {
                label: 'Max daily loss',
                value: '2%',
                hint: 'hard portfolio cap',
                dot: 'bg-spark-rose',
              },
              {
                label: 'Position size',
                value: '≤ 5%',
                hint: 'per single trade',
                dot: 'bg-spark-cyan',
              },
            ].map((s, i) => (
              <div
                key={s.label}
                className="glass rounded-2xl p-5 relative animate-fade-up"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <span className={`absolute top-4 right-4 dot-spark ${s.dot}`} />
                <div className="text-xs uppercase tracking-[0.16em] text-bone-400">
                  {s.label}
                </div>
                <div className="mt-2 text-4xl font-display font-semibold text-gradient">
                  {s.value}
                </div>
                <div className="mt-1 text-sm text-bone-500">{s.hint}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Market Movers */}
        <section className="max-w-[1400px] mx-auto px-4 sm:px-6 pb-20">
          <div className="flex items-end justify-between mb-5">
            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-bone-400 mb-2">
                Market pulse
              </div>
              <h2 className="text-2xl sm:text-3xl text-display font-semibold text-gradient">
                Movers, losers & high-volume
              </h2>
            </div>
          </div>
          <Recommendations />
        </section>

        {/* Footer */}
        <footer className="border-t border-white/[0.05] py-8">
          <div className="max-w-[1400px] mx-auto px-4 sm:px-6 flex flex-wrap items-center justify-between gap-4 text-xs text-bone-500">
            <div className="flex items-center gap-2">
              <span className="dot-spark bg-spark-violet" />
              <span>
                StockPro · AI suggests, human executes. Past performance is not
                a guarantee.
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/scanner"
                className="hover:text-bone-200 transition-colors"
              >
                Scanner
              </Link>
              <span>·</span>
              <Link
                href="/analyze"
                className="hover:text-bone-200 transition-colors"
              >
                Analyze
              </Link>
              <span>·</span>
              <Link
                href="/news"
                className="hover:text-bone-200 transition-colors"
              >
                News
              </Link>
            </div>
          </div>
        </footer>
      </main>
    </>
  );
}
