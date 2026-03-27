"""Tests for foundation.auth.core — JWT, bcrypt, cookie helpers."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import jwt
import pytest
from pixl_api.foundation.auth.core import (
    clear_auth_cookie,
    decode_jwt,
    encode_jwt,
    get_token_from_request,
    hash_password,
    set_auth_cookie,
    verify_password,
)

SECRET = "test-secret-key-for-unit-tests-at-least-32-chars"


class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        hashed = hash_password("my-password")
        assert verify_password("my-password", hashed)

    def test_wrong_password_fails(self) -> None:
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_hash_is_not_plaintext(self) -> None:
        hashed = hash_password("secret")
        assert hashed != "secret"


class TestJWT:
    def test_encode_decode_roundtrip(self) -> None:
        payload = {"sub": "user-123", "role": "admin"}
        token = encode_jwt(payload, SECRET)
        decoded = decode_jwt(token, SECRET)
        assert decoded["sub"] == "user-123"
        assert decoded["role"] == "admin"

    def test_decode_contains_exp(self) -> None:
        token = encode_jwt({"sub": "u1"}, SECRET, expiry_hours=1)
        decoded = decode_jwt(token, SECRET)
        assert "exp" in decoded
        assert "iat" in decoded

    def test_expired_token_within_grace_period(self) -> None:
        payload = {"sub": "user-1", "exp": int(time.time()) - 30, "iat": int(time.time()) - 3600}
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        decoded = decode_jwt(token, SECRET)
        assert decoded["sub"] == "user-1"

    def test_expired_token_beyond_grace_period(self) -> None:
        payload = {"sub": "user-1", "exp": int(time.time()) - 120, "iat": int(time.time()) - 3600}
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_jwt(token, SECRET)

    def test_invalid_token_raises(self) -> None:
        with pytest.raises(jwt.InvalidTokenError):
            decode_jwt("garbage.token.value", SECRET)

    def test_wrong_secret_raises(self) -> None:
        token = encode_jwt({"sub": "u1"}, SECRET)
        with pytest.raises(jwt.InvalidTokenError):
            decode_jwt(token, "wrong-secret")


class TestGetTokenFromRequest:
    def test_from_bearer_header(self) -> None:
        request = MagicMock()
        request.headers = {"authorization": "Bearer my-token-123"}
        request.cookies = {}
        assert get_token_from_request(request) == "my-token-123"

    def test_from_cookie(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.cookies = {"auth": "cookie-token"}
        assert get_token_from_request(request) == "cookie-token"

    def test_header_takes_precedence_over_cookie(self) -> None:
        request = MagicMock()
        request.headers = {"authorization": "Bearer header-token"}
        request.cookies = {"auth": "cookie-token"}
        assert get_token_from_request(request) == "header-token"

    def test_returns_none_when_absent(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.cookies = {}
        assert get_token_from_request(request) is None

    def test_ignores_non_bearer_auth(self) -> None:
        request = MagicMock()
        request.headers = {"authorization": "Basic dXNlcjpwYXNz"}
        request.cookies = {}
        assert get_token_from_request(request) is None


class TestCookieHelpers:
    def test_set_auth_cookie(self) -> None:
        response = MagicMock()
        set_auth_cookie(response, "my-token")
        response.set_cookie.assert_called_once()
        call_kwargs = response.set_cookie.call_args
        assert call_kwargs.kwargs["key"] == "auth"
        assert call_kwargs.kwargs["value"] == "my-token"
        assert call_kwargs.kwargs["httponly"] is True

    def test_clear_auth_cookie(self) -> None:
        response = MagicMock()
        clear_auth_cookie(response)
        response.delete_cookie.assert_called_once()
        call_kwargs = response.delete_cookie.call_args
        assert call_kwargs.kwargs["key"] == "auth"
