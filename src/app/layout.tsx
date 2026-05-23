import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: 'StockPro — AI-Assisted Trading for Indian Markets',
  description:
    'Production-grade, human-in-the-loop AI-assisted trading system for Indian markets. AI suggests, human executes.',
  keywords: ['trading', 'stocks', 'AI', 'Indian markets', 'NSE', 'BSE'],
};

export const viewport: Viewport = {
  themeColor: '#050507',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased relative`}
      >
        {/* Sparkle dot layer — fixed background ornamentation */}
        <div
          aria-hidden
          className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
        >
          <div className="absolute top-[8%] left-[12%] w-1 h-1 rounded-full bg-spark-emerald/70 animate-sparkle" />
          <div
            className="absolute top-[22%] right-[18%] w-1 h-1 rounded-full bg-spark-violet/70 animate-sparkle"
            style={{ animationDelay: '0.7s' }}
          />
          <div
            className="absolute top-[55%] left-[8%] w-1.5 h-1.5 rounded-full bg-spark-cyan/60 animate-sparkle"
            style={{ animationDelay: '1.4s' }}
          />
          <div
            className="absolute bottom-[18%] right-[22%] w-1 h-1 rounded-full bg-spark-rose/70 animate-sparkle"
            style={{ animationDelay: '2.1s' }}
          />
          <div
            className="absolute top-[40%] right-[40%] w-0.5 h-0.5 rounded-full bg-spark-amber/80 animate-sparkle"
            style={{ animationDelay: '1.0s' }}
          />
          <div
            className="absolute bottom-[35%] left-[35%] w-1 h-1 rounded-full bg-spark-violet/60 animate-sparkle"
            style={{ animationDelay: '2.8s' }}
          />
        </div>

        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
