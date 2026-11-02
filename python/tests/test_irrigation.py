import unittest

from waves_lawn_tools import irrigation as w


class RuntimeToInches(unittest.TestCase):
    def test_20_minutes_once_a_week_on_spray_heads_is_half_an_inch(self):
        r = w.derive_irrigation_inches_per_week(run_minutes=20, watering_days=["Sat"], system_type="spray")
        self.assertEqual(r["inches_per_week"], 0.5)
        self.assertEqual(r["rate_in_per_hr"], 1.5)
        self.assertIsNone(r["reason"])

    def test_60_minutes_twice_a_week_on_rotors_is_one_inch(self):
        r = w.derive_irrigation_inches_per_week(run_minutes=60, watering_days=["Tue", "Sat"], system_type="rotor")
        self.assertEqual(r["inches_per_week"], 1)
        self.assertEqual(r["runs_per_week"], 2)

    def test_drip_waters_beds_not_turf_so_it_declines_instead_of_guessing(self):
        r = w.derive_irrigation_inches_per_week(run_minutes=20, watering_days=["Sat"], system_type="drip")
        self.assertIsNone(r["inches_per_week"])
        self.assertEqual(r["reason"], "drip_only")

    def test_mixed_heads_and_missing_inputs_decline_with_a_reason(self):
        days = ["Mon"]
        self.assertEqual(w.derive_irrigation_inches_per_week(30, days, ["spray", "rotor"])["reason"], "mixed_head_types")
        self.assertEqual(w.derive_irrigation_inches_per_week(None, days, "spray")["reason"], "missing_minutes")
        self.assertEqual(w.derive_irrigation_inches_per_week(30, [], "spray")["reason"], "missing_days")
        self.assertEqual(w.derive_irrigation_inches_per_week(30, days, None)["reason"], "missing_head_type")
        self.assertEqual(w.derive_irrigation_inches_per_week(30, days, "sprinkler")["reason"], "unknown_head_type")

    def test_an_implausible_total_declines(self):
        r = w.derive_irrigation_inches_per_week(240, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "spray")
        self.assertEqual(r["reason"], "implausible_total")

    def test_full_day_names_and_json_strings_are_accepted_but_prefixes_are_not(self):
        self.assertEqual(w.normalize_runtime_inputs(watering_days=["Monday", " thurs "])["watering_days"], ["Mon", "Thu"])
        self.assertEqual(w.normalize_runtime_inputs(watering_days='["Sun","Sat"]')["watering_days"], ["Sat", "Sun"])
        self.assertEqual(w.normalize_runtime_inputs(watering_days=["monthly", "sunny"])["watering_days"], [])

    def test_describe_runtime_basis(self):
        derived = w.derive_irrigation_inches_per_week(20, ["Mon", "Thu", "Sat", "Sun"], "spray")
        self.assertEqual(w.describe_runtime_basis(derived), "20 minutes per zone, 4 days a week on spray heads")
        one = w.derive_irrigation_inches_per_week(60, ["Sat"], "rotor")
        self.assertEqual(w.describe_runtime_basis(one), "60 minutes per zone, 1 day a week on rotor heads")
        self.assertIsNone(w.describe_runtime_basis(None))

    def test_ignore_drip_leaves_drip_out_of_the_head_count(self):
        r = w.derive_irrigation_inches_per_week(20, ["Sat"], ["spray", "drip"], ignore_drip=True)
        self.assertEqual(r["inches_per_week"], 0.5)
        r = w.derive_irrigation_inches_per_week(20, ["Sat"], ["spray", "drip"])
        self.assertEqual(r["reason"], "mixed_head_types")


class JavaScriptRounding(unittest.TestCase):
    def test_halves_round_up_like_math_round_not_to_even(self):
        self.assertEqual(round(20.5), 20)
        # 20.5 minutes: Python's round(20.5) is 20; JavaScript's Math.round gives 21.
        self.assertEqual(w.derive_irrigation_inches_per_week(20.5, ["Sat"], "spray")["run_minutes"], 21)
        self.assertEqual(w.derive_irrigation_inches_per_week(240.4, ["Sat"], "spray")["run_minutes"], 240)
        self.assertEqual(w.derive_irrigation_inches_per_week(240.5, ["Sat"], "spray")["reason"], "missing_minutes")

    def test_js_round_matches_math_round_including_negatives(self):
        js_round = w._js_round
        self.assertEqual([js_round(x) for x in (0.5, 1.5, 2.5, 3.5)], [1, 2, 3, 4])
        self.assertEqual([js_round(x) for x in (-0.5, -1.5, -2.5, -3.5)], [0, -1, -2, -3])
        self.assertEqual([js_round(x) for x in (-0.4, -0.6, 0.4, 0.6, 2.4999999999999996)], [0, -1, 0, 1, 2])
        self.assertEqual(js_round(0.49999999999999994), 0)  # floor(x + 0.5) would say 1
        self.assertEqual(js_round(4503599627370497), 4503599627370497)

    def test_js_number_coerces_like_number(self):
        n = w._js_number
        self.assertEqual([n(None), n(""), n(" 12 "), n("0x10"), n("1e1"), n(True), n([20]), n([])], [0, 0, 12, 16, 10, 1, 20, 0])
        for junk in ("abc", "1,2", [1, 2], {}, "1_0", "inf", "nan", "٣"):
            self.assertNotEqual(n(junk), n(junk), junk)  # NaN
        self.assertEqual(n("Infinity"), float("inf"))


class WeekPlan(unittest.TestCase):
    DRY = dict(
        target_inches_per_week=0.75,
        last_week_rain_inches=0.2,
        forecast_rain_inches=0,
        season="peak",
        restriction={"max_days_per_week": 1},
        system_type=["spray"],
        rain_known=True,
        rain_only_carryover=True,
    )

    def test_a_dry_week_under_a_one_day_limit_one_watering(self):
        p = w.build_week_plan(**self.DRY)
        self.assertEqual(p["action"], "run")
        self.assertEqual(p["events"], 1)
        self.assertEqual(p["legal_max_events"], 1)
        self.assertEqual(p["depth_inches"], 0.75)
        self.assertEqual(p["minutes_per_event"], 30)  # 0.75 in at 1.5 in/hr is 30 minutes

    def test_a_soaked_week_carries_over_and_holds_the_watering(self):
        p = w.build_week_plan(**{**self.DRY, "last_week_rain_inches": 2.4, "last_week_target_inches": 0.75, "forecast_rain_inches": 0.1})
        self.assertEqual(p["action"], "hold")
        self.assertEqual(p["events"], 0)
        self.assertIn("prior_week_rain_surplus", p["reasons"])

    def test_no_legal_watering_policy_means_no_plan_never_an_invented_limit(self):
        p = w.build_week_plan(target_inches_per_week=0.75, season="peak", restriction=None)
        self.assertEqual(p["action"], "unavailable")
        self.assertEqual(p["reasons"], ["restriction_policy_missing"])

    def test_the_javascript_style_restriction_key_works_too(self):
        p = w.build_week_plan(**{**self.DRY, "restriction": {"maxDaysPerWeek": 1}})
        self.assertEqual(p["legal_max_events"], 1)

    def test_a_forecast_of_half_an_inch_makes_the_run_conditional(self):
        p = w.build_week_plan(**{**self.DRY, "forecast_rain_inches": 0.5})
        self.assertEqual(p["action"], "run")
        self.assertTrue(p["conditional_on_forecast"])
        self.assertIn("forecast_rain", p["reasons"])

    def test_a_ban_holds_even_a_thirsty_lawn(self):
        p = w.build_week_plan(**{**self.DRY, "restriction": {"max_days_per_week": 0}})
        self.assertEqual(p["action"], "hold")
        self.assertIn("restriction_prohibits", p["reasons"])

    def test_a_measured_rate_gives_whole_minutes(self):
        p = w.build_week_plan(**{**self.DRY, "run_minutes": 20, "watering_days": ["Sat"], "explicit_inches_per_week": 0.7})
        self.assertEqual(p["rate_source"], "measured")
        self.assertEqual(p["confidence"], "high")
        self.assertIsInstance(p["minutes_per_event"], int)

    def test_default_minutes_for_a_half_inch_watering(self):
        self.assertEqual(w.default_event_minutes(), {"spray": 20, "rotor": 60})
        self.assertEqual(w.default_event_minutes(w.OWNER_HEAD_RATE_IN_PER_HR), {"spray": 30, "rotor": 80})

    def test_the_constants_are_read_only(self):
        with self.assertRaises(TypeError):
            w.HEAD_PRECIP_RATE_IN_PER_HR["spray"] = 9
        self.assertEqual(dict(w.OWNER_HEAD_RATE_IN_PER_HR), {"spray": 1.0, "rotor": 0.375})


if __name__ == "__main__":
    unittest.main()
