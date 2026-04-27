import os
import logging
from datetime import datetime
import google.generativeai as genai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("coach_log.txt", mode="a"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ai_coach")

# Few-shot examples that specialise the model to quantitative binary-search coaching
_FEW_SHOT = """
EXAMPLES OF CORRECT COACHING:

Example A — Easy (1–20), no guesses yet:
  analyze_range → {current_low: 1, current_high: 20, reasoning: "No guesses made; full Easy range applies."}
  suggest_guess → {optimal_guess: 10, strategy: "Midpoint of [1,20] halves the space every time.", expected_outcomes: "Too Low → [11,20]; Too High → [1,9]; Win → done!"}
  Message: "Start at 10 — the perfect midpoint! Binary search finds any number in at most 4 guesses."

Example B — Normal (1–50), guess 25 was Too High, guess 12 was Too Low:
  analyze_range → {current_low: 13, current_high: 24, reasoning: "25 Too High → max=24. 12 Too Low → min=13."}
  suggest_guess → {optimal_guess: 18, strategy: "Midpoint of [13,24] is (13+24)//2=18, splitting 12 candidates into halves.", expected_outcomes: "Too Low → [19,24] (6 left); Too High → [13,17] (5 left); Win → done!"}
  Message: "You've narrowed it to 12 numbers! Guess 18 to cut that in half — excellent work!"
"""

_SYSTEM = (
    "You are an expert coach for a number guessing game. "
    "Help the player find the secret number efficiently using binary search. "
    "You MUST call analyze_range first, then suggest_guess. "
    "After both tools complete, write a short coaching message (2–3 sentences) "
    "that is encouraging and shows the math quantitatively.\n\n"
    + _FEW_SHOT
)

_TOOL_CONFIG = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="analyze_range",
            description=(
                "Analyze the guess/feedback history and report the tightest valid range "
                "the secret must fall within, based strictly on the feedback received."
            ),
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "current_low": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Tightest lower bound, derived from 'Too Low' feedback.",
                    ),
                    "current_high": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Tightest upper bound, derived from 'Too High' feedback.",
                    ),
                    "reasoning": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Step-by-step derivation showing how each feedback narrowed the range.",
                    ),
                },
                required=["current_low", "current_high", "reasoning"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="suggest_guess",
            description=(
                "Suggest the optimal next guess — the binary-search midpoint of the valid range — "
                "and explain why it is the best move."
            ),
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "optimal_guess": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Recommended next guess (should be the midpoint of the valid range).",
                    ),
                    "strategy": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Why this guess is optimal — show the midpoint calculation explicitly.",
                    ),
                    "expected_outcomes": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="What each possible feedback (Too Low / Too High / Win) narrows the range to.",
                    ),
                },
                required=["optimal_guess", "strategy", "expected_outcomes"],
            ),
        ),
    ]
)


def _compute_true_range(
    original_low: int,
    original_high: int,
    guess_history: list,
    feedback_history: list,
) -> tuple[int, int]:
    """Derive the provably correct valid range from guess/feedback pairs."""
    low, high = original_low, original_high
    for guess, feedback in zip(guess_history, feedback_history):
        if not isinstance(guess, int):
            continue
        if feedback == "Too Low":
            low = max(low, guess + 1)
        elif feedback == "Too High":
            high = min(high, guess - 1)
    return low, high


def _handle_analyze_range(
    args: dict,
    true_low: int,
    true_high: int,
    steps: list,
) -> tuple[dict, str]:
    """Validate the AI's range call against ground truth. Returns (range_result, model_feedback)."""
    result = args
    ai_low = int(result["current_low"])
    ai_high = int(result["current_high"])

    if ai_low != true_low or ai_high != true_high:
        result["current_low"] = true_low
        result["current_high"] = true_high
        validation = "CORRECTED"
        feedback = (
            f"Range correction: your [{ai_low}, {ai_high}] → "
            f"correct range is [{true_low}, {true_high}]. "
            "Use the corrected range when calling suggest_guess."
        )
        logger.warning("Range correction | AI=[%d,%d] corrected to=[%d,%d]", ai_low, ai_high, true_low, true_high)
    else:
        validation = "OK"
        feedback = f"Range [{ai_low}, {ai_high}] is correct. Now call suggest_guess with the midpoint."

    steps.append({
        "tool": "analyze_range",
        "output": {"low": result["current_low"], "high": result["current_high"], "reasoning": result.get("reasoning", "")},
        "validation": validation,
    })
    return result, feedback


def _handle_suggest_guess(
    args: dict,
    range_result: dict | None,
    true_low: int,
    true_high: int,
    steps: list,
) -> tuple[dict, str]:
    """Validate the AI's suggested guess is within range. Returns (suggestion_result, model_feedback)."""
    result = args
    guess_val = int(result["optimal_guess"])
    current_low = range_result["current_low"] if range_result else true_low
    current_high = range_result["current_high"] if range_result else true_high

    if not (current_low <= guess_val <= current_high):
        corrected = (current_low + current_high) // 2
        result["optimal_guess"] = corrected
        validation = "CORRECTED"
        feedback = (
            f"Guess {guess_val} is outside [{current_low}, {current_high}]. "
            f"Corrected to midpoint {corrected}. Now write the coaching message."
        )
        logger.warning("Guess correction | %d outside [%d,%d] → corrected to %d", guess_val, current_low, current_high, corrected)
    else:
        result["optimal_guess"] = guess_val
        validation = "OK"
        feedback = f"Guess {guess_val} is valid. Now write a short coaching message."

    steps.append({
        "tool": "suggest_guess",
        "output": {"optimal_guess": result["optimal_guess"], "expected_outcomes": result.get("expected_outcomes", "")},
        "validation": validation,
    })
    return result, feedback


def _run_agentic_loop(chat, response, true_low: int, true_high: int) -> tuple:
    """Iterate the tool-call loop until the model returns a plain text response."""
    range_result = None
    suggestion_result = None
    final_text = ""
    steps: list = []

    for iteration in range(8):
        function_calls = [
            part.function_call
            for part in response.candidates[0].content.parts
            if part.function_call.name
        ]
        if not function_calls:
            final_text = response.text
            break

        logger.debug("Iteration=%d calls=%s", iteration, [fc.name for fc in function_calls])
        response_parts = []

        for fc in function_calls:
            name = fc.name
            args = dict(fc.args.items())

            if name == "analyze_range":
                range_result, feedback = _handle_analyze_range(args, true_low, true_high, steps)
            elif name == "suggest_guess":
                suggestion_result, feedback = _handle_suggest_guess(args, range_result, true_low, true_high, steps)
            else:
                feedback = "Unknown tool — ignored."

            response_parts.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(name=name, response={"result": feedback})
                )
            )

        response = chat.send_message(response_parts)

    return range_result, suggestion_result, final_text, steps


def _build_range_reasoning(
    guess_history: list,
    feedback_history: list,
    original_low: int,
    original_high: int,
) -> str:
    """Build a human-readable derivation of the valid range from guess/feedback pairs."""
    if not guess_history:
        return f"No guesses yet; full range [{original_low}, {original_high}] applies."
    low, high = original_low, original_high
    parts = []
    for guess, feedback in zip(guess_history, feedback_history):
        if not isinstance(guess, int):
            continue
        if feedback == "Too Low":
            new_low = max(low, guess + 1)
            if new_low > low:
                parts.append(f"{guess} Too Low → min raised to {new_low}")
                low = new_low
        elif feedback == "Too High":
            new_high = min(high, guess - 1)
            if new_high < high:
                parts.append(f"{guess} Too High → max lowered to {new_high}")
                high = new_high
    return "; ".join(parts) if parts else f"Range is [{low}, {high}]."


def _demo_coaching(
    low: int,
    high: int,
    guess_history: list,
    feedback_history: list,
    attempts_left: int,
    difficulty: str,
) -> dict:
    """
    Demo mode — runs the full agentic workflow deterministically without an API call.
    Uses the provably optimal binary-search midpoint, shows realistic agent steps.
    """
    true_low, true_high = _compute_true_range(low, high, guess_history, feedback_history)
    optimal = (true_low + true_high) // 2
    candidates = true_high - true_low + 1
    reasoning = _build_range_reasoning(guess_history, feedback_history, low, high)

    result = {
        "optimal_guess": optimal,
        "strategy": (
            f"Midpoint of [{true_low}, {true_high}]: "
            f"({true_low}+{true_high})//2 = {optimal}. "
            f"Halves the remaining {candidates} candidate{'s' if candidates != 1 else ''}."
        ),
        "expected_outcomes": (
            f"Too Low → [{optimal + 1}, {true_high}]; "
            f"Too High → [{true_low}, {optimal - 1}]; "
            "Win → done!"
        ),
        "valid_range": {"low": true_low, "high": true_high, "reasoning": reasoning},
        "coach_message": (
            f"[{difficulty}] The secret must be in [{true_low}, {true_high}] — {candidates} "
            f"candidate{'s' if candidates != 1 else ''} left. "
            f"Guess {optimal} (the exact midpoint) to cut the search space in half "
            f"no matter what feedback you get. "
            f"Binary search guarantees a win in at most "
            f"{max(1, (candidates - 1).bit_length())} more guess{'es' if candidates > 2 else ''}!"
        ),
        "steps": [
            {
                "tool": "analyze_range",
                "output": {"low": true_low, "high": true_high, "reasoning": reasoning},
                "validation": "OK",
            },
            {
                "tool": "suggest_guess",
                "output": {
                    "optimal_guess": optimal,
                    "expected_outcomes": (
                        f"Too Low → [{optimal + 1}, {true_high}]; "
                        f"Too High → [{true_low}, {optimal - 1}]"
                    ),
                },
                "validation": "OK",
            },
        ],
        "timestamp": datetime.now().isoformat(),
        "demo_mode": True,
    }
    logger.info(
        "Demo coaching | guess=%d | range=[%d,%d] | attempts_left=%d",
        optimal, true_low, true_high, attempts_left,
    )
    return result


def get_ai_coaching(
    low: int,
    high: int,
    guess_history: list,
    feedback_history: list,
    attempts_left: int,
    difficulty: str,
) -> dict:
    """
    Agentic coaching workflow.
    Set DEMO_MODE=true in .env to run without an API key (deterministic, no network call).
    Otherwise calls Gemini: Plan → Act → validate → coaching message.

    Raises ValueError  if GEMINI_API_KEY is not set and DEMO_MODE is not true.
    Raises RuntimeError if the agent completes without producing a suggestion.
    """
    if os.environ.get("DEMO_MODE", "").lower() == "true":
        return _demo_coaching(low, high, guess_history, feedback_history, attempts_left, difficulty)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Get a free key at aistudio.google.com, copy .env.example → .env, and restart."
        )

    genai.configure(api_key=api_key)
    true_low, true_high = _compute_true_range(low, high, guess_history, feedback_history)

    history_lines = [
        f"  Attempt {i + 1}: guessed {g} → {f}"
        for i, (g, f) in enumerate(zip(guess_history, feedback_history))
    ]
    history_text = "\n".join(history_lines) if history_lines else "  No guesses yet."

    user_content = (
        f"Game state:\n"
        f"  Difficulty:         {difficulty}\n"
        f"  Full range:         {low} to {high}\n"
        f"  Attempts remaining: {attempts_left}\n\n"
        f"Guess history:\n{history_text}\n\n"
        "Analyze the valid range, then suggest the optimal next guess."
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        tools=[_TOOL_CONFIG],
        system_instruction=_SYSTEM,
    )
    chat = model.start_chat()
    initial_response = chat.send_message(user_content)
    range_result, suggestion_result, final_text, steps = _run_agentic_loop(
        chat, initial_response, true_low, true_high
    )

    if suggestion_result is None:
        raise RuntimeError("AI coach did not produce a suggestion. Please try again.")

    corrections = sum(1 for s in steps if s["validation"] == "CORRECTED")
    result = {
        "optimal_guess": int(suggestion_result["optimal_guess"]),
        "strategy": suggestion_result.get("strategy", ""),
        "expected_outcomes": suggestion_result.get("expected_outcomes", ""),
        "valid_range": {
            "low": range_result["current_low"] if range_result else true_low,
            "high": range_result["current_high"] if range_result else true_high,
            "reasoning": range_result.get("reasoning", "") if range_result else "",
        },
        "coach_message": final_text,
        "steps": steps,
        "timestamp": datetime.now().isoformat(),
    }

    logger.info(
        "Coaching complete | guess=%d | range=[%d,%d] | attempts_left=%d | corrections=%d",
        result["optimal_guess"], result["valid_range"]["low"],
        result["valid_range"]["high"], attempts_left, corrections,
    )
    return result
