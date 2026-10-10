# Corral

Corral is a runtime that runs untrusted programs in isolated sandboxes. Each sandbox
gets only the files, processes, and network destinations that its policy declares,
and Corral enforces that policy on every connection that leaves the sandbox.

Use Corral when a program needs real capabilities (files, network, credentials) but
must not get unrestricted access to your systems.
