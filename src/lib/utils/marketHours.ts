/**
 * Market Hours Utility for Indian Markets (NSE/BSE)
 *
 * Market Hours: 9:15 AM - 3:30 PM IST
 * Trading Days: Monday - Friday (excluding holidays)
 */

// NSE Holidays 2024-2026 (dates in IST)
const NSE_HOLIDAYS = new Set([
  // 2024
  '2024-01-26', // Republic Day
  '2024-03-08', // Maha Shivaratri
  '2024-03-25', // Holi
  '2024-03-29', // Good Friday
  '2024-04-11', // Id-Ul-Fitr
  '2024-04-14', // Dr. Ambedkar Jayanti
  '2024-04-17', // Ram Navami
  '2024-04-21', // Mahavir Jayanti
  '2024-05-01', // Maharashtra Day
  '2024-05-23', // Buddha Purnima
  '2024-06-17', // Eid ul-Adha
  '2024-07-17', // Muharram
  '2024-08-15', // Independence Day
  '2024-10-02', // Gandhi Jayanti
  '2024-11-01', // Diwali
  '2024-11-15', // Guru Nanak Jayanti
  '2024-12-25', // Christmas
  // 2025
  '2025-01-26', // Republic Day
  '2025-02-26', // Maha Shivaratri
  '2025-03-14', // Holi
  '2025-03-31', // Id-Ul-Fitr
  '2025-04-10', // Mahavir Jayanti
  '2025-04-14', // Dr. Ambedkar Jayanti
  '2025-04-18', // Good Friday
  '2025-05-01', // Maharashtra Day
  '2025-06-07', // Eid ul-Adha
  '2025-08-15', // Independence Day
  '2025-08-27', // Janmashtami
  '2025-10-02', // Gandhi Jayanti
  '2025-10-21', // Diwali
  '2025-10-22', // Diwali Balipratipada
  '2025-11-05', // Guru Nanak Jayanti
  '2025-12-25', // Christmas
  // 2026
  '2026-01-26', // Republic Day
  '2026-08-15', // Independence Day
  '2026-10-02', // Gandhi Jayanti
  '2026-12-25', // Christmas
]);

// Market timing constants (IST)
const MARKET_OPEN_HOUR = 9;
const MARKET_OPEN_MINUTE = 15;
const MARKET_CLOSE_HOUR = 15;
const MARKET_CLOSE_MINUTE = 30;

/**
 * Get current time in IST timezone
 */
export function getISTNow(): Date {
  // Create a date in IST
  const now = new Date();
  // IST is UTC+5:30
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  const ist = new Date(utc + 5.5 * 60 * 60 * 1000);
  return ist;
}

/**
 * Format date to YYYY-MM-DD string
 */
function formatDateString(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Check if a date is a weekend (Saturday or Sunday)
 */
function isWeekend(date: Date): boolean {
  const day = date.getDay();
  return day === 0 || day === 6; // Sunday = 0, Saturday = 6
}

/**
 * Check if a date is an NSE holiday
 */
function isHoliday(date: Date): boolean {
  const dateStr = formatDateString(date);
  return NSE_HOLIDAYS.has(dateStr);
}

/**
 * Check if a date is a trading day
 */
export function isTradingDay(date: Date = getISTNow()): boolean {
  return !isWeekend(date) && !isHoliday(date);
}

/**
 * Check if the Indian market is currently open
 *
 * Market Hours: 9:15 AM - 3:30 PM IST (Monday-Friday, excluding holidays)
 */
export function isMarketOpen(): boolean {
  const now = getISTNow();

  // Check if it's a trading day
  if (!isTradingDay(now)) {
    return false;
  }

  const hours = now.getHours();
  const minutes = now.getMinutes();
  const currentMinutes = hours * 60 + minutes;

  const openMinutes = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE; // 9:15 = 555
  const closeMinutes = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE; // 15:30 = 930

  return currentMinutes >= openMinutes && currentMinutes < closeMinutes;
}

/**
 * Get the next market open time
 */
export function getNextMarketOpen(): Date {
  const now = getISTNow();
  const nextOpen = new Date(now);

  // Set to market open time
  nextOpen.setHours(MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE, 0, 0);

  // If market is already open today or past close, move to next day
  if (now >= nextOpen || !isTradingDay(now)) {
    nextOpen.setDate(nextOpen.getDate() + 1);
  }

  // Find next trading day
  while (!isTradingDay(nextOpen)) {
    nextOpen.setDate(nextOpen.getDate() + 1);
  }

  return nextOpen;
}

/**
 * Get market status details
 */
export function getMarketStatus(): {
  isOpen: boolean;
  isTradingDay: boolean;
  currentTimeIST: string;
  nextOpen?: string;
  session: 'PRE_MARKET' | 'OPEN' | 'CLOSED';
} {
  const now = getISTNow();
  const isOpen = isMarketOpen();
  const tradingDay = isTradingDay(now);

  const hours = now.getHours();
  const minutes = now.getMinutes();
  const currentMinutes = hours * 60 + minutes;
  const openMinutes = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE;

  let session: 'PRE_MARKET' | 'OPEN' | 'CLOSED' = 'CLOSED';
  if (isOpen) {
    session = 'OPEN';
  } else if (
    tradingDay &&
    currentMinutes < openMinutes &&
    currentMinutes >= openMinutes - 15
  ) {
    session = 'PRE_MARKET';
  }

  const result: ReturnType<typeof getMarketStatus> = {
    isOpen,
    isTradingDay: tradingDay,
    currentTimeIST: now.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }),
    session,
  };

  if (!isOpen) {
    result.nextOpen = getNextMarketOpen().toISOString();
  }

  return result;
}

/**
 * Get time until market open/close in milliseconds
 */
export function getTimeUntilMarketChange(): {
  isOpen: boolean;
  timeUntilChange: number;
  changeEvent: 'OPEN' | 'CLOSE';
} {
  const now = getISTNow();
  const isOpen = isMarketOpen();

  if (isOpen) {
    // Time until close
    const closeTime = new Date(now);
    closeTime.setHours(MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE, 0, 0);
    return {
      isOpen: true,
      timeUntilChange: closeTime.getTime() - now.getTime(),
      changeEvent: 'CLOSE',
    };
  } else {
    // Time until next open
    const nextOpen = getNextMarketOpen();
    return {
      isOpen: false,
      timeUntilChange: nextOpen.getTime() - now.getTime(),
      changeEvent: 'OPEN',
    };
  }
}
