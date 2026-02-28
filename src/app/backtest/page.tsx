'use client';

import { useState } from 'react';
import Link from 'next/link';

interface BacktestResult {
  symbol: string;
  strategy: string;
  strategy_params: Record<string, any>;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_return: number;
  total_return_percent: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  max_drawdown_percent: number;
  sharpe_ratio: number;
  avg_trade_pnl: number;
  avg_winning_trade: number;
  avg_losing_trade: number;
  largest_win: number;
  largest_loss: number;
  avg_hold_duration: number;
  trades: any[];
  equity_curve: any[];
}

const STRATEGIES = [
  {
    id: 'ema_crossover',
    name: 'EMA Crossover',
    description: 'Buy when fast EMA crosses above slow EMA',
    params: [
      { name: 'fast_period', label: 'Fast Period', default: 9 },
      { name: 'slow_period', label: 'Slow Period', default: 21 },
    ],
  },
  {
    id: 'rsi_reversal',
    name: 'RSI Reversal',
    description: 'Buy at oversold, sell at overbought',
    params: [
      { name: 'period', label: 'RSI Period', default: 14 },
      { name: 'overbought', label: 'Overbought', default: 70 },
      { name: 'oversold', label: 'Oversold', default: 30 },
    ],
  },
  {
    id: 'breakout',
    name: 'Breakout',
    description: 'Trade breakouts with volume confirmation',
    params: [
      { name: 'lookback', label: 'Lookback', default: 20 },
      { name: 'volume_threshold', label: 'Volume Threshold', default: 1.5 },
    ],
  },
  {
    id: 'macd',
    name: 'MACD',
    description: 'Trade MACD crossovers',
    params: [
      { name: 'fast_period', label: 'Fast', default: 12 },
      { name: 'slow_period', label: 'Slow', default: 26 },
      { name: 'signal_period', label: 'Signal', default: 9 },
    ],
  },
];

export default function BacktestPage() {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [strategy, setStrategy] = useState('ema_crossover');
  const [timeframe, setTimeframe] = useState('1d');
  const [capital, setCapital] = useState(100000);
  const [lookback, setLookback] = useState(365);
  const [params, setParams] = useState<Record<string, number>>({});

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runBacktest = async () => {
    setLoading(true);
    setError(null);

    try {
      const selectedStrategy = STRATEGIES.find((s) => s.id === strategy);
      const strategyParams = selectedStrategy?.params.reduce(
        (acc, p) => ({
          ...acc,
          [p.name]: params[p.name] ?? p.default,
        }),
        {}
      );

      const res = await fetch('http://localhost:8000/api/v1/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol.toUpperCase(),
          strategy,
          strategy_params: strategyParams,
          timeframe,
          initial_capital: capital,
          position_size_percent: 100,
          stop_loss_enabled: true,
          take_profit_enabled: true,
          lookback,
        }),
      });

      if (!res.ok) {
        throw new Error('Backtest failed');
      }
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Backtest failed');
    } finally {
      setLoading(false);
    }
  };

  const selectedStrategy = STRATEGIES.find((s) => s.id === strategy);

  return (
    <main className="min-h-screen bg-[#0b0e11]">
      {/* Header */}
      <div className="bg-[#131722] border-b border-[#2a2e39]">
        <div className="max-w-[1800px] mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="text-xl font-bold text-white hover:text-blue-400 transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-8 h-8 text-blue-500"
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
                StockPro
              </Link>
              <span className="text-gray-500">|</span>
              <h1 className="text-lg font-semibold text-white">Backtesting</h1>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/scanner"
                className="px-4 py-2 text-sm text-gray-300 hover:text-white bg-[#1e222d] rounded-lg"
              >
                Scanner
              </Link>
              <Link
                href="/analyze"
                className="px-4 py-2 text-sm text-gray-300 hover:text-white bg-[#1e222d] rounded-lg"
              >
                Analyze
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-[1800px] mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Configuration Panel */}
          <div className="lg:col-span-1">
            <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-5 sticky top-6">
              <h2 className="text-lg font-semibold text-white mb-4">
                Configuration
              </h2>

              {/* Symbol */}
              <div className="mb-4">
                <label className="text-xs text-gray-500 uppercase mb-2 block">
                  Symbol
                </label>
                <input
                  type="text"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 bg-[#1e222d] border border-[#2a2e39] rounded-lg text-white"
                  placeholder="RELIANCE"
                />
              </div>

              {/* Strategy */}
              <div className="mb-4">
                <label className="text-xs text-gray-500 uppercase mb-2 block">
                  Strategy
                </label>
                <div className="space-y-2">
                  {STRATEGIES.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => setStrategy(s.id)}
                      className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                        strategy === s.id
                          ? 'bg-blue-600 text-white'
                          : 'bg-[#1e222d] text-gray-300 hover:bg-[#2a2e39]'
                      }`}
                    >
                      <div className="font-medium">{s.name}</div>
                      <div className="text-xs opacity-75">{s.description}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Strategy Parameters */}
              {selectedStrategy && (
                <div className="mb-4">
                  <label className="text-xs text-gray-500 uppercase mb-2 block">
                    Parameters
                  </label>
                  <div className="space-y-2">
                    {selectedStrategy.params.map((p) => (
                      <div
                        key={p.name}
                        className="flex items-center justify-between"
                      >
                        <span className="text-sm text-gray-400">{p.label}</span>
                        <input
                          type="number"
                          value={params[p.name] ?? p.default}
                          onChange={(e) =>
                            setParams({
                              ...params,
                              [p.name]: Number(e.target.value),
                            })
                          }
                          className="w-20 px-2 py-1 bg-[#1e222d] border border-[#2a2e39] rounded text-white text-sm text-right"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Timeframe */}
              <div className="mb-4">
                <label className="text-xs text-gray-500 uppercase mb-2 block">
                  Timeframe
                </label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="w-full px-3 py-2 bg-[#1e222d] border border-[#2a2e39] rounded-lg text-white"
                >
                  <option value="1h">1 Hour</option>
                  <option value="1d">Daily</option>
                </select>
              </div>

              {/* Capital */}
              <div className="mb-4">
                <label className="text-xs text-gray-500 uppercase mb-2 block">
                  Initial Capital
                </label>
                <input
                  type="number"
                  value={capital}
                  onChange={(e) => setCapital(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-[#1e222d] border border-[#2a2e39] rounded-lg text-white"
                />
              </div>

              {/* Lookback */}
              <div className="mb-4">
                <label className="text-xs text-gray-500 uppercase mb-2 block">
                  Lookback (days)
                </label>
                <input
                  type="number"
                  value={lookback}
                  onChange={(e) => setLookback(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-[#1e222d] border border-[#2a2e39] rounded-lg text-white"
                  min={30}
                  max={1000}
                />
              </div>

              {/* Run Button */}
              <button
                onClick={runBacktest}
                disabled={loading || !symbol}
                className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Running Backtest...
                  </>
                ) : (
                  <>
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
                        d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    Run Backtest
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-2">
            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg mb-4 text-red-400">
                {error}
              </div>
            )}

            {!result && !loading && (
              <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-12 text-center">
                <div className="w-16 h-16 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-blue-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-white mb-2">
                  Configure and Run Backtest
                </h2>
                <p className="text-gray-500">
                  Select a symbol, strategy, and parameters, then click
                  &ldquo;Run Backtest&rdquo;
                </p>
              </div>
            )}

            {result && (
              <div className="space-y-4">
                {/* Summary Header */}
                <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="text-xl font-bold text-white">
                        {result.symbol}
                      </h2>
                      <p className="text-gray-500">
                        {result.strategy} • {result.timeframe}
                      </p>
                    </div>
                    <div className="text-right">
                      <p
                        className={`text-3xl font-bold ${result.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}
                      >
                        {result.total_return >= 0 ? '+' : ''}₹
                        {result.total_return.toLocaleString()}
                      </p>
                      <p
                        className={`text-sm ${result.total_return_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}
                      >
                        {result.total_return_percent >= 0 ? '+' : ''}
                        {result.total_return_percent}%
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-[#2a2e39]">
                    <div>
                      <p className="text-xs text-gray-500">Initial Capital</p>
                      <p className="text-lg text-white">
                        ₹{result.initial_capital.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Final Capital</p>
                      <p className="text-lg text-white">
                        ₹{result.final_capital.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Total Trades</p>
                      <p className="text-lg text-white">
                        {result.total_trades}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Win Rate</p>
                      <p
                        className={`text-lg ${result.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}
                      >
                        {result.win_rate}%
                      </p>
                    </div>
                  </div>
                </div>

                {/* Metrics Grid */}
                <div className="grid md:grid-cols-2 gap-4">
                  {/* Performance Metrics */}
                  <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-5">
                    <h3 className="font-semibold text-white mb-4">
                      Performance Metrics
                    </h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Profit Factor</span>
                        <span
                          className={`font-mono ${result.profit_factor >= 1.5 ? 'text-green-400' : result.profit_factor >= 1 ? 'text-yellow-400' : 'text-red-400'}`}
                        >
                          {result.profit_factor}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Sharpe Ratio</span>
                        <span
                          className={`font-mono ${result.sharpe_ratio >= 1 ? 'text-green-400' : 'text-yellow-400'}`}
                        >
                          {result.sharpe_ratio}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Max Drawdown</span>
                        <span className="font-mono text-red-400">
                          -{result.max_drawdown_percent}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Avg Hold Duration</span>
                        <span className="font-mono text-white">
                          {result.avg_hold_duration} bars
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Trade Statistics */}
                  <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-5">
                    <h3 className="font-semibold text-white mb-4">
                      Trade Statistics
                    </h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Winning Trades</span>
                        <span className="font-mono text-green-400">
                          {result.winning_trades}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Losing Trades</span>
                        <span className="font-mono text-red-400">
                          {result.losing_trades}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Avg Winning Trade</span>
                        <span className="font-mono text-green-400">
                          ₹{result.avg_winning_trade.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Avg Losing Trade</span>
                        <span className="font-mono text-red-400">
                          ₹{Math.abs(result.avg_losing_trade).toLocaleString()}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Largest Win</span>
                        <span className="font-mono text-green-400">
                          ₹{result.largest_win.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Largest Loss</span>
                        <span className="font-mono text-red-400">
                          ₹{Math.abs(result.largest_loss).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Trade History */}
                <div className="bg-[#131722] rounded-lg border border-[#2a2e39] overflow-hidden">
                  <div className="px-5 py-3 border-b border-[#2a2e39]">
                    <h3 className="font-semibold text-white">Trade History</h3>
                  </div>
                  <div className="overflow-x-auto max-h-96">
                    <table className="w-full">
                      <thead className="bg-[#1e222d] sticky top-0">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs text-gray-500">
                            #
                          </th>
                          <th className="px-4 py-2 text-left text-xs text-gray-500">
                            Direction
                          </th>
                          <th className="px-4 py-2 text-right text-xs text-gray-500">
                            Entry
                          </th>
                          <th className="px-4 py-2 text-right text-xs text-gray-500">
                            Exit
                          </th>
                          <th className="px-4 py-2 text-right text-xs text-gray-500">
                            P&L
                          </th>
                          <th className="px-4 py-2 text-right text-xs text-gray-500">
                            %
                          </th>
                          <th className="px-4 py-2 text-left text-xs text-gray-500">
                            Reason
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#2a2e39]">
                        {result.trades.map((trade, idx) => (
                          <tr key={idx} className="hover:bg-[#1e222d]">
                            <td className="px-4 py-2 text-gray-500">
                              {idx + 1}
                            </td>
                            <td className="px-4 py-2">
                              <span
                                className={`px-2 py-0.5 rounded text-xs ${
                                  trade.direction === 'LONG'
                                    ? 'bg-green-500/20 text-green-400'
                                    : 'bg-red-500/20 text-red-400'
                                }`}
                              >
                                {trade.direction}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-right text-white font-mono text-sm">
                              ₹{trade.entry_price.toFixed(2)}
                            </td>
                            <td className="px-4 py-2 text-right text-white font-mono text-sm">
                              ₹{trade.exit_price.toFixed(2)}
                            </td>
                            <td
                              className={`px-4 py-2 text-right font-mono text-sm ${
                                trade.pnl >= 0
                                  ? 'text-green-400'
                                  : 'text-red-400'
                              }`}
                            >
                              {trade.pnl >= 0 ? '+' : ''}₹{trade.pnl.toFixed(0)}
                            </td>
                            <td
                              className={`px-4 py-2 text-right font-mono text-sm ${
                                trade.pnl_percent >= 0
                                  ? 'text-green-400'
                                  : 'text-red-400'
                              }`}
                            >
                              {trade.pnl_percent >= 0 ? '+' : ''}
                              {trade.pnl_percent.toFixed(1)}%
                            </td>
                            <td className="px-4 py-2 text-gray-400 text-sm truncate max-w-[200px]">
                              {trade.exit_reason}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
