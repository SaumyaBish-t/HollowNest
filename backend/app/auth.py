"""Clerk JWT verification for FastAPI.

The frontend (Clerk) attaches an `Authorization: Bearer <session-jwt>` header
to every request. This module verifies that JWT against Clerk's JWKS endpoint
and exposes a `require_user` dependency that returns the Clerk user id.

Configuration:
- CLERK_JWT_ISSUER: e.g. https://your-app.clerk.accounts.dev
  JWKS is fetched from {issuer}/.well-known/jwks.json.
- CLERK_DISABLE_AUTH: set to true to bypass verification entirely. Local dev
  only — never enable in production.
"""

from __future__ import annotations

import jwt
from jwt import PyJWKClient, InvalidTokenError
from fastapi import Header, HTTPException, status
from app.config import settings


_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        issuer = settings.clerk_jwt_issuer.rstrip("/")
        if not issuer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Backend is missing CLERK_JWT_ISSUER. Set it to your "
                    "Clerk Frontend API URL (e.g. "
                    "https://your-app.clerk.accounts.dev) and restart."
                ),
            )
        _jwks_client = PyJWKClient(f"{issuer}/.well-known/jwks.json")
    return _jwks_client


def verify_clerk_token(token: str) -> dict:
    """Validate a Clerk session JWT and return its claims."""
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token).key
        # Clerk session tokens are signed with RS256. We verify signature +
        # exp + nbf. The audience claim isn't fixed across Clerk versions, so
        # we skip aud verification.
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={"verify_aud": False, "require": ["exp", "iat", "sub"]},
            leeway=10,
        )
        return claims
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid session token: {e}",
        )


async def require_user(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency. Returns the Clerk user id (`sub` claim).

    Raises 401 if the Authorization header is missing or the token is invalid.
    """
    if settings.clerk_disable_auth:
        # Local-dev escape hatch. Returns a stable pseudo-id so every
        # downstream query that filters by user_id keeps working.
        return "local-dev-user"

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <token> header.",
        )

    token = authorization.split(" ", 1)[1].strip()
    claims = verify_clerk_token(token)
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has no subject (sub) claim.",
        )
    return user_id
