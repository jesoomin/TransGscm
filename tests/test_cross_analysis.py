from pathlib import Path

from chatui.cross_analysis import analyze_pilot_folder


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "cross_analysis" / "pilot"


def test_reports_service_store_and_mapper_duplicates_separately() -> None:
    kinds = {group.kind for group in analyze_pilot_folder(FIXTURE_ROOT).duplicate_groups}
    assert {"SERVICE_METHOD_BODY", "STORE_METHOD_BODY", "MAPPER_STATEMENT_SQL"} <= kinds
