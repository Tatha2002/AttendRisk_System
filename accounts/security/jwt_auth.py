import os
import jwt

from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from ..models import User
load_dotenv()

# ==========================================================
# ACCESS TOKEN: is for a short period of time.
# ==========================================================

def create_access_token(user_id, role):       
    # user = User.objects.get(id=user_id)
    payload = {
        "user_id": user_id,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=1)       # Create JWT Access Token Valid for 30 minutes
    }

    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise Exception("JWT_SECRET_KEY not found in .env")

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


def decode_access_token(token):
    try:
        secret_key = os.getenv("JWT_SECRET_KEY")
        payload = jwt.decode(token,secret_key,algorithms=["HS256"])
        return payload["user_id"]

    except jwt.ExpiredSignatureError as e:
        raise AuthenticationFailed("Access token has expired") from e

    except jwt.InvalidTokenError as e:
        raise AuthenticationFailed("Invalid access token") from e

# ==========================================================
# REFRESH TOKEN: is for a long period of time. 
# It is used to generate new access tokens without requiring the user to log in again.
# ==========================================================

def create_refresh_token(user_id, role):
    payload = {
        "user_id": user_id,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=7)                   # Create JWT Refresh Token Valid for 7 days
    }

    secret_key = os.getenv("JWT_REFRESH_SECRET_KEY")

    if not secret_key:
        raise Exception("JWT_REFRESH_SECRET_KEY not found in .env")

    token = jwt.encode(payload,secret_key,algorithm="HS256")
    return token


def decode_refresh_token(token):
    try:
        secret_key = os.getenv("JWT_REFRESH_SECRET_KEY")
        payload = jwt.decode(token,secret_key,algorithms=["HS256"])

        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Refresh token has expired")

    except jwt.InvalidTokenError:
        raise AuthenticationFailed("Invalid refresh token")


# ==========================================================
# AUTHENTICATE USER: Use for the purpose of DRF and not used in case of template flow.
# ==========================================================

def authenticate_user(request):
    # Extract JWT token from Authorization header Validate token Return authenticated user
    auth_header = get_authorization_header(request).split()
    if not auth_header:
        raise AuthenticationFailed("Authorization header missing")

    if len(auth_header) != 2:
        raise AuthenticationFailed("Authorization header malformed")
    try:
        token = auth_header[1].decode("utf-8")
    except UnicodeDecodeError:
        raise AuthenticationFailed("Invalid token encoding")

    user_id = decode_access_token(token)
    try:
        user = User.objects.get(id=user_id)
        return user
    except User.DoesNotExist:
        raise AuthenticationFailed("User not found")
    
