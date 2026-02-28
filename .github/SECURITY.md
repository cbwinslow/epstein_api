# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please send an email to the maintainer or open a GitHub issue with the label `security`.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Requirements

### Dependencies
- All dependencies must be pinned in `pyproject.toml`
- Run security audits regularly: `pip-audit` or `safety`
- Update dependencies frequently

### Secrets
- NEVER commit secrets to git (API keys, passwords, tokens)
- Use environment variables or secrets management
- Use `.env.example` for required variables (no real values)

### SQL Security
- NEVER use f-strings or string concatenation for SQL queries
- ALWAYS use parameterized queries
- All SQL MUST go through the migrations module

### Rate Limiting
- Implement exponential backoff for retries
- Add timeouts to all network calls
- Limit request sizes
