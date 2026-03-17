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