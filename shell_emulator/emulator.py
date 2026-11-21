"""Run the interactive GUI shell for the virtual file system."""

import os
import sys


STARTUP_DELAY_MS = 100
EXIT_DELAY_MS = 1000


def build_tree(current_path):
    """Represent directories as dictionaries and files as None."""
    tree = {}
    for item in os.listdir(current_path):
        full_path = os.path.join(current_path, item)
        if os.path.isdir(full_path):
            tree[item] = build_tree(full_path)
        else:
            tree[item] = None
    return tree


def load_vfs(path):
    """Load the directory used by the emulator."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"VFS не найдена: {path}")
    if not os.path.isdir(path):
        raise ValueError("VFS должна быть директорией")
    return build_tree(path)


class Shell:
    """Keep the virtual working directory and dispatch shell commands."""

    def __init__(self, vfs, write, finish):
        """Connect the shell to the output and exit callbacks."""
        self.vfs = vfs
        self.current_path = []
        self.write = write
        self.finish = finish
        self.commands = {
            "ls": self.list_directory,
            "cd": self.change_directory,
            "exit": self.exit_shell,
        }

    def get_current_dir(self):
        """Follow the current path from the root of the VFS."""
        current = self.vfs
        for part in self.current_path:
            current = current[part]
        return current

    def execute_line(self, command_line):
        """Echo the command line and invoke its handler."""
        prompt = "/" + "/".join(self.current_path)
        self.write(f"{prompt}$ {command_line}\n")
        parts = command_line.split()
        if not parts:
            return

        command, *args = parts
        handler = self.commands.get(command)
        if handler is None:
            self.write(f"Ошибка: неизвестная команда '{command}'\n")
            return
        handler(args)

    def list_directory(self, args):
        """Print the files and directories in the current directory."""
        if args:
            self.write("Ошибка: команда ls не принимает аргументы\n")
            return
        for name in self.get_current_dir():
            self.write(f"{name}\n")

    def change_directory(self, args):
        """Move to the parent directory, the root, or a named child."""
        if len(args) != 1:
            self.write("Ошибка: команда cd требует один аргумент\n")
            return
        target = args[0]
        if target == "..":
            if self.current_path:
                self.current_path.pop()
        elif target == "/":
            self.current_path.clear()
        else:
            self.enter_child(target)

    def enter_child(self, target):
        """Enter a child directory after checking its type."""
        current = self.get_current_dir()
        if target not in current:
            self.write(f"Ошибка: директория '{target}' не найдена\n")
        elif current[target] is None:
            self.write(f"Ошибка: '{target}' не является директорией\n")
        else:
            self.current_path.append(target)

    def exit_shell(self, args):
        """Request that the emulator window close."""
        if args:
            self.write("Ошибка: команда exit не принимает аргументы\n")
            return
        self.write("Выход...\n")
        self.finish()


def run_startup_script(path, execute_line, write):
    """Execute the nonblank lines of the startup script in order."""
    if not os.path.isfile(path):
        write(f"Ошибка: стартовый скрипт '{path}' не найден\n")
        return

    write("Запуск стартового скрипта...\n\n")
    with open(path, encoding="utf-8") as script:
        for line in script:
            command_line = line.strip()
            if command_line:
                execute_line(command_line)
    write("\nСтартовый скрипт завершён\n\n")


def run_gui(vfs_path, startup_script, vfs):
    """Connect a Tkinter window to the command handlers."""
    import tkinter as tk

    root = tk.Tk()
    root.title(f"VFS Emulator - {vfs_path}")
    output = tk.Text(root, height=25, width=80)
    output.pack()
    entry = tk.Entry(root, width=80)
    entry.pack()

    def write(message):
        """Append text to the terminal area."""
        output.insert(tk.END, message)

    def finish():
        """Allow the exit message to remain visible briefly."""
        root.after(EXIT_DELAY_MS, root.destroy)

    shell = Shell(vfs, write, finish)

    def execute_line(command_line):
        """Execute a command and reveal the latest output."""
        shell.execute_line(command_line)
        output.see(tk.END)

    def submit(_event):
        """Read and clear the input field when Enter is pressed."""
        command_line = entry.get()
        entry.delete(0, tk.END)
        execute_line(command_line)

    write(f"Параметры запуска:\nVFS: {vfs_path}\n")
    write(f"Стартовый скрипт: {startup_script}\n\n")
    entry.bind("<Return>", submit)
    root.after(
        STARTUP_DELAY_MS, run_startup_script,
        startup_script, execute_line, write,
    )
    root.mainloop()


def main(argv=None):
    """Read the two positional arguments and start the emulator."""
    if argv is None:
        argv = sys.argv[1:]
    try:
        vfs_path, startup_script = argv
    except ValueError:
        print("Использование: python emulator.py <путь_VFS> <стартовый_скрипт>")
        return 1

    print("Параметры запуска:")
    print("VFS:", vfs_path)
    print("Стартовый скрипт:", startup_script)
    try:
        vfs = load_vfs(vfs_path)
    except (OSError, ValueError, RecursionError) as error:
        print(f"Ошибка загрузки VFS: {error}")
        return 1

    run_gui(vfs_path, startup_script, vfs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
