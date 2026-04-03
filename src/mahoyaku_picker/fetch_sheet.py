from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Sequence
from pathlib import Path
from urllib.parse import urlencode

from googleapiclient.http import build_http


class GoogleSheetFetchError(Exception):
    """Raised when a public Google Sheet cannot be fetched or parsed."""


def extract_gviz_json(response_text: str) -> dict[str, object]:
    prefix = "google.visualization.Query.setResponse("
    suffix = ");"

    start = response_text.find(prefix)
    if start == -1:
        raise GoogleSheetFetchError("Missing Google Visualization response wrapper.")

    start += len(prefix)
    end = response_text.rfind(suffix)
    if end == -1:
        raise GoogleSheetFetchError("Missing Google Visualization response terminator.")

    return json.loads(response_text[start:end])


def parse_google_sheet_rows(response_text: str) -> list[dict[str, str]]:
    payload = extract_gviz_json(response_text)
    table = payload["table"]
    columns = [column["label"] for column in table["cols"]]

    rows: list[dict[str, str]] = []
    for row in table["rows"]:
        values = row.get("c", [])
        parsed_row: dict[str, str] = {}
        for index, column_name in enumerate(columns):
            cell = values[index] if index < len(values) else None
            parsed_row[column_name] = "" if not cell else str(cell.get("v", ""))
        rows.append(parsed_row)

    return rows


def parse_google_sheet_table(response_text: str) -> list[dict[str, str]]:
    payload = extract_gviz_json(response_text)
    raw_rows = payload["table"]["rows"]

    if not raw_rows:
        return []

    header_cells = raw_rows[0].get("c", [])
    headers = []
    for cell in header_cells:
        if not cell:
            headers.append("")
            continue
        value = cell.get("v", "")
        headers.append("" if value is None else str(value).strip())

    # Drop empty leading/trailing header slots from sparse sheets.
    indexed_headers = [
        (index, header) for index, header in enumerate(headers) if header
    ]

    parsed_rows: list[dict[str, str]] = []
    for row in raw_rows[1:]:
        cells = row.get("c", [])
        parsed_row: dict[str, str] = {}
        for index, header in indexed_headers:
            cell = cells[index] if index < len(cells) else None
            parsed_row[header] = "" if not cell else str(cell.get("v", ""))
        parsed_rows.append(parsed_row)

    return parsed_rows


def fetch_google_sheet_tab(
    sheet_id: str,
    *,
    tab_name: str | None = None,
    gid: str | None = None,
) -> str:
    if (tab_name is None) == (gid is None):
        raise ValueError("Specify exactly one of tab_name or gid.")

    query_params = {"tqx": "out:json"}
    if tab_name is not None:
        query_params["sheet"] = tab_name
    if gid is not None:
        query_params["gid"] = gid

    query = urlencode(query_params)
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?{query}"

    http = build_http()
    response, content = http.request(url, "GET")
    if int(response.status) != 200:
        raise GoogleSheetFetchError(
            f"Unexpected response fetching public sheet tab: {response.status}"
        )

    return content.decode("utf-8")


def get_google_sheet_rows(sheet_id: str, tab_name: str) -> list[dict[str, str]]:
    return parse_google_sheet_rows(fetch_google_sheet_tab(sheet_id, tab_name=tab_name))


def get_google_sheet_table(sheet_id: str, gid: str) -> list[dict[str, str]]:
    return parse_google_sheet_table(fetch_google_sheet_tab(sheet_id, gid=gid))


def parse_sheet_id_from_url(sheet_url: str) -> str:
    marker = "/spreadsheets/d/"
    if marker not in sheet_url:
        raise GoogleSheetFetchError("Unrecognized Google Sheets URL.")

    return sheet_url.split(marker, maxsplit=1)[1].split("/", maxsplit=1)[0]


def resolve_sheet_gid(codes_rows: list[dict[str, str]], sheet_name: str) -> str:
    for row in codes_rows:
        if row.get("TYPE") == "SHEET" and row.get("NAME") == sheet_name:
            gid = row.get("CODE", "")
            if gid:
                return gid

    raise GoogleSheetFetchError(f"Could not find sheet gid for {sheet_name!r}.")


def get_leaders_rows_from_sheet_url(
    sheet_url: str,
    fetcher: Callable[..., str] = fetch_google_sheet_tab,
) -> list[dict[str, str]]:
    # Use environment variable if sheet_url is empty
    url = sheet_url.strip() if sheet_url else ""
    if not url:
        url = os.getenv("MAHOYAKU_SHEET_URL", "")
    if not url:
        raise GoogleSheetFetchError(
            "No Google Sheets URL provided. Either pass a URL or set MAHOYAKU_SHEET_URL environment variable."
        )

    sheet_id = parse_sheet_id_from_url(url)
    codes_rows = parse_google_sheet_rows(fetcher(sheet_id, tab_name="LEADERS"))
    leaders_gid = resolve_sheet_gid(codes_rows, "LEADERS")
    return parse_google_sheet_table(fetcher(sheet_id, gid=leaders_gid))


def build_leaders_export_payload(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return rows


def default_leaders_output_path() -> Path:
    return Path("data/leaders.json")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mahoyaku-picker-fetch-sheet",
        description="Fetch the LEADERS sheet and write it to data/leaders.json.",
    )
    parser.add_argument("sheet_url", help="Google Sheets URL")
    args = parser.parse_args(argv)

    rows = get_leaders_rows_from_sheet_url(args.sheet_url)
    output_path = default_leaders_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_leaders_export_payload(rows), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"leaders_rows: {len(rows)}")
    print(f"json_output: {output_path}")


if __name__ == "__main__":
    main()
