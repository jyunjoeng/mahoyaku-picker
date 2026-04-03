from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Sequence
from pathlib import Path


GOLD_REQUIRED_FIELDS = ("要求特性G1", "要求特性G2", "要求特性G3")
SILVER_REQUIRED_FIELDS = ("要求特性S1", "要求特性S2")
BRONZE_REQUIRED_FIELDS = ("要求特性B",)
ANY_REQUIRED_FIELDS = (
    "要求特性G1",
    "要求特性G2",
    "要求特性G3",
    "要求特性S1",
    "要求特性S2",
    "要求特性B",
    "要求特性N",
)
REJECTED_FIELDS = ("拒否特性G", "拒否特性S", "拒否特性B", "拒否特性N")
FIELD_BONUS_ATTRIBUTES: list[str] = []


def _non_empty_values(leader: dict[str, str], fields: Iterable[str]) -> list[str]:
    return [leader.get(field, "") for field in fields if leader.get(field, "")]


def _count_matches(values: Iterable[str], bonus_values: set[str]) -> int:
    return sum(1 for value in values if value in bonus_values)


def _highlight(values: Iterable[str], bonus_values: set[str]) -> str:
    rendered = []
    for value in values:
        rendered.append(f"***{value}***" if value in bonus_values else value)
    return ", ".join(rendered)


def rank_leaders(
    leaders: list[dict[str, str]],
    event_bonus: dict[str, list[str]],
) -> list[dict[str, object]]:
    event_bonus_attributes = set(event_bonus.get("event", []))
    field_bonus = set(event_bonus.get("field", []))
    rejected_event_bonus = event_bonus_attributes | field_bonus

    scored: list[dict[str, object]] = []
    for leader in leaders:
        metrics = {
            "gold_required_matches": _count_matches(
                _non_empty_values(leader, GOLD_REQUIRED_FIELDS),
                event_bonus_attributes,
            ),
            "silver_required_matches": _count_matches(
                _non_empty_values(leader, SILVER_REQUIRED_FIELDS),
                event_bonus_attributes,
            ),
            "field_bonus_matches": _count_matches(
                _non_empty_values(leader, ANY_REQUIRED_FIELDS),
                field_bonus,
            ),
            "bronze_required_matches": _count_matches(
                _non_empty_values(leader, BRONZE_REQUIRED_FIELDS),
                event_bonus_attributes,
            ),
        }

        scored.append(
            {
                "leader": leader,
                "metrics": metrics,
                "has_bonus_gold_growth": leader.get("成長特性G", "")
                in event_bonus_attributes,
                "has_rejected_event_bonus": any(
                    value in rejected_event_bonus
                    for value in _non_empty_values(leader, REJECTED_FIELDS)
                ),
            }
        )

    scored.sort(
        key=lambda entry: (
            -entry["metrics"]["gold_required_matches"],
            -entry["metrics"]["silver_required_matches"],
            -entry["metrics"]["field_bonus_matches"],
            -entry["metrics"]["bronze_required_matches"],
        )
    )

    promoted = [entry for entry in scored if entry["has_bonus_gold_growth"]]
    middle = [
        entry
        for entry in scored
        if not entry["has_bonus_gold_growth"] and not entry["has_rejected_event_bonus"]
    ]
    demoted = [entry for entry in scored if entry["has_rejected_event_bonus"]]
    final_ranked = promoted + middle + demoted

    previous_tuple: tuple[int, int, int, int] | None = None
    previous_rank = 0
    for index, entry in enumerate(final_ranked, start=1):
        metrics = entry["metrics"]
        score_tuple = (
            metrics["gold_required_matches"],
            metrics["silver_required_matches"],
            metrics["field_bonus_matches"],
            metrics["bronze_required_matches"],
        )
        if score_tuple == previous_tuple:
            entry["rank"] = previous_rank
        else:
            entry["rank"] = index
            previous_rank = index
            previous_tuple = score_tuple

    return final_ranked


def build_event_bonus(event_payload: dict[str, object]) -> dict[str, list[str]]:
    return {
        "event": list(event_payload.get("traits", [])),
        "field": list(FIELD_BONUS_ATTRIBUTES),
    }


def render_ranked_leaders_table(
    ranked_leaders: list[dict[str, object]],
    event_bonus: dict[str, list[str]],
) -> str:
    all_bonus = set(event_bonus.get("event", [])) | set(event_bonus.get("field", []))

    headers = [
        "Rank",
        "Leader",
        "Character",
        "Type",
        "Gold Required",
        "Silver Required",
        "Bronze Required",
        "Growth G",
        "Rejected",
    ]
    rows = [headers, ["---"] * len(headers)]

    for entry in ranked_leaders:
        leader = entry["leader"]
        rows.append(
            [
                str(entry["rank"]),
                leader.get("覚醒名", ""),
                leader.get("キャラ", ""),
                leader.get("キャラタイプ", ""),
                _highlight(_non_empty_values(leader, GOLD_REQUIRED_FIELDS), all_bonus),
                _highlight(
                    _non_empty_values(leader, SILVER_REQUIRED_FIELDS), all_bonus
                ),
                _highlight(
                    _non_empty_values(leader, BRONZE_REQUIRED_FIELDS), all_bonus
                ),
                _highlight(_non_empty_values(leader, ("成長特性G",)), all_bonus),
                _highlight(_non_empty_values(leader, REJECTED_FIELDS), all_bonus),
            ]
        )

    return "\n".join(f"| {' | '.join(row)} |" for row in rows)


def rank_event(
    event_payload: dict[str, object],
    leaders: list[dict[str, str]],
) -> list[dict[str, object]]:
    return rank_leaders(leaders, build_event_bonus(event_payload))


def default_ranking_output_path(event_json_path: Path) -> Path:
    return Path("data/rankings") / f"{event_json_path.stem}.md"


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mahoyaku-picker-rank",
        description="Rank leaders for an event using fetched event and leaders data.",
    )
    parser.add_argument("event_json", help="Path to event JSON from fetch_event")
    parser.add_argument(
        "--leaders-json",
        default="data/leaders.json",
        help="Path to parsed leaders JSON",
    )
    args = parser.parse_args(argv)

    event_payload = json.loads(Path(args.event_json).read_text(encoding="utf-8"))
    event_json_path = Path(args.event_json)
    leaders = json.loads(Path(args.leaders_json).read_text(encoding="utf-8"))
    ranked = rank_event(event_payload, leaders)
    rendered_table = render_ranked_leaders_table(
        ranked, build_event_bonus(event_payload)
    )

    output_path = default_ranking_output_path(event_json_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_table + "\n", encoding="utf-8")

    print(rendered_table)
    print(f"markdown_output: {output_path}")


if __name__ == "__main__":
    main()
