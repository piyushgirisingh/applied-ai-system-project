def get_range_for_difficulty(difficulty: str):
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 50
    if difficulty == "Hard":
        return 1, 100
    return 1, 100


def parse_guess(raw: str):
    # FIX: parse_guess normalizes numeric input (string/float) before comparison.
    # This avoids out-of-bounds behavior when secret is sometimes a string by design.
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


def check_guess(guess, secret):
    # FIX: Refactored logic into logic_utils.py using Copilot Agent mode for compatibility.
    # From game flow, `secret` can be either int or str (glitch), so normalize before compare.
    # This also solves out-of-bounds string comparison issues (e.g., "100" vs 50).
    normalized_guess = guess
    normalized_secret = secret

    if isinstance(guess, str):
        try:
            normalized_guess = int(
                float(guess)) if "." in guess else int(guess)
        except (ValueError, TypeError):
            normalized_guess = guess

    if isinstance(secret, str):
        try:
            normalized_secret = int(
                float(secret)) if "." in secret else int(secret)
        except (ValueError, TypeError):
            normalized_secret = secret

    if normalized_guess == normalized_secret:
        return "Win", "🎉 Correct!"

    try:
        if normalized_guess > normalized_secret:
            return "Too High", "📉 Go LOWER!"
        return "Too Low", "📈 Go HIGHER!"
    except TypeError:
        # Fall back to string compare for truly non-comparable values.
        g = str(guess)
        s = str(secret)

        if g == s:
            return "Win", "🎉 Correct!"
        if g > s:
            return "Too High", "📉 Go LOWER!"
        return "Too Low", "📈 Go HIGHER!"


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
