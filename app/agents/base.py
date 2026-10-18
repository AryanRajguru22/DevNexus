class AgentError(Exception):
    """An agent could not complete its work (reported to the orchestrator, never raised to the client)."""
