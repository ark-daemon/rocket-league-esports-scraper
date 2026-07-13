"""Golden HTML fixtures for Rocket League Liquipedia parsers."""

from rocketleague_scraper.parsers.liquipedia_parser import (
    parse_rosters,
    parse_tournament_page,
    table_rows,
)


TOURNAMENT_HTML = """
<html>
  <h1 class="firstHeading">RLCS 2026 - Europe Open 1</h1>
  <table class="infobox">
    <tr><td>Prize Pool:</td><td>$100,000</td></tr>
    <tr><td>Start Date:</td><td>2026-01-10</td></tr>
  </table>
  <p>Double elimination bracket for EU region.</p>
</html>
"""

ROSTER_HTML = """
<html><body>
<table>
  <tr><th>ID</th><th>Name</th><th>Join Date</th></tr>
  <tr><td>Firstkiller</td><td>Jason Corral</td><td>2025-01-01</td></tr>
  <tr><td>Sypical</td><td>Caden Pellegrin</td><td>2025-02-01</td></tr>
</table>
<table>
  <tr><th>ID</th><th>Role</th></tr>
  <tr><td>CoachPerson</td><td>Coach</td></tr>
</table>
</body></html>
"""


def test_table_rows_maps_headers() -> None:
    rows = table_rows("<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>")
    assert rows == [{"a": "1", "b": "2"}]


def test_parse_tournament_page_extracts_name_and_prize() -> None:
    row = parse_tournament_page(TOURNAMENT_HTML, "Rocket_League_Championship_Series/2026")
    assert "RLCS" in (row["name"] or "")
    assert row["prize_pool_total"] == 100000.0
    assert row["source"] == "liquipedia"


def test_parse_rosters_separates_players_and_staff() -> None:
    rosters, staff, transfers = parse_rosters(ROSTER_HTML, team_name="Example")
    assert len(rosters) >= 2
    assert any(r.get("player_ign") == "Firstkiller" for r in rosters)
    assert any(s.get("name") == "CoachPerson" for s in staff)
    assert transfers == []
