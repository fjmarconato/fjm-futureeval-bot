# FJM FutureEval Forecast Bot

Autonomous forecasting entry for the Metaculus FutureEval 2026 tournament and
MiniBench. The project starts from Metaculus' official bot template and adds a
resolution-first research process, calibrated ensembles, explicit probability
floors, dry-run defaults, tests, and scheduled GitHub Actions operation.

## Operating model

- `main.py` researches, forecasts, aggregates, and optionally submits answers.
- `calibration.py` contains deterministic binary and multiple-choice pooling.
- `tests/` protects the scoring-critical calibration behavior.
- `.github/workflows/run_bot_on_tournament.yaml` checks for new eligible
  questions every 20 minutes.
- `.github/workflows/test_bot.yaml` is the manual end-to-end smoke test.
- `.github/workflows/monitor_bot_health.yaml` checks the scheduler every two
  hours and manages a GitHub issue when operation becomes unhealthy. A run is
  considered stale after six hours to tolerate GitHub Actions scheduling delay.
- Questions and model calls run serially to stay below shared proxy rate limits.
- `OPERATIONS.md` records setup, cost controls, and the stop/scale criteria.

The CLI is safe by default. It will only publish when `--publish` is present.

## Setup

Requires Python 3.11+ and Poetry.

```bash
poetry install
cp .env.template .env
```

At minimum, configure `METACULUS_TOKEN` and one model-provider key such as
`GOOGLE_API_KEY` or `OPENROUTER_API_KEY`. Metaculus-hosted models can be used
only after the bot account receives a competition allowance.

## Run

Dry-run against the bot testing area:

```bash
poetry run python main.py --mode test_questions
```

Publish a controlled testing-area run:

```bash
poetry run python main.py --mode test_questions --publish
```

Forecast the live FutureEval tournament and current MiniBench:

```bash
poetry run python main.py --mode tournament --publish
```

## Tests

```bash
python -m unittest discover -s tests -v
python -m py_compile main.py calibration.py tests/test_calibration.py
```

## Secrets and costs

Credentials belong in local environment variables or GitHub Actions secrets;
they must never be committed. The initial operating policy forbids purchased
model credits until the free-credit run produces evidence that scaling is
economically justified. See `OPERATIONS.md` for the exact decision rule.

Tournament information and official setup instructions:

- https://www.metaculus.com/futureeval/
- https://www.metaculus.com/futureeval/participate/
- https://github.com/Metaculus/metac-bot-template
