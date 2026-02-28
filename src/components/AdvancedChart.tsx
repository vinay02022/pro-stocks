'use client';

import {
  useEffect,
  useRef,
  useState,
  useCallback,
  MouseEvent as ReactMouseEvent,
} from 'react';
import Link from 'next/link';
import { isMarketOpen, getMarketStatus } from '@/lib/utils/marketHours';

interface ChartDataResponse {
  symbol: string;
  timeframe: string;
  current_price: number;
  candles: Array<{
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  overlays: {
    ema9: Array<{ time: string; value: number }>;
    ema21: Array<{ time: string; value: number }>;
    ema50: Array<{ time: string; value: number }>;
    sma20: Array<{ time: string; value: number }>;
    bb_upper: Array<{ time: string; value: number }>;
    bb_middle: Array<{ time: string; value: number }>;
    bb_lower: Array<{ time: string; value: number }>;
  };
  panels: {
    rsi: {
      data: Array<{ time: string; value: number }>;
      overbought: number;
      oversold: number;
    };
    macd: {
      macd: Array<{ time: string; value: number }>;
      signal: Array<{ time: string; value: number }>;
      histogram: Array<{ time: string; value: number; color: string }>;
    };
    volume: Array<{ time: string; value: number; color: string }>;
  };
}

interface RealtimeQuote {
  symbol: string;
  ltp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
  source: string;
  is_market_open: boolean;
}

interface AdvancedChartProps {
  symbol: string;
  timeframe?: string;
}

type LineStyle = 'solid' | 'dashed' | 'dotted';

interface PriceLine {
  id: string;
  price: number;
  color: string;
  width: number;
  style: LineStyle;
}

const TIMEFRAMES = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1H' },
  { value: '1d', label: '1D' },
  { value: '1w', label: '1W' },
];

const INDICATORS = {
  overlays: [
    { id: 'ema9', label: 'EMA 9', color: '#f59e0b' },
    { id: 'ema21', label: 'EMA 21', color: '#3b82f6' },
    { id: 'ema50', label: 'EMA 50', color: '#8b5cf6' },
    { id: 'sma20', label: 'SMA 20', color: '#ec4899' },
    { id: 'bb', label: 'Bollinger Bands', color: '#6366f1' },
  ],
  panels: [
    { id: 'rsi', label: 'RSI (14)', color: '#8b5cf6' },
    { id: 'macd', label: 'MACD', color: '#3b82f6' },
    { id: 'volume', label: 'Volume', color: '#6b7280' },
  ],
};

const LINE_COLORS = [
  '#ef4444',
  '#f97316',
  '#f59e0b',
  '#eab308',
  '#84cc16',
  '#22c55e',
  '#10b981',
  '#14b8a6',
  '#06b6d4',
  '#0ea5e9',
  '#3b82f6',
  '#6366f1',
  '#8b5cf6',
  '#a855f7',
  '#d946ef',
  '#ec4899',
  '#f43f5e',
  '#ffffff',
  '#94a3b8',
  '#64748b',
];

const LINE_WIDTHS = [1, 2, 3, 4];

// Default visible candles for different timeframes
const VISIBLE_CANDLES = {
  '1m': 60, // 1 hour of data
  '5m': 48, // 4 hours of data
  '15m': 48, // 12 hours of data
  '1h': 48, // 2 days of data
  '1d': 60, // ~3 months of data
  '1w': 52, // 1 year of data
};

// Default lookback for different timeframes
const DEFAULT_LOOKBACK = {
  '1m': 200,
  '5m': 200,
  '15m': 200,
  '1h': 300,
  '1d': 300,
  '1w': 200,
};

export default function AdvancedChart({
  symbol,
  timeframe: initialTimeframe = '15m', // Default to 15m for better view
}: AdvancedChartProps) {
  const mainChartRef = useRef<HTMLDivElement>(null);
  const rsiChartRef = useRef<HTMLDivElement>(null);
  const macdChartRef = useRef<HTMLDivElement>(null);
  const indicatorMenuRef = useRef<HTMLDivElement>(null);
  const lineEditorRef = useRef<HTMLDivElement>(null);

  const chartsRef = useRef<any[]>([]);
  const mainChartInstanceRef = useRef<any>(null);
  const candleSeriesRef = useRef<any>(null);

  // Store visible range to preserve zoom
  const visibleRangeRef = useRef<{ from: number; to: number } | null>(null);

  // Cache for timeframe data (instant switching)
  const dataCacheRef = useRef<Map<string, ChartDataResponse>>(new Map());

  // Real-time tracking
  const lastCandleRef = useRef<{
    time: any;
    open: number;
    high: number;
    low: number;
    close: number;
  } | null>(null);

  const [timeframe, setTimeframe] = useState(initialTimeframe);
  const [marketOpen, setMarketOpen] = useState(isMarketOpen());
  const [lastUpdateTime, setLastUpdateTime] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<string>('Yahoo Finance');
  const [data, setData] = useState<ChartDataResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lookback, setLookback] = useState(
    DEFAULT_LOOKBACK[initialTimeframe as keyof typeof DEFAULT_LOOKBACK] || 300
  );

  const [activeOverlays, setActiveOverlays] = useState<string[]>(['ema21']);
  const [activePanels, setActivePanels] = useState<string[]>(['volume']);
  const [showIndicatorMenu, setShowIndicatorMenu] = useState(false);

  // Price lines state
  const [priceLines, setPriceLines] = useState<PriceLine[]>([]);
  const [hoveredPrice, setHoveredPrice] = useState<number | null>(null);
  const [showPriceTooltip, setShowPriceTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [hoveredLine, setHoveredLine] = useState<PriceLine | null>(null);

  // Line editor state
  const [editingLine, setEditingLine] = useState<PriceLine | null>(null);
  const [lineEditorPosition, setLineEditorPosition] = useState({ x: 0, y: 0 });

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        indicatorMenuRef.current &&
        !indicatorMenuRef.current.contains(event.target as Node)
      ) {
        setShowIndicatorMenu(false);
      }
      if (
        lineEditorRef.current &&
        !lineEditorRef.current.contains(event.target as Node)
      ) {
        setEditingLine(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Prefetch all common timeframes on symbol change for instant switching
  useEffect(() => {
    if (!symbol) {
      return;
    }

    const prefetchTimeframes = ['1m', '5m', '15m', '1h', '1d'];

    // Prefetch in background (don't block UI)
    prefetchTimeframes.forEach((tf) => {
      const cacheKey = `${symbol}-${tf}-${DEFAULT_LOOKBACK[tf as keyof typeof DEFAULT_LOOKBACK] || 300}`;
      if (!dataCacheRef.current.has(cacheKey)) {
        fetch(
          `http://localhost:8000/api/v1/indicators/${symbol}/chart-data?timeframe=${tf}&lookback=${DEFAULT_LOOKBACK[tf as keyof typeof DEFAULT_LOOKBACK] || 300}`
        )
          .then((res) => (res.ok ? res.json() : null))
          .then((data) => {
            if (data) {
              dataCacheRef.current.set(cacheKey, data);
            }
          })
          .catch(() => {}); // Silently fail
      }
    });
  }, [symbol]);

  // Fetch data with caching for instant timeframe switching
  useEffect(() => {
    const fetchData = async () => {
      if (!symbol) {
        return;
      }

      const cacheKey = `${symbol}-${timeframe}-${lookback}`;

      // Check cache first for instant display (NO LOADING SPINNER)
      const cachedData = dataCacheRef.current.get(cacheKey);
      if (cachedData) {
        setData(cachedData);
        setIsLoading(false);
        // Still fetch fresh data in background (silent refresh)
        fetch(
          `http://localhost:8000/api/v1/indicators/${symbol}/chart-data?timeframe=${timeframe}&lookback=${lookback}`
        )
          .then((res) => (res.ok ? res.json() : null))
          .then((freshData) => {
            if (freshData) {
              dataCacheRef.current.set(cacheKey, freshData);
              setData(freshData);
            }
          })
          .catch(() => {}); // Silently fail background refresh
        return;
      }

      // Only show loading on first fetch (no cache)
      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch(
          `http://localhost:8000/api/v1/indicators/${symbol}/chart-data?timeframe=${timeframe}&lookback=${lookback}`
        );
        if (!res.ok) {
          throw new Error('Failed to fetch chart data');
        }
        const result = await res.json();
        dataCacheRef.current.set(cacheKey, result);
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load chart');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [symbol, timeframe, lookback]);

  // Real-time SSE streaming (replaces polling)
  useEffect(() => {
    if (!symbol) {
      return;
    }

    // Check market status periodically
    const marketCheckInterval = setInterval(() => {
      setMarketOpen(isMarketOpen());
    }, 60000); // Check every minute

    // Only stream during market hours
    if (!marketOpen) {
      return () => clearInterval(marketCheckInterval);
    }

    // Use Server-Sent Events for real-time updates
    const eventSource = new EventSource(
      `http://localhost:8000/api/v1/stream/price/${symbol}?interval=100`
    );

    eventSource.onmessage = (event) => {
      try {
        const quote: RealtimeQuote = JSON.parse(event.data);

        // Update last candle with real-time price (smooth update)
        if (candleSeriesRef.current && lastCandleRef.current) {
          const updatedCandle = {
            ...lastCandleRef.current,
            high: Math.max(lastCandleRef.current.high, quote.ltp),
            low: Math.min(lastCandleRef.current.low, quote.ltp),
            close: quote.ltp,
          };

          // Use requestAnimationFrame for smooth rendering
          requestAnimationFrame(() => {
            candleSeriesRef.current?.update(updatedCandle);
          });
          lastCandleRef.current = updatedCandle;
        }

        // Update UI state
        setLastUpdateTime(
          new Date(quote.timestamp).toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          })
        );
        setDataSource(quote.source);
        setMarketOpen(quote.is_market_open);
      } catch (err) {
        // Silently fail - don't disrupt chart
        console.debug('SSE parse error:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.debug('SSE connection error:', err);
      // EventSource will auto-reconnect
    };

    return () => {
      eventSource.close();
      clearInterval(marketCheckInterval);
    };
  }, [symbol, marketOpen]);

  // Auto-load more data when scrolling to the beginning
  const handleVisibleRangeChange = useCallback(
    async (logicalRange: { from: number; to: number } | null) => {
      if (!logicalRange || !data || isLoadingMore) {
        return;
      }

      // If user scrolls near the beginning (first 10 candles visible)
      // and we haven't loaded max data yet
      if (logicalRange.from < 10 && lookback < 1000) {
        setIsLoadingMore(true);
        // Increase lookback to load more data
        setLookback((prev) => Math.min(prev + 250, 1000));
      }
    },
    [data, isLoadingMore, lookback]
  );

  // Reset loading more flag when data changes
  useEffect(() => {
    setIsLoadingMore(false);
  }, [data]);

  // Add price line
  const addPriceLine = useCallback(
    (price: number) => {
      const newLine: PriceLine = {
        id: `line-${Date.now()}`,
        price,
        color: LINE_COLORS[priceLines.length % LINE_COLORS.length],
        width: 2,
        style: 'solid',
      };
      setPriceLines((prev) => [...prev, newLine]);
    },
    [priceLines.length]
  );

  // Update price line
  const updatePriceLine = useCallback(
    (id: string, updates: Partial<PriceLine>) => {
      setPriceLines((prev) =>
        prev.map((line) => (line.id === id ? { ...line, ...updates } : line))
      );
    },
    []
  );

  // Remove price line
  const removePriceLine = useCallback((id: string) => {
    setPriceLines((prev) => prev.filter((line) => line.id !== id));
    setEditingLine(null);
  }, []);

  // Handle mouse move on chart to detect price scale hover and line hover
  const handleChartMouseMove = useCallback(
    (e: ReactMouseEvent<HTMLDivElement>) => {
      if (!mainChartRef.current || !candleSeriesRef.current || editingLine) {
        return;
      }

      const rect = mainChartRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const priceScaleWidth = 70;
      const isOverPriceScale = x > rect.width - priceScaleWidth;

      // Check if hovering over a price line
      const lineHovered = priceLines.find((line) => {
        const linePriceY = candleSeriesRef.current.priceToCoordinate(
          line.price
        );
        return linePriceY && Math.abs(y - linePriceY) < 6;
      });
      setHoveredLine(lineHovered || null);

      if (isOverPriceScale && mainChartInstanceRef.current) {
        const price = candleSeriesRef.current.coordinateToPrice(y);
        if (price && price > 0) {
          setHoveredPrice(price);
          setShowPriceTooltip(true);
          setTooltipPosition({ x: e.clientX, y: e.clientY });
        }
      } else {
        setShowPriceTooltip(false);
        setHoveredPrice(null);
      }
    },
    [editingLine, priceLines]
  );

  // Handle click on chart - add line or edit existing line
  const handleChartClick = useCallback(
    (e: ReactMouseEvent<HTMLDivElement>) => {
      if (!mainChartRef.current || !candleSeriesRef.current) {
        return;
      }

      const rect = mainChartRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const priceScaleWidth = 70;
      const isClickOnPriceScale = x > rect.width - priceScaleWidth;

      // Check if clicking on an existing price line (within 5px tolerance)
      const clickedPrice = candleSeriesRef.current.coordinateToPrice(y);
      if (clickedPrice && !isClickOnPriceScale) {
        const clickedLine = priceLines.find((line) => {
          const linePriceY = candleSeriesRef.current.priceToCoordinate(
            line.price
          );
          return linePriceY && Math.abs(y - linePriceY) < 8; // 8px tolerance
        });

        if (clickedLine) {
          // Show editor near the line
          setEditingLine(clickedLine);
          setLineEditorPosition({ x: e.clientX, y: e.clientY - 60 });
          return;
        }
      }

      // Close line editor if clicking elsewhere
      if (editingLine) {
        setEditingLine(null);
        return;
      }

      // Add new line if clicking on price scale
      if (isClickOnPriceScale && hoveredPrice && hoveredPrice > 0) {
        addPriceLine(hoveredPrice);
        setShowPriceTooltip(false);
      }
    },
    [hoveredPrice, addPriceLine, editingLine, priceLines]
  );

  // Reset zoom when timeframe changes
  const handleTimeframeChange = useCallback((newTimeframe: string) => {
    visibleRangeRef.current = null; // Reset saved zoom
    setLookback(
      DEFAULT_LOOKBACK[newTimeframe as keyof typeof DEFAULT_LOOKBACK] || 300
    );
    setTimeframe(newTimeframe);
  }, []);

  const handleChartMouseLeave = useCallback(() => {
    setShowPriceTooltip(false);
    setHoveredPrice(null);
    setHoveredLine(null);
  }, []);

  // Handle click on a price line to edit it
  const handleLineClick = useCallback((line: PriceLine, e: MouseEvent) => {
    e.stopPropagation();
    setEditingLine(line);
    setLineEditorPosition({ x: e.clientX, y: e.clientY });
  }, []);

  // Initialize charts
  useEffect(() => {
    if (!data || !mainChartRef.current) {
      return;
    }

    const initCharts = async () => {
      try {
        const LightweightCharts = await import('lightweight-charts');

        // Clear previous charts
        chartsRef.current.forEach((c) => c?.remove());
        chartsRef.current = [];

        const chartOptions = {
          layout: {
            background: { color: '#131722' },
            textColor: '#d1d4dc',
          },
          grid: {
            vertLines: { color: 'rgba(42, 46, 57, 0.6)' },
            horzLines: { color: 'rgba(42, 46, 57, 0.6)' },
          },
          timeScale: {
            timeVisible: true,
            secondsVisible: false,
            borderColor: '#2a2e39',
            rightOffset: 10,
            barSpacing: 8,
            minBarSpacing: 2,
          },
          rightPriceScale: {
            borderColor: '#2a2e39',
            scaleMargins: {
              top: 0.1,
              bottom: 0.2,
            },
          },
          crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {
              color: '#758696',
              width: 1,
              style: LightweightCharts.LineStyle.Dashed,
              labelBackgroundColor: '#2962ff',
            },
            horzLine: {
              color: '#758696',
              width: 1,
              style: LightweightCharts.LineStyle.Dashed,
              labelBackgroundColor: '#2962ff',
            },
          },
          handleScroll: {
            vertTouchDrag: true,
          },
          handleScale: {
            axisPressedMouseMove: true,
            mouseWheel: true,
            pinch: true,
          },
        };

        const convertTime = (timeStr: string) => {
          const date = new Date(timeStr);
          return timeframe === '1d' || timeframe === '1w'
            ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
            : Math.floor(date.getTime() / 1000);
        };

        const getLineStyle = (style: LineStyle) => {
          switch (style) {
            case 'dashed':
              return LightweightCharts.LineStyle.Dashed;
            case 'dotted':
              return LightweightCharts.LineStyle.Dotted;
            default:
              return LightweightCharts.LineStyle.Solid;
          }
        };

        // ============ MAIN CHART ============
        const mainChart = LightweightCharts.createChart(mainChartRef.current!, {
          ...chartOptions,
          width: mainChartRef.current!.clientWidth,
          height: 400,
        });

        mainChartInstanceRef.current = mainChart;

        // Candlesticks
        const candleSeries = mainChart.addSeries(
          LightweightCharts.CandlestickSeries,
          {
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderDownColor: '#ef5350',
            borderUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            wickUpColor: '#26a69a',
          }
        );

        candleSeriesRef.current = candleSeries;

        const candleData = data.candles.map((c) => ({
          time: convertTime(c.time) as any,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }));

        candleSeries.setData(candleData);

        // Store last candle for real-time updates
        if (candleData.length > 0) {
          lastCandleRef.current = candleData[candleData.length - 1];
        }

        // Add price lines with click handlers
        priceLines.forEach((line) => {
          const priceLine = candleSeries.createPriceLine({
            price: line.price,
            color: line.color,
            lineWidth: line.width,
            lineStyle: getLineStyle(line.style),
            axisLabelVisible: true,
            title: '',
          });

          // Note: lightweight-charts doesn't have native click on price lines
          // We'll handle this via coordinate detection
        });

        // Subscribe to visible range changes for auto-loading more data and saving zoom
        mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
          if (range) {
            visibleRangeRef.current = range; // Save zoom level
          }
          handleVisibleRangeChange(range);
        });

        // Add overlay indicators
        const overlayColors: Record<string, string> = {
          ema9: '#f59e0b',
          ema21: '#2962ff',
          ema50: '#9c27b0',
          sma20: '#e91e63',
        };

        activeOverlays.forEach((overlay) => {
          if (overlay === 'bb') {
            const bbUpper = mainChart.addSeries(LightweightCharts.LineSeries, {
              color: 'rgba(99, 102, 241, 0.8)',
              lineWidth: 1,
              lineStyle: LightweightCharts.LineStyle.Dotted,
            });
            const bbMiddle = mainChart.addSeries(LightweightCharts.LineSeries, {
              color: 'rgba(99, 102, 241, 0.5)',
              lineWidth: 1,
            });
            const bbLower = mainChart.addSeries(LightweightCharts.LineSeries, {
              color: 'rgba(99, 102, 241, 0.8)',
              lineWidth: 1,
              lineStyle: LightweightCharts.LineStyle.Dotted,
            });

            bbUpper.setData(
              data.overlays.bb_upper.map((d) => ({
                time: convertTime(d.time) as any,
                value: d.value,
              }))
            );
            bbMiddle.setData(
              data.overlays.bb_middle.map((d) => ({
                time: convertTime(d.time) as any,
                value: d.value,
              }))
            );
            bbLower.setData(
              data.overlays.bb_lower.map((d) => ({
                time: convertTime(d.time) as any,
                value: d.value,
              }))
            );
          } else if (data.overlays[overlay as keyof typeof data.overlays]) {
            const series = mainChart.addSeries(LightweightCharts.LineSeries, {
              color: overlayColors[overlay] || '#888',
              lineWidth: 2,
            });

            const overlayData = data.overlays[
              overlay as keyof typeof data.overlays
            ] as Array<{
              time: string;
              value: number;
            }>;
            series.setData(
              overlayData.map((d) => ({
                time: convertTime(d.time) as any,
                value: d.value,
              }))
            );
          }
        });

        // Volume on main chart - anchored to very bottom
        if (activePanels.includes('volume')) {
          const volumeSeries = mainChart.addSeries(
            LightweightCharts.HistogramSeries,
            {
              priceFormat: { type: 'volume' },
              priceScaleId: 'volume',
              lastValueVisible: false,
              priceLineVisible: false,
              base: 0,
            }
          );

          mainChart.priceScale('volume').applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
            alignLabels: false,
            borderVisible: false,
          });

          volumeSeries.setData(
            data.panels.volume.map((d) => ({
              time: convertTime(d.time) as any,
              value: d.value,
              color: d.color,
            }))
          );
        }

        // Set initial zoom - show only recent candles, not all
        const totalCandles = data.candles.length;
        const visibleCandles =
          VISIBLE_CANDLES[timeframe as keyof typeof VISIBLE_CANDLES] || 60;

        // If we have a saved visible range, restore it
        if (visibleRangeRef.current) {
          mainChart.timeScale().setVisibleLogicalRange(visibleRangeRef.current);
        } else {
          // Default: show last N candles
          const from = Math.max(0, totalCandles - visibleCandles);
          const to = totalCandles;
          mainChart.timeScale().setVisibleLogicalRange({ from, to });
        }

        chartsRef.current.push(mainChart);

        // ============ RSI CHART ============
        if (activePanels.includes('rsi') && rsiChartRef.current) {
          const rsiChart = LightweightCharts.createChart(rsiChartRef.current!, {
            ...chartOptions,
            width: rsiChartRef.current!.clientWidth,
            height: 150,
            rightPriceScale: {
              ...chartOptions.rightPriceScale,
              scaleMargins: { top: 0.1, bottom: 0.1 },
            },
          });

          const overboughtLine = rsiChart.addSeries(
            LightweightCharts.LineSeries,
            {
              color: 'rgba(239, 68, 68, 0.5)',
              lineWidth: 1,
              lineStyle: LightweightCharts.LineStyle.Dashed,
              priceLineVisible: false,
              lastValueVisible: false,
            }
          );

          const oversoldLine = rsiChart.addSeries(
            LightweightCharts.LineSeries,
            {
              color: 'rgba(34, 197, 94, 0.5)',
              lineWidth: 1,
              lineStyle: LightweightCharts.LineStyle.Dashed,
              priceLineVisible: false,
              lastValueVisible: false,
            }
          );

          const middleLine = rsiChart.addSeries(LightweightCharts.LineSeries, {
            color: 'rgba(156, 163, 175, 0.3)',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dotted,
            priceLineVisible: false,
            lastValueVisible: false,
          });

          const rsiSeries = rsiChart.addSeries(LightweightCharts.LineSeries, {
            color: '#8b5cf6',
            lineWidth: 2,
          });

          const rsiData = data.panels.rsi.data.map((d) => ({
            time: convertTime(d.time) as any,
            value: d.value,
          }));

          const timeRange = rsiData.map((d) => ({ time: d.time, value: 70 }));
          const timeRange30 = rsiData.map((d) => ({ time: d.time, value: 30 }));
          const timeRange50 = rsiData.map((d) => ({ time: d.time, value: 50 }));

          overboughtLine.setData(timeRange);
          oversoldLine.setData(timeRange30);
          middleLine.setData(timeRange50);
          rsiSeries.setData(rsiData);

          rsiChart.timeScale().applyOptions({
            rightOffset: 10,
            barSpacing: 8,
          });
          rsiChart.timeScale().fitContent();

          mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
            if (range) {
              rsiChart.timeScale().setVisibleLogicalRange(range);
            }
          });

          chartsRef.current.push(rsiChart);
        }

        // ============ MACD CHART ============
        if (activePanels.includes('macd') && macdChartRef.current) {
          const macdChart = LightweightCharts.createChart(
            macdChartRef.current!,
            {
              ...chartOptions,
              width: macdChartRef.current!.clientWidth,
              height: 150,
            }
          );

          const macdLine = macdChart.addSeries(LightweightCharts.LineSeries, {
            color: '#2962ff',
            lineWidth: 2,
            priceLineVisible: false,
          });

          const signalLine = macdChart.addSeries(LightweightCharts.LineSeries, {
            color: '#ff6d00',
            lineWidth: 2,
            priceLineVisible: false,
          });

          const histogram = macdChart.addSeries(
            LightweightCharts.HistogramSeries,
            {
              priceScaleId: 'histogram',
              priceLineVisible: false,
            }
          );

          macdChart.priceScale('histogram').applyOptions({
            scaleMargins: { top: 0.5, bottom: 0 },
          });

          macdLine.setData(
            data.panels.macd.macd.map((d) => ({
              time: convertTime(d.time) as any,
              value: d.value,
            }))
          );

          signalLine.setData(
            data.panels.macd.signal.map((d) => ({
              time: convertTime(d.time) as any,
              value: d.value,
            }))
          );

          histogram.setData(
            data.panels.macd.histogram.map((d) => ({
              time: convertTime(d.time) as any,
              value: d.value,
              color: d.color,
            }))
          );

          macdChart.timeScale().applyOptions({
            rightOffset: 10,
            barSpacing: 8,
          });
          macdChart.timeScale().fitContent();

          mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
            if (range) {
              macdChart.timeScale().setVisibleLogicalRange(range);
            }
          });

          chartsRef.current.push(macdChart);
        }

        // Handle resize
        const handleResize = () => {
          chartsRef.current.forEach((chart, i) => {
            const container = [mainChartRef, rsiChartRef, macdChartRef][i]
              ?.current;
            if (container && chart) {
              chart.applyOptions({ width: container.clientWidth });
            }
          });
        };

        window.addEventListener('resize', handleResize);

        return () => {
          window.removeEventListener('resize', handleResize);
        };
      } catch (err) {
        console.error('Chart init error:', err);
        setError('Failed to initialize chart');
      }
    };

    initCharts();

    return () => {
      chartsRef.current.forEach((c) => c?.remove());
      chartsRef.current = [];
    };
  }, [
    data,
    activeOverlays,
    activePanels,
    timeframe,
    priceLines,
    handleVisibleRangeChange,
  ]);

  const toggleOverlay = (id: string) => {
    setActiveOverlays((prev) =>
      prev.includes(id) ? prev.filter((o) => o !== id) : [...prev, id]
    );
  };

  const togglePanel = (id: string) => {
    setActivePanels((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  if (isLoading) {
    return (
      <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-6">
        <div className="h-[500px] flex items-center justify-center">
          <div className="text-center">
            <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-gray-400 text-sm">Loading chart data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[#131722] rounded-lg border border-[#2a2e39] p-6">
        <div className="h-[400px] flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-400 mb-3">{error}</p>
            <button
              onClick={() => setTimeframe(timeframe)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const lastCandle = data?.candles[data.candles.length - 1];
  const prevCandle = data?.candles[data.candles.length - 2];
  const priceChange =
    lastCandle && prevCandle ? lastCandle.close - prevCandle.close : 0;
  const priceChangePercent = prevCandle
    ? (priceChange / prevCandle.close) * 100
    : 0;

  return (
    <div className="bg-[#131722] rounded-lg border border-[#2a2e39] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#2a2e39] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-4">
          <div>
            <h3 className="text-lg font-semibold text-white">{symbol}</h3>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-white">
                {data?.current_price.toFixed(2)}
              </span>
              <span
                className={`text-sm font-medium px-2 py-0.5 rounded ${
                  priceChange >= 0
                    ? 'text-green-400 bg-green-400/10'
                    : 'text-red-400 bg-red-400/10'
                }`}
              >
                {priceChange >= 0 ? '+' : ''}
                {priceChange.toFixed(2)} ({priceChangePercent.toFixed(2)}%)
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Clear Lines Button */}
          {priceLines.length > 0 && (
            <button
              onClick={() => setPriceLines([])}
              className="px-3 py-1.5 text-xs font-medium text-gray-400 hover:text-white bg-[#1e222d] hover:bg-[#2a2e39] rounded-lg transition-colors flex items-center gap-1.5"
              title="Clear all price lines"
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
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
              Clear Lines
            </button>
          )}

          {/* Indicators Button */}
          <div className="relative" ref={indicatorMenuRef}>
            <button
              onClick={() => setShowIndicatorMenu(!showIndicatorMenu)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors ${
                showIndicatorMenu
                  ? 'bg-blue-600 text-white'
                  : 'bg-[#1e222d] text-gray-300 hover:bg-[#2a2e39]'
              }`}
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
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              Indicators
              <span className="bg-blue-500 text-white text-xs px-1.5 rounded">
                {activeOverlays.length + activePanels.length}
              </span>
            </button>

            {showIndicatorMenu && (
              <div className="absolute right-0 mt-2 w-72 bg-[#1e222d] border border-[#2a2e39] rounded-lg shadow-2xl z-50">
                <div className="flex items-center justify-between px-4 py-2 border-b border-[#2a2e39]">
                  <span className="text-sm font-semibold text-white">
                    Indicators
                  </span>
                  <button
                    onClick={() => setShowIndicatorMenu(false)}
                    className="text-gray-400 hover:text-white transition-colors"
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
                </div>

                <div className="p-3">
                  <div className="mb-4">
                    <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                      Overlays
                    </h4>
                    <div className="space-y-1">
                      {INDICATORS.overlays.map((ind) => (
                        <label
                          key={ind.id}
                          className="flex items-center gap-3 px-2 py-1.5 rounded cursor-pointer hover:bg-[#2a2e39] transition-colors"
                        >
                          <input
                            type="checkbox"
                            checked={activeOverlays.includes(ind.id)}
                            onChange={() => toggleOverlay(ind.id)}
                            className="w-4 h-4 rounded border-gray-600 bg-[#131722] text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                          />
                          <span
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: ind.color }}
                          />
                          <span className="text-sm text-gray-200">
                            {ind.label}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                      Panels
                    </h4>
                    <div className="space-y-1">
                      {INDICATORS.panels.map((ind) => (
                        <label
                          key={ind.id}
                          className="flex items-center gap-3 px-2 py-1.5 rounded cursor-pointer hover:bg-[#2a2e39] transition-colors"
                        >
                          <input
                            type="checkbox"
                            checked={activePanels.includes(ind.id)}
                            onChange={() => togglePanel(ind.id)}
                            className="w-4 h-4 rounded border-gray-600 bg-[#131722] text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                          />
                          <span className="text-sm text-gray-200">
                            {ind.label}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Timeframe selector */}
          <div className="flex items-center bg-[#1e222d] rounded-lg p-1">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.value}
                onClick={() => handleTimeframeChange(tf.value)}
                className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                  timeframe === tf.value
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>

          {/* Fullscreen Chart Button */}
          <Link
            href={`/chart/${symbol}`}
            className="px-3 py-1.5 text-sm font-medium text-gray-300 bg-[#1e222d] hover:bg-[#2a2e39] rounded-lg transition-colors flex items-center gap-2"
            title="Open fullscreen chart"
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
                d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
              />
            </svg>
            Fullscreen
          </Link>
        </div>
      </div>

      {/* Active indicators and price lines display */}
      {(activeOverlays.length > 0 || priceLines.length > 0) && (
        <div className="px-4 py-2 border-b border-[#2a2e39] flex items-center gap-2 flex-wrap">
          {activeOverlays.map((id) => {
            const ind = INDICATORS.overlays.find((i) => i.id === id);
            return ind ? (
              <span
                key={id}
                className="px-2 py-1 text-xs rounded-full flex items-center gap-1.5 bg-[#1e222d] border border-[#2a2e39]"
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: ind.color }}
                />
                <span className="text-gray-300">{ind.label}</span>
                <button
                  onClick={() => toggleOverlay(id)}
                  className="text-gray-500 hover:text-white ml-1"
                >
                  ×
                </button>
              </span>
            ) : null;
          })}
          {priceLines.map((line) => (
            <button
              key={line.id}
              onClick={(e) => {
                setEditingLine(line);
                setLineEditorPosition({ x: e.clientX, y: e.clientY });
              }}
              className="px-2 py-1 text-xs rounded-full flex items-center gap-1.5 bg-[#1e222d] border border-[#2a2e39] hover:border-blue-500 transition-colors cursor-pointer"
            >
              <span
                className="w-3 h-0.5"
                style={{
                  backgroundColor: line.color,
                  borderStyle:
                    line.style === 'dashed'
                      ? 'dashed'
                      : line.style === 'dotted'
                        ? 'dotted'
                        : 'solid',
                }}
              />
              <span className="text-gray-300">{line.price.toFixed(2)}</span>
            </button>
          ))}
        </div>
      )}

      {/* Loading more indicator */}
      {isLoadingMore && (
        <div className="px-4 py-1 bg-blue-600/20 text-blue-400 text-xs flex items-center gap-2">
          <div className="w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin" />
          Loading more historical data...
        </div>
      )}

      {/* Main Chart */}
      <div
        ref={mainChartRef}
        className="w-full relative"
        style={{
          height: '400px',
          cursor: hoveredLine
            ? 'pointer'
            : showPriceTooltip
              ? 'crosshair'
              : 'default',
        }}
        onMouseMove={handleChartMouseMove}
        onClick={handleChartClick}
        onMouseLeave={handleChartMouseLeave}
      />

      {/* Price Line Add Tooltip */}
      {showPriceTooltip && hoveredPrice && !editingLine && (
        <div
          className="fixed z-50 pointer-events-none flex items-center gap-1"
          style={{
            left: tooltipPosition.x - 100,
            top: tooltipPosition.y - 14,
          }}
        >
          <div className="bg-blue-600 text-white pl-2 pr-3 py-1 rounded shadow-lg flex items-center gap-1.5 text-sm font-medium whitespace-nowrap">
            <svg
              className="w-4 h-4 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M12 4v16m8-8H4"
              />
            </svg>
            <span>Add line at {hoveredPrice.toFixed(2)}</span>
          </div>
          <div className="w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-l-[8px] border-l-blue-600"></div>
        </div>
      )}

      {/* Line Editor Toolbar - TradingView style */}
      {editingLine && (
        <div
          ref={lineEditorRef}
          className="fixed z-50"
          style={{
            left: Math.max(
              10,
              Math.min(lineEditorPosition.x - 200, window.innerWidth - 420)
            ),
            top: Math.max(10, lineEditorPosition.y),
          }}
        >
          <div className="bg-[#1e222d] border border-[#2a2e39] rounded-lg shadow-2xl flex items-center gap-1 p-1.5">
            {/* Line Style Icons */}
            <div className="flex items-center border-r border-[#2a2e39] pr-1 mr-1">
              {(['solid', 'dashed', 'dotted'] as LineStyle[]).map((style) => (
                <button
                  key={style}
                  onClick={() => updatePriceLine(editingLine.id, { style })}
                  className={`w-8 h-8 rounded flex items-center justify-center transition-colors ${
                    editingLine.style === style
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:bg-[#2a2e39] hover:text-white'
                  }`}
                  title={style.charAt(0).toUpperCase() + style.slice(1)}
                >
                  <svg width="20" height="2" viewBox="0 0 20 2">
                    <line
                      x1="0"
                      y1="1"
                      x2="20"
                      y2="1"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeDasharray={
                        style === 'dashed'
                          ? '4,2'
                          : style === 'dotted'
                            ? '1,2'
                            : 'none'
                      }
                    />
                  </svg>
                </button>
              ))}
            </div>

            {/* Line Width */}
            <div className="flex items-center border-r border-[#2a2e39] pr-1 mr-1">
              {LINE_WIDTHS.map((width) => (
                <button
                  key={width}
                  onClick={() => updatePriceLine(editingLine.id, { width })}
                  className={`w-8 h-8 rounded flex items-center justify-center text-xs font-medium transition-colors ${
                    editingLine.width === width
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:bg-[#2a2e39] hover:text-white'
                  }`}
                  title={`${width}px width`}
                >
                  {width}
                </button>
              ))}
            </div>

            {/* Color Picker */}
            <div className="relative group">
              <button
                className="w-8 h-8 rounded flex items-center justify-center transition-colors hover:bg-[#2a2e39]"
                title="Change color"
              >
                <div
                  className="w-5 h-5 rounded border border-gray-600"
                  style={{ backgroundColor: editingLine.color }}
                />
              </button>
              {/* Color dropdown on hover */}
              <div className="absolute left-0 top-full mt-1 hidden group-hover:block bg-[#1e222d] border border-[#2a2e39] rounded-lg shadow-2xl p-2 z-50">
                <div className="grid grid-cols-5 gap-1 w-32">
                  {LINE_COLORS.map((color) => (
                    <button
                      key={color}
                      onClick={() => updatePriceLine(editingLine.id, { color })}
                      className={`w-5 h-5 rounded border transition-transform hover:scale-125 ${
                        editingLine.color === color
                          ? 'border-white'
                          : 'border-transparent'
                      }`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Separator */}
            <div className="w-px h-6 bg-[#2a2e39] mx-1" />

            {/* Price Label */}
            <span className="text-xs text-gray-300 px-2 font-mono">
              {editingLine.price.toFixed(2)}
            </span>

            {/* Separator */}
            <div className="w-px h-6 bg-[#2a2e39] mx-1" />

            {/* Delete Button */}
            <button
              onClick={() => removePriceLine(editingLine.id)}
              className="w-8 h-8 rounded flex items-center justify-center text-gray-400 hover:bg-red-500/20 hover:text-red-400 transition-colors"
              title="Delete line"
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
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>

            {/* Close Button */}
            <button
              onClick={() => setEditingLine(null)}
              className="w-8 h-8 rounded flex items-center justify-center text-gray-400 hover:bg-[#2a2e39] hover:text-white transition-colors"
              title="Close"
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
          </div>
        </div>
      )}

      {/* RSI Panel */}
      {activePanels.includes('rsi') && (
        <div className="border-t border-[#2a2e39]">
          <div className="px-4 py-1 text-xs text-gray-500 flex items-center justify-between">
            <span>RSI (14)</span>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="text-red-400">Overbought: 70</span>
              <span className="text-green-400">Oversold: 30</span>
            </div>
          </div>
          <div
            ref={rsiChartRef}
            className="w-full"
            style={{ height: '150px' }}
          />
        </div>
      )}

      {/* MACD Panel */}
      {activePanels.includes('macd') && (
        <div className="border-t border-[#2a2e39]">
          <div className="px-4 py-1 text-xs text-gray-500 flex items-center justify-between">
            <span>MACD (12, 26, 9)</span>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="flex items-center gap-1">
                <span className="w-2 h-0.5 bg-[#2962ff]"></span>
                MACD
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-0.5 bg-[#ff6d00]"></span>
                Signal
              </span>
            </div>
          </div>
          <div
            ref={macdChartRef}
            className="w-full"
            style={{ height: '150px' }}
          />
        </div>
      )}

      {/* Footer */}
      <div className="px-4 py-2 border-t border-[#2a2e39] flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <span>{data?.candles.length} candles loaded</span>
          {lookback < 1000 && (
            <button
              onClick={() => setLookback(Math.min(lookback + 250, 1000))}
              className="text-blue-400 hover:text-blue-300 transition-colors"
            >
              Load more history (+250)
            </button>
          )}
          {lookback >= 1000 && (
            <span className="text-green-400">Max history loaded</span>
          )}
        </div>
        <div className="flex items-center gap-4">
          {marketOpen && (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-green-400">Live</span>
              {lastUpdateTime && (
                <span className="text-gray-500">• {lastUpdateTime}</span>
              )}
            </span>
          )}
          {!marketOpen && (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-gray-500 rounded-full" />
              <span>Market Closed</span>
            </span>
          )}
          <span>Data via {dataSource} • Click price scale to add lines</span>
        </div>
      </div>
    </div>
  );
}
