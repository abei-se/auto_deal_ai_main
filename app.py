import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime
import requests

# Wichtig: nimm den async scraper
from scrapers.scrape_willhaben_async import run_scrape as run_scrape_async

SERVER = "192.168.0.158:8000"
SEARCHES_FILE = "searches.json"

def load_searches():
    if not os.path.exists(SEARCHES_FILE):
        return []
    with open(SEARCHES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_searches(searches):
    with open(SEARCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(searches, f, ensure_ascii=False, indent=2)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Deal AI")
        self.geometry("1100x650")

        self.searches = load_searches()

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        # Left: searches
        left = ttk.LabelFrame(main, text="Suchen", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        btns = ttk.Frame(left)
        btns.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        btns.columnconfigure(2, weight=1)

        ttk.Button(btns, text="Hinzufügen", command=self.add_search).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(btns, text="Entfernen", command=self.remove_search).grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(btns, text="Speichern", command=self.save_all).grid(row=0, column=2, sticky="ew")

        self.listbox = tk.Listbox(left, height=12)
        self.listbox.grid(row=1, column=0, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        self.url_entry = ttk.Entry(left)
        self.url_entry.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        # Right: actions + log
        right = ttk.LabelFrame(main, text="Aktionen", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        options = ttk.Frame(right)
        options.grid(row=0, column=0, sticky="ew")
        options.columnconfigure(1, weight=1)

        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options, text="Headless", variable=self.headless_var).grid(row=0, column=0, sticky="w")

        ttk.Label(options, text="Worker:").grid(row=0, column=1, sticky="e", padx=(10, 5))
        self.workers_var = tk.StringVar(value="4")
        self.workers_combo = ttk.Combobox(options, textvariable=self.workers_var, values=["2", "4", "6"], width=5, state="readonly")
        self.workers_combo.grid(row=0, column=2, sticky="w")

        actions = ttk.Frame(right)
        actions.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)

        ttk.Button(actions, text="Scrape starten", command=self.run_scrape_selected).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(actions, text="Marktanalyse", command=self.run_analysis).grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(actions, text="Scrape + Analyse", command=self.run_scrape_and_analysis).grid(row=0, column=2, sticky="ew")

        self.status = ttk.Label(right, text="Bereit.")
        self.status.grid(row=2, column=0, sticky="w")

        self.log_text = tk.Text(right, height=20)
        self.log_text.grid(row=3, column=0, sticky="nsew")
        self.log_text.configure(state="disabled")

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for s in self.searches:
            self.listbox.insert(tk.END, s["name"])

    def log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def set_status(self, msg):
        self.status.configure(text=msg)

    def add_search(self):
        name = simpledialog.askstring("Name", "Name der Suche (z.B. a4_2018_30k):")
        if not name:
            return
        url = simpledialog.askstring("URL", "Willhaben Such-URL:")
        if not url:
            return
        self.searches.append({"name": name, "url": url})
        self._refresh_list()
        self.save_all()

    def remove_search(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.searches[idx]
        self._refresh_list()
        self.url_entry.delete(0, tk.END)
        self.save_all()

    def save_all(self):
        save_searches(self.searches)
        self.log("Suchen gespeichert: searches.json")

    def on_select(self, _evt=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        s = self.searches[sel[0]]
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, s["url"])

    def _run_in_thread(self, fn):
        t = threading.Thread(target=fn, daemon=True)
        t.start()

    def run_scrape_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return

        s = self.searches[sel[0]]

        payload = {
            "url": s["url"],
            "headless": self.headless_var.get(),
            "workers": int(self.workers_var.get())
        }

        try:
            r = requests.post(f"{SERVER}/scrape", json=payload, timeout=5)
            self.log(f"Server: {r.json()}")
        except Exception as e:
            self.log(f"Server Fehler: {e}")

        # Workers setzen (für async scraper: MAX_WORKERS als globale Variable)
        # Einfacher: env var, die dein scraper ausliest, oder du passt scraper an.
        workers = int(self.workers_var.get())

        def job():
            self.set_status(f"Scrape läuft: {s['name']}")
            self.log(f"Starte Scrape: {s['name']}")
            self.log(s["url"])

            # quick hack: setze workers per env var
            os.environ["MAX_WORKERS"] = str(workers)

            try:
                run_scrape_async(s["url"], log_cb=self.log, headless=headless)
                self.log("Scrape fertig.")
            except Exception as e:
                self.log(f"Scrape Fehler: {e}")
            finally:
                self.set_status("Bereit.")

        self._run_in_thread(job)

    def run_analysis(self):
        try:
            r = requests.post(f"{SERVER}/analyze", timeout=10)
            self.log("Analyse gestartet auf Server")
        except Exception as e:
            self.log(f"Analyse Fehler: {e}")

    def run_scrape_and_analysis(self):
        run_started_at = datetime.now()

        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Bitte eine Suche auswählen.")
            return
        s = self.searches[sel[0]]
        headless = self.headless_var.get()
        workers = int(self.workers_var.get())

        def job():
            self.set_status(f"Scrape + Analyse läuft: {s['name']}")
            self.log(f"Starte Scrape: {s['name']}")
            self.log(s["url"])

            os.environ["MAX_WORKERS"] = str(workers)

            try:
                # 1) Scrape synchron im selben Thread
                run_scrape_async(s["url"], log_cb=self.log, headless=headless)
                self.log("Scrape fertig.")

                # 2) Analyse danach
                self.log("Starte Marktanalyse (nur aktuelle DB)...")
                import importlib
                import market_analysis
                importlib.reload(market_analysis)

                market_analysis.main(min_last_seen=run_started_at)
                self.log("Marktanalyse fertig. Schau in exports/.")
            except Exception as e:
                self.log(f"Fehler: {e}")
            finally:
                self.set_status("Bereit.")

        self._run_in_thread(job)


if __name__ == "__main__":
    App().mainloop()
