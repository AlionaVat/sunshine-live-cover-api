import secrets
import os        
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

DEMO_USERNAME = os.getenv("DEMO_USERNAME", "demo_user")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "change_me")


def check_demo_access(
    credentials: HTTPBasicCredentials = Depends(security)
):
    valid_username = secrets.compare_digest(
        credentials.username,
        DEMO_USERNAME
    )

    valid_password = secrets.compare_digest(
        credentials.password,
        DEMO_PASSWORD
    )

    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
