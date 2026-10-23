# Competition notes

## Task and score

The main track grades submitted patches by whether validation tests pass after the patch is applied. The competition's global generation-run limit is 12 hours, including sandbox setup and excluding patch validation. A run-level failure or timeout can prevent a score from being published.

## Active submission model

The current candidate keeps `gemma-4-31b-it-qat-w4a16-ct` to align with the strongest measured public reference discussed in the October 23 study. That study reports updated host support for smaller E4B/E2B/12B variants and a bonus for E4B/E2B, but these changes are secondary-source findings and should be confirmed on the live Rules page before making a separate bonus-track candidate. The tested 12B comparison in that study was below 31B under the tested settings; it does not establish how E4B/E2B would perform.

## Source references

- https://www.kaggle.com/competitions/gemma-4-developer-agent/overview
- https://github.com/Strider221B/gemma4_dev_agent/blob/main/data/HARNESS_README.md
- https://pilkwangkim.github.io/posts/Gemma-4-Developer-Agent-Part-2-Measuring-an-Agent-While-Its-Evaluator-Moved/

Read `docs/HARNESS.md` for the operational submission contract. The live notebook/harness version takes precedence over an older cached page or a third-party mirror.
