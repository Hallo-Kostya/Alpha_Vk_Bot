from fastapi import HTTPException, Header, status
import jwt
from src.common.constants import ServerConfig


class AuthService:
    @staticmethod
    def _encode_jwt(service_name: str):
        encoded_jwt = jwt.encode(
            {"service_name": service_name},
            ServerConfig.hash_secret,
            algorithm=ServerConfig.hash_algorithm,
        )
        return encoded_jwt

    @staticmethod
    def _decode_jwt(token: str) -> dict:
        payload = jwt.decode(
            token,
            ServerConfig.hash_secret,
            algorithms=[ServerConfig.hash_algorithm],
        )
        return payload

    @staticmethod
    def __verify_service(token: str) -> None:
        payload = AuthService._decode_jwt(token)
        service_name = payload.get("service_name", "UNKNOWN")
        if service_name not in ServerConfig.services_whitelist:
            raise HTTPException(status_code=401, detail="Wrong credentials")

    @staticmethod
    def verify_service(authorization: str = Header(...)) -> None:
        try:
            AuthService.__verify_service(authorization)
        except (jwt.exceptions.InvalidTokenError, jwt.exceptions.DecodeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization token",
            )
