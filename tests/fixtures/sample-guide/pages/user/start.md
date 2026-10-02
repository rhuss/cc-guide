# Get started

<!-- Sources:
mini:docs/setup.md:4
mini:config/defaults.yaml:3-4
url:https://example.com/minisvc
-->

Users talk to minisvc through its status endpoint on port 9090.
Ask your administrator for access to the host, because the service only listens there.

:::tip
On the host, `make status` is a shortcut for the request below.
:::

## Ask for the status

Check: the status endpoint answers with ok.

```bash
curl -s http://127.0.0.1:9090/status
```
<!-- expect: contains "ok" and lines == 1 -->

## Status history

:::experimental feature="Status history" pr=4 anchor=status-history tier=in-review

The proposed history would show earlier answers next to the current one.

:::important
The status answer describes the service at baseline {{attr:baseline-date}}.
:::
