"""Domain exceptions surfaced to HTTP clients."""


class InfraUnavailableError(Exception):
    """PostgreSQL, Redis, or Qdrant is required but unreachable."""
