'use client';

import { useEffect, useRef, useState } from 'react';

interface OHLCV {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface ChartData {
  symbol: string;
  timeframe: string;
  candles: OHLCV[];
  current_price: number;
  day_change_percent: number;
}

interface StockChartProps {
  symbol: string;
  timeframe?: string;
}

const TIMEFRAMES = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1H' },
  { value: '1d', label: '1D' },
  { value: '1w', label: '1W' },
];

export default function StockChart({
  symbol,
  timeframe: initialTimeframe = '1d',
}: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);

  const [timeframe, setTimeframe] = useState(initialTimeframe);
  const [data, setData] = useState<ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      if (!symbol) {
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch(
          `http://localhost:8000/api/v1/market/ohlcv/${symbol}?timeframe=${timeframe}&lookback=100`
        );
        if (!res.ok) {
          throw new Error('Failed to fetch chart data');
        }
        const result = await res.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load chart');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [symbol, timeframe]);

  // Initialize and update chart
  useEffect(() => {
    if (!chartContainerRef.current || !data || data.candles.length === 0) {
      return;
    }

    const initChart = async () => {
      try {
        // Dynamically import lightweight-charts v5
        const LightweightCharts = await import('lightweight-charts');

        // Clear previous chart
        if (chartRef.current) {
          chartRef.current.remove();
          chartRef.current = null;
        }

        // Create chart with v5 API
        const chart = LightweightCharts.createChart(
          chartContainerRef.current!,
          {
            layout: {
              background: { color: 'transparent' },
              textColor: '#9ca3af',
            },
            grid: {
              vertLines: { color: 'rgba(156, 163, 175, 0.1)' },
              horzLines: { color: 'rgba(156, 163, 175, 0.1)' },
            },
            width: chartContainerRef.current!.clientWidth,
            height: 400,
            timeScale: {
              timeVisible: true,
              secondsVisible: false,
            },
            rightPriceScale: {
              borderColor: 'rgba(156, 163, 175, 0.2)',
            },
            crosshair: {
              mode: 0, // Normal mode
            },
          }
        );

        // Add candlestick series - v5 API
        const candleSeries = chart.addSeries(
          LightweightCharts.CandlestickSeries,
          {
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderDownColor: '#ef4444',
            borderUpColor: '#22c55e',
            wickDownColor: '#ef4444',
            wickUpColor: '#22c55e',
          }
        );

        // Add volume series - v5 API
        const volumeSeries = chart.addSeries(
          LightweightCharts.HistogramSeries,
          {
            color: '#3b82f6',
            priceFormat: {
              type: 'volume',
            },
            priceScaleId: 'volume',
          }
        );

        // Configure volume scale
        chart.priceScale('volume').applyOptions({
          scaleMargins: {
            top: 0.8,
            bottom: 0,
          },
        });

        // Transform data - use string dates for daily timeframe
        const candleData = data.candles.map((candle) => {
          const date = new Date(candle.timestamp);
          const timeValue =
            timeframe === '1d' || timeframe === '1w'
              ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
              : Math.floor(date.getTime() / 1000);

          return {
            time: timeValue as any,
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close,
          };
        });

        const volumeData = data.candles.map((candle) => {
          const date = new Date(candle.timestamp);
          const timeValue =
            timeframe === '1d' || timeframe === '1w'
              ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
              : Math.floor(date.getTime() / 1000);

          return {
            time: timeValue as any,
            value: candle.volume,
            color:
              candle.close >= candle.open
                ? 'rgba(34, 197, 94, 0.5)'
                : 'rgba(239, 68, 68, 0.5)',
          };
        });

        candleSeries.setData(candleData);
        volumeSeries.setData(volumeData);

        // Fit content
        chart.timeScale().fitContent();

        // Handle resize
        const handleResize = () => {
          if (chartContainerRef.current && chartRef.current) {
            chartRef.current.applyOptions({
              width: chartContainerRef.current.clientWidth,
            });
          }
        };

        window.addEventListener('resize', handleResize);

        chartRef.current = chart;

        return () => {
          window.removeEventListener('resize', handleResize);
        };
      } catch (err) {
        console.error('Chart init error:', err);
        setError('Failed to initialize chart');
      }
    };

    initChart();

    // Cleanup
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [data, timeframe]);

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {symbol} Chart
          </h3>
        </div>
        <div className="h-[400px] flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded-lg">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-gray-500">Loading chart...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {symbol} Chart
          </h3>
        </div>
        <div className="h-[400px] flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded-lg">
          <div className="text-center">
            <p className="text-red-500 mb-2">{error}</p>
            <button
              onClick={() => setTimeframe(timeframe)}
              className="text-blue-500 hover:underline"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {symbol}
          </h3>
          {data && (
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-gray-900 dark:text-white">
                Rs.{data.current_price.toFixed(2)}
              </span>
              <span
                className={`text-sm font-medium ${
                  data.day_change_percent >= 0
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-red-600 dark:text-red-400'
                }`}
              >
                {data.day_change_percent >= 0 ? '+' : ''}
                {data.day_change_percent.toFixed(2)}%
              </span>
            </div>
          )}
        </div>

        {/* Timeframe selector */}
        <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.value}
              onClick={() => setTimeframe(tf.value)}
              className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                timeframe === tf.value
                  ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      <div
        ref={chartContainerRef}
        className="w-full h-[400px] bg-gray-50 dark:bg-gray-900 rounded-lg"
      />
    </div>
  );
}
