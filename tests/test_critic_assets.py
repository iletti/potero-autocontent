import unittest

from src.critic_assets import select_critic_reference_assets


class TestCriticAssets(unittest.TestCase):
    def test_filters_to_design_roles(self):
        assets = [
            "/repo/assets/references/ENV_CQB_OSB/cqb_osb_01.jpg",
            "/repo/assets/references/hoodies/reaper_vintage_black_front.png",
            "/repo/assets/references/GEAR_HELMET_HIGH_CUT/helmet_high_cut_01.png",
        ]
        role_map = {
            assets[0]: "ENV_CQB_OSB",
            assets[1]: "DESIGN_FRONT",
            assets[2]: "GEAR_HELMET_HIGH_CUT",
        }
        selected = select_critic_reference_assets(assets, role_map)
        self.assertEqual(selected, [assets[1]])

    def test_falls_back_to_hoodies_path(self):
        assets = [
            "/repo/assets/references/hoodies/reaper_vintage_black_back.png",
            "/repo/assets/references/ENV_CQB_OSB/cqb_osb_01.jpg",
        ]
        selected = select_critic_reference_assets(assets, {})
        self.assertEqual(selected, [assets[0]])
