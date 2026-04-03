from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from mahoyaku_picker.fetch_event import (
    build_export_payload,
    default_output_path,
    get_ssr_cards,
)
from mahoyaku_picker.fetch_sheet import (
    build_leaders_export_payload,
    default_leaders_output_path,
    get_leaders_rows_from_sheet_url,
)
from mahoyaku_picker.picker import rank_event, render_ranked_leaders_table


def _write_event_json(event_url: str) -> dict[str, object]:
    output_path = default_output_path(event_url)
    if output_path.exists():
        return json.loads(output_path.read_text(encoding="utf-8"))

    cards = get_ssr_cards(event_url)
    payload = build_export_payload(cards)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def _write_leaders_json(sheet_url: str) -> list[dict[str, str]]:
    output_path = default_leaders_output_path()
    if output_path.exists():
        return json.loads(output_path.read_text(encoding="utf-8"))

    leaders = get_leaders_rows_from_sheet_url(sheet_url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_leaders_export_payload(leaders), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return leaders


def _build_event_bonus(event_payload: dict[str, object]) -> dict[str, list[str]]:
    return {
        "event": list(event_payload.get("traits", [])),
        "field": [],
    }


def _ranked_leaders_dataframe(
    ranked: list[dict[str, object]],
    event_bonus: dict[str, list[str]],
) -> pd.io.formats.style.Styler:
    bonus_values = set(event_bonus.get("event", [])) | set(event_bonus.get("field", []))

    def value_or_empty(leader: dict[str, str], key: str) -> str:
        return leader.get(key, "")

    rows: list[dict[str, object]] = []
    for entry in sorted(
        ranked,
        key=lambda item: (
            item["rank"],
            item["leader"].get("キャラ", ""),
            item["leader"].get("覚醒名", ""),
        ),
    ):
        leader = entry["leader"]
        rows.append(
            {
                "Rank": entry["rank"],
                "Leader": value_or_empty(leader, "覚醒名"),
                "Character": value_or_empty(leader, "キャラ"),
                "Type": value_or_empty(leader, "キャラタイプ"),
                "G1": value_or_empty(leader, "要求特性G1"),
                "G2": value_or_empty(leader, "要求特性G2"),
                "G3": value_or_empty(leader, "要求特性G3"),
                "S1": value_or_empty(leader, "要求特性S1"),
                "S2": value_or_empty(leader, "要求特性S2"),
                "B": value_or_empty(leader, "要求特性B"),
                "N": value_or_empty(leader, "要求特性N"),
                "Growth G": value_or_empty(leader, "成長特性G"),
                "Reject G": value_or_empty(leader, "拒否特性G"),
                "Reject S": value_or_empty(leader, "拒否特性S"),
                "Reject B": value_or_empty(leader, "拒否特性B"),
                "Reject N": value_or_empty(leader, "拒否特性N"),
            }
        )

    frame = pd.DataFrame(rows)
    highlight_columns = [
        "G1",
        "G2",
        "G3",
        "S1",
        "S2",
        "B",
        "N",
        "Growth G",
        "Reject G",
        "Reject S",
        "Reject B",
        "Reject N",
    ]

    def highlight_cell(value: object) -> str:
        if value and str(value) in bonus_values:
            # Semi-transparent gold works in both light and dark modes
            return "background-color: rgba(255, 193, 7, 0.3); font-weight: 700;"
        return ""

    return frame.style.map(highlight_cell, subset=highlight_columns)


st.set_page_config(page_title="Mahoyaku Picker", layout="wide")
st.title("Mahoyaku Picker")

with st.form("picker_form"):
    event_url = st.text_input("Event Page URL")
    sheet_url = st.text_input("Google Sheets URL")
    submitted = st.form_submit_button("Submit")

if submitted:
    if not event_url.strip():
        st.error("Event URL is required.")
    else:
        with st.spinner("Fetching event, leaders, and ranking data..."):
            try:
                event_payload = _write_event_json(event_url.strip())
                leaders = _write_leaders_json(sheet_url.strip())
                ranked = rank_event(event_payload, leaders)
                event_bonus = _build_event_bonus(event_payload)
                markdown_table = render_ranked_leaders_table(
                    ranked,
                    event_bonus,
                )
            except Exception as exc:  # pragma: no cover - thin UI wrapper
                st.exception(exc)
            else:
                st.subheader("Event SSR Cards")
                for card in event_payload["cards"]:
                    st.markdown(f"**{card['name']}**")
                    st.markdown(", ".join(card["traits"]))

                st.subheader("Leader Ranking")
                st.dataframe(
                    _ranked_leaders_dataframe(ranked, event_bonus),
                    use_container_width=True,
                    hide_index=True,
                )

                with st.expander("Markdown Export Preview"):
                    st.markdown(markdown_table)
