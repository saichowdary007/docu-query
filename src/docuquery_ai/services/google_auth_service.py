import os
from typing import Any, Dict, Optional

import requests

# Google OAuth2 configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:3000/api/auth/google/callback"
)

# Google API endpoints
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleAuthException(Exception):
    """Exception raised for Google Auth errors."""

    pass


async def verify_google_token(id_token: str) -> Dict[str, Any]:
    """
    Verify a Google ID token and return user information.
    """
    try:
        # Option 1: Use Google's tokeninfo endpoint (easiest)
        response = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
        )
        if response.status_code != 200:
            raise GoogleAuthException("Invalid Google token")

        token_info = response.json()

        # Verify that the token was issued for our client_id
        if GOOGLE_CLIENT_ID and token_info.get("aud") != GOOGLE_CLIENT_ID:
            raise GoogleAuthException("Token not issued for this application")

        return token_info
    except Exception as e:
        raise GoogleAuthException(f"Google token verification failed: {str(e)}")


async def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """
    Exchange an authorization code for Google tokens.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise GoogleAuthException("Google OAuth credentials not configured")

    try:
        response = requests.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if response.status_code != 200:
            raise GoogleAuthException(
                f"Failed to exchange code for token: {response.text}"
            )

        return response.json()
    except Exception as e:
        raise GoogleAuthException(f"Failed to exchange code: {str(e)}")


async def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """
    Fetch Google user information using an access token.
    """
    try:
        response = requests.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            raise GoogleAuthException("Failed to fetch user info")

        return response.json()
    except Exception as e:
        raise GoogleAuthException(f"Failed to get user info: {str(e)}")
