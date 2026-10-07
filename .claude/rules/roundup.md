---
paths:
  - "src/portfolio/features/roundup/**"
  - "src/portfolio/interfaces/roundup_hook.py"
  - "src/portfolio/interfaces/news_provider.py"
  - "src/portfolio/**/*suggestion*"
  - "src/portfolio/**/*llm*"
  - "tests/**/*roundup*"
  - "tests/**/*suggestion*"
---

# Roundup and LLM rules

Signal maths (definitions, observation counts, insufficient-data handling)
is covered by the `quant` skill.

## LLMs and numbers (PT-044)

- Every signal and figure is computed by deterministic Python before a model
  is called. Each signal returns its value, window, and observation count
  (PT-043).
- The model receives the computed signal table plus headlines, never a
  request to calculate. It returns ranked observations validated against a
  Pydantic schema, each referencing the signal id and article ids it relies
  on.
- The model never calculates, estimates, converts, rounds, or originates a
  figure. Numbers shown come from the referenced signals, not from the
  model's text.
- An observation referencing a signal or article id that wasn't in the input
  is rejected.
- Output that fails validation is discarded and retried once. If the retry
  also fails, the roundup falls back to presenting the raw signals. Never
  repair output by regex or coercion.
- LLM API calls are external calls, so they go through the shared client and
  the quota ledger. The model provider is configurable, and the whole feature
  can be disabled.

## Suggestions (PT-045)

- Each suggestion row stores the signal snapshot, the prompt, the model name,
  the validated output, its created timestamp, and its state. Never discard
  the inputs: they are the dataset for evaluating decisions later.
- States are `new`, `accepted`, `dismissed`, and `stale` (superseded). Each
  transition is recorded with a timestamp and an optional note. Rows are
  never deleted.
- Accepting a suggestion records intent only. It never creates a transaction
  or places a trade.
- Copy describes signals and observations ("X fell 8% on 3× its 20-day average
  volume"). It never instructs ("sell X").
