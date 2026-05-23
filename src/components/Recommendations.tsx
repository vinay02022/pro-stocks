'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { TrendingUp, TrendingDown, BarChart2, Flame } from 'lucide-react';

interface Mover {
  symbol: string;
  name: string;
  sector: string;
  price: number;
  change_percent: number;
  volume: number;
}

interface MoversData {
  gainers: Mover[];
  losers: Mover[];
  high_volume: Mover[];
}

const LOADING_STEPS = [
  'Connecting to market data…',
  'Server is waking up (free tier)…',
  'This usually takes 30–60 seconds on first load…',
  'Almost there — fetching latest prices…',
];

type Tab = 'gainers' | 'losers' | 'volume';

const TABS: {
  id: Tab;
  label: string;
  icon: typeof TrendingUp;
  color: string;
  dot: string;
}[] = [
  {
    id: 'gainers',
    label: 'Top Gainers',
    icon: TrendingUp,
    color: 'text-spark-emerald',
    dot: 'bg-spark-emerald',
  },
  {
    id: 'losers',
    label: 'Top Losers',
    icon: TrendingDown,
    color: 'text-spark-rose',
    dot: 'bg-spark-rose',
  },
  {
    id: 'volume',
    label: 'High Volume',
    icon: Flame,
    color: 'text-spark-amber',
    dot: 'bg-spark-amber',
  },
];

export default function Recommendations() {
  const [movers, setMovers] = useState<MoversData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('gainers');
  const [loadingStep, setLoadingStep] = useState(0);
  const stepTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const fetchMovers = async () => {
      stepTimer.current = setInterval(() => {
        setLoadingStep((s) => Math.min(s + 1, LOADING_STEPS.length - 1));
      }, 7000);

      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/market/movers?count=8`
        );
        if (!res.ok) {
          throw new Error('Could not load market data');
        }
        const result = await res.json();
        setMovers(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        if (stepTimer.current) {
          clearInterval(stepTimer.current);
        }
        setIsLoading(false);
      }
    };

    fetchMovers();
    return () => {
      if (stepTimer.current) {
        clearInterval(stepTimer.current);
      }
    };
  }, []);

  if (isLoading) {
    return (
      <div className="glass rounded-2xl p-6 animate-fade-up">
        <div className="flex items-center gap-3 mb-5">
          <div className="relative w-9 h-9 flex-shrink-0">
            <div className="absolute inset-0 rounded-full border-2 border-white/10" />
            <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-spark-cyan border-r-spark-violet animate-spin" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-bone-100 text-sm font-medium">
              {LOADING_STEPS[loadingStep]}
            </p>
            <p className="text-xs text-bone-500 mt-0.5">
              Backend is hosted on Render&apos;s free tier — first request can
              be slow.
            </p>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-16 rounded-xl skeleton"
              style={{ animationDelay: `${i * 80}ms` }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass rounded-2xl p-8 text-center animate-fade-up">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-spark-rose/10 border border-spark-rose/20 mb-3">
          <BarChart2 className="w-5 h-5 text-spark-rose" />
        </div>
        <p className="text-bone-100 font-medium mb-1">
          Market data unavailable
        </p>
        <p className="text-sm text-bone-400 max-w-md mx-auto">
          The backend may still be waking up. Wait ~30 seconds and refresh —
          this is a quirk of the free tier, not your connection.
        </p>
      </div>
    );
  }

  const getActiveList = (): Mover[] => {
    if (!movers) {
      return [];
    }
    if (activeTab === 'gainers') {
      return movers.gainers;
    }
    if (activeTab === 'losers') {
      return movers.losers;
    }
    return movers.high_volume;
  };

  const list = getActiveList();

  return (
    <div className="glass rounded-2xl p-5 sm:p-6 animate-fade-up">
      {/* Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 mb-5 p-1 rounded-xl bg-white/[0.02] border border-white/[0.04] w-fit">
        {TABS.map(({ id, label, icon: Icon, color, dot }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`relative px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-300 flex items-center gap-2 ${
                active
                  ? 'bg-white/[0.06] text-bone-50 border border-white/[0.08]'
                  : 'text-bone-400 hover:text-bone-200'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${dot} ${active ? 'animate-sparkle' : ''}`}
              />
              <Icon className={`w-3.5 h-3.5 ${active ? color : ''}`} />
              {label}
            </button>
          );
        })}
      </div>

      {/* List */}
      <div className="grid sm:grid-cols-2 gap-3">
        {list.map((stock, i) => {
          const up = stock.change_percent >= 0;
          return (
            <Link
              key={stock.symbol}
              href={`/analyze?symbol=${stock.symbol}`}
              className="group glass glass-hover rounded-xl p-3.5 flex items-center justify-between gap-3 animate-fade-up"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div
                  className={`relative w-10 h-10 rounded-xl flex items-center justify-center text-ink-950 font-bold text-sm flex-shrink-0 ${
                    up
                      ? 'bg-gradient-to-br from-spark-emerald to-spark-cyan'
                      : 'bg-gradient-to-br from-spark-rose to-spark-amber'
                  }`}
                >
                  {up ? '▲' : '▼'}
                  <span
                    className={`absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full ${
                      up ? 'bg-spark-emerald' : 'bg-spark-rose'
                    } animate-sparkle`}
                  />
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-bone-50 group-hover:text-gradient-spark text-sm tracking-tight">
                    {stock.symbol}
                  </div>
                  <div className="text-xs text-bone-500 truncate max-w-[160px]">
                    {stock.name}
                  </div>
                </div>
              </div>

              <div className="text-right flex-shrink-0">
                <div className="font-mono text-sm text-bone-100">
                  ₹{stock.price.toFixed(2)}
                </div>
                <div
                  className={`text-xs font-medium ${
                    up ? 'text-spark-emerald' : 'text-spark-rose'
                  }`}
                >
                  {up ? '+' : ''}
                  {stock.change_percent.toFixed(2)}%
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {list.length === 0 && (
        <div className="text-center py-10 text-bone-500 text-sm">
          No data available
        </div>
      )}

      <div className="mt-5 pt-5 border-t border-white/[0.05] flex items-center justify-between gap-3">
        <p className="text-xs text-bone-500">
          Click any stock to load chart + run AI analysis
        </p>
        <span className="inline-flex items-center gap-1.5 text-xs text-bone-400">
          <span className="dot-spark bg-spark-emerald" />
          Live
        </span>
      </div>
    </div>
  );
}
