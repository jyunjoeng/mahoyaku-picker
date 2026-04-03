from mahoyaku_picker.fetch_sheet import (
    build_leaders_export_payload,
    default_leaders_output_path,
    extract_gviz_json,
    get_leaders_rows_from_sheet_url,
    parse_google_sheet_table,
    parse_google_sheet_rows,
    parse_sheet_id_from_url,
    resolve_sheet_gid,
)

FAKE_SHEET_ID = "test_sheet_id_123"
FAKE_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    f"{FAKE_SHEET_ID}"
    "/edit?gid=0#gid=0"
)


LEADERS_GVIZ_RESPONSE = """/*O_o*/
google.visualization.Query.setResponse({"version":"0.6","reqId":"0","status":"ok","sig":"1073756556","table":{"cols":[{"id":"A","label":"TYPE","type":"string"},{"id":"B","label":"NAME","type":"string"},{"id":"C","label":"CODE","type":"string"}],"rows":[{"c":[{"v":"SHEET"},{"v":"LEADERS"},{"v":"681936991"}]},{"c":[{"v":"SHEET"},{"v":"ATTRIBUTES"},{"v":"325062146"}]},{"c":[{"v":"SHEET"},{"v":"CARDS"},{"v":"2068307362"}]},{"c":[{"v":"COLUMN"},{"v":"PREFIX"},{"v":"覚醒名"}]},{"c":[{"v":"COLUMN"},{"v":"CHARACTER"},{"v":"キャラ"}]},{"c":[{"v":"COLUMN"},{"v":"CHARTYPE"},{"v":"キャラタイプ"}]},{"c":[{"v":"COLUMN"},{"v":"REQUIRED"},{"v":"要求特性"}]},{"c":[{"v":"COLUMN"},{"v":"REJECTED"},{"v":"拒否特性"}]},{"c":[{"v":"COLUMN"},{"v":"GROWTH"},{"v":"成長特性"}]}],"parsedNumHeaders":1}});"""


def test_extract_gviz_json_unwraps_visualization_response() -> None:
    payload = extract_gviz_json(LEADERS_GVIZ_RESPONSE)

    assert payload["status"] == "ok"
    assert payload["table"]["cols"][0]["label"] == "TYPE"


def test_parse_google_sheet_rows_returns_list_of_dicts() -> None:
    assert parse_google_sheet_rows(LEADERS_GVIZ_RESPONSE) == [
        {"TYPE": "SHEET", "NAME": "LEADERS", "CODE": "681936991"},
        {"TYPE": "SHEET", "NAME": "ATTRIBUTES", "CODE": "325062146"},
        {"TYPE": "SHEET", "NAME": "CARDS", "CODE": "2068307362"},
        {"TYPE": "COLUMN", "NAME": "PREFIX", "CODE": "覚醒名"},
        {"TYPE": "COLUMN", "NAME": "CHARACTER", "CODE": "キャラ"},
        {"TYPE": "COLUMN", "NAME": "CHARTYPE", "CODE": "キャラタイプ"},
        {"TYPE": "COLUMN", "NAME": "REQUIRED", "CODE": "要求特性"},
        {"TYPE": "COLUMN", "NAME": "REJECTED", "CODE": "拒否特性"},
        {"TYPE": "COLUMN", "NAME": "GROWTH", "CODE": "成長特性"},
    ]


LEADERS_TAB_GVIZ_RESPONSE = """/*O_o*/
google.visualization.Query.setResponse({"version":"0.6","reqId":"0","status":"ok","sig":"1334338955","table":{"cols":[{"id":"A","label":"","type":"string"},{"id":"B","label":"","type":"string"},{"id":"C","label":"","type":"string"},{"id":"D","label":"","type":"string"},{"id":"E","label":"","type":"string"},{"id":"F","label":"","type":"string"},{"id":"G","label":"","type":"string"},{"id":"H","label":"","type":"string"},{"id":"I","label":"","type":"string"},{"id":"J","label":"","type":"string"},{"id":"K","label":"","type":"string"},{"id":"L","label":"","type":"string"},{"id":"M","label":"","type":"string"},{"id":"N","label":"","type":"string"},{"id":"O","label":"","type":"string"},{"id":"P","label":"","type":"string"}],"rows":[{"c":[null,{"v":"覚醒名"},{"v":"キャラ"},{"v":"キャラタイプ"},{"v":"要求特性G1"},{"v":"要求特性G2"},{"v":"要求特性G3"},{"v":"成長特性G"},{"v":"拒否特性G"},{"v":"拒否特性S"},{"v":"拒否特性B"},{"v":"拒否特性N"},{"v":"要求特性S1"},{"v":"要求特性S2"},{"v":"要求特性B"},{"v":"要求特性N"}]},{"c":[null,{"v":"紫"},{"v":"アーサー"},{"v":"初期"},{"v":"優雅"},{"v":"威厳"},null,{"v":"高貴"},{"v":"幸運"},{"v":"情熱"},{"v":"派手"},null,{"v":"意地悪"},{"v":"希望"},{"v":"上品"},null]},{"c":[null,{"v":"白"},{"v":"ミスラ"},{"v":"初期"},{"v":"威厳"},{"v":"勇気"},null,{"v":"神聖"},{"v":"愛情"},{"v":"古風"},{"v":"陽気"},null,{"v":"純粋"},{"v":"堅実"},{"v":"清潔"},null]}],"parsedNumHeaders":0}});"""


def test_parse_google_sheet_table_uses_first_row_as_headers() -> None:
    assert parse_google_sheet_table(LEADERS_TAB_GVIZ_RESPONSE) == [
        {
            "覚醒名": "紫",
            "キャラ": "アーサー",
            "キャラタイプ": "初期",
            "要求特性G1": "優雅",
            "要求特性G2": "威厳",
            "要求特性G3": "",
            "成長特性G": "高貴",
            "拒否特性G": "幸運",
            "拒否特性S": "情熱",
            "拒否特性B": "派手",
            "拒否特性N": "",
            "要求特性S1": "意地悪",
            "要求特性S2": "希望",
            "要求特性B": "上品",
            "要求特性N": "",
        },
        {
            "覚醒名": "白",
            "キャラ": "ミスラ",
            "キャラタイプ": "初期",
            "要求特性G1": "威厳",
            "要求特性G2": "勇気",
            "要求特性G3": "",
            "成長特性G": "神聖",
            "拒否特性G": "愛情",
            "拒否特性S": "古風",
            "拒否特性B": "陽気",
            "拒否特性N": "",
            "要求特性S1": "純粋",
            "要求特性S2": "堅実",
            "要求特性B": "清潔",
            "要求特性N": "",
        },
    ]


def test_parse_sheet_id_from_url_extracts_spreadsheet_id() -> None:
    assert parse_sheet_id_from_url(FAKE_SHEET_URL) == FAKE_SHEET_ID


def test_resolve_sheet_gid_looks_up_sheet_name_in_codes_sheet() -> None:
    codes_rows = parse_google_sheet_rows(LEADERS_GVIZ_RESPONSE)

    assert resolve_sheet_gid(codes_rows, "LEADERS") == "681936991"


def test_get_leaders_rows_from_sheet_url_uses_codes_sheet_then_gid_table() -> None:
    def fake_fetcher(
        sheet_id: str,
        *,
        tab_name: str | None = None,
        gid: str | None = None,
    ) -> str:
        assert sheet_id == FAKE_SHEET_ID
        if tab_name == "LEADERS":
            return LEADERS_GVIZ_RESPONSE
        if gid == "681936991":
            return LEADERS_TAB_GVIZ_RESPONSE
        raise AssertionError(f"unexpected fetch args: {sheet_id=} {tab_name=} {gid=}")

    rows = get_leaders_rows_from_sheet_url(FAKE_SHEET_URL, fetcher=fake_fetcher)

    assert rows == parse_google_sheet_table(LEADERS_TAB_GVIZ_RESPONSE)


def test_build_leaders_export_payload_returns_rows() -> None:
    rows = parse_google_sheet_table(LEADERS_TAB_GVIZ_RESPONSE)
    assert build_leaders_export_payload(rows) == rows


def test_default_leaders_output_path_targets_data_directory() -> None:
    assert str(default_leaders_output_path()) == "data/leaders.json"
