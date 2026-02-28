/**
 * API Client for StockPro Backend
 *
 * This is the ONLY way the frontend communicates with the backend.
 * All business logic lives in the Python FastAPI backend.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ApiResponse<T> {
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        error: {
          code: `HTTP_${response.status}`,
          message: errorData.detail || response.statusText,
          details: errorData,
        },
      };
    }

    const data = await response.json();
    return { data };
  } catch (error) {
    return {
      error: {
        code: 'NETWORK_ERROR',
        message: error instanceof Error ? error.message : 'Network error',
      },
    };
  }
}

// =============================================================================
// MARKET DATA
// =============================================================================

export async function getQuote(symbol: string) {
  return fetchApi<{
    symbol: string;
    price: number;
    change: number;
    change_percent: number;
  }>(`/market/quote/${symbol}`);
}

export async function getMarketSnapshot(request: {
  symbols: string[];
  timeframe?: string;
  lookback?: number;
  include_options?: boolean;
  include_news?: boolean;
}) {
  return fetchApi('/market/snapshot', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getMarketStatus() {
  return fetchApi<{
    is_open: boolean;
    session: string;
    next_open?: string;
  }>('/market/status');
}

// =============================================================================
// INDICATORS
// =============================================================================

export async function getIndicators(
  symbol: string,
  timeframe: string = '15m',
  lookback: number = 100
) {
  return fetchApi(
    `/indicators/${symbol}?timeframe=${timeframe}&lookback=${lookback}`
  );
}

// =============================================================================
// STRATEGY (Main endpoint)
// =============================================================================

export interface AnalyzeRequest {
  symbol: string;
  timeframe?: string;
  portfolio_value?: number;
  risk_percent?: number;
  include_news?: boolean;
  include_options?: boolean;
}

export async function analyzeSymbol(request: AnalyzeRequest) {
  return fetchApi('/strategy/analyze', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getTradeIdeas(limit: number = 10, status?: string) {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (status) {
    params.append('status', status);
  }
  return fetchApi(`/strategy/ideas?${params}`);
}

export async function getTradeIdea(ideaId: string) {
  return fetchApi(`/strategy/ideas/${ideaId}`);
}

export async function markIdeaExecuted(ideaId: string) {
  return fetchApi(`/strategy/ideas/${ideaId}/execute`, { method: 'POST' });
}

export async function markIdeaSkipped(ideaId: string, reason?: string) {
  return fetchApi(`/strategy/ideas/${ideaId}/skip`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

// =============================================================================
// PORTFOLIO
// =============================================================================

export async function getPortfolios() {
  return fetchApi('/portfolio/');
}

export async function getPortfolio(portfolioId: string) {
  return fetchApi(`/portfolio/${portfolioId}`);
}

export async function getRiskConfig(portfolioId: string) {
  return fetchApi(`/portfolio/${portfolioId}/risk-config`);
}

export async function updateRiskConfig(
  portfolioId: string,
  config: {
    max_position_percent?: number;
    max_daily_loss_percent?: number;
    max_daily_trades?: number;
    min_risk_reward_ratio?: number;
  }
) {
  return fetchApi(`/portfolio/${portfolioId}/risk-config`, {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

export async function getPerformance(
  portfolioId: string,
  period: string = '1M'
) {
  return fetchApi(`/portfolio/${portfolioId}/performance?period=${period}`);
}

// =============================================================================
// HEALTH CHECK
// =============================================================================

export async function healthCheck() {
  return fetchApi<{
    status: string;
    app: string;
    version: string;
  }>('/health');
}
