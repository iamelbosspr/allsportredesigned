from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable

import requests
from bs4 import BeautifulSoup


MONTHS_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

KNOWN_BRANDS = (
    "Total",
    "Shell",
    "Texaco",
    "Puma",
    "Gulf",
    "Mobil",
    "Toral",
    "Peerless",
)


@dataclass(frozen=True)
class BrandPrice:
    brand: str
    regular: float
    premium: float
    diesel: float


@dataclass(frozen=True)
class PriceSnapshot:
    source_url: str
    source_updated_at: date | None
    prices: list[BrandPrice]


def _extract_numbers(text: str) -> list[float]:
    nums: list[float] = []
    for token in re.findall(r"\d{1,3}(?:[.,]\d+)?", text):
        nums.append(float(token.replace(",", ".")))
    return nums


def _parse_spanish_date(text: str) -> date | None:
    match = re.search(r"(\d{1,2})\s+de\s+([a-zA-Z]+)\s+de\s+(\d{4})", text, re.IGNORECASE)
    if not match:
        return None
    day = int(match.group(1))
    month_name = match.group(2).lower().replace("", "a").replace("", "e").replace("", "i").replace("", "o").replace("", "u")
    month = MONTHS_ES.get(month_name)
    if not month:
        return None
    year = int(match.group(3))
    return date(year, month, day)


def _find_updated_date(soup: BeautifulSoup) -> date | None:
    for token in soup.stripped_strings:
        if "Actualizado:" in token:
            return _parse_spanish_date(token)
    return None


def _build_snapshot_from_section(section_strings: Iterable[str], source_url: str, source_updated_at: date | None) -> PriceSnapshot:
    prices: list[BrandPrice] = []
    text = " ".join(section_strings)

    for brand in KNOWN_BRANDS:
        pattern = rf"{re.escape(brand)}[^\d]*(\d{{1,3}}(?:[.,]\d+)?)\D+(\d{{1,3}}(?:[.,]\d+)?)\D+(\d{{1,3}}(?:[.,]\d+)?)"
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            continue
        regular = float(m.group(1).replace(",", "."))
        premium = float(m.group(2).replace(",", "."))
        diesel = float(m.group(3).replace(",", "."))
        prices.append(BrandPrice(brand=brand, regular=regular, premium=premium, diesel=diesel))

    if not prices:
        raise ValueError("Could not parse fuel prices from DACO section")

    return PriceSnapshot(source_url=source_url, source_updated_at=source_updated_at, prices=prices)


def parse_snapshot(html: str, source_url: str) -> PriceSnapshot:
    soup = BeautifulSoup(html, "html.parser")
    source_updated_at = _find_updated_date(soup)

    section_header = soup.find(
        lambda tag: tag.name in {"h1", "h2", "h3", "h4"}
        and "Precio en bomba por marca" in " ".join(tag.stripped_strings)
    )
    if not section_header:
        raise ValueError("DACO price section not found")

    current_brand: str | None = None
    buckets: dict[str, list[float]] = {}
    section_strings: list[str] = []

    node = section_header.find_next_sibling()
    while node:
        node_name = getattr(node, "name", None)
        if node_name and str(node_name).lower() == "h2":
            break

        if hasattr(node, "stripped_strings"):
            chunk = " ".join(node.stripped_strings)
            if chunk:
                section_strings.append(chunk)

        if node_name and str(node_name).lower() in {"h3", "h4"}:
            brand = " ".join(node.stripped_strings).strip()
            brand = re.sub(r"\s+", " ", brand)
            if brand:
                current_brand = brand
                buckets.setdefault(current_brand, [])
                inline_numbers = _extract_numbers(brand)
                if inline_numbers:
                    buckets[current_brand].extend(inline_numbers)
        elif current_brand and node_name:
            chunk = " ".join(node.stripped_strings)
            values = _extract_numbers(chunk)
            if values:
                buckets[current_brand].extend(values)

        node = node.find_next_sibling()

    prices: list[BrandPrice] = []
    for brand, values in buckets.items():
        if len(values) < 3:
            continue
        prices.append(
            BrandPrice(
                brand=brand,
                regular=values[0],
                premium=values[1],
                diesel=values[2],
            )
        )

    if prices:
        return PriceSnapshot(source_url=source_url, source_updated_at=source_updated_at, prices=prices)

    return _build_snapshot_from_section(section_strings, source_url, source_updated_at)


def fetch_daco_snapshot(url: str, timeout_seconds: int = 25) -> PriceSnapshot:
    resp = requests.get(url, timeout=timeout_seconds)
    resp.raise_for_status()
    return parse_snapshot(resp.text, source_url=url)
