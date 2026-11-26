---
description: "Evolve a guide after its sources changed: drift report, targeted page updates with reviews, new baseline"
argument-hint: "[--help] [--check] [--adopt] [--pages] [--visuals] [--to ID=REF]... [--input PATH]... [--rigor fast|standard|strict] [--dir PATH]"
---

When the arguments contain `--help` or `-h`, do not run preflight and check nothing: use the `guide:evolve` skill with `--help` only, which prints its help and stops.

Otherwise, use the `guide:preflight` skill with the command `evolve` and these arguments (superpowers is not required with `--check`, `--pages`, or `--visuals`), and stop if it stops. Then use the `guide:evolve` skill. Pass `$ARGUMENTS` as the skill arguments.
