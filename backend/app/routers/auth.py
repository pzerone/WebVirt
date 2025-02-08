from typing import Annotated
from fastapi import APIRouter
from fastapi import Depends
from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.exceptions import HTTPException
from app.ldap.main import verify_password
from app.utils.auth import create_access_token
from app.utils.auth import decode_token
from app.models.token import Token
from app.models.token import TokenData


# Sub router for auth
router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", scheme_name="JWT")


# retrieves currently logged in user from jwt token and return a TokenData object to be used by endpoints
async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return TokenData(**user)


@router.post("/login", response_model=Token)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    if not verify_password(username=form_data.username, password=form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Access token and type only. refresh token is overkill for us.
    return Token(
        access_token=create_access_token({"username": form_data.username}),
        token_type="Bearer",
    )
