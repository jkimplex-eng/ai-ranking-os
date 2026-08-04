from datetime import UTC, datetime

import jwt
from argon2 import PasswordHasher as Argon2Engine
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from authentication.ports import Clock


class UtcClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._engine = Argon2Engine()

    def hash(self, password: str) -> str:
        return self._engine.hash(password)

    def verify(self, encoded: str, password: str) -> bool:
        try:
            return self._engine.verify(encoded, password)
        except (VerifyMismatchError, InvalidHashError):
            return False


class JwtTokenCodec:
    def __init__(self, secret: str, algorithm: str, issuer: str, audience: str) -> None:
        self.secret = secret
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience

    def encode(self, claims: dict[str, object]) -> str:
        return jwt.encode(
            {**claims, "iss": self.issuer, "aud": self.audience},
            self.secret,
            algorithm=self.algorithm,
        )

    def decode(self, token: str, expected_type: str) -> dict[str, object]:
        claims = jwt.decode(
            token,
            self.secret,
            algorithms=[self.algorithm],
            issuer=self.issuer,
            audience=self.audience,
            options={"require": ["exp", "iat", "jti", "sub", "sid", "typ", "ver"]},
        )
        if claims.get("typ") != expected_type:
            raise jwt.InvalidTokenError("Unexpected token type")
        return claims
