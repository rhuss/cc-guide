# Relay

Relay is an open-source message relay that buffers events between services, so a
slow or restarting consumer never loses data. Producers write to Relay over HTTP,
and consumers read at their own pace; Relay keeps every event on disk until each
consumer has acknowledged it.

Teams use Relay to decouple services that would otherwise call each other directly
and fail together.
