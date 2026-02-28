'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import StockSearch from '@/components/StockSearch';
import Recommendations from '@/components/Recommendations';
import { Search, Newspaper, History, BarChart3 } from 'lucide-react';

export default function Home() {
  const router = useRouter();

  const handleStockSelect = (symbol: string) => {
    router.push(`/analyze?symbol=${symbol}`);
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            StockPro
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300">
            AI-Assisted Trading System for Indian Markets
          </p>
        </div>

        {/* Search Bar */}
        <div className="max-w-2xl mx-auto mb-6">
          <StockSearch
            onSelect={handleStockSelect}
            placeholder="Search stocks (e.g., RELIANCE, TCS, TATASTEEL)..."
          />
        </div>

        {/* Quick Actions */}
        <div className="max-w-4xl mx-auto mb-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Link
              href="/analyze"
              className="flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 rounded-xl shadow hover:shadow-lg transition-all border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-500"
            >
              <BarChart3 className="w-6 h-6 text-blue-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Analyze
              </span>
            </Link>

            <Link
              href="/scanner"
              className="flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 rounded-xl shadow hover:shadow-lg transition-all border border-gray-200 dark:border-gray-700 hover:border-green-500 dark:hover:border-green-500"
            >
              <Search className="w-6 h-6 text-green-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Scanner
              </span>
            </Link>

            <Link
              href="/backtest"
              className="flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 rounded-xl shadow hover:shadow-lg transition-all border border-gray-200 dark:border-gray-700 hover:border-orange-500 dark:hover:border-orange-500"
            >
              <History className="w-6 h-6 text-orange-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Backtest
              </span>
            </Link>

            <Link
              href="/news"
              className="flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 rounded-xl shadow hover:shadow-lg transition-all border border-gray-200 dark:border-gray-700 hover:border-purple-500 dark:hover:border-purple-500"
            >
              <Newspaper className="w-6 h-6 text-purple-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                News
              </span>
            </Link>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Features - Left Side */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                How It Works
              </h2>

              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold">
                    1
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      Search a Stock
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Enter any NSE stock symbol to analyze
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold">
                    2
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      AI Analyzes
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Technical indicators + AI reasoning
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold">
                    3
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      Risk Validation
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Position sizing and stop-loss calculated
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center text-green-600 dark:text-green-400 font-bold">
                    4
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      You Decide
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Execute manually on your broker
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  <p className="mb-2">
                    <strong>Target:</strong> 60-70% win rate
                  </p>
                  <p>
                    <strong>Risk:</strong> Max 2% daily loss
                  </p>
                </div>
              </div>
            </div>

            {/* Disclaimer */}
            <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
              <p className="text-xs text-amber-800 dark:text-amber-200">
                <strong>Disclaimer:</strong> AI suggestions are based on
                probabilistic analysis. Past performance does not guarantee
                future results. Always trade responsibly.
              </p>
            </div>
          </div>

          {/* Recommendations - Right Side */}
          <div className="lg:col-span-2">
            <Recommendations />
          </div>
        </div>
      </div>
    </main>
  );
}
