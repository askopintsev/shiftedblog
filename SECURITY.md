# Security Policy

## Supported versions

Security fixes are applied on the default branch (`master`). Self-hosters should pull and redeploy regularly.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email the maintainer at the address listed in the repository profile / site contact, with:

- A clear description of the issue
- Steps to reproduce (or a proof of concept)
- Impact assessment if known
- Whether you are willing to be credited

You can expect an acknowledgement within a few days when possible. Please allow time for a fix before public disclosure.

## Hardening tips for self-hosters

- Set a strong `SECRET_KEY` and rotate it periodically (`SECRET_KEY_ROTATED_AT`)
- Change `ADMIN_URL` from the default and enable 2FA for staff accounts
- Keep `DEBUG=False` in production and restrict `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`
- Store production secrets in `secrets.env` (or a secret manager), never in git
- See [docs/security-runbook.md](docs/security-runbook.md) for operational notes
