# PREFLIGHT SUMMARY (current wheelhouse as mounted in THIS notebook)

swegemma=0.2.7 | adk-submission=0.2.11 | adk-eval-core=0.1.0 | google-adk=1.36.1 | google-genai=2.11.0
python 3.13.16 | install mode: skip | harness dir: /tmp/claude-0/-home-claude/eb9495f5-98fd-54ef-afd6-cdb1c702c7ab/scratchpad/ext/happyc0der_gemma-swe-agent/harness/official

| label | role | bytes | sha256 (16) | compile_submission | fake replay | evaluator smoke |
|---|---|---|---|---|---|---|
| VNEXT-ORIGINAL | NEGATIVE CONTROL (old mirror: include error) | 5938 | 292c4ab28c9c516f | FAIL | EXCEPTION | NOT TESTED |
| VNEXT-INCLUDEFIX-ADDITIVE | repair under test | 7700 | c26518e6a6b91eff | PASS | RAN_TO_COMPLETION | NOT TESTED |
| EVIDENCE-V1 | control (assumption A1) | 4849 | 46e455c81d594b95 | PASS | RAN_TO_COMPLETION | NOT TESTED |
| HYBRID-V2-ADAPTIVE | control | 5075 | 2932140057fca9e0 | PASS | RAN_TO_COMPLETION | NOT TESTED |
| GRAPH-FUSION-V2 | control | 5865 | a9e9b7a333a059dc | PASS | RAN_TO_COMPLETION | NOT TESTED |

Thinking variants (what the installed resolver put on the wire):
- BASE_include_thoughts_false: RAN_TO_COMPLETION -> ['{"chat_template_kwargs.enable_thinking": false}']
- V1_thoughts_true_budget4096: RAN_TO_COMPLETION -> ['{"chat_template_kwargs.enable_thinking": true}']
- V2_thoughts_false_budget4096: RAN_TO_COMPLETION -> ['{"chat_template_kwargs.enable_thinking": false}']
- V3_thoughts_false_level_none: RAN_TO_COMPLETION -> ['{"chat_template_kwargs.enable_thinking": false}']
- V4_budget_zero_only: EXCEPTION -> [] Submission schema validation failed: 1 validation error for SandboxedAgentConfig
LlmAgent.generate_c

Labels: a PASS here means ONLY that the installed compiler accepted the directory (and the replay ran with a scripted fake model).
It is NOT a Gemma result, NOT a score, NOT the scorer's own inference.py/metric.py.