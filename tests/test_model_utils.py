import unittest

from src.model_utils import model_dump, update_model


class DummyModel:
    def __init__(self, **values):
        self._values = dict(values)

    def model_copy(self, update=None):
        updated = dict(self._values)
        if update:
            updated.update(update)
        return DummyModel(**updated)

    def model_dump(self):
        return dict(self._values)


class LegacyModel:
    def __init__(self, **values):
        self._values = dict(values)

    def copy(self, update=None):
        updated = dict(self._values)
        if update:
            updated.update(update)
        return LegacyModel(**updated)

    def dict(self):
        return dict(self._values)


class TestModelUtils(unittest.TestCase):
    def test_update_model_with_model_copy(self):
        model = DummyModel(value="old")
        updated = update_model(model, {"value": "new"})
        self.assertEqual(model_dump(updated)["value"], "new")

    def test_update_model_with_copy(self):
        model = LegacyModel(value="old")
        updated = update_model(model, {"value": "new"})
        self.assertEqual(model_dump(updated)["value"], "new")
