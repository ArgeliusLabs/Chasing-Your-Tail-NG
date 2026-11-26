"""Keep known limitations visible as the recurrence policy changes."""
import unittest

from cyt_core.recurrence import summarize
from research.evaluate_route_cases import cases, evaluate


class RouteCounterexamples(unittest.TestCase):
    def test_policy_counterexamples(self):
        for row in evaluate()["cases"]:
            with self.subTest(case=row["case"]):
                self.assertTrue(row["policy_pass"], row)

    def test_intent_and_transmitter_movement_are_not_observable(self):
        scenarios = {name: observations for name, observations, _, _ in cases()}
        results = [summarize(scenarios[name], at=1200) for name in
                   ("persistent_hotspot", "consenting_companion", "fixed_ap_heard_across_route")]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])
        self.assertNotIn("threat_probability", results[0])


if __name__ == "__main__":
    unittest.main()
