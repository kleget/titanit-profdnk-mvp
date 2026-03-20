# ProfDNK Win TODO

Last update: 2026-03-21

## How to use this file
- Rule: only mark `[x]` when feature is demo-ready and tested manually.
- Rule: every dev session starts from first unchecked task in `P0`.
- Rule: if task is half-done, keep `[ ]` and add short note in `Notes`.
- Rule: after each closed task, add an entry to `docs/PROGRESS.md` with commit hash and `BONUS` tag (if applicable).
- Goal: when all `P0` + `P1` are closed, project is "final demo grade".

## P0: Mandatory case coverage (must be 100%)

### Auth and roles
- [x] Login page: email + password.
- [x] Redirect after login: psychologist -> cabinet, admin -> admin panel.
- [x] Admin can create psychologists (name/email/phone/password).
- [x] Admin can set access end date.
- [x] Admin can block/unblock psychologist.

### Organizer clarifications (Q&A 2026-03-21)
- [x] Psychologist self-registration is disabled; accounts are created by admin only.
- [x] Access period behaves like manual subscription window (admin sets/extends date).
- [x] No automatic access renewal without admin action.
- [x] Access expiry reminders for admin and psychologist (e.g., 7/3/1 days before expiry).
- [x] Payment integration is not required.
- [x] One public test link can be used by multiple clients.
- [x] Named invite links/campaign labels for grouping (e.g., "School-234").
- [ ] Dynamic extra client fields per test (full_name fixed + configurable fields/templates).
- [x] Grouped results view by invite-link label/campaign.

### Psychologist cabinet
- [x] Upload photo.
- [x] "About me" field with Markdown support.
- [x] Psychologist cannot edit full name / email / phone directly.
- [x] Public business card page.
- [x] QR code for business card.

### My questionnaires screen
- [x] Table columns: test title / submissions count / last submission date / actions.
- [x] Copy unique client link button.
- [x] Show access date info ("Access until YYYY-MM-DD").

### Test detail screen
- [x] Table columns: client name / submission date / actions.
- [x] Two report actions for each submission:
- [x] Client report (DOCX + HTML).
- [x] Psychologist report (DOCX + HTML).
- [x] AJAX refresh button without full page reload.

### Client flow by unique URL
- [x] Client opens unique URL without auth.
- [x] Client fills required personal fields (full_name always required).
- [x] Client passes test online.
- [x] Progress % is shown during completion.
- [x] Answers are saved to DB.
- [x] Submission becomes visible for psychologist.
- [x] Client report visibility controlled by test setting.

### Test builder
- [x] Create test via UI.
- [x] Import test config from JSON.
- [x] Export test config to JSON.
- [x] Question type: text.
- [x] Question type: textarea.
- [x] Question type: single choice.
- [x] Question type: multiple choice.
- [x] Question type: yes/no.
- [x] Question type: number.
- [x] Question type: slider.
- [x] Question type: datetime.
- [x] Question type: rating.
- [x] Section grouping.
- [x] Advanced custom formulas editor for derived metrics.

### Reports
- [x] On-demand HTML report generation.
- [x] On-demand DOCX report generation.
- [x] Reports are not stored as files on disk.
- [x] Two templates: client and psychologist.
- [x] Report includes answers.
- [x] Report includes computed metrics.
- [x] Report includes charts/visual profile.

### Delivery requirements
- [x] GitHub repository exists.
- [x] README with run instructions.
- [x] Architecture description in docs.
- [x] At least one seeded test and templates.
- [x] docker-compose deployment setup.
- [x] Public VPS demo URL in README.

## P1: Quality and "winner-level" polish

### Reliability
- [ ] Add Alembic migrations and migration docs.
- [ ] Add centralized error pages (400/403/404/500) with UX-friendly text.
- [ ] Add backend request logging and app startup diagnostics.
- [ ] Add strict server-side validation schemas for builder payloads.

### Security
- [ ] Move secrets to `.env` for all environments, remove hardcoded fallback secrets.
- [ ] Add rate limiting for auth and public submit endpoints.
- [ ] Add CSRF protection for form POST routes.
- [ ] Add basic audit log for admin actions.

### Tests
- [ ] Add integration tests for full flow (create test -> pass -> report).
- [ ] Add unit tests for scoring service.
- [ ] Add unit tests for report generation service.
- [ ] Add CI workflow: run tests + lint on push.

### UX/UI
- [ ] Improve builder UX: inline validation + better hints.
- [ ] Add empty states and success/error toasts.
- [x] Improve mobile layout for tables and long forms.
- [ ] Add printable report styles for HTML.

### Demo readiness
- [ ] Prepare demo script (3-5 minutes) and pin it in docs.
- [ ] Prepare fallback "offline demo path" if internet fails.
- [ ] Add sample data package for fast reset before jury demo.

## P2: Extra points ("star level")

- [ ] Drag-and-drop builder for sections/questions.
- [ ] Branching logic (show/hide questions, jump between sections).
- [ ] Clone test action.
- [ ] Extended JSON schema with versioning.
- [ ] Visual analytics dashboard (charts, profiles, scales).
- [ ] Light/dark theme switch.
- [ ] Multi-psychologist workspace isolation and permissions hardening.

## Current score
- P0 completion: 64 / 65.
- P1 completion: 1 / 16.
- P2 completion: 0 / 7.
- Global completion: 65 / 88.

## Notes
- P0 blockers now: organizer Q&A clarifications (dynamic fields).
- Fastest path to jury impact: close P0 first, then 3-4 tasks from P1 UX + Tests.
