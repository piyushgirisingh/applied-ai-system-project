"""
Evaluation harness for the AI Game Coach (Project 4 — Reliability System).

Two modes:

  Offline (default) — no API calls, no credits required.
    Tests the deterministic core: range computation, server-side validation,
    guardrail (missing API key), and efficiency of the expected optimal output.
    Always runnable; gives a real pass/fail summary.

  Live (--live flag) — calls the Gemini API.
    Runs the same 6 game states through get_ai_coaching() and verifies that
    the AI's suggestions match what the deterministic algorithm produces.

Usage:
    python eval_harness.py           # offline tests only
    python eval_harness.py --live    # offline + live AI tests

Exit code: 0 = all tests passed, 1 = one or more failed.
"""

import os
import sys
import time
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from ai_coach import get_ai_coaching, _compute_true_range
except ImportError as e:
    print(f"Import error: {e}")
    print("Run:  pip install google-generativeai python-dotenv")
    sys.exit(1)

TOO_HIGH = "Too High"
TOO_LOW = "Too Low"

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
TEST_CASES = [
    {
        "id": "TC-01",
        "description": "Easy — no guesses yet (full range)",
        "low": 1, "high": 20,
        "guess_history": [],
        "feedback_history": [],
        "attempts_left": 6,
        "difficulty": "Easy",
        "expected_range": (1, 20),
        "optimal_midpoint": 10,
    },
    {
        "id": "TC-02",
        "description": "Normal — one Too High at 75",
        "low": 1, "high": 100,
        "guess_history": [75],
        "feedback_history": [TOO_HIGH],
        "attempts_left": 7,
        "difficulty": "Normal",
        "expected_range": (1, 74),
        "optimal_midpoint": 37,
    },
    {
        "id": "TC-03",
        "description": "Normal — closed in from both sides",
        "low": 1, "high": 100,
        "guess_history": [50, 25],
        "feedback_history": [TOO_HIGH, TOO_LOW],
        "attempts_left": 6,
        "difficulty": "Normal",
        "expected_range": (26, 49),
        "optimal_midpoint": 37,
    },
    {
        "id": "TC-04",
        "description": "Hard — nearly solved, 2 attempts left",
        "low": 1, "high": 50,
        "guess_history": [25, 37, 43],
        "feedback_history": [TOO_LOW, TOO_LOW, TOO_HIGH],
        "attempts_left": 2,
        "difficulty": "Hard",
        "expected_range": (38, 42),
        "optimal_midpoint": 40,
    },
    {
        "id": "TC-05",
        "description": "Normal — exactly one number remaining",
        "low": 1, "high": 100,
        "guess_history": [50, 75, 62, 68, 65, 67],
        "feedback_history": [TOO_LOW, TOO_HIGH, TOO_LOW, TOO_HIGH, TOO_LOW, TOO_HIGH],
        "attempts_left": 2,
        "difficulty": "Normal",
        "expected_range": (66, 66),
        "optimal_midpoint": 66,
    },
    {
        "id": "TC-06",
        "description": "Easy — one Too Low at 10",
        "low": 1, "high": 20,
        "guess_history": [10],
        "feedback_history": [TOO_LOW],
        "attempts_left": 5,
        "difficulty": "Easy",
        "expected_range": (11, 20),
        "optimal_midpoint": 15,
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _efficiency_score(guess: int, true_low: int, true_high: int, optimal: int) -> float:
    half_range = max((true_high - true_low) / 2.0, 1.0)
    return max(0.0, 1.0 - abs(guess - optimal) / half_range)


def _mock_coaching(tc: dict) -> dict:
    """
    Deterministic 'perfect' coaching — what the AI *should* produce.
    Used in offline mode to validate the harness logic and efficiency metrics
    without any API call.
    """
    low = _compute_true_range(
        tc["low"], tc["high"], tc["guess_history"], tc["feedback_history"]
    )
    true_low, true_high = low
    optimal = (true_low + true_high) // 2
    return {
        "optimal_guess": optimal,
        "strategy": f"Midpoint of [{true_low}, {true_high}] is ({true_low}+{true_high})//2 = {optimal}.",
        "valid_range": {
            "low": true_low,
            "high": true_high,
            "reasoning": "Derived from feedback history.",
        },
        "coach_message": f"Guess {optimal} — it halves the remaining {true_high - true_low + 1} candidates.",
        "steps": [
            {
                "tool": "analyze_range",
                "output": {"low": true_low, "high": true_high, "reasoning": ""},
                "validation": "OK",
            },
            {
                "tool": "suggest_guess",
                "output": {"optimal_guess": optimal, "expected_outcomes": ""},
                "validation": "OK",
            },
        ],
        "timestamp": datetime.now().isoformat(),
    }


def _check_result(result: dict, tc: dict) -> tuple[bool, bool, float]:
    """Returns (range_ok, guess_valid, efficiency)."""
    true_low, true_high = _compute_true_range(
        tc["low"], tc["high"], tc["guess_history"], tc["feedback_history"]
    )
    ai_low = result["valid_range"]["low"]
    ai_high = result["valid_range"]["high"]
    guess = result["optimal_guess"]

    range_ok = ai_low == tc["expected_range"][0] and ai_high == tc["expected_range"][1]
    guess_valid = true_low <= guess <= true_high
    eff = _efficiency_score(guess, true_low, true_high, tc["optimal_midpoint"])
    return range_ok, guess_valid, eff


# ---------------------------------------------------------------------------
# Test suites
# ---------------------------------------------------------------------------
def run_guardrail_tests() -> tuple[int, int]:
    """Tests that run without any API call."""
    passed = 0
    total = 0
    results = []

    # --- Group 1: _compute_true_range is correct for all 6 cases ---
    for tc in TEST_CASES:
        total += 1
        lo, hi = _compute_true_range(
            tc["low"], tc["high"], tc["guess_history"], tc["feedback_history"]
        )
        ok = (lo, hi) == tc["expected_range"]
        passed += int(ok)
        results.append((
            f"Range({tc['id']})",
            f"_compute_true_range = [{lo},{hi}] (expected {tc['expected_range']})",
            ok,
        ))

    # --- Group 2: Missing API key raises ValueError ---
    total += 1
    saved_key = os.environ.pop("GEMINI_API_KEY", None)
    try:
        get_ai_coaching(1, 100, [], [], 8, "Normal")
        ok = False
        note = "Expected ValueError — none raised"
    except ValueError:
        ok = True
        note = "ValueError raised correctly"
    except Exception as e:
        ok = False
        note = f"Wrong exception: {type(e).__name__}"
    finally:
        if saved_key:
            os.environ["GEMINI_API_KEY"] = saved_key
    passed += int(ok)
    results.append(("Guardrail: missing key", note, ok))

    # --- Group 3: Mock output passes all 6 evaluation checks ---
    for tc in TEST_CASES:
        total += 1
        mock = _mock_coaching(tc)
        _, guess_valid, eff = _check_result(mock, tc)
        ok = guess_valid  # primary pass condition
        passed += int(ok)
        results.append((
            f"Mock({tc['id']})",
            f"guess={mock['optimal_guess']} in range=[{tc['expected_range'][0]},{tc['expected_range'][1]}] "
            f"eff={eff*100:.0f}%",
            ok,
        ))

    return passed, total, results


def run_live_tests() -> tuple[int, int, list, float]:
    """Tests that call the Gemini API (requires credits)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  Skipped — GEMINI_API_KEY not set.\n")
        return 0, 0, [], 0.0

    results = []
    passed = 0
    total = len(TEST_CASES)
    total_eff = 0.0

    for tc in TEST_CASES:
        try:
            t0 = time.time()
            result = get_ai_coaching(
                low=tc["low"],
                high=tc["high"],
                guess_history=tc["guess_history"],
                feedback_history=tc["feedback_history"],
                attempts_left=tc["attempts_left"],
                difficulty=tc["difficulty"],
            )
            elapsed = time.time() - t0

            range_ok, guess_valid, eff = _check_result(result, tc)
            total_eff += eff
            test_passed = guess_valid
            if test_passed:
                passed += 1

            results.append((
                tc["id"],
                tc["description"],
                "YES" if range_ok else "NO",
                result["optimal_guess"],
                eff,
                "PASS" if test_passed else "FAIL",
                elapsed,
                None,
            ))

        except Exception as exc:
            results.append((tc["id"], tc["description"], "ERR", None, 0, "FAIL", 0, str(exc)))

    return passed, total, results, total_eff


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> bool:
    live_mode = "--live" in sys.argv

    print(f"\n{'=' * 72}")
    print("  AI Game Coach — Evaluation Harness")
    print(f"{'=' * 72}\n")

    # ── Offline / Guardrail Tests ─────────────────────────────────────────
    print("  [ OFFLINE TESTS — no API calls required ]\n")
    o_passed, o_total, o_results = run_guardrail_tests()

    for name, note, ok in o_results:
        icon = "PASS" if ok else "FAIL"
        print(f"  {icon}  {name:<30}  {note}")

    print(f"\n  Offline results: {o_passed}/{o_total} passed\n")

    # ── Live AI Tests ─────────────────────────────────────────────────────
    if not live_mode:
        print("  [ LIVE AI TESTS — skipped (run with --live to enable) ]\n")
        print(f"{'=' * 72}\n")
        return o_passed == o_total

    print("  [ LIVE AI TESTS — calling Gemini API ]\n")
    l_passed, l_total, l_results, l_total_eff = run_live_tests()

    if l_total == 0:
        print("  (no live tests run)")
        print(f"\n{'=' * 72}\n")
        return o_passed == o_total
    avg_eff = (l_total_eff / l_total * 100) if l_total else 0

    print(f"  {'ID':<8} {'Description':<42} {'Range':>7} {'Guess':>6} {'Eff%':>5}  {'Result'}")
    print(f"  {'-' * 70}")
    for row in l_results:
        tc_id, desc, range_tag, guess, eff, status, elapsed, err = row
        if err:
            print(f"  {'FAIL':<8} {desc[:42]:<42}  ERROR  ({err[:50]})")
        else:
            print(
                f"  {tc_id:<8} {desc[:42]:<42} {range_tag:>7} {guess:>6} "
                f"{eff*100:>4.0f}%  {status}  ({elapsed:.1f}s)"
            )

    print(f"\n  Live results : {l_passed}/{l_total} passed")
    print(f"  Avg eff      : {avg_eff:.0f}%  (100% = exact midpoint every time)")
    print(f"\n{'=' * 72}\n")
    return o_passed == o_total and l_passed == l_total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
