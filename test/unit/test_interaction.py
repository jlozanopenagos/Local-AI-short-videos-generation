"""
test/unit/test_interaction.py — Unit tests for interaction provider layer.
"""

import unittest
from core.interaction import (
    InteractionProvider,
    CliInteractionProvider,
    PresetInteractionProvider,
    get_interaction,
    set_interaction,
)


class TestInteractionLayer(unittest.TestCase):
    def setUp(self):
        self.original_provider = get_interaction()

    def tearDown(self):
        set_interaction(self.original_provider)

    def test_preset_interaction_provider_choice(self):
        provider = PresetInteractionProvider(presets={"mode": "2"}, auto_default=True)
        choice = provider.ask_choice("Select mode", valid_choices=["1", "2", "3"], default="1")
        self.assertEqual(choice, "2")

    def test_preset_interaction_provider_default_fallback(self):
        provider = PresetInteractionProvider(presets={}, auto_default=True)
        choice = provider.ask_choice("Select mode", valid_choices=["1", "2", "3"], default="1")
        self.assertEqual(choice, "1")

    def test_preset_interaction_provider_confirm(self):
        provider = PresetInteractionProvider(presets={"overwrite": True})
        self.assertTrue(provider.confirm("Overwrite existing files?"))
        provider_no = PresetInteractionProvider(presets={"overwrite": False})
        self.assertFalse(provider_no.confirm("Overwrite existing files?"))

    def test_get_and_set_interaction(self):
        mock_p = PresetInteractionProvider()
        set_interaction(mock_p)
        self.assertIs(get_interaction(), mock_p)
