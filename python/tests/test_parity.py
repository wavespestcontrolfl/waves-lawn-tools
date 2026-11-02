"""Every output of src/irrigation.js, reproduced exactly.

fixtures/irrigation_cases.json is written by fixtures/make_fixtures.js, which runs the
JavaScript over a varied list of inputs. Each case here must come out identical:
same keys, same values, same types (a number is a number, never a string or a bool).
"""

import json
import math
import re
import unittest
from pathlib import Path

from waves_lawn_tools import irrigation as w

FIXTURES = Path(__file__).parent / "fixtures" / "irrigation_cases.json"
DATA = json.loads(FIXTURES.read_text(encoding="utf-8"))

FUNCTIONS = {
    "deriveIrrigationInchesPerWeek": w.derive_irrigation_inches_per_week,
    "describeRuntimeBasis": w.describe_runtime_basis,
    "normalizeRuntimeInputs": w.normalize_runtime_inputs,
    "resolveApplicationRate": w.resolve_application_rate,
    "defaultEventMinutes": w.default_event_minutes,
    "buildWeekPlan": w.build_week_plan,
}


def snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def snake_keys(value):
    """camelCase JS keys to snake_case, all the way down (values stay as they are)."""
    if isinstance(value, dict):
        return {snake(k): snake_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [snake_keys(v) for v in value]
    return value


def call(case):
    fn = FUNCTIONS[case["fn"]]
    args = case["args"]
    if case["fn"] == "describeRuntimeBasis":
        return fn(snake_keys(args[0]) if args[0] is not None else None)
    if case["fn"] == "defaultEventMinutes":
        return fn(*args)
    kwargs = {}
    # the first object is the input; the second (derive, resolve) holds the options
    for given in args[:2]:
        kwargs.update({snake(k): v for k, v in given.items()})
    return fn(**kwargs)


def same(a, b, path="result"):
    """Strict deep equality. Returns None when equal, else a short description."""
    if isinstance(a, bool) or isinstance(b, bool):
        return None if (isinstance(a, bool) and isinstance(b, bool) and a is b) else f"{path}: {a!r} != {b!r}"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return None if a == b and not (math.isnan(a) or math.isnan(b)) else f"{path}: {a!r} != {b!r}"
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return f"{path}: keys {sorted(a)} != {sorted(b)}"
        for key in a:
            problem = same(a[key], b[key], f"{path}.{key}")
            if problem:
                return problem
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            problem = same(x, y, f"{path}[{i}]")
            if problem:
                return problem
        return None
    if type(a) is type(b) and a == b:
        return None
    return f"{path}: {a!r} != {b!r}"


class ParityWithJavaScript(unittest.TestCase):
    def test_the_fixtures_are_a_real_suite(self):
        self.assertGreaterEqual(len(DATA["cases"]), 1000)
        self.assertEqual(set(c["fn"] for c in DATA["cases"]), set(FUNCTIONS))

    def test_every_case_matches_the_javascript_output(self):
        failures = []
        for number, case in enumerate(DATA["cases"]):
            expected = snake_keys(case["result"])
            try:
                actual = call(case)
            except Exception as err:  # a crash is a mismatch too
                failures.append(f"case {number} {case['fn']} {json.dumps(case['args'])}: raised {err!r}")
                continue
            problem = same(actual, expected)
            if problem:
                failures.append(f"case {number} {case['fn']} {json.dumps(case['args'])}: {problem}")
        self.assertEqual(failures[:5], [], f"{len(failures)} of {len(DATA['cases'])} cases differ")

    def test_constants_match(self):
        constants = DATA["constants"]
        for name in (
            "HEAD_PRECIP_RATE_IN_PER_HR",
            "OWNER_MINUTES_PER_QUARTER_INCH",
            "OWNER_HEAD_RATE_IN_PER_HR",
            "HEAD_LABELS",
            "DAY_ALIASES",
            "MAX_RUN_MINUTES",
            "MAX_INCHES_PER_WEEK",
        ):
            self.assertIsNone(same(dict(getattr(w, name)) if hasattr(getattr(w, name), "items") else getattr(w, name), constants[name], name))
        self.assertEqual(list(w.DAY_KEYS), constants["DAY_KEYS"])
        plan_constants = {k: (dict(v) if hasattr(v, "items") else v) for k, v in w.WEEK_PLAN_CONSTANTS.items()}
        self.assertIsNone(same(plan_constants, constants["WEEK_PLAN_CONSTANTS"]))


if __name__ == "__main__":
    unittest.main()
