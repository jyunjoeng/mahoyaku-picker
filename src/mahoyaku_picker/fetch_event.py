from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Callable, Sequence
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


class MahoyakuPickerError(Exception):
    """Base exception for the package."""


class FetchBlockedError(MahoyakuPickerError):
    """Raised when the target site returns a verification page instead of content."""


def resolve_browser_executable_path() -> str | None:
    # For Streamlit Cloud, use system chromium; locally can override with env var
    return os.environ.get("MAHOYAKU_BROWSER_PATH") or "/usr/bin/chromium"


def _fetch_page_text_with_browser(url: str) -> str:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=resolve_browser_executable_path(),
        )
        page = browser.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(5_000)
            page_text = page.content()
        finally:
            browser.close()

    if "Human Verification" in page_text:
        raise FetchBlockedError(
            "The browser session still received a human-verification page."
        )

    return page_text


TRAIT_UNLOCK_NOTE_PATTERN = re.compile(r"\(.*?\)")


def extract_traits(card_html: str) -> list[str]:
    soup = BeautifulSoup(card_html, "html.parser")

    for header in soup.find_all(["th", "h3", "h4"]):
        if header.get_text(" ", strip=True) != "パートナー特性":
            continue

        if header.name == "th":
            row = header.find_parent("tr")
            if row is None:
                continue
            value_row = row.find_next_sibling("tr")
            if value_row is None:
                continue
            value_cell = value_row.find(["td", "th"])
            if value_cell is None:
                continue
            for br in value_cell.find_all("br"):
                br.replace_with("\n")
            raw_text = value_cell.get_text("", strip=False)
            traits: list[str] = []
            for line in raw_text.splitlines():
                for part in line.split("/"):
                    cleaned = TRAIT_UNLOCK_NOTE_PATTERN.sub("", part).strip()
                    if cleaned:
                        traits.append(cleaned)
            return traits

        next_tag = header.find_next(["div", "p", "table"])
        if next_tag is not None:
            raw_text = next_tag.get_text("\n", strip=True)
            traits = []
            for line in raw_text.splitlines():
                for part in line.split("/"):
                    cleaned = TRAIT_UNLOCK_NOTE_PATTERN.sub("", part).strip()
                    if cleaned:
                        traits.append(cleaned)
            return traits

    return []


def extract_ssr_cards(
    page_html: str,
    fetcher: Callable[[str], str] | None = None,
) -> list[dict[str, str]]:
    soup = BeautifulSoup(page_html, "html.parser")
    cards: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for row in soup.select("tr"):
        columns = row.find_all(["td", "th"], recursive=False)
        if len(columns) < 3:
            continue

        rarity = columns[2].get_text(" ", strip=True)
        if rarity != "SSR":
            continue

        name_link = columns[1].find("a", href=True)
        if name_link is None:
            continue

        gamerch_url = name_link["href"]
        if gamerch_url in seen_urls:
            continue

        acquisition_method = ""
        if len(columns) >= 4:
            acquisition_method = columns[3].get_text(" ", strip=True)

        traits: list[str] = []
        if fetcher is not None:
            traits = extract_traits(fetcher(gamerch_url))

        seen_urls.add(gamerch_url)
        cards.append(
            {
                "name": name_link.get_text(" ", strip=True),
                "rarity": rarity,
                "gamerch_url": gamerch_url,
                "acquisition_method": acquisition_method,
                "traits": traits,
            }
        )

    return cards


def fetch_page_text(url: str) -> str:
    try:
        return _fetch_page_text_with_browser(url)
    except PlaywrightError as exc:
        raise FetchBlockedError(
            f"Unable to fetch the event page through the browser fallback: {exc}"
        ) from exc


def get_ssr_cards(
    url: str,
    fetcher: Callable[[str], str] = fetch_page_text,
) -> list[dict[str, str]]:
    return extract_ssr_cards(fetcher(url), fetcher=fetcher)


def build_export_payload(cards: list[dict[str, str]]) -> dict[str, object]:
    all_traits = sorted({trait for card in cards for trait in card["traits"]})
    return {
        "traits": all_traits,
        "cards": cards,
    }


def default_output_path(url: str) -> Path:
    page_id = url.rstrip("/").split("/")[-1]
    return Path("data/events") / f"{page_id}.json"


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mahoyaku-picker",
        description="Extract SSR event card names from a Mahoyaku event page.",
    )
    parser.add_argument("url", help="Event page URL to inspect")
    args = parser.parse_args(argv)

    cards = get_ssr_cards(args.url)
    output_path = default_output_path(args.url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_export_payload(cards), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    all_traits: set[str] = set()
    for card in cards:
        traits = card["traits"]
        all_traits.update(traits)
        print(f'{card["name"]}: {traits}')

    print(f"all_traits: {all_traits}")
    print(f"json_output: {output_path}")


if __name__ == "__main__":
    main()
