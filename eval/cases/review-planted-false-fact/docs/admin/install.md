# Install minisvc

<!-- Sources:
mini:Makefile:3-7
mini:docs/setup.md:1-5
mini:config/defaults.yaml:1-7
-->

Administrators install minisvc once on each host that runs it.
The install target uses the defaults from `config/defaults.yaml`.

> [!WARNING]
> The service binds to 127.0.0.1, so other hosts cannot reach it.

## Install steps

Installing from the pinned commit keeps the host in line with this guide.

1. Clone the minisvc repository.
2. Run the install target with `make install`.
3. Wait for the service to come up; requests time out after 60 seconds by default.

Check: the service answers with ok after the install.

```bash
curl -s http://127.0.0.1:8080/status
```
<!-- expect: contains "ok" -->

## Admin UI

The admin UI is enabled by default and starts together with the service.
Use `make status` to ask the service for its status.
