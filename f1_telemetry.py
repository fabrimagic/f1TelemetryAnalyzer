from pathlib import Path

import fastf1
from fastf1 import plotting

import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# Abilita la cache locale di FastF1
CACHE_DIR = Path(r"X:\fastf1_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)
plotting.setup_mpl()  # opzionale, migliora lo stile dei grafici


class F1TelemetryApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("F1 Telemetria - FastF1 GUI")
        self.root.geometry("1920x1080")

        # Oggetti FastF1
        self.session = None
        self.drivers = []
        self.driver_map = {}   # indice listbox -> (driver_num, abbrev, nome)
        self.laps = None       # Laps del pilota selezionato

        # Costruisci interfaccia
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        # Layout principale: sinistra controlli, destra grafico
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=0)   # pannello sinistro
        self.root.columnconfigure(1, weight=1)   # pannello destro (grafici)

        left_frame = ttk.Frame(self.root, padding=10)
        left_frame.grid(row=0, column=0, sticky="nsw")
        left_frame.rowconfigure(3, weight=1)  # per far crescere la parte liste
        left_frame.columnconfigure(0, weight=1)

        right_frame = ttk.Frame(self.root, padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # -------------------- PANNELLO SESSIONE -------------------------
        session_frame = ttk.LabelFrame(left_frame, text="Selezione Sessione", padding=10)
        session_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for i in range(2):
            session_frame.columnconfigure(i, weight=1)

        ttk.Label(session_frame, text="Anno (es. 2024):").grid(row=0, column=0, sticky="w")
        self.year_var = tk.StringVar(value="2024")
        ttk.Entry(session_frame, textvariable=self.year_var, width=10).grid(row=0, column=1, sticky="ew")

        ttk.Label(session_frame, text="Evento (es. Bahrain Grand Prix):").grid(row=1, column=0, sticky="w")
        self.event_var = tk.StringVar()
        ttk.Entry(session_frame, textvariable=self.event_var).grid(row=1, column=1, sticky="ew")

        ttk.Label(session_frame, text="Sessione (es. FP1, FP2, FP3, Q, R, S):").grid(row=2, column=0, sticky="w")
        self.session_var = tk.StringVar(value="R")
        ttk.Entry(session_frame, textvariable=self.session_var, width=10).grid(row=2, column=1, sticky="ew")

        load_btn = ttk.Button(session_frame, text="Carica Sessione", command=self.load_session)
        load_btn.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        # -------------------- PANNELLO PILOTI / GIRI --------------------
        data_frame = ttk.Frame(left_frame)
        data_frame.grid(row=1, column=0, sticky="nsew")

        data_frame.rowconfigure(1, weight=1)
        data_frame.rowconfigure(3, weight=1)
        data_frame.columnconfigure(0, weight=1)

        # Lista piloti
        drivers_frame = ttk.LabelFrame(data_frame, text="Piloti", padding=5)
        drivers_frame.grid(row=0, column=0, sticky="ew")
        drivers_frame.columnconfigure(0, weight=1)

        self.drivers_listbox = tk.Listbox(drivers_frame, height=8, exportselection=False)
        self.drivers_listbox.grid(row=0, column=0, sticky="ew")
        self.drivers_listbox.bind("<<ListboxSelect>>", self.on_driver_selected)

        drivers_scroll = ttk.Scrollbar(drivers_frame, orient="vertical", command=self.drivers_listbox.yview)
        drivers_scroll.grid(row=0, column=1, sticky="ns")
        self.drivers_listbox.config(yscrollcommand=drivers_scroll.set)

        # Lista giri
        laps_frame = ttk.LabelFrame(data_frame, text="Giri del pilota selezionato", padding=5)
        laps_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        laps_frame.rowconfigure(0, weight=1)
        laps_frame.columnconfigure(0, weight=1)

        self.laps_listbox = tk.Listbox(laps_frame, exportselection=False)
        self.laps_listbox.grid(row=0, column=0, sticky="nsew")
        self.laps_listbox.bind("<<ListboxSelect>>", self.on_lap_selected)

        laps_scroll = ttk.Scrollbar(laps_frame, orient="vertical", command=self.laps_listbox.yview)
        laps_scroll.grid(row=0, column=1, sticky="ns")
        self.laps_listbox.config(yscrollcommand=laps_scroll.set)

        # ----------------------- AREA GRAFICO ---------------------------
        graph_frame = ttk.LabelFrame(right_frame, text="Telemetria Giro", padding=5)
        graph_frame.grid(row=0, column=0, sticky="nsew")
        graph_frame.rowconfigure(0, weight=1)
        graph_frame.columnconfigure(0, weight=1)

        # Figura matplotlib con 5 sottoplot
        self.fig = Figure(figsize=(10, 8), dpi=100)
        self.ax_speed = self.fig.add_subplot(511)
        self.ax_throttle = self.fig.add_subplot(512, sharex=self.ax_speed)
        self.ax_brake = self.fig.add_subplot(513, sharex=self.ax_speed)
        self.ax_gear = self.fig.add_subplot(514, sharex=self.ax_speed)
        self.ax_drs = self.fig.add_subplot(515, sharex=self.ax_speed)

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")

        # Label info in basso (facoltativa)
        self.status_var = tk.StringVar(value="Carica una sessione per iniziare.")
        status_label = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=(10, 2))
        status_label.grid(row=1, column=0, columnspan=2, sticky="ew")

    # ------------------------------------------------------------------
    # CALLBACKS
    # ------------------------------------------------------------------
    def load_session(self):
        year_str = self.year_var.get().strip()
        event = self.event_var.get().strip()
        sess_name = self.session_var.get().strip()

        if not year_str or not event or not sess_name:
            messagebox.showwarning("Input mancante", "Inserisci anno, evento e sessione.")
            return

        try:
            year = int(year_str)
        except ValueError:
            messagebox.showerror("Errore", "L'anno deve essere un numero intero.")
            return

        try:
            self.status_var.set("Caricamento sessione in corso...")
            self.root.update_idletasks()

            self.session = fastf1.get_session(year, event, sess_name)
            self.session.load()

        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare la sessione:\n{e}")
            self.status_var.set("Errore nel caricamento della sessione.")
            return

        # Popola lista piloti
        self.populate_drivers()
        self.status_var.set(f"Sessione caricata: {year} - {event} - {sess_name}")

    def populate_drivers(self):
        self.drivers_listbox.delete(0, tk.END)
        self.laps_listbox.delete(0, tk.END)
        self.driver_map.clear()
        self.laps = None

        if self.session is None:
            return

        # session.drivers restituisce i numeri di gara
        self.drivers = list(self.session.drivers)

        for idx, drv_num in enumerate(self.drivers):
            drv_info = self.session.get_driver(drv_num)
            abbrev = drv_info['Abbreviation']
            name = f"{drv_info['Surname']} ({abbrev})"
            display = f"{drv_num:>3} - {name}"
            self.drivers_listbox.insert(tk.END, display)
            self.driver_map[idx] = (drv_num, abbrev, name)

    def on_driver_selected(self, event=None):
        if self.session is None:
            return

        selection = self.drivers_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        drv_num, abbrev, name = self.driver_map.get(idx, (None, None, None))
        if abbrev is None:
            return

        # Prendi tutti i giri di quel pilota
        try:
            laps = self.session.laps.pick_driver(abbrev)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile recuperare i giri per {name}:\n{e}")
            return

        self.laps = laps

        # Popola lista giri
        self.laps_listbox.delete(0, tk.END)
        if laps is None or len(laps) == 0:
            self.laps_listbox.insert(tk.END, "Nessun giro disponibile")
            self.status_var.set(f"Nessun giro trovato per {name}.")
            return

        for lap in laps.iterlaps():
            lap_number = lap[1]['LapNumber']
            lap_time = lap[1]['LapTime']
            compound = lap[1].get('Compound', '')
            text_lap_time = str(lap_time) if lap_time is not None else "N/A"
            line = f"Lap {lap_number:>2} - {text_lap_time} - {compound}"
            self.laps_listbox.insert(tk.END, line)

        self.status_var.set(f"Selezionato pilota: {name}. Giri disponibili: {len(laps)}.")

    def on_lap_selected(self, event=None):
        if self.laps is None or self.session is None:
            return

        selection = self.laps_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if idx >= len(self.laps):
            return  # potrebbe essere la riga "Nessun giro disponibile"

        try:
            lap_row = self.laps.iloc[idx]
            lap_number = int(lap_row['LapNumber'])
        except Exception:
            return

        self.plot_lap_telemetry(lap_number)

    # ------------------------------------------------------------------
    # TELEMETRIA
    # ------------------------------------------------------------------
    def plot_lap_telemetry(self, lap_number: int):
        try:
            lap = self.laps.pick_lap(lap_number)
            tel = lap.get_telemetry()
            tel = tel.add_distance()  # aggiunge colonna 'Distance'
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile ottenere la telemetria del giro {lap_number}:\n{e}")
            return

        x = tel['Distance']

        # Pulisci assi
        self.ax_speed.clear()
        self.ax_throttle.clear()
        self.ax_brake.clear()
        self.ax_gear.clear()
        self.ax_drs.clear()

        # Speed
        self.ax_speed.plot(x, tel['Speed'])
        self.ax_speed.set_ylabel("Velocità\n[km/h]")
        self.ax_speed.grid(True)

        # Throttle
        self.ax_throttle.plot(x, tel['Throttle'])
        self.ax_throttle.set_ylabel("Acceleratore\n[%]")
        self.ax_throttle.set_ylim(-5, 105)
        self.ax_throttle.grid(True)

        # Brake
        self.ax_brake.plot(x, tel['Brake'])
        self.ax_brake.set_ylabel("Freno\n(0-1)")
        self.ax_brake.set_ylim(-0.05, 1.05)
        self.ax_brake.grid(True)

        # Gear
        self.ax_gear.plot(x, tel['nGear'])
        self.ax_gear.set_ylabel("Marcia")
        self.ax_gear.grid(True)

        # DRS (step per evidenziare stati)
        self.ax_drs.step(x, tel['DRS'], where='post')
        self.ax_drs.set_ylabel("DRS")
        self.ax_drs.set_xlabel("Distanza [m]")
        self.ax_drs.grid(True)

        self.fig.suptitle(f"Giro {lap_number} - Telemetria", fontsize=12)
        self.fig.tight_layout(rect=[0, 0.03, 1, 0.95])

        self.canvas.draw()

        self.status_var.set(f"Mostrata telemetria giro {lap_number}.")

def main():
    root = tk.Tk()
    app = F1TelemetryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
