'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

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

export default function Recommendations() {
  const [movers, setMovers] = useState<MoversData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'gainers' | 'losers' | 'volume'>(
    'gainers'
  );

  useEffect(() => {
    const fetchMovers = async () => {
      try {
        const res = await fetch(
          'http://localhost:8000/api/v1/market/movers?count=8'
        );
        if (!res.ok) {
          throw new Error('Failed to fetch market data');
        }
        const result = await res.json();
        setMovers(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setIsLoading(false);
      }
    };

    fetchMovers();
  }, []);

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Market Movers
        </h2>
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-16 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Market Movers
        </h2>
        <div className="text-center py-8">
          <p className="text-red-500 mb-4">{error}</p>
          <p className="text-gray-500 dark:text-gray-400">
            Make sure the backend server is running at localhost:8000
          </p>
        </div>
      </div>
    );
  }

  const getActiveList = () => {
    if (!movers) {
      return [];
    }
    switch (activeTab) {
      case 'gainers':
        return movers.gainers;
      case 'losers':
        return movers.losers;
      case 'volume':
        return movers.high_volume;
      default:
        return movers.gainers;
    }
  };

  const activeList = getActiveList();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          Market Movers
        </h2>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Click to analyze
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 border-b border-gray-200 dark:border-gray-700 pb-2">
        <button
          onClick={() => setActiveTab('gainers')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeTab === 'gainers'
              ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
        >
          Top Gainers
        </button>
        <button
          onClick={() => setActiveTab('losers')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeTab === 'losers'
              ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
        >
          Top Losers
        </button>
        <button
          onClick={() => setActiveTab('volume')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeTab === 'volume'
              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
        >
          High Volume
        </button>
      </div>

      {/* Stock List */}
      <div className="space-y-2">
        {activeList.map((stock) => (
          <Link
            key={stock.symbol}
            href={`/analyze?symbol=${stock.symbol}`}
            className="block"
          >
            <div className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 hover:shadow-md transition-all group">
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold text-sm ${
                    stock.change_percent >= 0 ? 'bg-green-500' : 'bg-red-500'
                  }`}
                >
                  {stock.change_percent >= 0 ? '▲' : '▼'}
                </div>
                <div>
                  <div className="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600">
                    {stock.symbol}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[150px]">
                    {stock.name}
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="font-semibold text-gray-900 dark:text-white">
                  Rs.{stock.price.toFixed(2)}
                </div>
                <div
                  className={`text-sm font-medium ${
                    stock.change_percent >= 0
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {stock.change_percent >= 0 ? '+' : ''}
                  {stock.change_percent.toFixed(2)}%
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {activeList.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          No data available
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
          Click any stock for full AI analysis with entry/exit recommendations
        </p>
      </div>
    </div>
  );
}
