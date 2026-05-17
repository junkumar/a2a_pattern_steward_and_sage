"""Tests for public scenario metadata.

Runnable without a test framework:

    ./venv/bin/python demos/02_viz_comparison/test_scenarios.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "scenarios"

REQUIRED_TOP_LEVEL = {
    "title",
    "question",
    "data_summary",
    "visualization_risk",
    "data",
}
PRIVATE_ADVANTAGE_KEY = "expected_sage" + "_advantage"
PROMPT_EXPECTATION_KEY = "prompt" + "_expectation"
RUN_OBSERVATION_KEY = "run" + "_observation"
RUN_OBSERVATIONS_FILE = RUN_OBSERVATION_KEY + "s.json"
REQUIRED_ADVANTAGE = {PROMPT_EXPECTATION_KEY}
BANNED_PUBLIC_PHRASES = (
    "Pending" + " rerender",
    "Judge" + " whether",
    "llm" + "_png_judgment",
    "LLM PNG" + " judgment",
)


def scenario_paths() -> list[Path]:
    return sorted(SCENARIOS.glob("*.json"))


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_scenario_count_is_public_set() -> None:
    paths = scenario_paths()
    assert len(paths) == 6, f"expected 6 public scenarios, found {len(paths)}"


def test_required_metadata_is_present() -> None:
    for path in scenario_paths():
        data = load(path)
        missing = REQUIRED_TOP_LEVEL - set(data)
        assert not missing, f"{path.name} missing top-level keys: {sorted(missing)}"
        for key in REQUIRED_TOP_LEVEL - {"data"}:
            assert str(data[key]).strip(), f"{path.name} has empty {key}"
        if PRIVATE_ADVANTAGE_KEY not in data:
            continue
        advantage = data[PRIVATE_ADVANTAGE_KEY]
        assert isinstance(advantage, dict), f"{path.name} private advantage metadata must be object"
        missing_advantage = REQUIRED_ADVANTAGE - set(advantage)
        assert not missing_advantage, (
            f"{path.name} missing advantage keys: {sorted(missing_advantage)}"
        )
        for key in REQUIRED_ADVANTAGE:
            assert str(advantage[key]).strip(), f"{path.name} has empty {key}"
        assert RUN_OBSERVATION_KEY not in advantage, (
            f"{path.name} must not contain {RUN_OBSERVATION_KEY}; "
            f"post-hoc observations live in output/{RUN_OBSERVATIONS_FILE}"
        )


def test_public_metadata_has_no_placeholders() -> None:
    for path in scenario_paths():
        text = path.read_text()
        for phrase in BANNED_PUBLIC_PHRASES:
            assert phrase not in text, f"{path.name} contains placeholder/private phrase: {phrase}"


def test_observation_file_uses_snapshot_language() -> None:
    obs_path = ROOT / "output" / RUN_OBSERVATIONS_FILE
    if not obs_path.exists():
        return
    payload = json.loads(obs_path.read_text())
    scenarios = payload.get("scenarios", {})
    for name, observation in scenarios.items():
        assert observation.startswith("In this run, "), (
            f"{RUN_OBSERVATIONS_FILE}[{name}] should describe the checked-in snapshot"
        )
        assert "should " not in observation.lower(), (
            f"{RUN_OBSERVATIONS_FILE}[{name}] should not read like an expectation"
        )


TESTS = [
    test_scenario_count_is_public_set,
    test_required_metadata_is_present,
    test_public_metadata_has_no_placeholders,
    test_observation_file_uses_snapshot_language,
]


def main() -> int:
    failed = 0
    for test in TESTS:
        try:
            test()
            print(f"ok  {test.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
    if failed:
        print(f"\n{failed} failure(s)")
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
