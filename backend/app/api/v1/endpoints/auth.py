"""
Authentication endpoints for broker API connections.

Handles OAuth2 callbacks and token management.
"""

import logging
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.services.data_ingestion.upstox_adapter import get_upstox_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/upstox/login")
async def upstox_login():
    """
    Initiate Upstox OAuth2 login flow.

    Redirects user to Upstox login page.
    After login, user is redirected to /api/v1/auth/upstox/callback.
    """
    if not settings.upstox_api_key:
        raise HTTPException(status_code=400, detail="Upstox API key not configured")

    client = get_upstox_client()
    auth_url = client.get_auth_url()

    return RedirectResponse(url=auth_url)


@router.get("/upstox/callback")
async def upstox_callback(
    code: str = Query(None, description="Authorization code from Upstox"),
    error: str = Query(None, description="Error from Upstox"),
):
    """
    Upstox OAuth2 callback endpoint.

    Receives authorization code and exchanges it for access token.
    """
    if error:
        logger.error(f"Upstox OAuth error: {error}")
        raise HTTPException(status_code=400, detail=f"Upstox login failed: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")

    client = get_upstox_client()
    success = await client.exchange_code_for_token(code)

    if success:
        # Redirect to frontend with success
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?upstox=connected",
            status_code=302
        )
    else:
        raise HTTPException(status_code=400, detail="Failed to exchange token")


@router.get("/upstox/status")
async def upstox_status():
    """Check Upstox connection status."""
    client = get_upstox_client()
    return {
        "connected": client.is_authenticated,
        "login_url": client.get_auth_url() if not client.is_authenticated else None,
    }


@router.get("/angelone/status")
async def angelone_status():
    """Check Angel One connection status."""
    from app.services.data_ingestion.angelone_adapter import get_angel_client

    client = get_angel_client()
    connected = await client.connect()

    return {
        "connected": connected,
        "requires_totp": not connected and settings.angel_one_client_id is not None,
    }


@router.get("/status")
async def broker_status():
    """Get status of all broker connections."""
    from app.services.data_ingestion.angelone_adapter import get_angel_client

    # Check Angel One
    angel_client = get_angel_client()
    angel_connected = await angel_client.connect()

    # Check Upstox
    upstox_client = get_upstox_client()
    upstox_connected = upstox_client.is_authenticated

    return {
        "angel_one": {
            "configured": bool(settings.angel_one_client_id),
            "connected": angel_connected,
            "ws_enabled": settings.angel_one_ws_enabled,
        },
        "upstox": {
            "configured": bool(settings.upstox_api_key),
            "connected": upstox_connected,
            "ws_enabled": settings.upstox_ws_enabled,
            "login_url": upstox_client.get_auth_url() if not upstox_connected else None,
        },
    }
