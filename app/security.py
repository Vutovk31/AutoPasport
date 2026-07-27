from datetime import datetime, timedelta, timezone
import base64, hashlib, hmac, os, secrets
from fastapi import Cookie, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import SessionToken, User

SESSION_COOKIE = "autopassport_session"
CSRF_COOKIE = "autopassport_csrf"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

def now(): return datetime.now(timezone.utc)
def sha(value: str): return hashlib.sha256(value.encode()).hexdigest()

def password_hash(password: str):
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt${}${}".format(base64.urlsafe_b64encode(salt).decode(), base64.urlsafe_b64encode(digest).decode())

def password_valid(password: str, encoded: str):
    try:
        _, salt64, digest64 = encoded.split("$", 2)
        actual = hashlib.scrypt(password.encode(), salt=base64.urlsafe_b64decode(salt64), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(digest64))
    except Exception:
        return False

def db():
    with SessionLocal() as session:
        yield session

def set_session(response: Response, session: Session, user: User):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    session.add(SessionToken(token_hash=sha(token), csrf_hash=sha(csrf), user_id=user.id, expires_at=now()+timedelta(days=30)))
    session.commit()
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/")
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=COOKIE_SECURE, samesite="lax", path="/")

def auth_pair(token: str | None = Cookie(default=None, alias=SESSION_COOKIE), session: Session = Depends(db)):
    if not token: raise HTTPException(401, "Authentication required")
    auth = session.scalar(select(SessionToken).where(SessionToken.token_hash == sha(token)))
    if not auth: raise HTTPException(401, "Invalid session")
    expires = auth.expires_at if auth.expires_at.tzinfo else auth.expires_at.replace(tzinfo=timezone.utc)
    if expires <= now(): raise HTTPException(401, "Session expired")
    user = session.get(User, auth.user_id)
    if not user: raise HTTPException(401, "User not found")
    return user, auth

def current_user(pair=Depends(auth_pair)): return pair[0]

def mutation_guard(request: Request, x_csrf_token: str | None = Header(default=None), csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE), pair=Depends(auth_pair)):
    if request.method in {"POST", "PATCH", "DELETE"}:
        if not x_csrf_token or not csrf_cookie: raise HTTPException(403, "CSRF token required")
        if not hmac.compare_digest(x_csrf_token, csrf_cookie): raise HTTPException(403, "CSRF mismatch")
        if not hmac.compare_digest(sha(x_csrf_token), pair[1].csrf_hash): raise HTTPException(403, "CSRF invalid")
    return pair[0]
