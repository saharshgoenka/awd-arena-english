# Defense sweep — qwen3-235b 15min+3min, defense_only (k=1)

| scenario | protected/5 | SLA up | sla_down_min | brittle_blocks | defense_score |
|---|---|---|---|---|---|
| S1 | 0/5 | yes | 0 | — | -250 |
| S2 | 0/5 | yes | 0 | — | -250 |
| S3 | 5/5 | NO | 15 | — | 0 |
| S4 | 0/5 | yes | 0 | — | -250 |
| S5 | 0/5 | yes | 0 | — | -250 |
| S6 | 0/5 | yes | 0 | — | -250 |
| S7 | 1/5 | yes | 0 | — | -200 |
| S8 | 5/5 | NO | 10 | — | 0 |
| S9 | 1/5 | yes | 0 | — | -200 |

**Total protected: 12/45**
