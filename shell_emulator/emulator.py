import tkinter as tk
import sys
import os


def load_vfs(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"VFS не найдена: {path}")

    if not os.path.isdir(path):
        raise ValueError("VFS должна быть директорией")

    def build_tree(current_path):
        tree = {}

        for item in os.listdir(current_path):
            full_path = os.path.join(current_path, item)

            if os.path.isdir(full_path):
                tree[item] = build_tree(full_path)
            else:
                tree[item] = None

        return tree

    return build_tree(path)


if len(sys.argv) != 3:
    print("Использование: python emulator.py <путь_VFS> <стартовый_скрипт>")
    sys.exit(1)


vfs_path = sys.argv[1]
startup_script = sys.argv[2]


print("Параметры запуска:")
print("VFS:", vfs_path)
print("Стартовый скрипт:", startup_script)


try:
    vfs = load_vfs(vfs_path)
except Exception as e:
    print(f"Ошибка загрузки VFS: {e}")
    sys.exit(1)


current_path = []


def get_current_dir():
    current = vfs

    for part in current_path:
        current = current[part]

    return current


def get_prompt():
    if not current_path:
        return "/"

    return "/" + "/".join(current_path)


root = tk.Tk()
root.title(f"VFS Emulator - {vfs_path}")

output = tk.Text(root, height=25, width=80)
output.pack()

entry = tk.Entry(root, width=80)
entry.pack()


def execute_line(command_line):
    output.insert(
        tk.END,
        f"{get_prompt()}$ {command_line}\n"
    )

    parts = command_line.split()

    if not parts:
        return

    command = parts[0]
    args = parts[1:]


    if command == "ls":

        if len(args) != 0:
            output.insert(
                tk.END,
                "Ошибка: команда ls не принимает аргументы\n"
            )
            return

        current = get_current_dir()

        for name in current:
            output.insert(
                tk.END,
                name + "\n"
            )


    elif command == "cd":

        if len(args) != 1:
            output.insert(
                tk.END,
                "Ошибка: команда cd требует один аргумент\n"
            )
            return

        target = args[0]

        if target == "..":

            if current_path:
                current_path.pop()

        elif target == "/":

            current_path.clear()

        else:

            current = get_current_dir()

            if target not in current:
                output.insert(
                    tk.END,
                    f"Ошибка: директория '{target}' не найдена\n"
                )
                return

            if current[target] is None:
                output.insert(
                    tk.END,
                    f"Ошибка: '{target}' не является директорией\n"
                )
                return

            current_path.append(target)


    elif command == "exit":

        if len(args) != 0:
            output.insert(
                tk.END,
                "Ошибка: команда exit не принимает аргументы\n"
            )
            return

        output.insert(
            tk.END,
            "Выход...\n"
        )

        root.after(
            1000,
            root.destroy
        )


    else:

        output.insert(
            tk.END,
            f"Ошибка: неизвестная команда '{command}'\n"
        )


    output.see(tk.END)


def execute_command(event=None):

    command_line = entry.get()

    entry.delete(
        0,
        tk.END
    )

    execute_line(command_line)


def run_startup_script():

    if not os.path.isfile(startup_script):

        output.insert(
            tk.END,
            f"Ошибка: стартовый скрипт '{startup_script}' не найден\n"
        )

        return


    output.insert(
        tk.END,
        "Запуск стартового скрипта...\n\n"
    )


    with open(
        startup_script,
        "r",
        encoding="utf-8"
    ) as file:

        for line in file:

            command_line = line.strip()

            if not command_line:
                continue

            execute_line(command_line)


    output.insert(
        tk.END,
        "\nСтартовый скрипт завершён\n\n"
    )


output.insert(
    tk.END,
    "Параметры запуска:\n"
)

output.insert(
    tk.END,
    f"VFS: {vfs_path}\n"
)

output.insert(
    tk.END,
    f"Стартовый скрипт: {startup_script}\n\n"
)


entry.bind(
    "<Return>",
    execute_command
)


root.after(
    100,
    run_startup_script
)


root.mainloop()