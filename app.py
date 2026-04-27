import os
import random
import logging
import streamlit as st
from logic_utils import check_guess  #FIX: Moved check_guess import from app.py to logic_utils.py together with Copilot.

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from ai_coach import get_ai_coaching
    AI_AVAILABLE = bool(os.environ.get("GEMINI_API_KEY"))
except ImportError:
    AI_AVAILABLE = False

_log = logging.getLogger("app")


def get_range_for_difficulty(difficulty: str):
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 50
    return 1, 100


def parse_guess(raw: str):
    if raw is None:
        return False, None, "Enter a guess."

    if raw == "":
        return False, None, "Enter a guess."

    try:
        if "." in raw:
            value = int(float(raw))
        else:
            value = int(raw)
    except Exception:
        return False, None, "That is not a number."

    return True, value, None


def update_score(current_score: int, outcome: str, attempt_number: int):
    if outcome == "Win":
        points = 100 - 10 * (attempt_number + 1)
        if points < 10:
            points = 10
        return current_score + points

    if outcome == "Too High":
        if attempt_number % 2 == 0:
            return current_score + 5
        return current_score - 5

    if outcome == "Too Low":
        return current_score - 5

    return current_score


st.set_page_config(page_title="Glitchy Guesser", page_icon="🎮")

st.title("🎮 Game Glitch Investigator")
st.caption("An AI-generated guessing game. Something is off.")

st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Normal", "Hard"],
    index=1,
)

attempt_limit_map = {
    "Easy": 6,
    "Normal": 8,
    "Hard": 5,
}
attempt_limit = attempt_limit_map[difficulty]

low, high = get_range_for_difficulty(difficulty)

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

if "secret" not in st.session_state:
    st.session_state.secret = random.randint(low, high)

if "attempts" not in st.session_state:
    st.session_state.attempts = 0

if "score" not in st.session_state:
    st.session_state.score = 0

if "status" not in st.session_state:
    st.session_state.status = "playing"

if "history" not in st.session_state:
    st.session_state.history = []

if "feedback_history" not in st.session_state:
    st.session_state.feedback_history = []

if "ai_log" not in st.session_state:
    st.session_state.ai_log = []

if "last_coaching" not in st.session_state:
    st.session_state.last_coaching = None

if "agent_steps" not in st.session_state:
    st.session_state.agent_steps = []

st.subheader("Make a guess")

st.info(
    f"Guess a number between 1 and 100. "
    f"Attempts left: {attempt_limit - st.session_state.attempts}"
)

with st.expander("Developer Debug Info"):
    st.write("Secret:", st.session_state.secret)
    st.write("Attempts:", st.session_state.attempts)
    st.write("Score:", st.session_state.score)
    st.write("Difficulty:", difficulty)
    st.write("History:", st.session_state.history)

raw_guess = st.text_input(
    "Enter your guess:",
    key=f"guess_input_{difficulty}"
)

col1, col2, col3 = st.columns(3)
with col1:
    submit = st.button("Submit Guess 🚀")
with col2:
    new_game = st.button("New Game 🔁")
with col3:
    show_hint = st.checkbox("Show hint", value=True)

if new_game:
    #FIX: New Game button is explicitly designed to reset all game state variables.
    # This was added per collaboration to avoid stale state after a previous win/loss.
    st.session_state.attempts = 0
    st.session_state.secret = random.randint(low, high)
    st.session_state.score = 0
    st.session_state.status = "playing"
    st.session_state.history = []
    st.session_state.feedback_history = []
    st.session_state.ai_log = []
    st.session_state.last_coaching = None
    st.session_state.agent_steps = []
    st.success("New game started.")
    st.rerun()

if st.session_state.status != "playing":
    if st.session_state.status == "won":
        st.success("You already won. Start a new game to play again.")
    else:
        st.error("Game over. Start a new game to try again.")
    st.stop()

if submit:
    st.session_state.attempts += 1

    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.session_state.history.append(raw_guess)
        st.error(err)
    else:
        st.session_state.history.append(guess_int)

        if st.session_state.attempts % 2 == 0:
            secret = str(st.session_state.secret)
        else:
            secret = st.session_state.secret

        outcome, message = check_guess(guess_int, secret)
        st.session_state.feedback_history.append(outcome)

        if show_hint:
            st.warning(message)

        st.session_state.score = update_score(
            current_score=st.session_state.score,
            outcome=outcome,
            attempt_number=st.session_state.attempts,
        )

        if outcome == "Win":
            st.balloons()
            st.session_state.status = "won"
            st.success(
                f"You won! The secret was {st.session_state.secret}. "
                f"Final score: {st.session_state.score}"
            )
        else:
            if st.session_state.attempts >= attempt_limit:
                st.session_state.status = "lost"
                st.error(
                    f"Out of attempts! "
                    f"The secret was {st.session_state.secret}. "
                    f"Score: {st.session_state.score}"
                )

st.divider()
st.subheader("🤖 AI Game Coach")

if not AI_AVAILABLE:
    if not os.environ.get("GEMINI_API_KEY"):
        st.warning(
            "AI Coach is disabled. Add `GEMINI_API_KEY` to a `.env` file "
            "(see `.env.example`) and restart the app."
        )
    else:
        st.error("Install the `google-generativeai` package: `pip install google-generativeai`")
else:
    valid_guesses = [g for g in st.session_state.history if isinstance(g, int)]

    if os.environ.get("DEMO_MODE", "").lower() == "true":
        st.info("🎭 **Demo Mode** — AI responses use the deterministic binary-search algorithm. No API call is made.")

    if st.button("Ask AI Coach for a Hint 🤖", disabled=(st.session_state.status != "playing")):
        with st.spinner("AI coach is analyzing your game…"):
            try:
                coaching = get_ai_coaching(
                    low=low,
                    high=high,
                    guess_history=valid_guesses,
                    feedback_history=st.session_state.feedback_history,
                    attempts_left=attempt_limit - st.session_state.attempts,
                    difficulty=difficulty,
                )
                st.session_state.last_coaching = coaching
                st.session_state.agent_steps = coaching.get("steps", [])
                st.session_state.ai_log.append({
                    "attempt": st.session_state.attempts,
                    "suggestion": coaching["optimal_guess"],
                    "range": f"[{coaching['valid_range']['low']}, {coaching['valid_range']['high']}]",
                })
                _log.info(
                    "AI coach invoked | attempt=%d | suggestion=%d",
                    st.session_state.attempts,
                    coaching["optimal_guess"],
                )
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                _log.error("AI coaching failed: %s", e, exc_info=True)
                st.error(f"AI coach error: {e}")

    if st.session_state.last_coaching:
        coaching = st.session_state.last_coaching
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("💡 Suggested Guess", coaching["optimal_guess"])
            st.caption(
                f"Valid range: **{coaching['valid_range']['low']}** – "
                f"**{coaching['valid_range']['high']}**"
            )
        with col_b:
            st.markdown("**Strategy**")
            st.write(coaching.get("strategy", ""))

        if coaching.get("coach_message"):
            st.info(coaching["coach_message"])

        with st.expander("🔍 Agent Reasoning Steps"):
            for i, step in enumerate(st.session_state.agent_steps, start=1):
                icon = "✅" if step["validation"] == "OK" else "⚠️ Corrected"
                out = step["output"]
                if step["tool"] == "analyze_range":
                    st.markdown(
                        f"**Step {i} — `analyze_range`** {icon}  \n"
                        f"Range: **[{out['low']}, {out['high']}]**  \n"
                        f"Reasoning: {out.get('reasoning', '')}"
                    )
                elif step["tool"] == "suggest_guess":
                    st.markdown(
                        f"**Step {i} — `suggest_guess`** {icon}  \n"
                        f"Optimal guess: **{out['optimal_guess']}**  \n"
                        f"Expected outcomes: {out.get('expected_outcomes', '')}"
                    )

    if st.session_state.ai_log:
        with st.expander("📋 AI Suggestion Log (Reliability)"):
            for entry in st.session_state.ai_log:
                st.write(
                    f"After attempt **{entry['attempt']}**: "
                    f"suggested **{entry['suggestion']}** "
                    f"(valid range {entry['range']})"
                )

st.divider()
st.caption("Built by an AI that claims this code is production-ready.")
