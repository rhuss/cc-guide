# Internal notes

<!-- Sources:
input:customer-notes
input:walkthrough
mini:config/defaults.yaml:6-7
-->

These notes are for the minisvc team only.
ACME Corp is the first customer, and the rollout questions are tracked in MINI-42.

:::caution
Do not share these notes outside the team.
:::

## Corrections to the walkthrough

The walkthrough said that an admin UI listens on port 7070 and starts with the service.
No pinned source supports this, and `config/defaults.yaml` turns the admin UI off by default.

:::experimental feature="Admin UI" pr=5 anchor=admin-ui tier=on-main

Check: nothing answers on port 7070 on a default install.

```bash
curl -s http://127.0.0.1:7070/
```
<!-- expect: exit 7 -->

The fixture baseline was captured on {{attr:baseline-date}}.
