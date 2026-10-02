# minisvc guide

<!-- Sources:
mini:README.md:1-3
mini:config/defaults.yaml:2-4
mini:docs/setup.md:4
-->

This guide explains how to install and use minisvc {{attr:mini-version}}.
It has one part for administrators and one part for users.

:::note
Every statement in this guide was checked against the pinned minisvc sources.
:::

## Where to start

- Administrators start with [Install minisvc](admin/install.md).
- Users start with [Get started](user/start.md).

## Status history

:::experimental feature="Status history" pr=4 anchor=status-history tier=in-review

A proposed change adds a history of earlier status answers.

## Check the service

Check: the service answers on its status endpoint.

```bash
curl -s http://127.0.0.1:9090/status
```
<!-- expect: contains "ok" -->
