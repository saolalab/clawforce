"""Resource-level authorization: agent ownership and access checks."""

from fastapi import HTTPException, status

from clawforce.core.domain.agent import AgentDef


def can_access_agent(user: dict, agent: AgentDef) -> bool:
    """Return True if user is allowed to access this agent.

    All admin users can access agents they own (or unowned agents).
    Ownership is enforced only when agent.owner_user_id is set.
    """
    if agent.owner_user_id and agent.owner_user_id != user.get("id"):
        return False
    return True


def require_agent_access(user: dict, agent: AgentDef) -> None:
    """Raise 403 if user cannot access agent. Call after fetching agent."""
    if not can_access_agent(user, agent):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this agent"
        )
