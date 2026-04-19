from fastapi import APIRouter, HTTPException, status

from app.schemas import AuthResponse, LoginRequest, SignUpRequest
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignUpRequest) -> AuthResponse:
    try:
        user = auth_service.create_user(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    token = auth_service.create_token(user["id"])
    return AuthResponse(access_token=token, user_id=user["id"])


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    try:
        user = auth_service.authenticate(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    token = auth_service.create_token(user["id"])
    return AuthResponse(access_token=token, user_id=user["id"])
