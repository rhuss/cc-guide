# Relay recipe

This recipe deploys Relay, a logging tool, on the platform.

Everything lives in `relay/`. The `deploy/` directory holds the manifests and the
`Containerfile.corral` that builds a Corral sandbox image for the same Relay.

## Ways to run it

1. Raw manifests (recommended): `kubectl apply -k deploy/`. The Deployment runs one
   replica, and its state sits on a PersistentVolumeClaim.
2. Corral sandbox (experimental): build `deploy/Containerfile.corral`, push it, and
   create a sandbox from it. The sandbox policy blocks all network egress by default.

## Support

The Relay image is published by the Relay community, not by the kit maintainers.
