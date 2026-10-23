# Results: cognee vs baseline
> **SYNTHETIC DRY-RUN.** These numbers come from the fake LLM backend (`harness/fake_upstream.py`, `harness/fake_claude.py`). They are not Cognee token savings. The stand-in agent uses a fixed call pattern (baseline: 4 Claude calls; cognee: 2 Claude calls plus 1 internal call) so every `net_delta` term is non-zero. It does not actually skip exploration. Do not cite this report as a result.

Negative = Cognee saves tokens. Only pairs where both arms pass count toward token deltas.
Coding tasks are inside this headline, on the same formula as project_ops and meetings.

## Headline
| model             |   pairs |   both_pass |   succ_base |   succ_cognee |   succ_delta |   median_base_tokens |   median_net_delta |   median_net_delta_pct | ci95_pct       |   median_delta_pct_excl_ingest |   median_weighted_delta_pct |
|:------------------|--------:|------------:|------------:|--------------:|-------------:|---------------------:|-------------------:|-----------------------:|:---------------|-------------------------------:|----------------------------:|
| claude-opus-5-5   |      30 |          30 |           1 |             1 |            0 |                  144 |                287 |                  199.3 | [180.0, 214.2] |                          131.4 |                        78.2 |
| claude-sonnet-5-5 |      30 |          30 |           1 |             1 |            0 |                  148 |                286 |                  193.2 | [180.4, 213.8] |                          132.1 |                        76.8 |

## Where the tokens go (means, cognee arm minus baseline)
`exploration_delta + carried_ctx + tooldefs + cognee_internal + ingest_share = net_delta`. `carry_multiplier` = how often each injected Cognee token is re-billed in Claude's context.

| model             |   n |   base_claude |   exploration_delta |   + carried_ctx (first) |   + carried_ctx (resent) |   + tooldefs |   + cognee_internal |   + ingest_share |   = net_delta |   injected_unique |   carry_multiplier |
|:------------------|----:|--------------:|--------------------:|------------------------:|-------------------------:|-------------:|--------------------:|-----------------:|--------------:|------------------:|-------------------:|
| claude-opus-5-5   |  30 |           170 |                  81 |                      17 |                       24 |           55 |                  40 |              103 |           320 |                17 |                2.4 |
| claude-sonnet-5-5 |  30 |           171 |                  81 |                      17 |                       24 |           55 |                  41 |              103 |           321 |                17 |                2.4 |

## By topic
| model             | topic       |   pairs |   both_pass |   succ_base |   succ_cognee |   succ_delta |   median_base_tokens |   median_net_delta |   median_net_delta_pct | ci95_pct       |   median_delta_pct_excl_ingest |   median_weighted_delta_pct |
|:------------------|:------------|--------:|------------:|------------:|--------------:|-------------:|---------------------:|-------------------:|-----------------------:|:---------------|-------------------------------:|----------------------------:|
| claude-opus-5-5   | coding      |      10 |          10 |           1 |             1 |            0 |                  152 |                287 |                  188.8 | [172.8, 214.2] |                          127.1 |                        75.4 |
| claude-opus-5-5   | meetings    |      10 |          10 |           1 |             1 |            0 |                  128 |                284 |                  225.8 | [177.1, 231.2] |                          145.2 |                        84.8 |
| claude-opus-5-5   | project_ops |      10 |          10 |           1 |             1 |            0 |                  144 |                287 |                  199.3 | [146.1, 214.6] |                          127.8 |                        78.2 |
| claude-sonnet-5-5 | coding      |      10 |          10 |           1 |             1 |            0 |                  152 |                288 |                  189.5 | [173.8, 215.0] |                          128.5 |                        75.7 |
| claude-sonnet-5-5 | meetings    |      10 |          10 |           1 |             1 |            0 |                  132 |                284 |                  215.9 | [177.5, 228.2] |                          137.9 |                        82.5 |
| claude-sonnet-5-5 | project_ops |      10 |          10 |           1 |             1 |            0 |                  148 |                286 |                  193.2 | [146.7, 211.5] |                          125.7 |                        76.8 |

| model             | topic       |   n |   base_claude |   exploration_delta |   + carried_ctx (first) |   + carried_ctx (resent) |   + tooldefs |   + cognee_internal |   + ingest_share |   = net_delta |   injected_unique |   carry_multiplier |
|:------------------|:------------|----:|--------------:|--------------------:|------------------------:|-------------------------:|-------------:|--------------------:|-----------------:|--------------:|------------------:|-------------------:|
| claude-opus-5-5   | coding      |  10 |           173 |                  83 |                      17 |                       24 |           55 |                  41 |              103 |           323 |                17 |                2.4 |
| claude-opus-5-5   | meetings    |  10 |           159 |                  83 |                      17 |                       24 |           55 |                  40 |              103 |           321 |                17 |                2.4 |
| claude-opus-5-5   | project_ops |  10 |           179 |                  78 |                      17 |                       24 |           55 |                  40 |              103 |           317 |                17 |                2.4 |
| claude-sonnet-5-5 | coding      |  10 |           173 |                  84 |                      17 |                       24 |           55 |                  42 |              103 |           325 |                17 |                2.4 |
| claude-sonnet-5-5 | meetings    |  10 |           161 |                  82 |                      17 |                       24 |           55 |                  40 |              103 |           321 |                17 |                2.4 |
| claude-sonnet-5-5 | project_ops |  10 |           180 |                  78 |                      17 |                       24 |           55 |                  41 |              103 |           318 |                17 |                2.4 |

## By task type
| model             | type         |   pairs |   both_pass |   succ_base |   succ_cognee |   succ_delta |   median_base_tokens |   median_net_delta |   median_net_delta_pct | ci95_pct       |   median_delta_pct_excl_ingest |   median_weighted_delta_pct |
|:------------------|:-------------|--------:|------------:|------------:|--------------:|-------------:|---------------------:|-------------------:|-----------------------:|:---------------|-------------------------------:|----------------------------:|
| claude-opus-5-5   | action       |       4 |           4 |           1 |             1 |            0 |                  180 |                273 |                  154.2 | [131.5, 176.9] |                           96.2 |                        64.6 |
| claude-opus-5-5   | code_fix     |       2 |           2 |           1 |             1 |            0 |                  152 |                287 |                  188.8 | [188.8, 188.8] |                          121.1 |                        75.4 |
| claude-opus-5-5   | codebase_qa  |       2 |           2 |           1 |             1 |            0 |                  132 |                287 |                  217.4 | [217.4, 217.4] |                          139.4 |                        82.8 |
| claude-opus-5-5   | control      |       6 |           6 |           1 |             1 |            0 |                  128 |                285 |                  225.8 | [182.7, 229.8] |                          145.3 |                        84.8 |
| claude-opus-5-5   | cross_source |       6 |           6 |           1 |             1 |            0 |                  136 |                287 |                  211   | [199.3, 236.7] |                          135.3 |                        81.2 |
| claude-opus-5-5   | multi_turn   |       6 |           6 |           1 |             1 |            0 |                  288 |                468 |                  162.8 | [160.8, 177.3] |                          127.1 |                        38.5 |
| claude-opus-5-5   | recall       |       4 |           4 |           1 |             1 |            0 |                  132 |                285 |                  216.6 | [205.0, 228.2] |                          138.3 |                        82.4 |
| claude-sonnet-5-5 | action       |       4 |           4 |           1 |             1 |            0 |                  180 |                274 |                  154.8 | [132.0, 177.5] |                           96.8 |                        64.9 |
| claude-sonnet-5-5 | code_fix     |       2 |           2 |           1 |             1 |            0 |                  152 |                288 |                  189.5 | [189.5, 189.5] |                          121.7 |                        75.7 |
| claude-sonnet-5-5 | codebase_qa  |       2 |           2 |           1 |             1 |            0 |                  132 |                288 |                  218.2 | [218.2, 218.2] |                          140.2 |                        83.1 |
| claude-sonnet-5-5 | control      |       6 |           6 |           1 |             1 |            0 |                  132 |                285 |                  215.9 | [183.3, 229.8] |                          137.9 |                        82.5 |
| claude-sonnet-5-5 | cross_source |       6 |           6 |           1 |             1 |            0 |                  136 |                286 |                  211.8 | [193.2, 236.7] |                          136   |                        81.6 |
| claude-sonnet-5-5 | multi_turn   |       6 |           6 |           1 |             1 |            0 |                  288 |                467 |                  164.2 | [161.5, 174.3] |                          128.5 |                        38.9 |
| claude-sonnet-5-5 | recall       |       4 |           4 |           1 |             1 |            0 |                  132 |                286 |                  217   | [205.7, 228.2] |                          138.7 |                        82.5 |

## Cognee ingestion and break-even
| topic       |   ingest_tokens |   mean_delta_per_task_excl_ingest | break_even_tasks   |
|:------------|----------------:|----------------------------------:|:-------------------|
| coding      |             515 |                               221 | never              |
| meetings    |             515 |                               218 | never              |
| project_ops |             515 |                               214 | never              |

## Judge disagreements
Primary judge versus the secondary model. A row appears only when both verdicts succeeded and differ. Review the gold for these tasks. A transport or parse error is not a flag.

| task_id       | model             | arm      |   rep | success   |   secondary_success | grade_reason                                   | secondary_reason                                        |
|:--------------|:------------------|:---------|------:|:----------|--------------------:|:-----------------------------------------------|:--------------------------------------------------------|
| cd-qa-001     | claude-opus-5-5   | baseline |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| cd-qa-001     | claude-opus-5-5   | cognee   |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| cd-qa-001     | claude-opus-5-5   | cognee   |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| cd-qa-001     | claude-opus-5-5   | baseline |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| mt-recall-001 | claude-opus-5-5   | baseline |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| mt-recall-001 | claude-opus-5-5   | cognee   |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| mt-recall-001 | claude-opus-5-5   | baseline |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| mt-recall-001 | claude-opus-5-5   | cognee   |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| po-recall-001 | claude-opus-5-5   | cognee   |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| po-recall-001 | claude-opus-5-5   | baseline |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| po-recall-001 | claude-opus-5-5   | cognee   |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| po-recall-001 | claude-opus-5-5   | baseline |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| cd-qa-001     | claude-sonnet-5-5 | baseline |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| cd-qa-001     | claude-sonnet-5-5 | cognee   |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| cd-qa-001     | claude-sonnet-5-5 | baseline |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| cd-qa-001     | claude-sonnet-5-5 | cognee   |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| mt-recall-001 | claude-sonnet-5-5 | cognee   |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| mt-recall-001 | claude-sonnet-5-5 | baseline |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| mt-recall-001 | claude-sonnet-5-5 | cognee   |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| mt-recall-001 | claude-sonnet-5-5 | baseline |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| po-recall-001 | claude-sonnet-5-5 | baseline |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| po-recall-001 | claude-sonnet-5-5 | cognee   |     0 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| po-recall-001 | claude-sonnet-5-5 | cognee   |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |
| po-recall-001 | claude-sonnet-5-5 | baseline |     1 | True      |                   0 | synthetic judge: answer contains the reference | synthetic secondary judge disagrees ([[review]] marker) |

## Data quality
- runs where proxy and stream-json disagree by more than 1%: 0
- API responses without usage (check proxy parsing for that provider): 0
- logged Cognee hook texts not found in Claude's requests: 0
- runs flagged for judge disagreement: 24