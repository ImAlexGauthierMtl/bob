# Template: Authentification JWT complète

> Recette pour créer un module d'authentification JWT avec register/login/refresh/logout/me.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `API_NAME` | Nom de l'API auth | `auth-api` |
| `DEFAULT_ADMIN_EMAIL` | Email admin par défaut | `admin@company.com` |

## Fichiers à créer (7 fichiers)

### 1. `app/domain/entities/user.py` — Entité User

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.ext.declarative import declarative_base
import bcrypt

Base = declarative_base()


class User(Base):
    """User entity for authentication."""
    __tablename__ = "users"

    # Identifiers
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, default=1, nullable=False)

    # Soft delete fields
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(100), nullable=True)
    deleted_reason = Column(Text, nullable=True)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash un mot de passe avec bcrypt."""
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str) -> bool:
        """Vérifie un mot de passe contre le hash stocké."""
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        hash_bytes = self.password_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
```

### 2. `app/presentation/schemas/auth_schemas.py` — Schemas

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegisterRequest(BaseModel):
    """Schéma pour l'enregistrement d'un utilisateur."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Mot de passe (minimum 8 caractères)")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserLoginRequest(BaseModel):
    """Schéma pour la connexion d'un utilisateur."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schéma pour la réponse de token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Schéma pour le rafraîchissement de token."""
    refresh_token: str


class UserResponse(BaseModel):
    """Schéma pour la réponse d'un utilisateur."""
    id: int
    email: str
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Schéma pour la réponse de health check."""
    status: str
    service: str = "{API_NAME}"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### 3. `app/infrastructure/persistence/user_repository.py` — Repository

```python
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.domain.entities.user import User


class UserRepository:
    """Repository pour les opérations sur les utilisateurs."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user: User) -> User:
        """Crée un nouvel utilisateur."""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Récupère un utilisateur par son ID."""
        return self.db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False
        ).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Récupère un utilisateur par son email (case-insensitive)."""
        return self.db.query(User).filter(
            func.lower(User.email) == func.lower(email),
            User.is_deleted == False
        ).first()

    def update(self, user: User) -> User:
        """Met à jour un utilisateur."""
        user.version += 1
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User, deleted_by: str, reason: Optional[str] = None) -> User:
        """Soft delete d'un utilisateur."""
        from datetime import datetime
        user.is_deleted = True
        user.deleted_at = datetime.utcnow()
        user.deleted_by = deleted_by
        user.deleted_reason = reason
        user.version += 1
        self.db.commit()
        self.db.refresh(user)
        return user
```

### 4. `app/application/use_cases/authenticate_user.py`

```python
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.entities.user import User
from app.infrastructure.persistence.user_repository import UserRepository


class AuthenticateUserUseCase:
    """Use case pour l'authentification d'un utilisateur."""

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(self, email: str, password: str) -> Optional[User]:
        """Authentifie un utilisateur avec email et mot de passe."""
        email_normalized = email.strip().lower()
        user = self.user_repository.get_by_email(email_normalized)

        if not user:
            return None
        if not user.verify_password(password):
            return None

        return user
```

### 5. `app/application/use_cases/register_user.py`

```python
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.entities.user import User
from app.infrastructure.persistence.user_repository import UserRepository


class RegisterUserUseCase:
    """Use case pour l'enregistrement d'un nouvel utilisateur."""

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        created_by: Optional[str] = None
    ) -> User:
        """Enregistre un nouvel utilisateur."""
        email_normalized = email.strip().lower()

        existing_user = self.user_repository.get_by_email(email_normalized)
        if existing_user:
            raise ValueError("Un utilisateur avec cet email existe déjà")

        user = User(
            email=email_normalized,
            password_hash=User.hash_password(password),
            first_name=first_name,
            last_name=last_name,
            created_by=created_by or "system"
        )

        return self.user_repository.create(user)
```

### 6. `app/application/use_cases/refresh_token.py`

```python
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.entities.user import User
from app.infrastructure.persistence.user_repository import UserRepository


class RefreshTokenUseCase:
    """Use case pour le rafraîchissement d'un token."""

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(self, user_id: int) -> Optional[User]:
        """Récupère un utilisateur pour le rafraîchissement de token."""
        return self.user_repository.get_by_id(user_id)
```

### 7. `app/presentation/routes/auth_routes.py` — Router complet

```python
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.infrastructure.database import get_db
from app.application.use_cases.register_user import RegisterUserUseCase
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.refresh_token import RefreshTokenUseCase
from app.presentation.schemas.auth_schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    RefreshTokenRequest, UserResponse, HealthResponse
)
from app.config import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security = HTTPBearer()

settings = get_settings()
SECRET_KEY = settings.secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

# Rate limiting (in production, use Redis)
rate_limit_storage: dict[str, list[datetime]] = {}
RATE_LIMIT_MAX_ATTEMPTS = settings.rate_limit_max_attempts
RATE_LIMIT_WINDOW_MINUTES = settings.rate_limit_window_minutes


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crée un access token JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Crée un refresh token JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Vérifie et décode un token JWT."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def is_rate_limited(identifier: str) -> bool:
    """Check if identifier is rate limited."""
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)
    if identifier not in rate_limit_storage:
        return False
    rate_limit_storage[identifier] = [
        a for a in rate_limit_storage[identifier] if a > window_start
    ]
    return len(rate_limit_storage[identifier]) >= RATE_LIMIT_MAX_ATTEMPTS


def add_failed_attempt(identifier: str) -> None:
    """Record a failed login attempt."""
    if identifier not in rate_limit_storage:
        rate_limit_storage[identifier] = []
    rate_limit_storage[identifier].append(datetime.utcnow())


def reset_rate_limit(identifier: str) -> None:
    """Reset rate limiting pour un identifiant."""
    if identifier in rate_limit_storage:
        rate_limit_storage[identifier] = []


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """Dependency pour obtenir l'utilisateur actuel depuis le token."""
    payload = verify_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")
    return {"user_id": user_id, "payload": payload}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
    """Enregistre un nouvel utilisateur."""
    use_case = RegisterUserUseCase(db)
    try:
        user = use_case.execute(
            email=user_data.email, password=user_data.password,
            first_name=user_data.first_name, last_name=user_data.last_name
        )
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authentifie un utilisateur et retourne les tokens."""
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Trop de tentatives")

    use_case = AuthenticateUserUseCase(db)
    user = use_case.execute(credentials.email, credentials.password)

    if not user:
        add_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    reset_rate_limit(client_ip)
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(token_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Rafraîchit un access token avec un refresh token."""
    payload = verify_token(token_data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide")

    user_id = int(payload.get("sub", 0))
    use_case = RefreshTokenUseCase(db)
    user = use_case.execute(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user: dict = Depends(get_current_user)):
    """Déconnexion."""
    return {"message": "Déconnexion réussie"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Récupère les informations de l'utilisateur actuel."""
    from app.infrastructure.persistence.user_repository import UserRepository
    user = UserRepository(db).get_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return UserResponse.model_validate(user)
```

### 8. `app/infrastructure/seed.py` — Seed admin

```python
"""Seed script — creates default admin user."""
import os
import logging
from sqlalchemy.orm import Session
from app.domain.entities.user import User
from app.infrastructure.persistence.user_repository import UserRepository

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "{DEFAULT_ADMIN_EMAIL}")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin123!")
DEFAULT_ADMIN_FIRST_NAME = os.getenv("ADMIN_FIRST_NAME", "Admin")
DEFAULT_ADMIN_LAST_NAME = os.getenv("ADMIN_LAST_NAME", "System")


def seed_admin_user(db: Session) -> None:
    """Create default admin user if it doesn't exist."""
    repo = UserRepository(db)
    existing = repo.get_by_email(DEFAULT_ADMIN_EMAIL.lower())
    if existing:
        logger.info(f"Admin user {DEFAULT_ADMIN_EMAIL} already exists, skipping seed.")
        return

    admin = User(
        email=DEFAULT_ADMIN_EMAIL.lower(),
        password_hash=User.hash_password(DEFAULT_ADMIN_PASSWORD),
        first_name=DEFAULT_ADMIN_FIRST_NAME,
        last_name=DEFAULT_ADMIN_LAST_NAME,
        created_by="system-seed"
    )
    created = repo.create(admin)
    logger.info(f"Admin user created: {created.email} (id={created.id})")


def run_seed(db: Session) -> None:
    """Run all seed operations."""
    seed_admin_user(db)
```

## Règles NON-NÉGOCIABLES

1. Passwords hashés avec bcrypt (rounds=12), jamais en clair
2. JWT avec access token (30min) + refresh token (7 jours)
3. Rate limiting sur `/login` — en production utiliser Redis
4. Soft delete sur les users (jamais de hard delete)
5. Email normalisé en minuscules
6. `get_current_user` comme dependency injectable
7. Validation avec Pydantic `EmailStr` et `min_length`

## Tests obligatoires

- `test_register_success` → POST /register → 201
- `test_register_duplicate_email` → POST /register → 400
- `test_login_success` → POST /login → 200 + tokens
- `test_login_wrong_password` → POST /login → 401
- `test_refresh_token` → POST /refresh → 200 + new tokens
- `test_get_me` → GET /me → 200 + user info
- `test_rate_limiting` → POST /login N times → 429
