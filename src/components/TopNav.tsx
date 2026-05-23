'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BarChart3, Search, History, Newspaper, Sparkles } from 'lucide-react';

const NAV = [
  { href: '/analyze', label: 'Analyze', icon: BarChart3 },
  { href: '/scanner', label: 'Scanner', icon: Search },
  { href: '/backtest', label: 'Backtest', icon: History },
  { href: '/news', label: 'News', icon: Newspaper },
];

export default function TopNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 backdrop-blur-2xl bg-ink-950/70 border-b border-white/[0.05]">
      <div className="max-w-[1800px] mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
        <Link
          href="/"
          className="group flex items-center gap-2.5 transition-opacity hover:opacity-90"
        >
          <span className="relative inline-flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-spark-emerald via-spark-cyan to-spark-violet shadow-glow-violet">
            <Sparkles className="w-4.5 h-4.5 text-ink-950" strokeWidth={2.5} />
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-spark-rose animate-sparkle" />
          </span>
          <span className="text-display font-bold text-lg tracking-tight">
            <span className="text-bone-50">Stock</span>
            <span className="text-gradient-spark">Pro</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active =
              pathname === href || pathname?.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={`relative px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-300 flex items-center gap-2 ${
                  active
                    ? 'text-bone-50 bg-white/[0.06] border border-white/[0.08]'
                    : 'text-bone-400 hover:text-bone-100 hover:bg-white/[0.03]'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
                {active && (
                  <span className="absolute -bottom-px left-3 right-3 h-px bg-gradient-to-r from-transparent via-spark-violet to-transparent" />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-bone-400">
            <span className="w-1.5 h-1.5 rounded-full bg-spark-emerald animate-pulse-glow" />
            Live
          </span>
        </div>
      </div>
    </header>
  );
}
