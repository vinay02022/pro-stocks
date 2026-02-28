/**
 * API Client for StockPro Backend
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface AnalyzeRequest {
  symbol: string;
  timeframe?: string;
  portfolio_value?: number;
  risk_percent?: number;
}

export interface ConfidenceBand {
  low: number;
  mid: number;
  high: number;
}

export interface TradeIdea {
  id: string;
  symbol: string;
  direction: 'LONG' | 'SHORT' | 'NEUTRAL';
  confidence_band: ConfidenceBand;
  timeframe: string;
  regime: {
    trend: string;
    volatility: string;
    momentum: string;
  };
  reasoning: {
    primary_factors: string[];
    confluences: string[];
    concerns: string[];
  };
  suggested_entry: {
    entry_type: string;
    entry_price: number | null;
  };
  invalidation: string;
}

export interface RiskPlan {
  trade_id: string;
  validation_status: 'APPROVED' | 'REJECTED' | 'MODIFIED';
  rejection_reasons?: string[];
  approved_plan?: {
    position_size: number;
    position_value: number;
    max_loss_amount: number;
    max_loss_percent: number;
    risk_reward_ratio: number;
    stop_loss: number;
    take_profit: Array<{ price: number; exit_percent: number; label?: string }>;
  };
  portfolio_impact: {
    current_exposure_percent: number;
    new_exposure_percent: number;
    max_drawdown_if_all_sl_hit: number;
  };
  risk_warnings: string[];
}

export interface TradeExplanation {
  summary: string;
  rationale: string;
  risk_disclosure: string;
  what_could_go_wrong: string[];
  confidence_statement: string;
  human_checklist: string[];
}

export interface TradeSuggestion {
  idea: TradeIdea;
  risk_plan: RiskPlan;
  explanation: TradeExplanation;
  generated_at: string;
  expires_at: string;
}

export async function analyzeSymbol(
  request: AnalyzeRequest
): Promise<TradeSuggestion> {
  const response = await fetch(`${API_BASE}/strategy/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      symbol: request.symbol.toUpperCase(),
      timeframe: request.timeframe || '1d',
      portfolio_value: request.portfolio_value || 1000000,
      risk_percent: request.risk_percent || 1.0,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Analysis failed');
  }

  return response.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE.replace('/api/v1', '')}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
