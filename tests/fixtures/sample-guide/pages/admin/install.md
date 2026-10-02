# Install minisvc

<!-- Sources:
mini:Makefile:3-4
mini:docs/setup.md:1-5
mini:config/defaults.yaml:2-4,6-7
-->

Administrators install minisvc once on each host that runs it.
The install target uses the defaults from `config/defaults.yaml`.

:::warning
The service binds to 127.0.0.1, so other hosts cannot reach it.
:::

## Install steps

Installing from the pinned commit keeps the host in line with this guide.

1. Clone the minisvc repository and check out commit {{attr:mini-commit-short}}.
2. Run the install target.

```bash
make install
```

Check: the service answers with ok after the install.

```bash
curl -s http://127.0.0.1:9090/status
```
<!-- expect: contains "ok" -->

## Admin UI

:::experimental feature="Admin UI" pr=5 anchor=admin-ui tier=on-main

The admin UI is off by default.
Continue with [Get started](../user/start.md) to hand the service over to its users.
