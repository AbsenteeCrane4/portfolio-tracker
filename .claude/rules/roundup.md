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

## LLMs and numbers

- Every signal, figure, and statistic is computed by deterministic Python
  before any model is called.
- The model receives that computed table plus text (news, context). It
  returns structured output, such as narrative, ranking, or categorisation,
  validated against a Pydantic schema.
- The model never calculates, estimates, converts, or rounds a figure, and
  never originates one. A figure that appears in user-visible output comes
  from the computed inputs, not from the model's text.
- Output that fails validation is discarded and the failure logged. It is
  never repaired by regex or coercion.
- LLM API calls are external calls. They go through the shared client and the
  quota ledger.

## Suggestions

- Persist each suggestion with its full inputs: the signal snapshot, the news
  items used, the raw validated model output, and its state
  (`new` / `accepted` / `dismissed`). Never discard the inputs. They are the
  dataset for evaluating decision quality later.
- Copy describes signals and observations, such as "X fell 8% on volume 3x
  its 20-day average". It never instructs ("sell X"). This is not an advice
  product, and nothing here places orders.
