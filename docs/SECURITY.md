# Security & Privacy Policy

## 1. Resume File Upload Constraints
- **Storage Path:** `/data/resumes` (Docker volume / bind mount). Never served directly by Nginx or FastAPI static routes.
- **File Naming:** Files on disk must be named using a server-generated UUID (e.g., `<application_id>.pdf`). The original client-provided filename must only be stored in the Postgres database and sanitized before display.
- **File Type Enforcement:** PDF only. The application must verify the "magic bytes" (the first 4 bytes must be `b"%PDF"`) before writing the full file to disk. Relying solely on `Content-Type` headers or file extensions is prohibited.
- **Max File Size:** 5MB per resume. The API must stream the upload to disk and abort the transaction (deleting any partial file and returning 413) if the 5MB limit is breached, preventing memory exhaustion.
- **File Permissions:** Created files must have `0600` permissions. The directory must be `0700` (owned by the app's user).

## 2. Authentication & Admin Access
- **Mechanism:** HttpOnly, Secure, SameSite=Lax session cookies for the Admin panel. No raw JWTs in `localStorage`.
- **Credentials:** Passwords hashed using bcrypt (via `passlib`).
- **Rate Limiting (Admin):** Max 5 failed login attempts per minute per IP to prevent brute force.

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

## 6. Rich Text (Job Description and Requirements) Cleaning (DECIDED 2026-10-15, NOT implemented)
- The job description and the requirements are formatted text saved by an admin and shown to every visitor of the careers site, so they are untrusted input (stored XSS risk). Both fields get the same cleaning (decided 2026-10-15, user).
- The server cleans it on every write, in Python, with an allowlist (tags `p`, `br`, `ul`, `ol`, `li`, `strong`, `em`, `u`, `span`; attribute `class` only, limited to the editor's indent and size values). The cleaned value is the only thing stored and returned. Cleaning in the browser is never relied on.
- No inline styles, links, images, scripts or event handlers are allowed. Disallowed markup is stripped, not rejected.
- The public website renders only the stored, cleaned value. The allowlist is CONFIRMED by the user (2026-10-15) as written; it is extended only after the editor's real output is checked.
- Existing gap, unchanged: the admin endpoints have no HR-auth check yet (see section 2).
