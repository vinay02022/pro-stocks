'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Newspaper,
  TrendingUp,
  TrendingDown,
  Minus,
  Search,
  RefreshCw,
  ExternalLink,
  Building2,
  Clock,
  Filter,
  ArrowUpCircle,
  ArrowDownCircle,
  MinusCircle,
  Info,
} from 'lucide-react';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface NewsArticle {
  title: string;
  source: string;
  url: string;
  published_at: string;
  summary: string | null;
  sentiment: string;
  sentiment_score: number;
  related_symbols: string[] | null;
}

interface SentimentSummary {
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
  avg_score: number;
}

interface TrendingNewsResponse {
  articles: NewsArticle[];
  overall_sentiment: string;
  sentiment_score: number;
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
}

interface SymbolNewsResponse {
  symbol: string;
  count: number;
  sentiment_summary: SentimentSummary;
  articles: NewsArticle[];
}

interface Sector {
  id: string;
  name: string;
  description: string;
}

export default function NewsPage() {
  const [activeTab, setActiveTab] = useState<'trending' | 'symbol' | 'sector'>(
    'trending'
  );
  const [trendingNews, setTrendingNews] = useState<TrendingNewsResponse | null>(
    null
  );
  const [symbolNews, setSymbolNews] = useState<SymbolNewsResponse | null>(null);
  const [sectorNews, setSectorNews] = useState<SymbolNewsResponse | null>(null);
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Search states
  const [symbolSearch, setSymbolSearch] = useState('');
  const [selectedSector, setSelectedSector] = useState('');

  // Fetch trending news
  const fetchTrendingNews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/news/trending?limit=20`);
      if (!response.ok) {
        throw new Error('Failed to fetch trending news');
      }
      const data = await response.json();
      setTrendingNews(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch news');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch symbol news
  const fetchSymbolNews = useCallback(async (symbol: string) => {
    if (!symbol.trim()) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/news/symbol/${symbol.toUpperCase()}?limit=15`
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch news for ${symbol}`);
      }
      const data = await response.json();
      setSymbolNews(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch news');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch sector news
  const fetchSectorNews = useCallback(async (sector: string) => {
    if (!sector) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/news/sector/${sector}?limit=15`
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch news for ${sector}`);
      }
      const data = await response.json();
      setSectorNews(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch news');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch available sectors
  const fetchSectors = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/news/sectors`);
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      setSectors(data.sectors || []);
    } catch {
      // Ignore sector fetch errors
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchTrendingNews();
    fetchSectors();
  }, [fetchTrendingNews, fetchSectors]);

  // Handle symbol search
  const handleSymbolSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (symbolSearch.trim()) {
      setActiveTab('symbol');
      fetchSymbolNews(symbolSearch);
    }
  };

  // Handle sector selection
  const handleSectorSelect = (sector: string) => {
    setSelectedSector(sector);
    setActiveTab('sector');
    fetchSectorNews(sector);
  };

  // Get sentiment icon and color
  const getSentimentDisplay = (sentiment: string, score: number) => {
    const isBullish = sentiment.includes('bullish');
    const isBearish = sentiment.includes('bearish');

    if (isBullish) {
      return {
        icon: <TrendingUp className="w-4 h-4" />,
        color: 'text-green-400',
        bgColor: 'bg-green-500/20',
        label: sentiment === 'very_bullish' ? 'Very Bullish' : 'Bullish',
      };
    } else if (isBearish) {
      return {
        icon: <TrendingDown className="w-4 h-4" />,
        color: 'text-red-400',
        bgColor: 'bg-red-500/20',
        label: sentiment === 'very_bearish' ? 'Very Bearish' : 'Bearish',
      };
    }
    return {
      icon: <Minus className="w-4 h-4" />,
      color: 'text-gray-400',
      bgColor: 'bg-gray-500/20',
      label: 'Neutral',
    };
  };

  // Format relative time
  const formatRelativeTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 60) {
        return `${diffMins}m ago`;
      }
      if (diffHours < 24) {
        return `${diffHours}h ago`;
      }
      if (diffDays < 7) {
        return `${diffDays}d ago`;
      }
      return date.toLocaleDateString();
    } catch {
      return dateString;
    }
  };

  // Get stock impact info for tooltip
  const getStockImpact = (sentiment: string, score: number) => {
    const isBullish = sentiment.includes('bullish');
    const isBearish = sentiment.includes('bearish');
    const isVery = sentiment.includes('very');

    if (isBullish) {
      return {
        icon: <ArrowUpCircle className="w-6 h-6" />,
        direction: 'UP',
        color: 'text-green-400',
        bgColor: 'bg-green-500/20',
        borderColor: 'border-green-500/50',
        tooltip: isVery
          ? 'Strong positive news - Stock likely to go UP significantly'
          : 'Positive news - Stock may go UP',
        strength: isVery ? 'Strong Buy Signal' : 'Mild Buy Signal',
      };
    } else if (isBearish) {
      return {
        icon: <ArrowDownCircle className="w-6 h-6" />,
        direction: 'DOWN',
        color: 'text-red-400',
        bgColor: 'bg-red-500/20',
        borderColor: 'border-red-500/50',
        tooltip: isVery
          ? 'Strong negative news - Stock likely to go DOWN significantly'
          : 'Negative news - Stock may go DOWN',
        strength: isVery ? 'Strong Sell Signal' : 'Mild Sell Signal',
      };
    }
    return {
      icon: <MinusCircle className="w-6 h-6" />,
      direction: 'NEUTRAL',
      color: 'text-gray-400',
      bgColor: 'bg-gray-500/20',
      borderColor: 'border-gray-500/50',
      tooltip: 'Neutral news - No significant impact expected on stock price',
      strength: 'No Clear Signal',
    };
  };

  // Render news card with stock impact indicator
  const renderNewsCard = (article: NewsArticle, index: number) => {
    const sentiment = getSentimentDisplay(
      article.sentiment,
      article.sentiment_score
    );
    const impact = getStockImpact(article.sentiment, article.sentiment_score);

    return (
      <div
        key={index}
        className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors"
      >
        <div className="flex gap-4">
          {/* Stock Impact Indicator */}
          <div className="flex-shrink-0 relative group">
            <div
              className={`w-14 h-14 rounded-lg ${impact.bgColor} border ${impact.borderColor} flex flex-col items-center justify-center cursor-help`}
            >
              <span className={impact.color}>{impact.icon}</span>
              <span className={`text-[10px] font-bold ${impact.color}`}>
                {impact.direction}
              </span>
            </div>
            {/* Tooltip */}
            <div className="absolute left-0 bottom-full mb-2 w-64 p-3 bg-gray-900 border border-gray-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-20">
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className={`text-sm font-medium ${impact.color}`}>
                    {impact.strength}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">{impact.tooltip}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    Sentiment Score: {article.sentiment_score > 0 ? '+' : ''}
                    {(article.sentiment_score * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
              <div className="absolute left-4 bottom-0 transform translate-y-1/2 rotate-45 w-2 h-2 bg-gray-900 border-r border-b border-gray-700" />
            </div>
          </div>

          {/* News Content */}
          <div className="flex-1 min-w-0">
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-white font-medium hover:text-blue-400 transition-colors line-clamp-2 flex items-start gap-2"
            >
              {article.title}
              <ExternalLink className="w-4 h-4 flex-shrink-0 mt-1 opacity-50" />
            </a>

            <div className="flex items-center gap-3 mt-2 text-sm text-gray-400">
              <span className="flex items-center gap-1">
                <Building2 className="w-3 h-3" />
                {article.source}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatRelativeTime(article.published_at)}
              </span>
              <span className={`flex items-center gap-1 ${sentiment.color}`}>
                {sentiment.icon}
                {sentiment.label}
              </span>
            </div>

            {article.related_symbols && article.related_symbols.length > 0 && (
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-gray-500">Affects:</span>
                {article.related_symbols.map((symbol) => (
                  <button
                    key={symbol}
                    onClick={() => {
                      setSymbolSearch(symbol);
                      setActiveTab('symbol');
                      fetchSymbolNews(symbol);
                    }}
                    className={`text-xs px-2 py-0.5 rounded flex items-center gap-1 transition-colors ${
                      article.sentiment.includes('bullish')
                        ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                        : article.sentiment.includes('bearish')
                          ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                          : 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30'
                    }`}
                  >
                    {symbol}
                    {article.sentiment.includes('bullish') && (
                      <TrendingUp className="w-3 h-3" />
                    )}
                    {article.sentiment.includes('bearish') && (
                      <TrendingDown className="w-3 h-3" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Render sentiment summary
  const renderSentimentSummary = (
    bullish: number,
    bearish: number,
    neutral: number,
    avgScore: number,
    overallSentiment?: string
  ) => {
    const total = bullish + bearish + neutral;
    const bullishPct = total > 0 ? (bullish / total) * 100 : 0;
    const bearishPct = total > 0 ? (bearish / total) * 100 : 0;
    const neutralPct = total > 0 ? (neutral / total) * 100 : 0;

    return (
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium text-gray-400 mb-3">
          Market Sentiment
        </h3>

        <div className="flex items-center gap-4 mb-4">
          {overallSentiment && (
            <div
              className={`text-lg font-semibold ${
                overallSentiment.includes('bullish')
                  ? 'text-green-400'
                  : overallSentiment.includes('bearish')
                    ? 'text-red-400'
                    : 'text-gray-400'
              }`}
            >
              {overallSentiment.replace('_', ' ').toUpperCase()}
            </div>
          )}
          <div className="text-sm text-gray-400">
            Score:{' '}
            <span
              className={
                avgScore > 0
                  ? 'text-green-400'
                  : avgScore < 0
                    ? 'text-red-400'
                    : 'text-gray-400'
              }
            >
              {avgScore > 0 ? '+' : ''}
              {avgScore.toFixed(2)}
            </span>
          </div>
        </div>

        <div className="h-2 bg-gray-700 rounded-full overflow-hidden flex">
          <div
            className="bg-green-500 transition-all duration-300"
            style={{ width: `${bullishPct}%` }}
          />
          <div
            className="bg-gray-500 transition-all duration-300"
            style={{ width: `${neutralPct}%` }}
          />
          <div
            className="bg-red-500 transition-all duration-300"
            style={{ width: `${bearishPct}%` }}
          />
        </div>

        <div className="flex justify-between mt-2 text-xs">
          <span className="text-green-400">
            Bullish: {bullish} ({bullishPct.toFixed(0)}%)
          </span>
          <span className="text-gray-400">
            Neutral: {neutral} ({neutralPct.toFixed(0)}%)
          </span>
          <span className="text-red-400">
            Bearish: {bearish} ({bearishPct.toFixed(0)}%)
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/95 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                Back
              </Link>
              <div className="flex items-center gap-2">
                <Newspaper className="w-6 h-6 text-purple-400" />
                <h1 className="text-xl font-bold">Market News</h1>
              </div>
            </div>

            <button
              onClick={() => {
                if (activeTab === 'trending') {
                  fetchTrendingNews();
                } else if (activeTab === 'symbol' && symbolSearch) {
                  fetchSymbolNews(symbolSearch);
                } else if (activeTab === 'sector' && selectedSector) {
                  fetchSectorNews(selectedSector);
                }
              }}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw
                className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`}
              />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Search and Filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Symbol Search */}
          <form onSubmit={handleSymbolSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={symbolSearch}
                onChange={(e) => setSymbolSearch(e.target.value.toUpperCase())}
                placeholder="Search by symbol (e.g., RELIANCE)"
                className="w-full pl-10 pr-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500 text-white placeholder-gray-500"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-medium"
            >
              Search
            </button>
          </form>

          {/* Sector Filter */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <select
                value={selectedSector}
                onChange={(e) => handleSectorSelect(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500 text-white appearance-none cursor-pointer"
              >
                <option value="">Select Sector</option>
                {sectors.map((sector) => (
                  <option key={sector.id} value={sector.id}>
                    {sector.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-800 pb-2">
          <button
            onClick={() => {
              setActiveTab('trending');
              if (!trendingNews) {
                fetchTrendingNews();
              }
            }}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'trending'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            Trending News
          </button>
          {symbolNews && (
            <button
              onClick={() => setActiveTab('symbol')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'symbol'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {symbolNews.symbol} News
            </button>
          )}
          {sectorNews && selectedSector && (
            <button
              onClick={() => setActiveTab('sector')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'sector'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {selectedSector.charAt(0).toUpperCase() + selectedSector.slice(1)}{' '}
              Sector
            </button>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/20 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin text-blue-400" />
          </div>
        )}

        {/* Trending News Tab */}
        {!loading && activeTab === 'trending' && trendingNews && (
          <div>
            {renderSentimentSummary(
              trendingNews.bullish_count,
              trendingNews.bearish_count,
              trendingNews.neutral_count,
              trendingNews.sentiment_score,
              trendingNews.overall_sentiment
            )}

            <div className="space-y-3">
              {trendingNews.articles.map((article, index) =>
                renderNewsCard(article, index)
              )}
            </div>

            {trendingNews.articles.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                No trending news available at the moment.
              </div>
            )}
          </div>
        )}

        {/* Symbol News Tab */}
        {!loading && activeTab === 'symbol' && symbolNews && (
          <div>
            <h2 className="text-lg font-semibold mb-4">
              News for{' '}
              <span className="text-blue-400">{symbolNews.symbol}</span>
              <span className="text-gray-400 text-sm font-normal ml-2">
                ({symbolNews.count} articles)
              </span>
            </h2>

            {renderSentimentSummary(
              symbolNews.sentiment_summary.bullish_count,
              symbolNews.sentiment_summary.bearish_count,
              symbolNews.sentiment_summary.neutral_count,
              symbolNews.sentiment_summary.avg_score
            )}

            <div className="space-y-3">
              {symbolNews.articles.map((article, index) =>
                renderNewsCard(article, index)
              )}
            </div>

            {symbolNews.articles.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                No news found for {symbolNews.symbol}.
              </div>
            )}
          </div>
        )}

        {/* Sector News Tab */}
        {!loading && activeTab === 'sector' && sectorNews && (
          <div>
            <h2 className="text-lg font-semibold mb-4">
              <span className="text-green-400 capitalize">
                {selectedSector}
              </span>{' '}
              Sector News
              <span className="text-gray-400 text-sm font-normal ml-2">
                ({sectorNews.count} articles)
              </span>
            </h2>

            {renderSentimentSummary(
              sectorNews.sentiment_summary.bullish_count,
              sectorNews.sentiment_summary.bearish_count,
              sectorNews.sentiment_summary.neutral_count,
              sectorNews.sentiment_summary.avg_score
            )}

            <div className="space-y-3">
              {sectorNews.articles.map((article, index) =>
                renderNewsCard(article, index)
              )}
            </div>

            {sectorNews.articles.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                No news found for {selectedSector} sector.
              </div>
            )}
          </div>
        )}

        {/* Sector Quick Links */}
        {activeTab === 'trending' && sectors.length > 0 && (
          <div className="mt-8 pt-6 border-t border-gray-800">
            <h3 className="text-sm font-medium text-gray-400 mb-3">
              Browse by Sector
            </h3>
            <div className="flex flex-wrap gap-2">
              {sectors.map((sector) => (
                <button
                  key={sector.id}
                  onClick={() => handleSectorSelect(sector.id)}
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 hover:text-white transition-colors"
                  title={sector.description}
                >
                  {sector.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
