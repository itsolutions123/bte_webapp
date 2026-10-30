# Security & Privacy Policy

## 1. Resume File Upload Constraints
- **Storage Path:** `/data/resumes` (Docker volume / bind mount). Never served directly by Nginx or FastAPI static routes.
- **File Naming:** Files on disk must be named using a server-generated UUID (e.g., `<application_id>.pdf`). The original client-provided filename must only be stored in the Postgres database and sanitized before display.
- **File Type Enforcement:** PDF only. The application must verify the "magic bytes" (the first 4 bytes must be `b"%PDF"`) before writing the full file to disk. Relying solely on `Content-Type` headers or file extensions is prohibited.
- **Max File Size:** 5MB per resume. The API must stream the upload to disk and abort the transaction (deleting any partial file and returning 413) if the 5MB limit is breached, preventing memory exhaustion.
- **File Permissions:** Created files must have `0600` permissions. The directory must be `0700` (owned by the app's user).

## 2. Authentication & Admin Access
- **Mechanism:** HttpOnly, SameSite=Lax session cookies for the Admin panel. No raw JWTs in `localStorage`. **Secure flag dropped for now (DECIDED 2026-10-30, user):** the app is LAN-only HTTP with no TLS per the scope lock; a Secure cookie is never sent by the browser over plain HTTP, which would make login appear to succeed (200 OK) while the session never actually persists. Re-add Secure the moment TLS/a real domain is added — a deliberate, temporary exception, not a relaxation of the original policy.
- **Credentials:** Passwords hashed using bcrypt (via `passlib`).
- **Rate Limiting (Admin):** Max 5 failed login attempts per minute per IP to prevent brute force. In-memory sliding window, same pattern as the public apply endpoint's `RATE_LIMIT_CACHE`; counts failed attempts only (a correct login does not count against it).
- **Session timing (DECIDED 2026-10-30, user):** a session has a fixed 8-hour hard cap from login (`sessions.expires_at`, never extended) and a separate 10-minute idle timeout tracked via `sessions.last_active_at`, updated on every authenticated request. A session is valid only while both hold. The idle-timeout check itself is enforced by the `/admin/*` auth dependency, not yet built (see Status gap below).
- **Remember me (DECIDED 2026-10-30, user, Security option A):** the login page's "Remember me" checkbox remembers only the email address, in the browser's `localStorage`, to pre-fill it on the next visit. The password is NEVER stored by our code (no `localStorage`, no cookie); password saving is left to the browser's own password manager via the `autocomplete="username"` and `autocomplete="current-password"` attributes on the login form. Remember me does not change session lifetime: the 8-hour hard cap and the 10-minute idle timeout above still apply. Status: the checkbox is a UI shell, the email wiring is NOT implemented yet.

## 3. Public API Hardening (`POST /apply`)
- **Rate Limiting:** Max 3 submissions per IP per hour to prevent spam. (Implementation: lightweight in-memory sliding window or LRU cache to avoid adding Redis infrastructure).
- **Input Validation:** All strings (names, answers) must be stripped of leading/trailing whitespace.
- **Output Sanitization:** Answers rendered in the admin dashboard must be strictly escaped by the Jinja2 template engine to prevent stored XSS.

## 4. PII & Retention Policy
- **Access:** Only authenticated users with the Admin role may view applicant names, emails, phones, answers, and resumes.
- **Consent Logging:** Submissions must record the timestamp of application and the `terms_version` accepted. 
- **IP Logging:** Strictly no IP logging. IP addresses will not be stored in the database to minimize PII footprint.
- **Retention / Deletion:** Governed by the Philippine Data Privacy Act of 2012 (RA 10173). Personal data (resumes, answers, applicant details) will be permanently purged after 1 year, as they are no longer necessary for the purpose of the specific hiring cycle. Applicants may exercise their right to erasure under RA 10173 to request earlier deletion.

## 5. Secrets, Configuration & Network Exposure
- **No fallback credentials:** `docker-compose.yml` and application code must never define a default value for a password, key, token or database URL. Compose requires the value (`${DB_PASSWORD:?DB_PASSWORD must be set in .env}`) and the app raises an error if `DATABASE_URL` is missing, so a missing secret stops the start instead of silently using a guessable default. Non-secret defaults (such as database and user names) are allowed but must be listed as hardcodes in the audit.
- **Where secrets live:** only in `.env` on the host (git-ignored, permissions `0600`). `.env.example` contains placeholders only and lists every required variable, including `DB_PASSWORD`. Secrets are never written into code, docs, commit messages or `PROJECT_STATE.md`.
- **Before every commit:** `git status` must show no `.env`, key or credential files, and no tracked file may contain a live secret value.
- **Database exposure:** Postgres is published on `127.0.0.1` only (`"127.0.0.1:5432:5432"`). The web container reaches it over the compose network (`db:5432`). No service may publish a database port on all interfaces.
- **If a credential was ever committed or exposed:** rotate it. Change it inside Postgres first, then update `.env`, then restart the containers. Removing it from the file is not enough, because it stays in git history. A history rewrite is not needed once the value is dead.
- **Testing database passwords:** the official Postgres image trusts loopback connections inside its own container, so a check run over `127.0.0.1` passes for any password. Test password authentication over the network (`-h db`).

## 6. Rich Text (Job Description and Requirements) Cleaning (DECIDED 2026-10-15; server cleaning on create IMPLEMENTED and verified live; editor wired into the Create job modal and verified in the browser; saved jobs render in the detail modal and on the careers site)
- The job description and the requirements are formatted text saved by an admin and shown to every visitor of the careers site, so they are untrusted input (stored XSS risk). Both fields get the same cleaning (decided 2026-10-15, user).
- The server cleans it on every write, in Python, with an allowlist (tags `p`, `br`, `ul`, `ol`, `li`, `strong`, `em`, `u`, `span`; attribute `class` only, allowed on `p`, `li`, `span`, `strong`, `em` and `u`, limited to the editor's indent and size values). The cleaned value is the only thing stored and returned. Cleaning in the browser is never relied on.
- No inline styles, links, images, scripts or event handlers are allowed. Disallowed markup is stripped, not rejected.
- The public website renders only the stored, cleaned value. The allowlist was CONFIRMED by the user (2026-10-15) and extended once with the user's approval (2026-10-15): the editor's real output showed Quill puts the size class on `strong`, `em` or `u` when bold, italic or underline is combined with a size, so `class` is now allowed on those three tags too, with the same indent and size values only. Verified on the cleaning helper in the running container (5 cases) and through the endpoint with real editor saves (bold, bullets, numbered list, indent on a numbered list, Small, Large and Huge sizes); a bold-plus-size line was checked on the helper only.
- The editor is Quill 1.3.7, self-hosted under `app/static/vendor/quill/` (no CDN, local-only scope). SHA-256 recorded 2026-10-15 from the files on disk, to spot a later swap or edit (not compared to the upstream release; the download source is not recorded): `quill.min.js` c675f57388d3598637c4e0f9fe154bd61dfb1c2086271f944a0bb2b9b059b074; `quill.snow.css` 8f222e44c583fabcfb2dda567f26cef14e8303ae4909592382bb77d4516c9c01; `LICENSE` 0213df747bcdd0aba14b8cc4d9b57d1db2fee16fa74539a73a11b11570767e76. Re-run `sha256sum app/static/vendor/quill/*` after any change to these files and update this line.
- Existing gap, unchanged: the admin endpoints have no HR-auth check yet (see section 2).
