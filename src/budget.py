from typing import Optional

from src.state import RunBudget


def can_consume(budget: RunBudget, kind: str, amount: int = 1) -> bool:
    if budget.exceeded:
        return False
    if amount <= 0:
        return True
    total_after = budget.total_calls + amount
    if total_after > budget.max_total_calls:
        return False
    if kind == "planner":
        return budget.planner_calls + amount <= budget.max_planner_calls
    if kind == "artist":
        return budget.artist_calls + amount <= budget.max_artist_calls
    if kind == "critic":
        return budget.critic_calls + amount <= budget.max_critic_calls
    if kind == "editor":
        return budget.editor_calls + amount <= budget.max_editor_calls
    return True


def consume(budget: RunBudget, kind: str, amount: int = 1) -> bool:
    if not can_consume(budget, kind, amount):
        budget.exceeded = True
        return False
    budget.total_calls += amount
    if kind == "planner":
        budget.planner_calls += amount
    elif kind == "artist":
        budget.artist_calls += amount
    elif kind == "critic":
        budget.critic_calls += amount
    elif kind == "editor":
        budget.editor_calls += amount
    return True
