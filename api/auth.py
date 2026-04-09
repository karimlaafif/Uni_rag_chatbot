"""
api/auth.py — JWT Authentication & Role-Based Access Control
=============================================================
Provides:
  - Token generation  : create_access_token()
  - Token validation  : get_current_user() (FastAPI dependency)
  - Role enforcement  : require_role() (decorator factory)

Roles hierarchy (lowest → highest):
  public < student < staff < admin

Usage in routes:
    @app.post("/admin/only")
    async def admin_endpoint(user = Depends(require_role("admin"))):
        ...
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

ALGORITHM = "HS256"

ROLE_HIERARCHY: Dict[str, int] = {
    "public":  0,
    "student": 1,
    "staff":   2,
    "admin":   3,
}

# ── Security scheme ──────────────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)


# ── Token utilities ──────────────────────────────────────────────────────────

def create_access_token(
    username: str,
    role: str,
    expires_hours: int = 24,
) -> str:
    """
    Create a signed JWT token embedding username and role.

    Parameters
    ----------
    username      : User identifier (email or student ID)
    role          : One of public | student | staff | admin
    expires_hours : Token lifetime in hours (default: 24)

    Returns
    -------
    Signed JWT string
    """
    if role not in ROLE_HIERARCHY:
        raise ValueError(f"Invalid role '{role}'. Must be one of {list(ROLE_HIERARCHY)}")

    payload = {
        "sub":  username,
        "role": role,
        "iat":  datetime.utcnow(),
        "exp":  datetime.utcnow() + timedelta(hours=expires_hours),
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict:
    """
    Decode and validate a JWT token.
    Raises HTTPException on invalid / expired tokens.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependencies ─────────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Dict:
    """
    FastAPI dependency that extracts and validates the Bearer token.
    Returns the decoded JWT payload dict: {"sub": ..., "role": ..., ...}

    If no token is provided, returns a guest/public user dict so that
    unauthenticated access to public endpoints still works.
    """
    if credentials is None:
        # No Authorization header → treat as public/anonymous
        return {"sub": "anonymous", "role": "public"}

    return decode_token(credentials.credentials)


def require_role(minimum_role: str):
    """
    Dependency factory — enforces a minimum role level.

    Usage:
        @app.delete("/admin/nuke")
        async def nuke(user = Depends(require_role("admin"))):
            ...

    Parameters
    ----------
    minimum_role : Minimum role required (public | student | staff | admin)
    """
    if minimum_role not in ROLE_HIERARCHY:
        raise ValueError(f"Unknown role '{minimum_role}'")

    def _check(user: Dict = Depends(get_current_user)) -> Dict:
        user_level     = ROLE_HIERARCHY.get(user.get("role", "public"), 0)
        required_level = ROLE_HIERARCHY[minimum_role]

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. This endpoint requires role '{minimum_role}' "
                    f"or higher. Your role: '{user.get('role', 'public')}'."
                ),
            )
        return user

    return _check


# ── Auth router (token endpoint) ─────────────────────────────────────────────

from fastapi import APIRouter
from pydantic import BaseModel

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenRequest(BaseModel):
    username: str
    password: str
    role: str = "student"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_hours: int


@auth_router.post("/token", response_model=TokenResponse, summary="Get a JWT access token")
def get_token(body: TokenRequest) -> TokenResponse:
    """
    Demo token endpoint — in production, replace the password check with
    your university LDAP / SSO / database lookup.

    For development, any non-empty password is accepted.
    """
    if not body.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password required.",
        )

    # ⚠️  DEMO ONLY — replace with real credential validation
    if body.role not in ROLE_HIERARCHY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Choose from: {list(ROLE_HIERARCHY.keys())}",
        )

    expire_hours = getattr(settings, "JWT_EXPIRE_HOURS", 24)
    token = create_access_token(
        username=body.username,
        role=body.role,
        expires_hours=expire_hours,
    )

    logger.info(f"Token issued for user '{body.username}' (role={body.role})")

    return TokenResponse(
        access_token=token,
        role=body.role,
        expires_hours=expire_hours,
    )
