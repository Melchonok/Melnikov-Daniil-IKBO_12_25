import tkinter as tk
import time

root = tk.Tk()
root.title("VFS Emulator")

output = tk.Text(root, height=20, width=70)
output.pack()

entry = tk.Entry(root, width=70)
entry.pack()


def execute_command(event=None):
    command_line = entry.get()

    output.insert(tk.END, f"> {command_line}\n")

    parts = command_line.split()

    if not parts:
        entry.delete(0, tk.END)
        return

    command = parts[0]
    args = parts[1:]

    if command == "ls":
        output.insert(tk.END, f"ls {args}\n")

    elif command == "cd":
        output.insert(tk.END, f"cd {args}\n")

    elif command == "exit":
        output.insert(tk.END, "Выход из системы...\n")
        root.update()
        time.sleep(1)
        root.destroy()

    else:
        output.insert(
            tk.END,
            f"Ошибка: неизвестная команда '{command}'\n"
        )

    entry.delete(0, tk.END)


entry.bind("<Return>", execute_command)

root.mainloop()
