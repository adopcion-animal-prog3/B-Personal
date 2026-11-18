from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.errors import COMMON_ERROR_RESPONSES
from app.services.policies import UserRole
from app.models.auth import (
    AuthSuccessResponse,
    AuthenticatedUserSuccessResponse,
    LoginRequest,
    MessageSuccessResponse,
    PublicUser,
    RegisterRequest,
    ResendCodeRequest,
    UserSuccessResponse,
    VerificationPendingResponse,
    VerifyRequest,
)
from app.services.auth import (
    AuthService,
    EmailAlreadyExistsError,
    ExpiredAuthTokenError,
    InvalidAuthTokenError,
    InvalidCredentialsError,
    WrongPortalError,
)

router = APIRouter(
    prefix="/api/auth", tags=["auth"], responses=COMMON_ERROR_RESPONSES
)
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


def require_role(*allowed_roles: UserRole | str) -> Callable[..., dict[str, Any]]:
    if not allowed_roles:
        raise ValueError("At least one role must be allowed")
    role_names = {
        role.value if isinstance(role, UserRole) else role for role in allowed_roles
    }

    def role_dependency(
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if user.get("rol") not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_dependency


def _user_data(user: dict[str, Any]) -> dict[str, Any]:
    return {key: user[key] for key in ("id", "nombre", "email", "rol")}


@router.post(
    "/register",
    response_model=UserSuccessResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    values: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)
) -> dict[str, Any]:
    """Crea la cuenta y envía un código de verificación al email."""
    try:
        user = auth_service.start_registration(values)
    except EmailAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    data = {**_user_data(user), "verificacion_requerida": True, "verificacion": user["verificacion"]}
    return {"success": True, "status": "success", "data": data}


@router.post(
    "/login",
    response_model=VerificationPendingResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def login(
    values: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
) -> dict[str, Any]:
    """Paso 1: valida la contraseña y envía un código de 6 dígitos al email."""
    try:
        verificacion = auth_service.start_login(values)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error
    except WrongPortalError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(error)
        ) from error
    data = {"verificacion_requerida": True, "verificacion": verificacion}
    return {"success": True, "status": "success", "data": data}


@router.post("/verify", response_model=AuthSuccessResponse)
def verify(
    values: VerifyRequest, auth_service: AuthService = Depends(get_auth_service)
) -> dict[str, Any]:
    """Paso 2 (login o registro): valida el código del email y devuelve el token."""
    token, user = auth_service.verify_code(values.email, values.codigo)
    return {"success": True, "status": "success", "data": {"token": token, "user": _user_data(user)}}


@router.post("/resend-code", response_model=MessageSuccessResponse)
def resend_code(
    values: ResendCodeRequest, auth_service: AuthService = Depends(get_auth_service)
) -> dict[str, Any]:
    """Reenvía el código pendiente; responde igual exista o no la cuenta."""
    auth_service.resend_code(values.email)
    message = "If a verification is pending, a new code was sent"
    return {"success": True, "status": "success", "data": {"message": message}}


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
