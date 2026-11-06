import unittest

from runtime_check import is_supported_python


class RuntimeVersionTests(unittest.TestCase):
    def test_rejects_python_310(self):
        self.assertFalse(is_supported_python((3, 10)))

    def test_accepts_python_311(self):
        self.assertTrue(is_supported_python((3, 11)))

    def test_accepts_newer_python(self):
        self.assertTrue(is_supported_python((3, 14)))


if __name__ == "__main__":
    unittest.main()
