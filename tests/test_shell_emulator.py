"""Verify emulator commands without opening a window."""

import unittest
from pathlib import Path

from shell_emulator.emulator import Shell, load_vfs, run_startup_script


EMULATOR = Path(__file__).resolve().parents[1] / "shell_emulator"


class ShellTests(unittest.TestCase):
    """Exercise directory navigation, validation, and startup scripts."""

    def setUp(self):
        """Connect the shell to in-memory output and exit callbacks."""
        self.output = []
        self.exits = []
        vfs = load_vfs(EMULATOR / "vfs")
        self.shell = Shell(vfs, self.output.append, self.record_exit)

    def record_exit(self):
        """Record the exit request so the test can check it."""
        self.exits.append(True)

    def test_ls_and_cd(self):
        """List the current directory and navigate back to its parent."""
        for command in ("ls", "cd docs", "ls", "cd inner", "cd ..", "cd /"):
            self.shell.execute_line(command)
        self.assertIn("docs\n", self.output)
        self.assertIn("inner\n", self.output)
        self.assertEqual(self.shell.current_path, [])

    def test_argument_and_file_errors(self):
        """Reject bad arguments and attempts to enter files."""
        for command in ("cd", "ls docs", "cd Regression.txt", "badcommand"):
            self.shell.execute_line(command)
        errors = "".join(self.output)
        self.assertIn("команда cd требует один аргумент", errors)
        self.assertIn("команда ls не принимает аргументы", errors)
        self.assertIn("не является директорией", errors)
        self.assertIn("неизвестная команда", errors)
        self.assertEqual(self.shell.current_path, [])

    def test_startup_and_exit(self):
        """Execute the startup script and close only on a valid exit."""
        run_startup_script(
            EMULATOR / "startup.txt", self.shell.execute_line,
            self.output.append,
        )
        self.assertEqual(self.shell.current_path, ["docs"])
        self.shell.execute_line("exit now")
        self.assertEqual(self.exits, [])
        self.shell.execute_line("exit")
        self.assertEqual(self.exits, [True])


if __name__ == "__main__":
    unittest.main()
