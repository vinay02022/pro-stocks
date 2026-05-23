'use client';

import { useState, useEffect, useRef } from 'react';

interface Stock {
  symbol: string;
  name: string;
  sector: string;
}

interface StockSearchProps {
  onSelect: (symbol: string) => void;
  placeholder?: string;
}

export default function StockSearch({
  onSelect,
  placeholder = 'Search stocks...',
}: StockSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Stock[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const searchStocks = async () => {
      if (query.length < 1) {
        setResults([]);
        return;
      }

      setIsLoading(true);
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/market/search?q=${encodeURIComponent(
            query
          )}&limit=8`
        );
        const data = await res.json();
        setResults(data.results || []);
        setShowDropdown(true);
        setSelectedIndex(-1);
      } catch (err) {
        console.error('Search failed:', err);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    };

    const debounce = setTimeout(searchStocks, 200);
    return () => clearTimeout(debounce);
  }, [query]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        !inputRef.current?.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (stock: Stock) => {
    setQuery(stock.symbol);
    setShowDropdown(false);
    onSelect(stock.symbol);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || results.length === 0) {
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault();
      handleSelect(results[selectedIndex]);
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  return (
    <div className="relative">
      <div className="relative group">
        <svg
          className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-bone-500 group-focus-within:text-spark-violet transition-colors"
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
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value.toUpperCase())}
          onFocus={() => query.length > 0 && setShowDropdown(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full pl-12 pr-11 py-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.08] text-bone-50 placeholder-bone-500 focus:bg-white/[0.05] focus:border-white/[0.16] outline-none transition-all shadow-inner-light"
        />
        {isLoading && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-spark-violet border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {!isLoading && query && (
          <button
            onClick={() => {
              setQuery('');
              setResults([]);
            }}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-bone-500 hover:text-bone-200 transition-colors"
            aria-label="Clear search"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      {showDropdown && results.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-2 glass-strong rounded-2xl shadow-2xl max-h-80 overflow-y-auto animate-fade-in"
        >
          {results.map((stock, index) => (
            <button
              key={stock.symbol}
              onClick={() => handleSelect(stock)}
              className={`w-full px-4 py-3 text-left border-b border-white/[0.04] last:border-b-0 transition-colors ${
                index === selectedIndex
                  ? 'bg-spark-violet/10'
                  : 'hover:bg-white/[0.04]'
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-white/[0.06] to-white/[0.02] border border-white/[0.06] flex items-center justify-center flex-shrink-0">
                    <span className="text-xs font-bold text-bone-300">
                      {stock.symbol.slice(0, 2)}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <span className="font-semibold text-bone-50 block">
                      {stock.symbol}
                    </span>
                    <p className="text-sm text-bone-400 truncate max-w-[220px]">
                      {stock.name}
                    </p>
                  </div>
                </div>
                <span className="text-[10px] uppercase tracking-wider px-2 py-1 bg-white/[0.04] text-bone-400 rounded-md border border-white/[0.06] flex-shrink-0">
                  {stock.sector}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {showDropdown &&
        query.length > 0 &&
        results.length === 0 &&
        !isLoading && (
          <div className="absolute z-50 w-full mt-2 glass-strong rounded-2xl p-6 text-center animate-fade-in">
            <svg
              className="w-10 h-10 text-bone-500 mx-auto mb-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-bone-400">
              No stocks found for &ldquo;
              <span className="text-bone-200">{query}</span>&rdquo;
            </p>
            <p className="text-xs text-bone-500 mt-1">
              Try searching for TCS, RELIANCE, INFY…
            </p>
          </div>
        )}
    </div>
  );
}
