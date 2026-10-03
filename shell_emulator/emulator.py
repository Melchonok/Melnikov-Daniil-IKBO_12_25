import tkinter as tk
import sys
import os


if len(sys.argv) != 3:
    print("Использование: python emulator.py <путь_VFS> <стартовый_скрипт>")
    sys.exit(1)


vfs_path = sys.argv[1]
startup_script = sys.argv[2]


print("Параметры запуска:")
print("VFS:", vfs_path)
print("Стартовый скрипт:", startup_script)


root = tk.Tk()
root.title(f"VFS Emulator - {vfs_path}")

output = tk.Text(root, height=20, width=70)
output.pack()

entry = tk.Entry(root, width=70)
entry.pack()


def execute_line(command_line):
    output.insert(tk.END, f"> {command_line}\n")

    parts = command_line.split()

    if not parts:
        return

    command = parts[0]
    args = parts[1:]

    if command == "ls":
        output.insert(tk.END, f"ls {args}\n")

    elif command == "cd":
        if len(args) != 1:
            output.insert(
                tk.END,
                "Ошибка: команда cd требует один аргумент\n"
            )
            return

        output.insert(tk.END, f"cd {args}\n")

    elif command == "exit":
        if args:
            output.insert(
                tk.END,
                "Ошибка: команда exit не принимает аргументы\n"
            )
            return

        output.insert(tk.END, "Выход...\n")
        root.after(1000, root.destroy)

    else:
        output.insert(
            tk.END,
            f"Ошибка: неизвестная команда '{command}'\n"
        )

    output.see(tk.END)


def execute_command(event=None):
    command_line = entry.get()

    entry.delete(0, tk.END)

    execute_line(command_line)


def run_startup_script():
    if not os.path.isfile(startup_script):
        output.insert(
            tk.END,
            f"Ошибка: стартовый скрипт '{startup_script}' не найден\n"
        )
        return

    output.insert(tk.END, "Запуск стартового скрипта...\n\n")

    with open(startup_script, "r", encoding="utf-8") as file:
        for line in file:
            command_line = line.strip()

            if not command_line:
                continue

            execute_line(command_line)

    output.insert(
        tk.END,
        "\nСтартовый скрипт завершён\n"
    )


output.insert(tk.END, "Параметры запуска:\n")
output.insert(tk.END, f"VFS: {vfs_path}\n")
output.insert(tk.END, f"Стартовый скрипт: {startup_script}\n\n")

entry.bind("<Return>", execute_command)

root.after(100, run_startup_script)

root.mainloop()