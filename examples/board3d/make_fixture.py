"""Export one real computer action, through the server's public projection only."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from traveler_quartet.match.session import Session, public_events, watched
from traveler_quartet.match.tournament import COMPUTERS
from traveler_quartet.rules.engine import actor, apply, legal_actions, new_game


def make_fixture():
    session = Session(new_game(seed=1, player_count=4), ("normal",) * 4, {})
    for _ in range(2000):
        before = watched(session)
        state = session.state
        answer = COMPUTERS[session.seats[actor(state)]](state, legal_actions(state))
        action = answer[0] if isinstance(answer, tuple) else answer
        session.state, events = apply(state, action)
        session.revision += 1
        session.log.extend((state.round, event, session.revision) for event in events)
        after = watched(session)
        rows = public_events(session, since=before["log_length"], until=after["log_length"])
        moves = [event for event in rows if event["kind"] == "moved"]
        if _suitable(moves, before, after):
            return {"before": before, "after": after, "events": rows}
        if session.state.over:
            break
    raise RuntimeError("No single multi-square computer walk found in the fixture game")


def _suitable(moves, before, after):
    if len(moves) != 1:
        return False
    move = moves[0]
    data, seat = move["data"], move["player"]
    return (data["travel"] == "walk" and 2 <= data["steps"] <= 8
            and before["view"]["players"][seat]["position"] == data["from"]
            and after["view"]["players"][seat]["position"] == data["to"])


if __name__ == "__main__":
    Path(__file__).with_name("fixture.json").write_text(
        json.dumps(make_fixture(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
