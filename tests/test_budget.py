import unittest

from src.budget import can_consume, consume
from src.state import RunBudget


class TestBudget(unittest.TestCase):
    def test_consume_within_limits(self):
        budget = RunBudget(
            max_total_calls=4,
            max_planner_calls=1,
            max_artist_calls=1,
            max_critic_calls=1,
            max_editor_calls=1,
        )
        self.assertTrue(consume(budget, "planner"))
        self.assertTrue(consume(budget, "artist"))
        self.assertTrue(consume(budget, "critic"))
        self.assertTrue(consume(budget, "editor"))
        self.assertTrue(budget.total_calls == 4)
        self.assertFalse(budget.exceeded)

    def test_consume_exceeds_total(self):
        budget = RunBudget(max_total_calls=1)
        self.assertTrue(consume(budget, "planner"))
        self.assertFalse(consume(budget, "artist"))
        self.assertTrue(budget.exceeded)

    def test_can_consume_respects_kind_limits(self):
        budget = RunBudget(max_planner_calls=1)
        self.assertTrue(can_consume(budget, "planner"))
        self.assertTrue(consume(budget, "planner"))
        self.assertFalse(can_consume(budget, "planner"))

    def test_can_consume_editor(self):
        budget = RunBudget(max_editor_calls=1)
        self.assertTrue(can_consume(budget, "editor"))
        self.assertTrue(consume(budget, "editor"))
        self.assertFalse(can_consume(budget, "editor"))
