"""Plan access control: enforce agent assignment for plan operations."""

from fastapi import HTTPException, status


def require_plan_access(plan, caller: dict) -> None:
    """Raise 403 if caller is an agent not assigned to the plan.

    Users (admins) have full access. Agents must be in plan.agent_ids.
    """
    if caller.get("type") == "user":
        return
    if (
        caller.get("type") == "agent"
        and plan
        and caller.get("agent_id") not in (plan.agent_ids or [])
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent is not assigned to this plan",
        )
