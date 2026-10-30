from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.auth import (
    AuthSuccessResponse,
    AuthenticatedUserSuccessResponse,
    LoginRequest,
    PublicUser,
    RegisterRequest,
    UserSuccessResponse,
)
from app.services.auth import (
    AuthService,
    EmailAlreadyExistsError,
    ExpiredAuthTokenError,
    InvalidAuthTokenError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return auth_service.authenticate(credentials.credentials)
    except ExpiredAuthTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except InvalidAuthTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


@router.post(
    "/register",
    response_model=UserSuccessResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    values: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)
) -> dict[str, Any]:
    try:
        user = auth_service.register(values)
    except EmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    return {
        "success": True,
        "status": "success",
        "data": {
            "id": user["id"],
            "nombre": user["nombre"],
            "email": user["email"],
            "rol": user["rol"],
        },
    }


@router.post("/login", response_model=AuthSuccessResponse)
def login(
    values: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
) -> dict[str, Any]:
    try:
        token, user = auth_service.login(values)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error
    return {
        "success": True,
        "status": "success",
        "data": {
            "token": token,
            "user": {
                "id": user["id"],
                "nombre": user["nombre"],
                "email": user["email"],
                "rol": user["rol"],
            },
        },
    }


@router.get("/me", response_model=AuthenticatedUserSuccessResponse)
def me(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "success": True,
        "status": "success",
        "data": {
            "user": PublicUser(
                id=user["id"],
                nombre=user["nombre"],
                email=user["email"],
                rol=user["rol"],
            )
        },
    }
