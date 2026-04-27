# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

- What did the game look like the first time you ran it? 

the game looked like a guess game where i had to find a correct number predicted by the computer.

- List at least two concrete bugs you noticed at the start  
  (for example: "the secret number kept changing" or "the hints were backwards").
  it prints " Go lower" for the number I enter even the correct number is higher.

  the attempts allowed says 8 but there is only 7 attempts that i was able to do.

  the game says to "Go Lower" when I guess the number as 1 so technically I cannot go lower than it as the games says to guess the number between 1 and 100.

  The New Game button is not working properly as I cannot submit a new guess after finishing a game, it just resets the attempts but does not run the game.

  When i guessed the number as 768, it still said to go higher which is a out of bound number. It should say to go lower



  

---

## 2. How did you use AI as a teammate?

- Which AI tools did you use on this project (for example: ChatGPT, Gemini, Copilot)?

ChatGPT, Copilot

- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).

One suggestion it gave was about the new game button, i verified that the state of game was still the same even after finishing a game which made the new game button not work.

- Give one example of an AI suggestion that was incorrect or misleading (including what the AI suggested and how you verified the result).

--- I asked the copilot agent to fix a part of code in my app.py file but instead it fixed more stuff that I did not want to be fixed.

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?

I went on the localhost of my game and played the buggy part to verify if it was fixed. I also ran some tests to see if it failed or not.

- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.

  I ran pytest -q and before the fixings one or more tests failed, but after fixing all the problems, all tests passed


- Did AI help you design or understand any tests? How?

Copilot helped to interpret the failure message and pointed me to the core condition needing the change. It also suggested exactly which test case to run and what output to check, making the debug cycle faster.
---

## 4. What did you learn about Streamlit and state?

- In your own words, explain why the secret number kept changing in the original app.

The secret number kept changing because it was being regenerated on each rerun.

- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?

Streamlit re-executes your script every time the UI changes.

- What change did you make that finally gave the game a stable secret number?

I changed the code to set st.session_state['secret_number'] once (on new game) and only reset it when needed, so the number stays stable during one round

---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?

  - This could be a testing habit, a prompting strategy, or a way you used Git.

  Write a failing test first

- What is one thing you would do differently next time you work with AI on a coding task?

I will ask for exact code patch suggestions and review them carefully before accepting

- In one or two sentences, describe how this project changed the way you think about AI generated code.

After this project I view AI code suggestions like a strong assistant.

---

## Project 4 Reflection: Building the AI Game Coach

### How I Used AI During Development

I used Claude Code (Anthropic) as my primary AI collaborator throughout Project 4. I used it for three distinct tasks: (1) designing the agentic loop structure — I described what I wanted (plan → act → verify) and asked it to scaffold the tool-call iteration pattern; (2) debugging the Streamlit session state integration, specifically ensuring `feedback_history` stayed parallel to valid integer guesses; (3) writing the few-shot examples in the system prompt, where I described the desired coaching style and the AI drafted example conversations that I then reviewed and refined.

### One Helpful AI Suggestion

When designing the reliability system, I asked Claude how to validate the AI agent's reasoning without having access to the secret number. It suggested computing the "ground truth range" independently from the guess/feedback history and comparing the AI's proposed range against it — flagging and correcting any deviation before the suggestion reaches the player. This was exactly the right approach: it gave me a server-side sanity check that didn't depend on trusting the model. I verified it by manually tracing through test cases with known feedback sequences and confirming the correction logic fired correctly.

### One Flawed AI Suggestion

When I first asked for the agentic loop, the AI suggested running both tools in a single API call using `tool_choice: "auto"` without an iteration loop. This would have been fine for a simple one-shot tool call, but it wouldn't produce the observable multi-step reasoning required by the rubric. I had to push back and ask it to structure the loop so each tool call is a separate API round-trip with tool results fed back in — that's what makes the intermediate steps inspectable. The lesson: AI is good at generating plausible patterns, but it doesn't always know which pattern is the right one for your specific constraints.

### System Limitations and Future Improvements

The current system has two main limitations. First, the AI coach can only suggest the optimal binary-search guess — it doesn't adapt to the player's skill level or explain *why* binary search is efficient beyond a single sentence. A future version could include a "teach me" mode that walks the player through the math. Second, the coach is stateless across sessions: `coach_log.txt` accumulates data but nothing reads it back to improve future suggestions. A RAG enhancement could index past game sessions and retrieve relevant strategy patterns (e.g., "players who took this path often miss X") to give more personalized coaching over time.
---

## Project 4 — Ethics and Critical Reflection

### What are the limitations or biases in your system?

The biggest limitation is that the AI coach always recommends binary search, regardless of context. If a player is learning and wants to explore the number space differently, or if they're 1 guess away from losing and need a strategic risk assessment rather than a math lesson, the coach still gives the same midpoint advice. It doesn't read the emotional state of the player or adapt to their skill level. There's also a subtle bias baked into the few-shot examples: they only show "correct" binary search behavior, so the model is steered away from ever explaining *why* a player's non-optimal guess might actually be reasonable. This makes the coach feel prescriptive rather than supportive for beginners.

### Could your AI be misused, and how would you prevent that?

For a number guessing game the misuse surface is small, but it's not zero. Someone could spam the "Ask AI Coach" button to generate hundreds of API requests rapidly, running up costs on a shared key. The current code has no rate limiting. A more serious concern: the coach logs all game states to `coach_log.txt` including guess histories — if this were deployed with real user accounts, those logs could accumulate personal gameplay data without explicit consent. To prevent both: I'd add a simple per-session request counter in `st.session_state` to cap AI calls, and I'd either anonymize the logs or add a clear disclosure in the UI that game data is logged.

### What surprised you while testing your AI's reliability?

The most surprising thing was how often the model got the range right but then suggested a guess *outside* that range — a logical contradiction. It would correctly compute `[26, 49]` and then suggest `50`. This happened consistently enough in early testing that I had to add the server-side guess validation step as a separate guardrail. I also didn't expect the model to sometimes call `suggest_guess` before `analyze_range`, skipping the order the system prompt required. The few-shot examples fixed most of that, but it showed me that even simple ordering constraints need to be enforced in code, not just in prompts.

### Collaboration with AI During This Project

I used Claude Code as my primary AI collaborator for Project 4, alongside Copilot for smaller in-editor edits.

**Helpful suggestion:** When I was stuck on how to validate the AI agent's output without knowing the secret number, Claude suggested computing the ground-truth range independently from the guess/feedback history in Python and comparing it against whatever the model returned — correcting and overwriting wrong values before they reached the player. That was exactly the right insight and became the core of the reliability system.

**Flawed suggestion:** When I first asked Claude to build the agentic loop, it suggested calling both tools in a single prompt with `tool_choice: "auto"` and no iteration loop — essentially treating it as a one-shot tool call. That would have produced the right answer most of the time but would have hidden all the intermediate steps, which were required by the rubric. I had to explicitly ask it to restructure into a multi-turn loop where each tool result is fed back to the model before the next step. The AI's first instinct was the simpler implementation, not the one that met the actual requirements.

## What This Project Says About Me as an AI Engineer

This project showed me that being an AI engineer is less about knowing which model to call and more about knowing when to stop trusting it. I spent real time chasing 404 and 429 errors across three different model versions, and the fix every time wasn't more AI — it was reading the docs, listing the available models, and picking one that actually existed. That same instinct showed up in the code: the most important design decision I made was not trusting the AI coach's range calculations at face value, but validating them against a deterministic Python function I could reason about myself. I'm someone who leans on AI heavily for scaffolding and drafting, but I've learned I need to stay in the driver's seat for the decisions that actually matter — what the system is supposed to guarantee, and how you verify it when the model gets it wrong. That's the skill I want to keep building.