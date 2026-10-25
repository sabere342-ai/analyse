from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PARSER_VERSION = "1.2.0"
CONTRACT_VERSION = "1.2.0"
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
ReportType = Literal["snapshot", "sales", "movement", "costs", "expenses", "targets"]


def decimal_value(value: object) -> Decimal:
    text = str(value).strip().translate(DIGITS).replace("٫", ".").replace("٬", "")
    text = text.replace("−", "-")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    if "," in text:
        if not re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", text):
            raise ValueError("ambiguous_number_separator")
        text = text.replace(",", "")
    if not re.fullmatch(r"-?\d+(\.\d{1,6})?", text):
        raise ValueError("invalid_decimal")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("invalid_decimal") from exc
    if not result.is_finite() or abs(result) > Decimal("1000000000000"):
        raise ValueError("number_out_of_range")
    return result


def code_value(value: object) -> str:
    result = str(value).strip().translate(DIGITS)
    if not result or len(result) > 100 or any(ord(c) < 32 for c in result):
        raise ValueError("missing_or_invalid_barcode")
    return result


def date_value(value: str) -> str:
    value = value.strip().translate(DIGITS)
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", value):
        d, m, y = value.split("/")
        return date(int(y), int(m), int(d)).isoformat()
    return date.fromisoformat(value).isoformat()


class ImportSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_type: ReportType
    start: date
    end: date
    scope: str = Field(default="store", min_length=1, max_length=100)
    currency: str = Field(default="EGP", pattern=r"^[A-Z]{3}$")
    expected: dict[str, str] = Field(default_factory=dict, max_length=20)
    column_map: dict[str, str] = Field(default_factory=dict, max_length=40)
    encoding: Literal["utf-8-sig", "cp1256"] = "utf-8-sig"
    delimiter: Literal[",", ";", "\t", "auto"] = "auto"
    sheets: list[str] = Field(default_factory=list, max_length=20)
    pdf_profile: Literal["auto", "generic", "arabic_pos_v1"] = "auto"
    source_dates: Literal["manual", "report"] = "manual"
    sales_coverage: Literal["store", "assigned_only"] = "store"
    complete: bool = False
    financial_verified: bool = False
    reservation_verified: bool = False
    availability_verified: bool = False
    rounding: Literal["ROUND_HALF_UP"] = "ROUND_HALF_UP"
    note: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def periods(self) -> ImportSpec:
        if self.sales_coverage == "assigned_only" and (self.report_type != "sales" or not self.note.strip()):
            raise ValueError("assigned_sales_scope_requires_sales_report_and_source_note")
        if self.currency not in {"EGP", "USD", "EUR", "SAR", "AED", "GBP"}:
            raise ValueError("unsupported_currency_minor_unit_policy")
        if self.end < self.start:
            raise ValueError("invalid_period")
        if self.report_type in {"snapshot", "costs"} and self.start != self.end:
            raise ValueError("point_in_time_report_requires_one_date")
        for value in self.expected.values():
            decimal_value(value)
        return self


class Rules(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_cover_days: int = Field(default=14, ge=1, le=365)
    lead_time_days: int = Field(default=3, ge=0, le=365)
    min_history_days: int = Field(default=30, ge=1, le=730)
    dead_no_sale_days: int = Field(default=90, ge=30, le=1095)
    max_cover_days: int = Field(default=60, ge=1, le=1095)
    slow_velocity: str = "0.2"
    return_alert_rate: str = "20"
    discount_alert_rate: str = "20"
    minimum_margin_rate: str = "20"
    safety_units: str = "0"

    @field_validator(
        "slow_velocity", "return_alert_rate", "discount_alert_rate", "minimum_margin_rate", "safety_units"
    )
    @classmethod
    def positive(cls, value: str) -> str:
        if decimal_value(value) < 0:
            raise ValueError("threshold_must_be_nonnegative")
        return value
