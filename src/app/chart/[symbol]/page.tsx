'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import FullScreenChart from '@/components/FullScreenChart';

interface MarketIndex {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
}

export default function ChartPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = (params.symbol as string)?.toUpperCase() || '';

  const [searchQuery, setSearchQuery] = useState(symbol);
  const [marketIndices, setMarketIndices] = useState<MarketIndex[]>([
    {
      symbol: 'NIFTY',
      name: 'NIFTY 50',
      price: 22150.5,
      change: 125.3,
      changePercent: 0.57,
    },
    {
      symbol: 'SENSEX',
      name: 'SENSEX',
      price: 73158.24,
      change: 412.85,
      changePercent: 0.57,
    },
    {
      symbol: 'BANKNIFTY',
      name: 'BANK NIFTY',
      price: 46892.15,
      change: -156.4,
      changePercent: -0.33,
    },
  ]);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update time every second
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () =>
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Toggle true browser fullscreen
  const toggleFullscreen = useCallback(async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch (err) {
      console.error('Fullscreen error:', err);
    }
  }, []);

  // Handle ESC key to exit fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'F11') {
        e.preventDefault();
        toggleFullscreen();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [toggleFullscreen]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/chart/${searchQuery.trim().toUpperCase()}`);
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  // Theme colors
  const theme = {
    bg: isDarkMode ? 'bg-[#0b0e11]' : 'bg-gray-100',
    headerBg: isDarkMode ? 'bg-[#131722]' : 'bg-white',
    border: isDarkMode ? 'border-[#2a2e39]' : 'border-gray-200',
    text: isDarkMode ? 'text-white' : 'text-gray-900',
    textMuted: isDarkMode ? 'text-gray-400' : 'text-gray-500',
    inputBg: isDarkMode ? 'bg-[#1e222d]' : 'bg-gray-100',
    buttonBg: isDarkMode ? 'bg-[#1e222d]' : 'bg-gray-200',
    buttonHover: isDarkMode ? 'hover:bg-[#2a2e39]' : 'hover:bg-gray-300',
  };

  return (
    <div className={`min-h-screen ${theme.bg} flex flex-col`}>
      {/* Top Header - Market Indices Bar */}
      <header
        className={`${theme.headerBg} border-b ${theme.border} px-4 py-2`}
      >
        <div className="flex items-center justify-between">
          {/* Logo and Search */}
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className={`flex items-center gap-2 ${theme.text} font-bold text-lg`}
            >
              <svg
                className="w-7 h-7 text-blue-500"
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
              <span>StockPro</span>
            </Link>

            <form onSubmit={handleSearch} className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
                placeholder="Search stocks, F&O, Indices..."
                className={`w-80 pl-10 pr-4 py-2 ${theme.inputBg} border ${theme.border} rounded-lg ${theme.text} text-sm placeholder-gray-500 focus:border-blue-500 focus:outline-none`}
              />
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500"
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
            </form>
          </div>

          {/* Market Indices */}
          <div className="flex items-center gap-6">
            {marketIndices.map((index) => (
              <div key={index.symbol} className="text-right">
                <div className={`text-xs ${theme.textMuted}`}>{index.name}</div>
                <div className="flex items-center gap-2">
                  <span className={`${theme.text} font-medium`}>
                    {index.price.toLocaleString()}
                  </span>
                  <span
                    className={`text-xs ${index.change >= 0 ? 'text-green-400' : 'text-red-400'}`}
                  >
                    {index.change >= 0 ? '+' : ''}
                    {index.change.toFixed(2)} ({index.changePercent.toFixed(2)}
                    %)
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Right side - Time and controls */}
          <div className="flex items-center gap-3">
            <span className={`${theme.textMuted} text-sm font-mono`}>
              {formatTime(currentTime)}
            </span>

            {/* Fullscreen toggle */}
            <button
              onClick={toggleFullscreen}
              className={`w-8 h-8 rounded-lg ${theme.buttonBg} flex items-center justify-center ${theme.textMuted} hover:text-white ${theme.buttonHover} transition-colors`}
              title={
                isFullscreen
                  ? 'Exit Fullscreen (F11)'
                  : 'Enter Fullscreen (F11)'
              }
            >
              {isFullscreen ? (
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
                    d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25"
                  />
                </svg>
              ) : (
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
                    d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                  />
                </svg>
              )}
            </button>

            {/* Dark/Light mode toggle */}
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className={`w-8 h-8 rounded-lg ${theme.buttonBg} flex items-center justify-center ${theme.textMuted} hover:text-white ${theme.buttonHover} transition-colors`}
              title={
                isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'
              }
            >
              {isDarkMode ? (
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
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
              ) : (
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
                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                  />
                </svg>
              )}
            </button>

            {/* Back to analysis */}
            <Link
              href={`/analyze?symbol=${symbol}`}
              className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-1.5"
            >
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
              AI Analysis
            </Link>
          </div>
        </div>
      </header>

      {/* Main Chart Area */}
      <main className="flex-1 flex">
        {symbol ? (
          <FullScreenChart symbol={symbol} isDarkMode={isDarkMode} />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
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
              <h2 className={`text-xl font-semibold ${theme.text} mb-2`}>
                Search for a stock
              </h2>
              <p className={theme.textMuted}>
                Enter a symbol to view its chart
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
