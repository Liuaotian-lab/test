# Security Policy

MM-AI OS processes user-provided problem statements, spreadsheets, documents, images, and archives. Treat all case inputs as untrusted.

## Supported security practices

- Archive extraction must reject path traversal and absolute paths.
- Agent-generated outputs should stay in allowed candidate/result/report paths unless promoted by OS gates.
- Secrets, private keys, `.env` files, and local credentials must not be committed.
- External tool or connector integrations should be mediated through explicit policy checks.

## Reporting

Please report suspected vulnerabilities by opening a private security advisory or contacting the repository maintainer.
