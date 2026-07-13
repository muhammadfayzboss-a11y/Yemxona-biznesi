# -*- coding: utf-8 -*-
"""Yordamchi formatlash funksiyalari."""

from config import UZS, USD


def fmt_money(uzs, usd):
    """Qolgan qarzni '... so'm + ... $' ko'rinishida qaytaradi."""
    parts = []
    if uzs and uzs > 0.0001:
        parts.append(f"{uzs:,.0f} {UZS}")
    if usd and usd > 0.0001:
        parts.append(f"{usd:,.0f} {USD}")
    if not parts:
        return f"0 {UZS}"
    return " + ".join(parts)


def fmt_num(n):
    if n is None:
        return "0"
    return f"{n:,.0f}"
