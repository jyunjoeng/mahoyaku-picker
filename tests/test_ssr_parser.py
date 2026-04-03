from mahoyaku_picker import (
    FetchBlockedError,
    build_export_payload,
    default_output_path,
    extract_ssr_cards,
    get_ssr_cards,
    resolve_browser_executable_path,
)


EVENT_URL = "https://example.com/event/000001"
FIRST_CARD_URL = "card-1-url"
SECOND_CARD_URL = "card-2-url"
THIRD_CARD_URL = "card-3-url"

EVENT_HTML = """<h3>特効カード一覧</h3>
<div class="mu__wikidb-list"><div class="mu__table"><table>
<thead>
<tr class="mu__table--row1 sort">
<th class="mu__table--col1">画像</th>
<th class="mu__table--col2">カード名</th>
<th class="mu__table--col3">レア</th>
<th class="mu__table--col4">入手方法</th>
</tr>
</thead>
<tbody>
<tr class="mu__table--row2">
<td class="mu__table--col1"><a href="card-1-url">img</a></td>
<td class="mu__table--col2"><a href="card-1-url">Card 1 Name</a></td>
<td class="mu__table--col3">SSR</td>
<td class="mu__table--col4">イベントガチャ→通常ガチャ</td>
</tr>
<tr class="mu__table--row3">
<td class="mu__table--col1"><a href="card-2-url">img</a></td>
<td class="mu__table--col2"><a href="card-2-url">Card 2 Name</a></td>
<td class="mu__table--col3">SSR</td>
<td class="mu__table--col4">イベントガチャ→通常ガチャ</td>
</tr>
<tr class="mu__table--row4">
<td class="mu__table--col1"><a href="card-3-url">img</a></td>
<td class="mu__table--col2"><a href="card-3-url">Card 3 Name</a></td>
<td class="mu__table--col3">SSR</td>
<td class="mu__table--col4">イベントガチャ→通常ガチャ</td>
</tr>
<tr class="mu__table--row5">
<td class="mu__table--col1"><a href="sr-card-url">img</a></td>
<td class="mu__table--col2"><a href="sr-card-url">SR Card Name</a></td>
<td class="mu__table--col3">SR</td>
<td class="mu__table--col4">イベントガチャ→通常ガチャ</td>
</tr>
</tbody>
</table></div></div>
"""

FIRST_CARD_HTML = """<table>
<tbody>
<tr class="mu__table--row10"><th class="mu__table--col1" colspan="2">パートナー特性</th></tr>
<tr class="mu__table--row11"><td class="mu__table--col1" colspan="2">
<a href="trait-1-url">気まま</a>/宝石/<a href="trait-2-url">熱狂</a>/<a href="trait-3-url">独創</a><br>
<a href="trait-4-url">朴訥</a>(レベル30で解放)<br>
<a href="trait-5-url">熱血</a>(レベル55で解放)<br>
探求(レベル75で解放)<br>
<a href="trait-6-url">勝利</a>(レベル100で解放)</td></tr>
</tbody>
</table>
"""

OTHER_CARD_HTML = """<table><tbody><tr><th colspan="2">パートナー特性</th></tr><tr><td colspan="2">別データ</td></tr></tbody></table>"""

EXPECTED_CARDS = [
    {
        "name": "Card 1 Name",
        "rarity": "SSR",
        "gamerch_url": FIRST_CARD_URL,
        "acquisition_method": "イベントガチャ→通常ガチャ",
        "traits": [
            "気まま",
            "宝石",
            "熱狂",
            "独創",
            "朴訥",
            "熱血",
            "探求",
            "勝利",
        ],
    },
    {
        "name": "Card 2 Name",
        "rarity": "SSR",
        "gamerch_url": SECOND_CARD_URL,
        "acquisition_method": "イベントガチャ→通常ガチャ",
        "traits": ["別データ"],
    },
    {
        "name": "Card 3 Name",
        "rarity": "SSR",
        "gamerch_url": THIRD_CARD_URL,
        "acquisition_method": "イベントガチャ→通常ガチャ",
        "traits": ["別データ"],
    },
]


def test_extract_ssr_cards_from_event_html_and_card_pages() -> None:
    def fake_fetcher(url: str) -> str:
        pages = {
            EVENT_URL: EVENT_HTML,
            FIRST_CARD_URL: FIRST_CARD_HTML,
            SECOND_CARD_URL: OTHER_CARD_HTML,
            THIRD_CARD_URL: OTHER_CARD_HTML,
        }
        return pages[url]

    assert extract_ssr_cards(EVENT_HTML, fetcher=fake_fetcher) == EXPECTED_CARDS


def test_get_ssr_cards_uses_supplied_fetcher() -> None:
    def fake_fetcher(url: str) -> str:
        pages = {
            EVENT_URL: EVENT_HTML,
            FIRST_CARD_URL: FIRST_CARD_HTML,
            SECOND_CARD_URL: OTHER_CARD_HTML,
            THIRD_CARD_URL: OTHER_CARD_HTML,
        }
        return pages[url]

    assert get_ssr_cards(EVENT_URL, fetcher=fake_fetcher) == EXPECTED_CARDS


def test_get_ssr_cards_propagates_waf_blocking() -> None:
    def blocked_fetcher(url: str) -> str:
        raise FetchBlockedError(f"blocked: {url}")

    try:
        get_ssr_cards(EVENT_URL, fetcher=blocked_fetcher)
    except FetchBlockedError as exc:
        assert "blocked" in str(exc)
    else:
        raise AssertionError("Expected FetchBlockedError")


def test_build_export_payload_keeps_full_card_info_without_image() -> None:
    payload = build_export_payload(EXPECTED_CARDS)
    assert set(payload["traits"]) == {
        "別データ",
        "勝利",
        "探求",
        "朴訥",
        "気まま",
        "宝石",
        "熱狂",
        "独創",
        "熱血",
    }
    assert payload["cards"] == EXPECTED_CARDS


def test_default_output_path_uses_event_page_id() -> None:
    assert default_output_path(EVENT_URL).name == "000001.json"


def test_resolve_browser_executable_path_uses_env_var(monkeypatch) -> None:
    monkeypatch.setenv("MAHOYAKU_BROWSER_PATH", "/usr/bin/brave-browser")
    assert resolve_browser_executable_path() == "/usr/bin/brave-browser"


def test_resolve_browser_executable_path_returns_none_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("MAHOYAKU_BROWSER_PATH", raising=False)
    assert resolve_browser_executable_path() == "/usr/bin/chromium"
