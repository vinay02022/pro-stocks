'use client';

import {
  useEffect,
  useRef,
  useState,
  useCallback,
  MouseEvent as ReactMouseEvent,
} from 'react';
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

interface FullScreenChartProps {
  symbol: string;
  isDarkMode?: boolean;
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
  { value: '1d', label: 'D' },
  { value: '1w', label: 'W' },
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
    { id: 'rsi', label: 'RSI', color: '#8b5cf6' },
    { id: 'macd', label: 'MACD', color: '#3b82f6' },
    { id: 'volume', label: 'Vol', color: '#6b7280' },
  ],
};

const LINE_COLORS = [
  '#ef4444',
  '#22c55e',
  '#3b82f6',
  '#f59e0b',
  '#8b5cf6',
  '#ec4899',
  '#14b8a6',
  '#f97316',
  '#6366f1',
  '#ffffff',
];

const VISIBLE_CANDLES: Record<string, number> = {
  '1m': 80,
  '5m': 60,
  '15m': 60,
  '1h': 60,
  '1d': 80,
  '1w': 60,
};

export default function FullScreenChart({
  symbol,
  isDarkMode = true,
}: FullScreenChartProps) {
  const mainChartRef = useRef<HTMLDivElement>(null);
  const rsiChartRef = useRef<HTMLDivElement>(null);
  const macdChartRef = useRef<HTMLDivElement>(null);
  const indicatorMenuRef = useRef<HTMLDivElement>(null);
  const lineEditorRef = useRef<HTMLDivElement>(null);

  const chartsRef = useRef<any[]>([]);
  const mainChartInstanceRef = useRef<any>(null);
  const candleSeriesRef = useRef<any>(null);
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

  const [timeframe, setTimeframe] = useState('15m');
  const [data, setData] = useState<ChartDataResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lookback, setLookback] = useState(200);
  const [marketOpen, setMarketOpen] = useState(isMarketOpen());
  const [lastUpdateTime, setLastUpdateTime] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<string>('Yahoo Finance');

  const [activeOverlays, setActiveOverlays] = useState<string[]>(['ema21']);
  const [activePanels, setActivePanels] = useState<string[]>(['volume']);
  const [showIndicatorMenu, setShowIndicatorMenu] = useState(false);

  // OHLC display
  const [ohlcData, setOhlcData] = useState<{
    open: number;
    high: number;
    low: number;
    close: number;
    change: number;
    changePercent: number;
  } | null>(null);

  // Price lines
  const [priceLines, setPriceLines] = useState<PriceLine[]>([]);
  const [hoveredPrice, setHoveredPrice] = useState<number | null>(null);
  const [showPriceTooltip, setShowPriceTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [hoveredLine, setHoveredLine] = useState<PriceLine | null>(null);

  // Line editor
  const [editingLine, setEditingLine] = useState<PriceLine | null>(null);
  const [lineEditorPosition, setLineEditorPosition] = useState({ x: 0, y: 0 });

  // Drawing tool
  const [activeTool, setActiveTool] = useState<string | null>(null);

  // Default lookback for different timeframes
  const DEFAULT_LOOKBACK: Record<string, number> = {
    '1m': 200,
    '5m': 200,
    '15m': 200,
    '1h': 300,
    '1d': 300,
    '1w': 200,
  };

  // Close dropdowns
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
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Prefetch all common timeframes on symbol change for instant switching
  useEffect(() => {
    if (!symbol) {
      return;
    }

    const prefetchTimeframes = ['1m', '5m', '15m', '1h', '1d'];

    // Prefetch in background (don't block UI)
    prefetchTimeframes.forEach((tf) => {
      const tfLookback = DEFAULT_LOOKBACK[tf] || 200;
      const cacheKey = `${symbol}-${tf}-${tfLookback}`;
      if (!dataCacheRef.current.has(cacheKey)) {
        fetch(
          `http://localhost:8000/api/v1/indicators/${symbol}/chart-data?timeframe=${tf}&lookback=${tfLookback}`
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

      // Check cache first for instant display
      const cachedData = dataCacheRef.current.get(cacheKey);
      if (cachedData) {
        setData(cachedData);
        setIsLoading(false);

        // Set initial OHLC from cached data
        if (cachedData.candles?.length > 0) {
          const last = cachedData.candles[cachedData.candles.length - 1];
          const prev = cachedData.candles[cachedData.candles.length - 2];
          setOhlcData({
            open: last.open,
            high: last.high,
            low: last.low,
            close: last.close,
            change: last.close - (prev?.close || last.open),
            changePercent: prev
              ? ((last.close - prev.close) / prev.close) * 100
              : 0,
          });
        }

        // Still fetch fresh data in background
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

      setIsLoading(true);
      try {
        const res = await fetch(
          `http://localhost:8000/api/v1/indicators/${symbol}/chart-data?timeframe=${timeframe}&lookback=${lookback}`
        );
        if (!res.ok) {
          throw new Error('Failed to fetch');
        }
        const result = await res.json();
        dataCacheRef.current.set(cacheKey, result);
        setData(result);

        // Set initial OHLC from last candle
        if (result.candles?.length > 0) {
          const last = result.candles[result.candles.length - 1];
          const prev = result.candles[result.candles.length - 2];
          setOhlcData({
            open: last.open,
            high: last.high,
            low: last.low,
            close: last.close,
            change: last.close - (prev?.close || last.open),
            changePercent: prev
              ? ((last.close - prev.close) / prev.close) * 100
              : 0,
          });
        }
      } catch (err) {
        console.error(err);
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

          // Update OHLC display
          setOhlcData((prev) =>
            prev
              ? {
                  ...prev,
                  high: Math.max(prev.high, quote.ltp),
                  low: Math.min(prev.low, quote.ltp),
                  close: quote.ltp,
                  change: quote.ltp - (prev.open || quote.ltp),
                  changePercent: prev.open
                    ? ((quote.ltp - prev.open) / prev.open) * 100
                    : 0,
                }
              : null
          );
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

  // Price line functions
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

  const updatePriceLine = useCallback(
    (id: string, updates: Partial<PriceLine>) => {
      setPriceLines((prev) =>
        prev.map((line) => (line.id === id ? { ...line, ...updates } : line))
      );
    },
    []
  );

  const removePriceLine = useCallback((id: string) => {
    setPriceLines((prev) => prev.filter((line) => line.id !== id));
    setEditingLine(null);
  }, []);

  // Mouse handlers
  const handleChartMouseMove = useCallback(
    (e: ReactMouseEvent<HTMLDivElement>) => {
      if (!mainChartRef.current || !candleSeriesRef.current || editingLine) {
        return;
      }
      const rect = mainChartRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const priceScaleWidth = 60;
      const isOverPriceScale = x > rect.width - priceScaleWidth;

      // Check line hover
      const lineHovered = priceLines.find((line) => {
        const linePriceY = candleSeriesRef.current.priceToCoordinate(
          line.price
        );
        return linePriceY && Math.abs(y - linePriceY) < 6;
      });
      setHoveredLine(lineHovered || null);

      if (isOverPriceScale) {
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

  const handleChartClick = useCallback(
    (e: ReactMouseEvent<HTMLDivElement>) => {
      if (!mainChartRef.current || !candleSeriesRef.current) {
        return;
      }
      const rect = mainChartRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const priceScaleWidth = 60;
      const isClickOnPriceScale = x > rect.width - priceScaleWidth;

      // Check line click
      const clickedLine = priceLines.find((line) => {
        const linePriceY = candleSeriesRef.current.priceToCoordinate(
          line.price
        );
        return linePriceY && Math.abs(y - linePriceY) < 8;
      });

      if (clickedLine && !isClickOnPriceScale) {
        setEditingLine(clickedLine);
        setLineEditorPosition({ x: e.clientX, y: e.clientY - 50 });
        return;
      }

      if (editingLine) {
        setEditingLine(null);
        return;
      }

      if (isClickOnPriceScale && hoveredPrice && hoveredPrice > 0) {
        addPriceLine(hoveredPrice);
        setShowPriceTooltip(false);
      }
    },
    [hoveredPrice, addPriceLine, editingLine, priceLines]
  );

  const handleChartMouseLeave = useCallback(() => {
    setShowPriceTooltip(false);
    setHoveredPrice(null);
    setHoveredLine(null);
  }, []);

  const handleTimeframeChange = useCallback((newTf: string) => {
    visibleRangeRef.current = null;
    setTimeframe(newTf);
  }, []);

  // Initialize chart
  useEffect(() => {
    if (!data || !mainChartRef.current) {
      return;
    }

    const initCharts = async () => {
      const LightweightCharts = await import('lightweight-charts');
      chartsRef.current.forEach((c) => c?.remove());
      chartsRef.current = [];

      // Theme-dependent colors
      const themeColors = isDarkMode
        ? {
            background: '#131722',
            text: '#d1d4dc',
            gridLines: 'rgba(42, 46, 57, 0.5)',
            border: '#2a2e39',
            crosshair: '#758696',
          }
        : {
            background: '#ffffff',
            text: '#333333',
            gridLines: 'rgba(200, 200, 200, 0.5)',
            border: '#e0e0e0',
            crosshair: '#888888',
          };

      const chartOptions = {
        layout: {
          background: { color: themeColors.background },
          textColor: themeColors.text,
        },
        grid: {
          vertLines: { color: themeColors.gridLines },
          horzLines: { color: themeColors.gridLines },
        },
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
          borderColor: themeColors.border,
          rightOffset: 5,
          barSpacing: 10,
        },
        rightPriceScale: {
          borderColor: themeColors.border,
          scaleMargins: { top: 0.05, bottom: 0.15 },
        },
        crosshair: {
          mode: LightweightCharts.CrosshairMode.Normal,
          vertLine: {
            color: themeColors.crosshair,
            width: 1,
            style: 2,
            labelBackgroundColor: '#2962ff',
          },
          horzLine: {
            color: themeColors.crosshair,
            width: 1,
            style: 2,
            labelBackgroundColor: '#2962ff',
          },
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

      // Calculate chart height based on panels
      const rsiHeight = activePanels.includes('rsi') ? 100 : 0;
      const macdHeight = activePanels.includes('macd') ? 100 : 0;
      const mainHeight =
        mainChartRef.current!.parentElement!.clientHeight -
        rsiHeight -
        macdHeight -
        40;

      const mainChart = LightweightCharts.createChart(mainChartRef.current!, {
        ...chartOptions,
        width: mainChartRef.current!.clientWidth,
        height: Math.max(300, mainHeight),
      });

      mainChartInstanceRef.current = mainChart;

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

      // OHLC crosshair data
      mainChart.subscribeCrosshairMove((param: any) => {
        if (param.time && param.seriesData) {
          const candle = param.seriesData.get(candleSeries);
          if (candle) {
            const prevIdx =
              candleData.findIndex((c) => c.time === param.time) - 1;
            const prevClose =
              prevIdx >= 0 ? candleData[prevIdx].close : candle.open;
            setOhlcData({
              open: candle.open,
              high: candle.high,
              low: candle.low,
              close: candle.close,
              change: candle.close - prevClose,
              changePercent: ((candle.close - prevClose) / prevClose) * 100,
            });
          }
        }
      });

      // Price lines
      priceLines.forEach((line) => {
        candleSeries.createPriceLine({
          price: line.price,
          color: line.color,
          lineWidth: line.width,
          lineStyle: getLineStyle(line.style),
          axisLabelVisible: true,
        });
      });

      // Save visible range
      mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range) {
          visibleRangeRef.current = range;
        }
      });

      // Overlays
      const overlayColors: Record<string, string> = {
        ema9: '#f59e0b',
        ema21: '#2962ff',
        ema50: '#9c27b0',
        sma20: '#e91e63',
      };

      activeOverlays.forEach((overlay) => {
        if (overlay === 'bb') {
          ['bb_upper', 'bb_middle', 'bb_lower'].forEach((bb, i) => {
            const series = mainChart.addSeries(LightweightCharts.LineSeries, {
              color: i === 1 ? 'rgba(99,102,241,0.5)' : 'rgba(99,102,241,0.3)',
              lineWidth: 1,
              lineStyle:
                i !== 1 ? LightweightCharts.LineStyle.Dotted : undefined,
            });
            const bbData = data.overlays[
              bb as keyof typeof data.overlays
            ] as any[];
            series.setData(
              bbData.map((d) => ({
                time: convertTime(d.time) as any,
                value: d.value,
              }))
            );
          });
        } else if (data.overlays[overlay as keyof typeof data.overlays]) {
          const series = mainChart.addSeries(LightweightCharts.LineSeries, {
            color: overlayColors[overlay] || '#888',
            lineWidth: 2,
          });
          const overlayData = data.overlays[
            overlay as keyof typeof data.overlays
          ] as any[];
          series.setData(
            overlayData.map((d) => ({
              time: convertTime(d.time) as any,
              value: d.value,
            }))
          );
        }
      });

      // Volume - anchored to very bottom
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

      // Set zoom
      const totalCandles = data.candles.length;
      const visibleCandles = VISIBLE_CANDLES[timeframe] || 60;
      if (visibleRangeRef.current) {
        mainChart.timeScale().setVisibleLogicalRange(visibleRangeRef.current);
      } else {
        mainChart.timeScale().setVisibleLogicalRange({
          from: Math.max(0, totalCandles - visibleCandles),
          to: totalCandles,
        });
      }

      chartsRef.current.push(mainChart);

      // RSI
      if (activePanels.includes('rsi') && rsiChartRef.current) {
        const rsiChart = LightweightCharts.createChart(rsiChartRef.current, {
          ...chartOptions,
          width: rsiChartRef.current.clientWidth,
          height: 100,
        });

        const rsiSeries = rsiChart.addSeries(LightweightCharts.LineSeries, {
          color: '#8b5cf6',
          lineWidth: 2,
        });
        const rsiData = data.panels.rsi.data.map((d) => ({
          time: convertTime(d.time) as any,
          value: d.value,
        }));
        rsiSeries.setData(rsiData);

        // Reference lines
        [70, 30].forEach((level, i) => {
          const lineSeries = rsiChart.addSeries(LightweightCharts.LineSeries, {
            color: i === 0 ? 'rgba(239,68,68,0.3)' : 'rgba(34,197,94,0.3)',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          lineSeries.setData(
            rsiData.map((d) => ({ time: d.time, value: level }))
          );
        });

        rsiChart.timeScale().applyOptions({ visible: false });
        mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
          if (range) {
            rsiChart.timeScale().setVisibleLogicalRange(range);
          }
        });
        chartsRef.current.push(rsiChart);
      }

      // MACD
      if (activePanels.includes('macd') && macdChartRef.current) {
        const macdChart = LightweightCharts.createChart(macdChartRef.current, {
          ...chartOptions,
          width: macdChartRef.current.clientWidth,
          height: 100,
        });

        const macdLine = macdChart.addSeries(LightweightCharts.LineSeries, {
          color: '#2962ff',
          lineWidth: 2,
          priceLineVisible: false,
        });
        const signalLine = macdChart.addSeries(LightweightCharts.LineSeries, {
          color: '#ff6d00',
          lineWidth: 1,
          priceLineVisible: false,
        });
        const histogram = macdChart.addSeries(
          LightweightCharts.HistogramSeries,
          { priceLineVisible: false }
        );

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

        macdChart.timeScale().applyOptions({ visible: false });
        mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
          if (range) {
            macdChart.timeScale().setVisibleLogicalRange(range);
          }
        });
        chartsRef.current.push(macdChart);
      }

      // Resize handler
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
      return () => window.removeEventListener('resize', handleResize);
    };

    initCharts();
    return () => {
      chartsRef.current.forEach((c) => c?.remove());
      chartsRef.current = [];
    };
  }, [data, activeOverlays, activePanels, timeframe, priceLines, isDarkMode]);

  // UI theme classes
  const uiTheme = {
    bg: isDarkMode ? 'bg-[#131722]' : 'bg-white',
    bgSecondary: isDarkMode ? 'bg-[#1e222d]' : 'bg-gray-100',
    border: isDarkMode ? 'border-[#2a2e39]' : 'border-gray-200',
    text: isDarkMode ? 'text-white' : 'text-gray-900',
    textMuted: isDarkMode ? 'text-gray-400' : 'text-gray-500',
    textSecondary: isDarkMode ? 'text-gray-300' : 'text-gray-700',
    hover: isDarkMode ? 'hover:bg-[#2a2e39]' : 'hover:bg-gray-200',
  };

  if (isLoading) {
    return (
      <div className={`flex-1 flex items-center justify-center ${uiTheme.bg}`}>
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className={`flex-1 flex flex-col ${uiTheme.bg}`}>
      {/* Toolbar */}
      <div
        className={`flex items-center gap-4 px-4 py-2 border-b ${uiTheme.border}`}
      >
        {/* Symbol Info */}
        <div className="flex items-center gap-3">
          <span className={`${uiTheme.text} font-semibold text-lg`}>
            {symbol}
          </span>
          <span className={`${uiTheme.textMuted} text-sm`}>• NSE</span>
          {/* Market Status Indicator */}
          {marketOpen ? (
            <span className="flex items-center gap-1.5 text-xs">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-green-500">Live</span>
              {lastUpdateTime && (
                <span className={uiTheme.textMuted}>• {lastUpdateTime}</span>
              )}
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs">
              <span className="w-2 h-2 bg-gray-500 rounded-full" />
              <span className={uiTheme.textMuted}>Closed</span>
            </span>
          )}
        </div>

        {/* OHLC Display */}
        {ohlcData && (
          <div className="flex items-center gap-4 text-sm">
            <span className={uiTheme.textMuted}>
              O
              <span className={`${uiTheme.text} ml-1`}>
                {ohlcData.open.toFixed(2)}
              </span>
            </span>
            <span className={uiTheme.textMuted}>
              H
              <span className="text-green-500 ml-1">
                {ohlcData.high.toFixed(2)}
              </span>
            </span>
            <span className={uiTheme.textMuted}>
              L
              <span className="text-red-500 ml-1">
                {ohlcData.low.toFixed(2)}
              </span>
            </span>
            <span className={uiTheme.textMuted}>
              C
              <span className={`${uiTheme.text} ml-1`}>
                {ohlcData.close.toFixed(2)}
              </span>
            </span>
            <span
              className={`${ohlcData.change >= 0 ? 'text-green-500' : 'text-red-500'}`}
            >
              {ohlcData.change >= 0 ? '+' : ''}
              {ohlcData.change.toFixed(2)} ({ohlcData.changePercent.toFixed(2)}
              %)
            </span>
          </div>
        )}

        <div className="flex-1" />

        {/* Timeframe */}
        <div
          className={`flex items-center ${uiTheme.bgSecondary} rounded p-0.5`}
        >
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.value}
              onClick={() => handleTimeframeChange(tf.value)}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                timeframe === tf.value
                  ? 'bg-blue-600 text-white'
                  : `${uiTheme.textMuted} hover:text-white`
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>

        {/* Indicators */}
        <div className="relative" ref={indicatorMenuRef}>
          <button
            onClick={() => setShowIndicatorMenu(!showIndicatorMenu)}
            className={`flex items-center gap-2 px-3 py-1.5 ${uiTheme.bgSecondary} rounded text-sm ${uiTheme.textSecondary} hover:text-white`}
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
          </button>

          {showIndicatorMenu && (
            <div
              className={`absolute right-0 top-full mt-1 w-56 ${uiTheme.bgSecondary} border ${uiTheme.border} rounded-lg shadow-xl z-50 p-2`}
            >
              <div
                className={`text-xs ${uiTheme.textMuted} uppercase mb-2 px-2`}
              >
                Overlays
              </div>
              {INDICATORS.overlays.map((ind) => (
                <label
                  key={ind.id}
                  className={`flex items-center gap-2 px-2 py-1.5 ${uiTheme.hover} rounded cursor-pointer`}
                >
                  <input
                    type="checkbox"
                    checked={activeOverlays.includes(ind.id)}
                    onChange={() =>
                      setActiveOverlays((prev) =>
                        prev.includes(ind.id)
                          ? prev.filter((o) => o !== ind.id)
                          : [...prev, ind.id]
                      )
                    }
                    className="w-3 h-3 rounded"
                  />
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: ind.color }}
                  />
                  <span className={`text-sm ${uiTheme.textSecondary}`}>
                    {ind.label}
                  </span>
                </label>
              ))}
              <div
                className={`text-xs ${uiTheme.textMuted} uppercase mt-3 mb-2 px-2`}
              >
                Panels
              </div>
              {INDICATORS.panels.map((ind) => (
                <label
                  key={ind.id}
                  className={`flex items-center gap-2 px-2 py-1.5 ${uiTheme.hover} rounded cursor-pointer`}
                >
                  <input
                    type="checkbox"
                    checked={activePanels.includes(ind.id)}
                    onChange={() =>
                      setActivePanels((prev) =>
                        prev.includes(ind.id)
                          ? prev.filter((p) => p !== ind.id)
                          : [...prev, ind.id]
                      )
                    }
                    className="w-3 h-3 rounded"
                  />
                  <span className={`text-sm ${uiTheme.textSecondary}`}>
                    {ind.label}
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Clear lines */}
        {priceLines.length > 0 && (
          <button
            onClick={() => setPriceLines([])}
            className={`px-3 py-1.5 text-sm ${uiTheme.textMuted} hover:text-white ${uiTheme.bgSecondary} rounded`}
          >
            Clear Lines
          </button>
        )}
      </div>

      {/* Chart Area */}
      <div className="flex-1 flex">
        {/* Left Toolbar */}
        <div
          className={`w-10 ${uiTheme.bg} border-r ${uiTheme.border} flex flex-col items-center py-2 gap-1`}
        >
          <button
            onClick={() =>
              setActiveTool(activeTool === 'crosshair' ? null : 'crosshair')
            }
            className={`w-8 h-8 rounded flex items-center justify-center ${activeTool === 'crosshair' ? 'bg-blue-600 text-white' : `${uiTheme.textMuted} hover:text-white ${uiTheme.hover}`}`}
            title="Crosshair"
          >
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m-8-8h16"
              />
            </svg>
          </button>
          <button
            className={`w-8 h-8 rounded flex items-center justify-center ${uiTheme.textMuted} hover:text-white ${uiTheme.hover}`}
            title="Trend Line"
          >
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 17l10-10"
              />
            </svg>
          </button>
          <button
            className={`w-8 h-8 rounded flex items-center justify-center ${uiTheme.textMuted} hover:text-white ${uiTheme.hover}`}
            title="Horizontal Line"
          >
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 12h16"
              />
            </svg>
          </button>
          <button
            className={`w-8 h-8 rounded flex items-center justify-center ${uiTheme.textMuted} hover:text-white ${uiTheme.hover}`}
            title="Rectangle"
          >
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <rect x="4" y="6" width="16" height="12" strokeWidth={2} />
            </svg>
          </button>
          <button
            className={`w-8 h-8 rounded flex items-center justify-center ${uiTheme.textMuted} hover:text-white ${uiTheme.hover}`}
            title="Text"
          >
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m-4-12h8"
              />
            </svg>
          </button>
          <div
            className={`w-6 h-px ${isDarkMode ? 'bg-[#2a2e39]' : 'bg-gray-300'} my-2`}
          />
          <button
            className={`w-8 h-8 rounded flex items-center justify-center ${uiTheme.textMuted} hover:text-white ${uiTheme.hover}`}
            title="Zoom In"
          >
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"
              />
            </svg>
          </button>
          <button
            className={`w-8 h-8 rounded flex items-center justify-center ${uiTheme.textMuted} hover:text-white ${uiTheme.hover}`}
            title="Zoom Out"
          >
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM7 10h6"
              />
            </svg>
          </button>
        </div>

        {/* Charts */}
        <div className="flex-1 flex flex-col">
          <div
            ref={mainChartRef}
            className="flex-1"
            style={{
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
          {activePanels.includes('rsi') && (
            <div className={`border-t ${uiTheme.border}`}>
              <div className={`px-2 py-0.5 text-[10px] ${uiTheme.textMuted}`}>
                RSI (14)
              </div>
              <div ref={rsiChartRef} />
            </div>
          )}
          {activePanels.includes('macd') && (
            <div className={`border-t ${uiTheme.border}`}>
              <div className={`px-2 py-0.5 text-[10px] ${uiTheme.textMuted}`}>
                MACD (12,26,9)
              </div>
              <div ref={macdChartRef} />
            </div>
          )}
        </div>
      </div>

      {/* Price Tooltip */}
      {showPriceTooltip && hoveredPrice && !editingLine && (
        <div
          className="fixed z-50 pointer-events-none"
          style={{ left: tooltipPosition.x - 80, top: tooltipPosition.y - 12 }}
        >
          <div className="bg-blue-600 text-white px-2 py-1 rounded text-sm flex items-center gap-1">
            <svg
              className="w-3 h-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            {hoveredPrice.toFixed(2)}
          </div>
        </div>
      )}

      {/* Line Editor */}
      {editingLine && (
        <div
          ref={lineEditorRef}
          className={`fixed z-50 ${uiTheme.bgSecondary} border ${uiTheme.border} rounded shadow-xl flex items-center gap-1 p-1`}
          style={{
            left: Math.max(
              10,
              Math.min(lineEditorPosition.x - 150, window.innerWidth - 350)
            ),
            top: Math.max(10, lineEditorPosition.y),
          }}
        >
          {/* Style */}
          {(['solid', 'dashed', 'dotted'] as LineStyle[]).map((style) => (
            <button
              key={style}
              onClick={() => updatePriceLine(editingLine.id, { style })}
              className={`w-7 h-7 rounded flex items-center justify-center ${editingLine.style === style ? 'bg-blue-600 text-white' : `${uiTheme.textMuted} ${uiTheme.hover}`}`}
            >
              <svg width="16" height="2">
                <line
                  x1="0"
                  y1="1"
                  x2="16"
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
          <div
            className={`w-px h-5 ${isDarkMode ? 'bg-[#2a2e39]' : 'bg-gray-300'} mx-0.5`}
          />
          {/* Width */}
          {[1, 2, 3, 4].map((w) => (
            <button
              key={w}
              onClick={() => updatePriceLine(editingLine.id, { width: w })}
              className={`w-7 h-7 rounded text-xs ${editingLine.width === w ? 'bg-blue-600 text-white' : `${uiTheme.textMuted} ${uiTheme.hover}`}`}
            >
              {w}
            </button>
          ))}
          <div
            className={`w-px h-5 ${isDarkMode ? 'bg-[#2a2e39]' : 'bg-gray-300'} mx-0.5`}
          />
          {/* Color */}
          <div className="relative group">
            <button
              className={`w-7 h-7 rounded flex items-center justify-center ${uiTheme.hover}`}
            >
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: editingLine.color }}
              />
            </button>
            <div
              className={`absolute left-0 top-full hidden group-hover:grid grid-cols-5 gap-1 p-2 ${uiTheme.bgSecondary} border ${uiTheme.border} rounded mt-1 z-50`}
            >
              {LINE_COLORS.map((c) => (
                <button
                  key={c}
                  onClick={() => updatePriceLine(editingLine.id, { color: c })}
                  className={`w-5 h-5 rounded border border-transparent ${isDarkMode ? 'hover:border-white' : 'hover:border-gray-800'}`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>
          <div
            className={`w-px h-5 ${isDarkMode ? 'bg-[#2a2e39]' : 'bg-gray-300'} mx-0.5`}
          />
          <span className={`text-xs ${uiTheme.textMuted} px-1`}>
            {editingLine.price.toFixed(2)}
          </span>
          <button
            onClick={() => removePriceLine(editingLine.id)}
            className="w-7 h-7 rounded text-gray-400 hover:text-red-400 hover:bg-red-400/10"
          >
            <svg
              className="w-4 h-4 mx-auto"
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
          <button
            onClick={() => setEditingLine(null)}
            className="w-7 h-7 rounded text-gray-400 hover:text-white hover:bg-[#2a2e39]"
          >
            <svg
              className="w-4 h-4 mx-auto"
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
      )}
    </div>
  );
}
