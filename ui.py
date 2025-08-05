import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import threading
import subprocess
import sys

# Импорт функции обработки одного файла из main.py
try:
    from main import process_single_csv_file
except ImportError:
    def process_single_csv_file(folder_uid, csv_file_path, log_callback):
        log_callback(f'Обрабатывается: {os.path.basename(csv_file_path)}\n')
        log_callback('Выполнено (заглушка)\n')

def select_csv_file():
    fname = filedialog.askopenfilename(filetypes=[('CSV Файлы', '*.csv')])
    if fname:
        csv_file_var.set(fname)

def start_conversion():
    uid = uid_entry.get().strip()
    csv_file = csv_file_var.get()
    if not uid:
        messagebox.showwarning("Внимание!", "Введите UID папки для ролей!")
        return
    if not csv_file or not os.path.isfile(csv_file):
        messagebox.showwarning("Внимание!", "Выберите действительный CSV-файл!")
        return

    log_box.config(state='normal')
    log_box.delete(1.0, tk.END)

    def run_job():
        try:
            process_single_csv_file(uid, csv_file, add_log)
            add_log("Обработка завершена.\n")
        except Exception as e:
            add_log(f"Ошибка: {e}\n")
        log_box.config(state='disabled')
    threading.Thread(target=run_job, daemon=True).start()

def add_log(txt):
    log_box.config(state='normal')
    log_box.insert(tk.END, txt)
    log_box.see(tk.END)
    log_box.update_idletasks()
    log_box.config(state='disabled')

def open_results_folder():
    csv_file = csv_file_var.get()
    folder = os.path.dirname(csv_file) if csv_file else ""
    if not folder or not os.path.isdir(folder):
        messagebox.showinfo("Инфо", "Папка не выбрана или не найдена.")
        return
    try:
        if sys.platform.startswith('win'):
            os.startfile(folder)
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

# ---------- UI ----------

root = tk.Tk()
root.title("Генерация XML из CSV")

tk.Label(root, text="UID папки для ролей:").grid(
    row=0, column=0, sticky="w", padx=6, pady=6)
uid_entry = tk.Entry(root, width=48)
uid_entry.grid(row=0, column=1, padx=6, pady=6, columnspan=2)

tk.Label(root, text="CSV-файл:").grid(row=1, column=0, sticky="w", padx=6, pady=6)
csv_file_var = tk.StringVar()
csv_file_entry = tk.Entry(root, textvariable=csv_file_var, width=48)
csv_file_entry.grid(row=1, column=1, padx=6, pady=6)
tk.Button(root, text="Выбрать...", command=select_csv_file).grid(
    row=1, column=2, padx=6)

start_btn = tk.Button(root, text="Старт", width=16, command=start_conversion)
start_btn.grid(row=2, column=0, padx=6, pady=8)
open_dir_btn = tk.Button(
    root, text="Открыть папку", width=30,
    command=open_results_folder
)
open_dir_btn.grid(row=2, column=2, padx=8, pady=8, sticky='e')

tk.Label(root, text="Протокол / лог:").grid(
    row=3, column=0, sticky='w', padx=6, pady=(4, 0))
log_box = scrolledtext.ScrolledText(
    root, width=72, height=15, state='disabled', font=('Consolas', 10))
log_box.grid(row=4, column=0, columnspan=3, padx=8, pady=4, sticky='ew')

root.grid_columnconfigure(1, weight=1)

root.mainloop()
