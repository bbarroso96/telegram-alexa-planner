"""Verify that an inbound /alexa request is genuinely from Amazon, for THIS skill.

Public Alexa skills must validate every request. We check four things:
  1. applicationId  — the request is for our skill (optional; needs ALEXA_SKILL_ID)
  2. timestamp      — within 150s, so old requests can't be replayed
  3. cert chain URL — the signing cert comes from a real Amazon S3 /echo.api/ URL
  4. signature      — the request body is signed by that cert's key (RSA, SHA-1)

Trust comes from (3)+(4): the cert is fetched over HTTPS from an Amazon-controlled
URL whose SAN includes echo-api.amazon.com, and the body signature verifies against
it — which only Amazon's Alexa service can produce. A forged request fails (4).
"""
import base64
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from config.settings import config

_MAX_SKEW_SECONDS = 150
_cert_cache: dict = {}


class VerificationError(Exception):
    pass


def _validate_cert_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme != "https":
        raise VerificationError("cert URL must be https")
    if (p.hostname or "").lower() != "s3.amazonaws.com":
        raise VerificationError("cert URL host must be s3.amazonaws.com")
    if p.port not in (None, 443):
        raise VerificationError("cert URL port must be 443")
    if not unquote(p.path).startswith("/echo.api/"):
        raise VerificationError("cert URL path must start with /echo.api/")


def _leaf_cert(cert_url: str):
    cert = _cert_cache.get(cert_url)
    if cert is None:
        _validate_cert_url(cert_url)
        with urllib.request.urlopen(cert_url, timeout=10) as resp:  # HTTPS authenticates the host
            pem = resp.read()
        block = pem.split(b"-----END CERTIFICATE-----")[0] + b"-----END CERTIFICATE-----\n"
        cert = x509.load_pem_x509_certificate(block)
        _cert_cache[cert_url] = cert

    now = datetime.now(timezone.utc)
    try:
        not_before, not_after = cert.not_valid_before_utc, cert.not_valid_after_utc
    except AttributeError:  # cryptography < 42
        not_before = cert.not_valid_before.replace(tzinfo=timezone.utc)
        not_after = cert.not_valid_after.replace(tzinfo=timezone.utc)
    if not (not_before <= now <= not_after):
        raise VerificationError("signing certificate expired or not yet valid")

    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    if "echo-api.amazon.com" not in san.get_values_for_type(x509.DNSName):
        raise VerificationError("certificate SAN missing echo-api.amazon.com")
    return cert


def _verify_signature(headers, raw_body: bytes) -> None:
    cert_url = headers.get("signaturecertchainurl")
    sig_b64 = headers.get("signature")
    if not cert_url or not sig_b64:
        raise VerificationError("missing signature headers")
    cert = _leaf_cert(cert_url)
    cert.public_key().verify(base64.b64decode(sig_b64), raw_body, padding.PKCS1v15(), hashes.SHA1())


def _verify_timestamp(body: dict) -> None:
    ts = body.get("request", {}).get("timestamp")
    if not ts:
        raise VerificationError("missing request timestamp")
    when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if abs((datetime.now(timezone.utc) - when).total_seconds()) > _MAX_SKEW_SECONDS:
        raise VerificationError("request timestamp outside tolerance")


def _verify_application(body: dict) -> None:
    if not config.alexa_skill_id:
        return  # optional check; skipped when ALEXA_SKILL_ID isn't set
    app_id = (body.get("context", {}).get("System", {}).get("application", {}).get("applicationId")
              or body.get("session", {}).get("application", {}).get("applicationId"))
    if app_id != config.alexa_skill_id:
        raise VerificationError("applicationId does not match this skill")


def verify(headers, raw_body: bytes, body: dict) -> None:
    """Raise VerificationError unless this is a genuine, fresh request for this skill."""
    _verify_application(body)
    _verify_timestamp(body)
    _verify_signature(headers, raw_body)
