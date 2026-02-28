'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Newspaper,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface NewsArticle {
  title: string;
  source: string;
  url: string;
  published_at: string;
  sentiment: string;
  sentiment_score: number;
}

interface SentimentSummary {
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
  avg_score: number;
}

interface SymbolNewsResponse {
  symbol: string;
  count: number;
  sentiment_summary: SentimentSummary;
  articles: NewsArticle[];
}

interface NewsWidgetProps {
  symbol: string;
  maxArticles?: number;
}

export default function NewsWidget({
  symbol,
  maxArticles = 5,
}: NewsWidgetProps) {
  const [news, setNews] = useState<SymbolNewsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNews = useCallback(async () => {
    if (!symbol) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/news/symbol/${symbol.toUpperCase()}?limit=${maxArticles}`
      );
      if (!response.ok) {
        throw new Error('Failed to fetch news');
      }
      const data = await response.json();
      setNews(data);
    } catch (err) {
      setError('Unable to load news');
    } finally {
      setLoading(false);
    }
  }, [symbol, maxArticles]);

  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

  const getSentimentIcon = (sentiment: string) => {
    if (sentiment.includes('bullish')) {
      return <TrendingUp className="w-3 h-3 text-green-400" />;
    } else if (sentiment.includes('bearish')) {
      return <TrendingDown className="w-3 h-3 text-red-400" />;
    }
    return <Minus className="w-3 h-3 text-gray-400" />;
  };

  const formatTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 60) {
        return `${diffMins}m`;
      }
      if (diffHours < 24) {
        return `${diffHours}h`;
      }
      if (diffDays < 7) {
        return `${diffDays}d`;
      }
      return date.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
      });
    } catch {
      return '';
    }
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.2) {
      return 'text-green-400';
    }
    if (score < -0.2) {
      return 'text-red-400';
    }
    return 'text-gray-400';
  };

  if (!symbol) {
    return null;
  }

  return (
    <div className="bg-[#131722] rounded-lg border border-[#2a2e39]">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-[#1e222d] transition-colors rounded-t-lg"
      >
        <div className="flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-medium text-white">{symbol} News</span>
          {news && (
            <span
              className={`text-xs ${getSentimentColor(news.sentiment_summary.avg_score)}`}
            >
              ({news.sentiment_summary.avg_score > 0 ? '+' : ''}
              {news.sentiment_summary.avg_score.toFixed(2)})
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              fetchNews();
            }}
            disabled={loading}
            className="p-1 hover:bg-[#2a2e39] rounded transition-colors"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-gray-400 ${loading ? 'animate-spin' : ''}`}
            />
          </button>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Content */}
      {expanded && (
        <div className="border-t border-[#2a2e39]">
          {loading && !news && (
            <div className="p-4 text-center">
              <RefreshCw className="w-5 h-5 animate-spin text-gray-400 mx-auto" />
            </div>
          )}

          {error && (
            <div className="p-3 text-center text-xs text-gray-500">{error}</div>
          )}

          {news && news.articles.length > 0 && (
            <>
              {/* Sentiment Bar */}
              <div className="px-3 py-2 border-b border-[#2a2e39]">
                <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden flex">
                  <div
                    className="bg-green-500"
                    style={{
                      width: `${
                        (news.sentiment_summary.bullish_count / news.count) *
                        100
                      }%`,
                    }}
                  />
                  <div
                    className="bg-gray-500"
                    style={{
                      width: `${
                        (news.sentiment_summary.neutral_count / news.count) *
                        100
                      }%`,
                    }}
                  />
                  <div
                    className="bg-red-500"
                    style={{
                      width: `${
                        (news.sentiment_summary.bearish_count / news.count) *
                        100
                      }%`,
                    }}
                  />
                </div>
                <div className="flex justify-between mt-1 text-[10px] text-gray-500">
                  <span className="text-green-400">
                    {news.sentiment_summary.bullish_count} bullish
                  </span>
                  <span className="text-red-400">
                    {news.sentiment_summary.bearish_count} bearish
                  </span>
                </div>
              </div>

              {/* Articles */}
              <div className="divide-y divide-[#2a2e39]">
                {news.articles.map((article, index) => (
                  <a
                    key={index}
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-2 p-3 hover:bg-[#1e222d] transition-colors group"
                  >
                    <div className="mt-0.5 flex-shrink-0">
                      {getSentimentIcon(article.sentiment)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-300 line-clamp-2 group-hover:text-white transition-colors">
                        {article.title}
                      </p>
                      <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-500">
                        <span>{article.source}</span>
                        <span>·</span>
                        <span>{formatTime(article.published_at)}</span>
                      </div>
                    </div>
                    <ExternalLink className="w-3 h-3 text-gray-600 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </a>
                ))}
              </div>

              {/* View More Link */}
              <a
                href={`/news?symbol=${symbol}`}
                className="block text-center py-2 text-xs text-blue-400 hover:text-blue-300 hover:bg-[#1e222d] transition-colors border-t border-[#2a2e39]"
              >
                View all {symbol} news
              </a>
            </>
          )}

          {news && news.articles.length === 0 && (
            <div className="p-4 text-center text-xs text-gray-500">
              No recent news for {symbol}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
