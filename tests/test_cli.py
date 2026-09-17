import unittest
from unittest.mock import patch
import io
import sys

from gemini_web2api.cli import cmd_status, cmd_client, cmd_logout, cmd_config
from gemini_web2api.config import CONFIG


class CLITests(unittest.TestCase):
    def setUp(self):
        self.original_config = dict(CONFIG)

    def tearDown(self):
        CONFIG.clear()
        CONFIG.update(self.original_config)

    def test_cmd_status_output(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            cmd_status()
        output = stdout.getvalue()
        self.assertIn("Gemini Web2API Status", output)
        self.assertIn("Authentication", output)

    def test_cmd_client_output(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            cmd_client()
        output = stdout.getvalue()
        self.assertIn("Cherry Studio", output)
        self.assertIn("OpenAI Python SDK", output)
        self.assertIn("curl", output)

    def test_cmd_logout(self):
        CONFIG["cookie_file"] = "/tmp/fake-cookie.txt"
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            cmd_logout()
        self.assertIsNone(CONFIG.get("cookie_file"))
        self.assertIn("Logged out successfully", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
