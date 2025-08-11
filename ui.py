import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import threading
import subprocess
import sys
from modules.config_manager import get_config_value
# Импортируем обработчик из main.py:
try:
    from main import process_all_csv_from_list
except ImportError:
    def process_all_csv_from_list(folder_uid, csv_dir, file_list, log_callback, allow_headdep_recursive=True):
        for fn in file_list:
            log_callback(f'Обрабатывается: {fn}\n')
        log_callback('Выполнено (заглушка)\n')

def select_folder():
    dirname = filedialog.askdirectory()
    if dirname:
        csv_dir_var.set(dirname)
        populate_file_list()

def populate_file_list():
    for w in files_frame.winfo_children():
        w.destroy()
    file_list.clear()
    found_files = []
    folder = csv_dir_var.get()
    if not folder or not os.path.isdir(folder):
        return
    for fname in os.listdir(folder):
        if fname.lower().endswith('.csv') and fname.lower() != 'sample.csv':
            found_files.append(fname)
    if not found_files:
        files_lbl = tk.Label(files_frame, text='(Нет подходящих файлов)', fg='red')
        files_lbl.grid(row=0, column=0, sticky="w")
        return
    for idx, fname in enumerate(found_files):
        var = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(files_frame, text=fname, variable=var)
        cb.var = var
        cb.grid(row=idx, column=0, sticky='w')
        file_list.append((fname, var))

def start_conversion():
    uid = uid_entry.get().strip()
    csv_dir = csv_dir_var.get()
    to_process = [fname for fname, var in file_list if var.get()]
    allow_recursive = allow_recursive_var.get()
    if not uid:
        messagebox.showwarning("Внимание!", "Введите UID папки для ролей!")
        return
    if not csv_dir or not os.path.isdir(csv_dir):
        messagebox.showwarning("Внимание!", "Выберите действительную папку с CSV-файлами!")
        return
    if not to_process:
        messagebox.showwarning("Внимание!", "Выделите хотя бы 1 файл!")
        return
    log_box.config(state='normal')
    log_box.delete(1.0, tk.END)

    def run_job():
        try:
            process_all_csv_from_list(
                uid, csv_dir, to_process, add_log, allow_headdep_recursive=allow_recursive
            )
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
    folder = csv_dir_var.get()
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

root = tk.Tk()
root.title("Генерация XML из CSV")

tk.Label(root, text="UID папки для ролей:").grid(
    row=0, column=0, sticky="w", padx=6, pady=6)
uid_entry = tk.Entry(root, width=48)
uid_entry.grid(row=0, column=1, padx=6, pady=6, columnspan=2)

tk.Label(root, text="Папка с CSV-файлами:").grid(row=1, column=0, sticky="w", padx=6, pady=6)
csv_dir_var = tk.StringVar()
csv_dir_entry = tk.Entry(root, textvariable=csv_dir_var, width=48)
csv_dir_entry.grid(row=1, column=1, padx=6, pady=6)
tk.Button(root, text="Выбрать...", command=select_folder).grid(
    row=1, column=2, padx=6)

tk.Label(root, text="Выберите файлы для обработки:").grid(
    row=2, column=0, sticky="w", padx=6, pady=6)
files_frame = tk.Frame(root, relief=tk.SUNKEN, borderwidth=1)
files_frame.grid(row=3, column=0, columnspan=3, sticky="we", padx=6)
file_list = []
populate_file_list()

# Чекбокс для опции headdep:
allow_recursive_var = tk.BooleanVar(
    value=get_config_value('csv_processing.allow_headdep_recursive', True)
)
allow_recursive_cb = tk.Checkbutton(
    root, 
    text="Рекурсивный доступ к дочерним подразделениям",
    variable=allow_recursive_var
)
allow_recursive_cb.grid(row=4, column=1, padx=6, pady=8, sticky='w')

start_btn = tk.Button(root, text="Старт", width=16, command=start_conversion)
start_btn.grid(row=4, column=0, padx=6, pady=8)
open_dir_btn = tk.Button(
    root, text="Открыть папку с результатами", width=30, command=open_results_folder)
open_dir_btn.grid(row=4, column=2, padx=8, pady=8, sticky='e')

tk.Label(root, text="Протокол / лог:").grid(
    row=5, column=0, sticky='w', padx=6, pady=(4, 0))
log_box = scrolledtext.ScrolledText(
    root, width=72, height=15, state='disabled', font=('Consolas', 10))
log_box.grid(row=6, column=0, columnspan=3, padx=8, pady=4, sticky='ew')

root.grid_columnconfigure(1, weight=1)

def _on_dir_entry_change(*a, **k):
    populate_file_list()

csv_dir_var.trace_add('write', _on_dir_entry_change)

root.mainloop()
