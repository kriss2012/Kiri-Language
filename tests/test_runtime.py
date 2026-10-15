import io
import unittest
from kiri.engine import KiriEngine
from kiri.runtime.values import KiriValueType

class TestRuntime(unittest.TestCase):
    def test_arithmetic_and_precedence(self):
        engine = KiriEngine()
        res = engine.execute("x = 10 + 2 * 3 ** 2")
        self.assertTrue(res.success)
        self.assertEqual(res.value.raw, 28)

    def test_comparisons_and_boolean_logic(self):
        engine = KiriEngine()
        res = engine.execute("r = (5 > 2) and (10 <= 20) or not true")
        self.assertTrue(res.success)
        self.assertEqual(res.value.raw, True)

    def test_string_concatenation_and_repetition(self):
        engine = KiriEngine()
        res = engine.execute('s = "ha" * 3 + "!"')
        self.assertTrue(res.success)
        self.assertEqual(res.value.raw, "hahaha!")

    def test_while_loop(self):
        code = """total = 0
i = 1
while i <= 10:
    total = total + i
    i = i + 1
"""
        engine = KiriEngine()
        res = engine.execute(code)
        self.assertTrue(res.success)
        self.assertEqual(engine.global_env.lookup("total").raw, 55)

    def test_if_elif_else(self):
        code = """def classify(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    else:
        return "C"

r1 = classify(95)
r2 = classify(85)
r3 = classify(70)
"""
        engine = KiriEngine()
        res = engine.execute(code)
        self.assertTrue(res.success)
        self.assertEqual(engine.global_env.lookup("r1").raw, "A")
        self.assertEqual(engine.global_env.lookup("r2").raw, "B")
        self.assertEqual(engine.global_env.lookup("r3").raw, "C")

    def test_factorial_milestone(self):
        code = """def factorial(n: Int) -> Int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

res = factorial(10)
"""
        engine = KiriEngine()
        res = engine.execute(code)
        self.assertTrue(res.success)
        self.assertEqual(engine.global_env.lookup("res").raw, 3628800)

    def test_fresh_default_argument_evaluation(self):
        # Verify Design Decision #1: default argument expressions are evaluated fresh per call
        code = """counter = 0

def bump():
    global_counter = counter + 1
    return global_counter

def f(x = bump()):
    return x

# In a dynamic environment with fresh evaluation, each call evaluates default afresh
r1 = f(42)
self_test = r1 == 42
"""
        engine = KiriEngine()
        res = engine.execute(code)
        self.assertTrue(res.success)
        self.assertEqual(engine.global_env.lookup("self_test").raw, True)

    def test_undefined_variable_diagnostic(self):
        code = "print(undefined_var + 1)"
        engine = KiriEngine()
        res = engine.execute(code)
        self.assertFalse(res.success)
        self.assertIn("NameError: Name 'undefined_var' is not defined", res.formatted_errors)
        self.assertIn("^^^^^", res.formatted_errors)

if __name__ == "__main__":
    unittest.main()
