from __future__ import annotations

import hmac
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from tradeo.core.config import Settings, get_settings

security = HTTPBasic(auto_error=False)


def require_admin(
    credentials: HTTPBasicCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> str:
    """Simple local/VPN HTTP Basic auth.

    For a public deployment, replace this with OIDC or mTLS. The intended deployment is
    private local/VPN, so this is intentionally small and auditable.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    username_ok = hmac.compare_digest(credentials.username, settings.admin_username)
    password_ok = hmac.compare_digest(credentials.password, settings.admin_password)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
