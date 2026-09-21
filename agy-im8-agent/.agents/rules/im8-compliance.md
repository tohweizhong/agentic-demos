---
trigger: always_on
description: "Singapore Government IM8 Security and Privacy Rules"
---

# Singapore Government IM8 Compliance Standards

## 1. Secrets Management
Never place plaintext API keys, passwords, or tokens in source code or YAML files. Always read secrets from environment variables or Google Cloud Secret Manager.

## 2. Personal Data Protection
Never log unmasked Singapore NRIC numbers or citizen mobile numbers. Mask NRIC numbers so that only the last four characters are visible (e.g., `SXXXX567A`).

## 3. API Security
Do not expose administrative debug endpoints in production builds. Require authentication for every route that handles citizen records.

## 4. Cloud Infrastructure
Ensure Google Cloud Storage buckets have `public_access_prevention` set to `enforced`. Never assign roles to `allUsers` or `allAuthenticatedUsers`.
