# Security Policy

## Supported versions

Security fixes are applied to the latest commit on `main`.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Prefer one of:

1. GitHub Security Advisories for this repository (Private vulnerability reporting), or
2. Contact the maintainer via GitHub (`@shahshrey`) with a private message / email listed on the profile.

Include:

- Description of the issue and impact
- Steps to reproduce
- Affected skill / script paths
- Whether any secrets, training data, or user photos could be exposed

You should receive an acknowledgement within a few business days.

## Secrets and personal data

- Never commit `FAL_KEY`, `FAL_API_KEY`, or `.env` files.
- Never commit personal portrait datasets, contact sheets of private photos, or training result URLs you consider sensitive.
- Paid training submission must remain gated behind explicit user confirmation.

## Safe defaults

If you find a change that weakens validation (for example, accepting captions that do not start with `[trigger]`, or submitting training without `--yes`), treat that as a security/safety regression and report it.
