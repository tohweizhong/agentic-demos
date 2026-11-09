---
name: geap-doctor
description: Runs the posture check to find stale IAM grants and missing gateway bindings.
---
# GEAP Doctor

This skill runs `scripts/doctor.sh`.

## Steps
1. Run `scripts/doctor.sh --project <PROJECT_ID> --region <REGION>`.
2. Review the output.
3. Remove stale grants if you find them.
