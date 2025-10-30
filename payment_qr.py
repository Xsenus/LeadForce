"""Utility helpers for generating bank payment QR codes."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from typing import Dict, Optional

import segno


@dataclass
class PaymentQRDetails:
    """Parameters for ST00012 (Russian bank) QR payload."""

    name: str = ""
    personal_account: str = ""
    bank_name: str = ""
    bik: str = ""
    correspondent_account: str = ""
    inn: str = ""
    kpp: str = ""
    purpose: str = ""
    sum_kopecks: Optional[int] = None

    @classmethod
    def from_mapping(cls, data: Dict[str, str], sum_kopecks: Optional[int]) -> "PaymentQRDetails":
        """Create details instance from HTTP params mapping."""

        return cls(
            name=(data.get("qr_name") or data.get("receiver_name") or "").strip(),
            personal_account=(data.get("qr_account") or data.get("receiver_account") or "").strip(),
            bank_name=(data.get("qr_bank") or data.get("receiver_bank") or "").strip(),
            bik=(data.get("qr_bik") or data.get("receiver_bik") or "").strip(),
            correspondent_account=(
                data.get("qr_correspondent_account")
                or data.get("receiver_correspondent_account")
                or ""
            ).strip(),
            inn=(data.get("qr_inn") or data.get("receiver_inn") or data.get("inn") or "").strip(),
            kpp=(data.get("qr_kpp") or data.get("receiver_kpp") or "").strip(),
            purpose=(data.get("qr_purpose") or data.get("purpose") or data.get("service") or "").strip(),
            sum_kopecks=sum_kopecks,
        )

    def is_valid(self) -> bool:
        """Return True if we have enough data for QR generation."""

        required = [self.name, self.personal_account, self.bank_name, self.bik]
        return all(required)


def parse_price_to_kopecks(price: str) -> Optional[int]:
    """Convert price string to integer amount in kopecks."""

    if not price:
        return None

    price = price.replace(" ", "").replace(",", ".")
    try:
        value = Decimal(price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None

    return int(value * 100)


def build_st00012_payload(details: PaymentQRDetails) -> Optional[str]:
    """Build ST00012 payload string for Russian bank QR."""

    if not details.is_valid():
        return None

    payload_parts = ["ST00012"]

    def append(key: str, value: str | int | None):
        if value is None:
            return
        text = str(value).strip()
        if not text:
            return
        payload_parts.append(f"{key}={text}")

    append("Name", details.name)
    append("PersonalAcc", details.personal_account)
    append("BankName", details.bank_name)
    append("BIC", details.bik)
    append("CorrespAcc", details.correspondent_account)
    append("PayeeINN", details.inn)
    append("KPP", details.kpp)
    append("Purpose", details.purpose)
    append("Sum", details.sum_kopecks)

    return "|".join(payload_parts)


def generate_qr_png(payload: str, scale: int = 6) -> bytes:
    """Generate PNG bytes for given QR payload."""

    qr = segno.make(payload, micro=False)
    buffer = BytesIO()
    qr.save(buffer, kind="png", scale=scale, border=2)
    return buffer.getvalue()


def build_payment_qr(data: Dict[str, str], price: str) -> Optional[bytes]:
    """Create payment QR PNG if enough data is provided."""

    sum_kopecks = parse_price_to_kopecks(price)
    details = PaymentQRDetails.from_mapping(data, sum_kopecks)
    payload = build_st00012_payload(details)

    if not payload:
        return None

    return generate_qr_png(payload)
