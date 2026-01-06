# app.py
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from init_db import init_db
from export_excel import export_to_excel

# TODO: hier gleich dein Scraper-Entry rein, sobald wir ihn in eine Funktion packen
# from scrapers.scrape_willhaben import run_scrape  # wir bauen das gleich sauber um

def safe_int(s: str):
    s = s.strip()
    return int(s) if s else None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Deal Scraper")
        self.geometry("820x520")

        # DB init on start
        try:
            init_db()
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            raise

        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        # Inputs
        row = 0
        ttk.Label(frm, text="Marke").grid(column=0, row=row, sticky="w")
        self.brand = ttk.Entry(frm, width=30)
        self.brand.grid(column=1, row=row, sticky="w", padx=8)

        ttk.Label(frm, text="Modell").grid(column=2, row=row, sticky="w")
        self.model = ttk.Entry(frm, width=30)
        self.model.grid(column=3, row=row, sticky="w", padx=8)

        row += 1
        ttk.Label(frm, text="Jahr von").grid(column=0, row=row, sticky="w")
        self.year_from = ttk.Entry(frm, width=10)
        self.year_from.grid(column=1, row=row, sticky="w", padx=8)

        ttk.Label(frm, text="Jahr bis").grid(column=2, row=row, sticky="w")
        self.year_to = ttk.Entry(frm, width=10)
        self.year_to.grid(column=3, row=row, sticky="w", padx=8)

        row += 1
        ttk.Label(frm, text="KM von").grid(column=0, row=row, sticky="w")
        self.km_from = ttk.Entry(frm, width=10)
        self.km_from.grid(column=1, row=row, sticky="w", padx=8)

        ttk.Label(frm, text="KM bis").grid(column=2, row=row, sticky="w")
        self.km_to = ttk.Entry(frm, width=10)
        self.km_to.grid(column=3, row=row, sticky="w", padx=8)

        row += 1
        ttk.Label(frm, text="PS von").grid(column=0, row=row, sticky="w")
        self.ps_from = ttk.Entry(frm, width=10)
        self.ps_from.grid(column=1, row=row, sticky="w", padx=8)

        ttk.Label(frm, text="PS bis").grid(column=2, row=row, sticky="w")
        self.ps_to = ttk.Entry(frm, width=10)
        self.ps_to.grid(column=3, row=row, sticky="w", padx=8)

        row += 1
        ttk.Label(frm, text="Preis von").grid(column=0, row=row, sticky="w")
        self.price_from = ttk.Entry(frm, width=10)
        self.price_from.grid(column=1, row=row, sticky="w", padx=8)

        ttk.Label(frm, text="Preis bis").grid(column=2, row=row, sticky="w")
        self.price_to = ttk.Entry(frm, width=10)
        self.price_to.grid(column=3, row=row, sticky="w", padx=8)

        row += 1
        ttk.Separator(frm).grid(column=0, row=row, columnspan=4, sticky="ew", pady=10)

        row += 1
        btns = ttk.Frame(frm)
        btns.grid(column=0, row=row, columnspan=4, sticky="w")

        self.run_btn = ttk.Button(btns, text="Scrape starten", command=self.on_run)
        self.run_btn.pack(side="left")

        self.export_btn = ttk.Button(btns, text="Export Excel", command=self.on_export)
        self.export_btn.pack(side="left", padx=8)

        row += 1
        ttk.Label(frm, text="Log").grid(column=0, row=row, sticky="w", pady=(12, 4))
        row += 1
        self.log = tk.Text(frm, height=16)
        self.log.grid(column=0, row=row, columnspan=4, sticky="nsew")

        frm.columnconfigure(1, weight=1)
        frm.columnconfigure(3, weight=1)
        frm.rowconfigure(row, weight=1)

        self._log("Ready. DB initialisiert.")

    def _log(self, msg: str):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def _read_filters(self):
        return {
            "brand": self.brand.get().strip(),
            "model": self.model.get().strip(),
            "year_from": safe_int(self.year_from.get()),
            "year_to": safe_int(self.year_to.get()),
            "km_from": safe_int(self.km_from.get()),
            "km_to": safe_int(self.km_to.get()),
            "ps_from": safe_int(self.ps_from.get()),
            "ps_to": safe_int(self.ps_to.get()),
            "price_from": safe_int(self.price_from.get()),
            "price_to": safe_int(self.price_to.get()),
        }

    def on_run(self):
        filters = self._read_filters()
        self._log(f"Start scrape mit Filtern: {filters}")

        self.run_btn.config(state="disabled")

        def worker():
            try:
                # TODO: hier hängen wir gleich den URL-Builder + deinen Scraper dran
                # run_scrape(filters, log_cb=self._log)
                self._log("Noch nicht verbunden: Scraper-Wrapper kommt als nächster Schritt.")
                self._log("Wenn du willst, machen wir es so: URL bauen -> scrape -> in DB speichern.")
            except Exception as e:
                self._log(f"ERROR: {e}")
            finally:
                self.run_btn.config(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    def on_export(self):
        out_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="auto_deal_export.xlsx",
        )
        if not out_path:
            return

        try:
            n = export_to_excel(out_path)
            self._log(f"Excel exportiert: {out_path} ({n} rows)")
        except Exception as e:
            self._log(f"Export ERROR: {e}")
            messagebox.showerror("Export Error", str(e))

if __name__ == "__main__":
    App().mainloop()
