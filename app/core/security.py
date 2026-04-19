from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt

<<<<<<< HEAD
from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
=======
from app.core.config import settings
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    to_encode = data.copy()

<<<<<<< HEAD
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"sub": str(data["sub"]), "role": data.get("role"), "exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
=======
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"sub": str(data["sub"]), "role": data.get("role"), "exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)

    return encoded_jwt
