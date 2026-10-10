# Relay on the platform

<!-- Sources:
kit:relay/README.md:1-17
kit:relay/deploy/deployment.yaml:6-9,13-15
-->

The kit ships a recipe for running Relay on the platform.
The recipe describes Relay as a logging tool.

All of it lives in `relay/`, and the `deploy/` directory holds the manifests and the `Containerfile.corral`.
The Deployment runs one replica with the Recreate strategy, its container listens on port 7400, and its state sits on a PersistentVolumeClaim.

## Two ways to run it

**Raw manifests.** The recipe recommends this way: apply everything with `kubectl apply -k deploy/`.

**Corral sandbox.** The second way runs Relay in a Corral sandbox, which the recipe marks as experimental.
You build `deploy/Containerfile.corral` and push it.
One catch: the sandbox policy blocks all network egress by default.

!!! important

    The Relay image is published by the Relay community, not by the kit maintainers.

## Find your part of the guide

- Administrators start with the [Administrator guide](admin/index.md).
- Users start with the [User guide](user/index.md).
