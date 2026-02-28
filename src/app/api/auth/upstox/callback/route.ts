import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get('code');
  const error = searchParams.get('error');

  if (error) {
    return NextResponse.redirect(
      new URL(`/settings?error=${encodeURIComponent(error)}`, request.url)
    );
  }

  if (!code) {
    return NextResponse.redirect(
      new URL('/settings?error=No authorization code received', request.url)
    );
  }

  try {
    // Forward the code to backend for token exchange
    const backendUrl =
      process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const response = await fetch(
      `${backendUrl}/auth/upstox/callback?code=${code}`
    );

    if (response.ok) {
      return NextResponse.redirect(
        new URL('/settings?upstox=connected', request.url)
      );
    } else {
      const errorData = await response.json();
      return NextResponse.redirect(
        new URL(
          `/settings?error=${encodeURIComponent(errorData.detail || 'Token exchange failed')}`,
          request.url
        )
      );
    }
  } catch (err) {
    return NextResponse.redirect(
      new URL('/settings?error=Failed to connect to backend', request.url)
    );
  }
}
