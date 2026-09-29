---
trigger: always_on
description: "IM8 Reform controls enforced by this lab"
---

# IM8 Reform controls in scope

This lab enforces four controls from the public Singapore Government ICT&SS
Policy (IM8 Reform) control catalog.

Source: https://github.com/GovTechSG/tech-standards, `catalogs/im8-reform.json`,
version 2025.05.13, MIT licence.

The full Instruction Manual 8 is not public. Only the IM8 Reform catalog for
low-risk cloud systems is published. Cite a control only if it appears in that
catalog. Never invent a control identifier.

## as-8 Secrets Management
Store secrets in a secrets management solution with access control, encryption,
and monitoring. Do not store secrets unencrypted in source code or in
configuration files.

## lm-19 Log Sanitisation
Sanitise logs to protect classified and sensitive data before any logging system
records it. Mask personal data, credentials, and API keys.

## as-13 Exposure of Internal System Details
Prevent the unnecessary disclosure of internal system details to end users. Do
not expose debug information, stack traces, or version strings.

## ns-2 Access Restrictions on CSP Resources Outside Virtual Network
Restrict access to cloud provider resources outside a virtual network. Restrict
object storage buckets with IAM policies and block public access from the
internet.
