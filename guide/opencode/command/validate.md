---
description: "Validate the guide's commands against a live cluster (read-only by default; full tier only on disposable clusters)"
argument-hint: "--cluster NAME [--tier read-only|full] [--page PATH]... [--dir PATH]"
---

Use the `guide:preflight` skill with the command `validate` and these arguments, and stop if it stops. Then use the `guide:validate` skill. Pass `$ARGUMENTS` as the skill arguments.
