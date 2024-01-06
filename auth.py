import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from models import User

load_dotenv()

JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM')

def create_jwt(username: str) -> dict[str, str]:
    expires = datetime.now() + timedelta(days=1)
    payload = {
        "username": username,
        "expires": expires.timestamp(),
    }
    token = jwt.encode(payload,JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {
        "access_token": token
    }

def decode_jwt(token:str) -> dict[str, str] | None:
    try:
        decoded_token = jwt.decode(token,JWT_SECRET, algorithms=JWT_ALGORITHM)
        return decoded_token if decoded_token["expires"] > datetime.now().timestamp() else None
    except:
        return None

async def verify_jwt(token: str)-> bool | User:
    payload = decode_jwt(token)
    if not payload:
        return False
    user = await User.filter(username=payload["username"]).first()
    return user if user else False

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        credentials = await super().__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(403, detail="Invalid authentication scheme.")
            user = await verify_jwt(credentials.credentials)
            if not user:
                raise HTTPException(403, detail="Invalid token or expired token.")
            return user
        raise HTTPException(403, detail="Invalid authentication code.")
