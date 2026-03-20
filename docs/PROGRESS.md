# ProfDNK Progress & Bonus Log

Last update: 2026-03-21

## Purpose
- Keep one place with completed work, especially features that go beyond minimum case scope.
- Help prepare fast jury narrative: "what is done", "what is mandatory", "what is bonus".

## Update Rule
- After each completed task, add one short entry to `Recent Entries`.
- If feature is beyond minimum case scope, mark it as `BONUS`.
- Always include commit hash for traceability.

## Current Snapshot
- P0: 64 / 65
- P1: 1 / 16
- P2: 0 / 7
- Global: 65 / 88

## Bonus Track (Beyond Minimum)
- Access expiry reminders (admin + psychologist, 7/3/1 days) with visual levels.
- Responsive table/card layout for mobile + layout hardening on desktop.
- Dedicated `/features` page for product capabilities and demo navigation.
- Named invite links + campaign grouping in analytics view.

## Recent Entries
| Date | Scope | Type | Impact for Jury | Commit |
|---|---|---|---|---|
| 2026-03-21 | Access expiry reminders for admin + psychologist | BONUS | Shows product maturity and proactive UX, not only raw MVP flow | `b95144b` |
| 2026-03-21 | Responsive UI for admin/tests/test-detail tables | BONUS | Better real-world usability on desktop/mobile during live demo | `36e6c29` |
| 2026-03-21 | `/features` page + global navigation link | BONUS | Makes demo story clear and quick for evaluators | `a368f8e` |
| 2026-03-21 | Named invite links UI + grouped stats + docs | P0 | Closes organizer clarification and improves campaign analytics | `21d5cca` |
| 2026-03-21 | Invite links backend model + token resolver | P0 | Adds multi-link test distribution and source tracking | `9c76e9b` |

## Jury Pitch Notes
- Core scenario is complete end-to-end.
- We additionally delivered practical "productization" layers:
- access reminders,
- responsive interface quality,
- campaign-level invite analytics,
- explicit capabilities page for clarity.
