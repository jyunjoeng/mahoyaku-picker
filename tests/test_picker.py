from pathlib import Path

from mahoyaku_picker.picker import (
    FIELD_BONUS_ATTRIBUTES,
    build_event_bonus,
    default_ranking_output_path,
    rank_leaders,
    render_ranked_leaders_table,
)


LEADERS = [
    {
        "覚醒名": "A",
        "キャラ": "Alpha",
        "キャラタイプ": "初期",
        "要求特性G1": "g1",
        "要求特性G2": "g2",
        "要求特性G3": "",
        "成長特性G": "growth_x",
        "拒否特性G": "",
        "拒否特性S": "",
        "拒否特性B": "",
        "拒否特性N": "",
        "要求特性S1": "s1",
        "要求特性S2": "",
        "要求特性B": "b1",
        "要求特性N": "n1",
    },
    {
        "覚醒名": "B",
        "キャラ": "Beta",
        "キャラタイプ": "初期",
        "要求特性G1": "g1",
        "要求特性G2": "",
        "要求特性G3": "",
        "成長特性G": "gold_bonus_growth",
        "拒否特性G": "",
        "拒否特性S": "",
        "拒否特性B": "",
        "拒否特性N": "",
        "要求特性S1": "s1",
        "要求特性S2": "s2",
        "要求特性B": "b1",
        "要求特性N": "",
    },
    {
        "覚醒名": "C",
        "キャラ": "Gamma",
        "キャラタイプ": "初期",
        "要求特性G1": "g1",
        "要求特性G2": "",
        "要求特性G3": "",
        "成長特性G": "growth_y",
        "拒否特性G": "",
        "拒否特性S": "",
        "拒否特性B": "",
        "拒否特性N": "",
        "要求特性S1": "s1",
        "要求特性S2": "",
        "要求特性B": "b2",
        "要求特性N": "",
    },
    {
        "覚醒名": "D",
        "キャラ": "Delta",
        "キャラタイプ": "初期",
        "要求特性G1": "g1",
        "要求特性G2": "g2",
        "要求特性G3": "",
        "成長特性G": "growth_z",
        "拒否特性G": "gold_reject",
        "拒否特性S": "",
        "拒否特性B": "",
        "拒否特性N": "",
        "要求特性S1": "",
        "要求特性S2": "",
        "要求特性B": "",
        "要求特性N": "",
    },
    {
        "覚醒名": "E",
        "キャラ": "Echo",
        "キャラタイプ": "初期",
        "要求特性G1": "",
        "要求特性G2": "",
        "要求特性G3": "",
        "成長特性G": "growth_none",
        "拒否特性G": "",
        "拒否特性S": "",
        "拒否特性B": "",
        "拒否特性N": "",
        "要求特性S1": "",
        "要求特性S2": "",
        "要求特性B": "",
        "要求特性N": "",
    },
    {
        "覚醒名": "F",
        "キャラ": "Foxtrot",
        "キャラタイプ": "初期",
        "要求特性G1": "",
        "要求特性G2": "",
        "要求特性G3": "",
        "成長特性G": "growth_none",
        "拒否特性G": "",
        "拒否特性S": "",
        "拒否特性B": "",
        "拒否特性N": "",
        "要求特性S1": "",
        "要求特性S2": "",
        "要求特性B": "",
        "要求特性N": "",
    },
]

EVENT_BONUS = {
    "event": ["g1", "g2", "gold_bonus_growth", "gold_reject", "s1", "s2", "b1"],
    "field": [],
}


def test_rank_leaders_applies_sorting_ties_and_stable_moves() -> None:
    ranked = rank_leaders(LEADERS, EVENT_BONUS)

    assert [entry["leader"]["キャラ"] for entry in ranked] == [
        "Beta",
        "Alpha",
        "Gamma",
        "Echo",
        "Foxtrot",
        "Delta",
    ]

    assert [entry["rank"] for entry in ranked] == [1, 2, 3, 4, 4, 6]


def test_rank_leaders_includes_metrics_and_flags() -> None:
    ranked = rank_leaders(LEADERS, EVENT_BONUS)
    beta = ranked[0]
    delta = ranked[-1]

    assert beta["metrics"] == {
        "gold_required_matches": 1,
        "silver_required_matches": 2,
        "field_bonus_matches": 0,
        "bronze_required_matches": 1,
    }
    assert beta["has_bonus_gold_growth"] is True
    assert beta["has_rejected_event_bonus"] is False

    assert delta["has_rejected_event_bonus"] is True


def test_render_ranked_leaders_table_highlights_bonus_attributes() -> None:
    table = render_ranked_leaders_table(rank_leaders(LEADERS, EVENT_BONUS), EVENT_BONUS)

    lines = table.splitlines()
    assert lines[2].startswith("| 1 |")
    assert "***g1***" in table
    assert "***g2***" in table
    assert "***s1***" in table
    assert "***b1***" in table
    assert "| Rank | Leader | Character | Type |" in table
    assert "| --- | --- | --- | --- |" in table


def test_build_event_bonus_uses_event_traits_as_gold_and_hardcoded_empty_field() -> (
    None
):
    event_payload = {
        "traits": ["a", "b"],
        "cards": [],
    }

    assert FIELD_BONUS_ATTRIBUTES == []
    assert build_event_bonus(event_payload) == {
        "event": ["a", "b"],
        "field": [],
    }


def test_default_ranking_output_path_mirrors_event_json_name() -> None:
    assert default_ranking_output_path(Path("data/events/973883.json")) == Path(
        "data/rankings/973883.md"
    )
