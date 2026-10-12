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
