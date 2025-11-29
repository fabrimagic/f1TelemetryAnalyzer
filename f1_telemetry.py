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

        # Colori tema scuro
        self.bg_color = "#121212"
        self.panel_color = "#1e1e1e"
        self.fg_color = "#f0f0f0"
        self.accent_color = "#bb86fc"
        self.grid_color = "#3a3a3a"

        # Colori confronto piloti (anche indicatori UI)
        self.slot_colors = ["#4fc3f7", "#ffb74d", "#ce93d8"]

        # Oggetti FastF1
        self.session = None
        self.drivers = []
        self.driver_map = {}   # indice listbox -> (driver_num, abbrev, nome)
        self.laps = None       # Laps del pilota selezionato
        self.selected_driver_abbrev = None

        # Costruisci interfaccia
        self._setup_theme()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_theme(self):
        self.root.configure(background=self.bg_color)
        style = ttk.Style()
        style.theme_use("clam")

        # Stile base per controlli
        style.configure(
            "TFrame",
            background=self.bg_color,
            foreground=self.fg_color,
        )
        style.configure(
            "TLabelframe",
            background=self.panel_color,
            foreground=self.fg_color,
            relief="groove",
        )
        style.configure(
            "TLabelframe.Label",
            background=self.panel_color,
            foreground=self.fg_color,
        )
        style.configure(
            "TLabel",
            background=self.panel_color,
            foreground=self.fg_color,
        )
        style.configure(
            "TButton",
            background=self.panel_color,
            foreground=self.fg_color,
            padding=6,
        )
        style.map("TButton", background=[("active", "#2e2e2e")])
        style.configure(
            "TEntry",
            fieldbackground="#2a2a2a",
            foreground=self.fg_color,
            insertcolor=self.fg_color,
            background=self.panel_color,
        )
        style.configure(
            "TCombobox",
            fieldbackground="#2a2a2a",
            background=self.panel_color,
            foreground=self.fg_color,
        )
        style.configure(
            "TCheckbutton",
            background=self.panel_color,
            foreground=self.fg_color,
        )
        style.configure("Vertical.TScrollbar", background=self.panel_color)

    def _build_ui(self):
        # Layout principale: sinistra controlli, destra grafico
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=0)   # pannello sinistro
        self.root.columnconfigure(1, weight=1)   # pannello destro (grafici)

        left_frame = ttk.Frame(self.root, padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.rowconfigure(2, weight=1)
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

        # -------------------- ANALISI PILOTA SINGOLO --------------------
        single_frame = ttk.LabelFrame(left_frame, text="Analisi singolo pilota", padding=10)
        single_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        single_frame.columnconfigure(0, weight=1)

        drivers_frame = ttk.LabelFrame(single_frame, text="Piloti", padding=5)
        drivers_frame.grid(row=0, column=0, sticky="ew")
        drivers_frame.columnconfigure(0, weight=1)

        self.drivers_listbox = tk.Listbox(
            drivers_frame,
            height=8,
            exportselection=False,
            background="#1e1e1e",
            foreground=self.fg_color,
            selectbackground="#2d2d2d",
            selectforeground=self.fg_color,
            highlightbackground=self.panel_color,
        )
        self.drivers_listbox.grid(row=0, column=0, sticky="ew")
        self.drivers_listbox.bind("<<ListboxSelect>>", self.on_driver_selected)

        drivers_scroll = ttk.Scrollbar(drivers_frame, orient="vertical", command=self.drivers_listbox.yview)
        drivers_scroll.grid(row=0, column=1, sticky="ns")
        self.drivers_listbox.config(yscrollcommand=drivers_scroll.set)

        laps_frame = ttk.LabelFrame(single_frame, text="Giri del pilota selezionato", padding=5)
        laps_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        laps_frame.columnconfigure(0, weight=1)

        laps_inner = ttk.Frame(laps_frame)
        laps_inner.grid(row=0, column=0, sticky="ew")
        laps_inner.columnconfigure(0, weight=1)

        self.laps_listbox = tk.Listbox(
            laps_inner,
            height=8,
            exportselection=False,
            background="#1e1e1e",
            foreground=self.fg_color,
            selectbackground="#2d2d2d",
            selectforeground=self.fg_color,
            highlightbackground=self.panel_color,
        )
        self.laps_listbox.grid(row=0, column=0, sticky="ew")
        self.laps_listbox.bind("<<ListboxSelect>>", self.on_lap_selected)

        laps_scroll = ttk.Scrollbar(laps_inner, orient="vertical", command=self.laps_listbox.yview)
        laps_scroll.grid(row=0, column=1, sticky="ns")
        self.laps_listbox.config(yscrollcommand=laps_scroll.set)

        fastest_btn = ttk.Button(laps_frame, text="Mostra giro più veloce", command=self.show_fastest_lap)
        fastest_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        # -------------------- CONFRONTO PILOTI --------------------
        compare_frame = ttk.LabelFrame(left_frame, text="Confronto piloti (max 3)", padding=10)
        compare_frame.grid(row=2, column=0, sticky="nsew")
        compare_frame.columnconfigure(0, weight=1)
        compare_frame.rowconfigure(3, weight=1)

        self.compare_slots = []
        for slot_idx in range(3):
            slot_frame = ttk.LabelFrame(
                compare_frame,
                text=f"Pilota {slot_idx + 1}",
                padding=5,
            )
            slot_frame.grid(row=slot_idx, column=0, sticky="ew", pady=(0, 8))
            for c in range(4):
                slot_frame.columnconfigure(c, weight=1)

            ttk.Label(slot_frame, text="Pilota").grid(row=0, column=0, sticky="w")
            driver_var = tk.StringVar()
            driver_combo = ttk.Combobox(slot_frame, textvariable=driver_var, state="readonly")
            driver_combo.grid(row=0, column=1, sticky="ew", columnspan=2)

            ttk.Label(slot_frame, text="Giro n°").grid(row=1, column=0, sticky="w")
            lap_var = tk.StringVar()
            lap_entry = ttk.Entry(slot_frame, textvariable=lap_var, width=8)
            lap_entry.grid(row=1, column=1, sticky="ew")

            fastest_var = tk.BooleanVar()
            fastest_check = ttk.Checkbutton(slot_frame, text="Usa giro più veloce", variable=fastest_var)
            fastest_check.grid(row=1, column=2, sticky="w", padx=(5, 0))

            color = self.slot_colors[slot_idx]
            color_indicator = tk.Label(slot_frame, text=" ", width=2, background=color, relief="groove")
            color_indicator.grid(row=0, column=3, rowspan=2, sticky="nswe", padx=(6, 0))

            self.compare_slots.append(
                {
                    "driver_var": driver_var,
                    "driver_combo": driver_combo,
                    "lap_var": lap_var,
                    "fastest_var": fastest_var,
                    "color": color,
                }
            )

        compare_btn = ttk.Button(compare_frame, text="Confronta telemetria", command=self.compare_telemetry)
        compare_btn.grid(row=3, column=0, sticky="ew")

        # ----------------------- AREA GRAFICO ---------------------------
        graph_frame = ttk.LabelFrame(right_frame, text="Telemetria", padding=5)
        graph_frame.grid(row=0, column=0, sticky="nsew")
        graph_frame.rowconfigure(0, weight=1)
        graph_frame.columnconfigure(0, weight=1)

        # Figura matplotlib con 5 sottoplot
        self.fig = Figure(figsize=(10, 8), dpi=100)
        self.fig.patch.set_facecolor(self.bg_color)
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

        self._apply_axes_style()
        self._configure_axes_labels()

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
        self.selected_driver_abbrev = None

        # Svuota combobox confronto
        driver_names = []

        if self.session is None:
            for slot in self.compare_slots:
                slot["driver_combo"].config(values=driver_names)
            return

        # session.drivers restituisce i numeri di gara
        self.drivers = list(self.session.drivers)

        for idx, drv_num in enumerate(self.drivers):
            drv_info = self.session.get_driver(drv_num)
            abbrev = drv_info['Abbreviation']
            surname = (
                drv_info.get('Surname')
                or drv_info.get('LastName')
                or drv_info.get('FamilyName')
                or drv_info.get('FullName')
                or drv_info.get('BroadcastName')
                or str(drv_num)
            )
            name = f"{surname} ({abbrev})"
            display = f"{drv_num:>3} - {name}"
            self.drivers_listbox.insert(tk.END, display)
            self.driver_map[idx] = (drv_num, abbrev, name)
            driver_names.append(f"{abbrev} - {surname}")

        for slot in self.compare_slots:
            slot["driver_combo"].config(values=driver_names)

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

        self.selected_driver_abbrev = abbrev

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

        if self.selected_driver_abbrev:
            self.plot_single_driver_lap(self.selected_driver_abbrev, lap_number)

    # ------------------------------------------------------------------
    # TELEMETRIA
    # ------------------------------------------------------------------
    def _apply_axes_style(self):
        for ax in [self.ax_speed, self.ax_throttle, self.ax_brake, self.ax_gear, self.ax_drs]:
            ax.set_facecolor(self.panel_color)
            ax.grid(True, color=self.grid_color, alpha=0.6)
            ax.tick_params(colors=self.fg_color, labelcolor=self.fg_color)
            for spine in ax.spines.values():
                spine.set_color(self.grid_color)
            ax.yaxis.label.set_color(self.fg_color)
            ax.xaxis.label.set_color(self.fg_color)

    def _clear_axes(self):
        self.ax_speed.clear()
        self.ax_throttle.clear()
        self.ax_brake.clear()
        self.ax_gear.clear()
        self.ax_drs.clear()
        self._apply_axes_style()

    def _configure_axes_labels(self):
        self.ax_speed.set_ylabel("Velocità\n[km/h]")
        self.ax_throttle.set_ylabel("Acceleratore\n[%]")
        self.ax_throttle.set_ylim(-5, 105)
        self.ax_brake.set_ylabel("Freno\n(0-1)")
        self.ax_brake.set_ylim(-0.05, 1.05)
        self.ax_gear.set_ylabel("Marcia")
        self.ax_drs.set_ylabel("DRS")
        self.ax_drs.set_xlabel("Distanza [m]")
        for ax in [self.ax_speed, self.ax_throttle, self.ax_brake, self.ax_gear, self.ax_drs]:
            ax.yaxis.label.set_color(self.fg_color)
        self.ax_drs.xaxis.label.set_color(self.fg_color)

    def _get_fastest_lap_number(self, laps):
        if laps is None or len(laps) == 0:
            return None
        try:
            fastest_lap = laps.pick_fastest()
            if fastest_lap is not None:
                return int(fastest_lap['LapNumber'])
        except Exception:
            pass
        try:
            filtered = laps.dropna(subset=['LapTime'])
            if not filtered.empty:
                lap_num = int(filtered.loc[filtered['LapTime'].idxmin()]['LapNumber'])
                return lap_num
        except Exception:
            return None
        return None

    def _get_lap_telemetry(self, driver_abbrev: str, lap_number: int):
        try:
            laps = self.session.laps.pick_driver(driver_abbrev)
            lap = laps.pick_lap(lap_number)
            tel = lap.get_telemetry().add_distance()
            return tel
        except Exception as e:
            messagebox.showerror(
                "Errore",
                f"Impossibile ottenere la telemetria di {driver_abbrev} giro {lap_number}:\n{e}",
            )
            return None

    def _plot_telemetry_series(self, driver_abbrev: str, lap_number: int, telemetry, color: str, add_label: bool):
        x = telemetry['Distance']
        label = f"{driver_abbrev} Lap {lap_number}" if add_label else None

        speed_line, = self.ax_speed.plot(x, telemetry['Speed'], color=color, label=label)
        self.ax_throttle.plot(x, telemetry['Throttle'], color=color)
        self.ax_brake.plot(x, telemetry['Brake'], color=color)
        self.ax_gear.plot(x, telemetry['nGear'], color=color)
        self.ax_drs.step(x, telemetry['DRS'], where='post', color=color)
        return speed_line

    def _highlight_lap_in_list(self, lap_number: int):
        try:
            laps_numbers = list(self.laps['LapNumber']) if self.laps is not None else []
            if lap_number in laps_numbers:
                idx = laps_numbers.index(lap_number)
                self.laps_listbox.selection_clear(0, tk.END)
                self.laps_listbox.selection_set(idx)
                self.laps_listbox.see(idx)
        except Exception:
            pass

    def plot_single_driver_lap(self, driver_abbrev: str, lap_number: int):
        telemetry = self._get_lap_telemetry(driver_abbrev, lap_number)
        if telemetry is None:
            return

        self._clear_axes()
        self._configure_axes_labels()
        self._plot_telemetry_series(driver_abbrev, lap_number, telemetry, self.accent_color, add_label=True)
        self.ax_speed.legend(
            loc="upper right",
            facecolor=self.panel_color,
            edgecolor=self.grid_color,
            labelcolor=self.fg_color,
        )

        self.fig.suptitle(
            f"{driver_abbrev} - Giro {lap_number} - Telemetria",
            fontsize=12,
            color=self.fg_color,
        )
        self.fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        self.canvas.draw()

        self._highlight_lap_in_list(lap_number)
        self.status_var.set(f"Mostrata telemetria {driver_abbrev} - giro {lap_number}.")

    def show_fastest_lap(self):
        if self.session is None or self.laps is None or not self.selected_driver_abbrev:
            messagebox.showinfo("Info", "Seleziona prima un pilota.")
            return

        lap_number = self._get_fastest_lap_number(self.laps)
        if lap_number is None:
            messagebox.showwarning("Nessun dato", "Impossibile trovare il giro più veloce per il pilota selezionato.")
            return

        self.plot_single_driver_lap(self.selected_driver_abbrev, lap_number)
        self.status_var.set(
            f"Mostrato il giro più veloce ({lap_number}) per {self.selected_driver_abbrev}."
        )

    def compare_telemetry(self):
        if self.session is None:
            messagebox.showinfo("Info", "Carica prima una sessione.")
            return

        selections = []
        for idx, slot in enumerate(self.compare_slots):
            driver_label = slot["driver_var"].get().strip()
            if not driver_label:
                continue
            abbrev = driver_label.split(" - ")[0]
            laps = self.session.laps.pick_driver(abbrev)
            lap_number = None

            if slot["fastest_var"].get():
                lap_number = self._get_fastest_lap_number(laps)
            else:
                lap_val = slot["lap_var"].get().strip()
                if lap_val:
                    try:
                        lap_number = int(lap_val)
                    except ValueError:
                        messagebox.showwarning(
                            "Input non valido",
                            f"Il numero di giro per il pilota {abbrev} deve essere un intero.",
                        )
                        return

            if lap_number is None:
                messagebox.showwarning(
                    "Giro mancante",
                    f"Specificare un giro o selezionare 'Usa giro più veloce' per {abbrev}.",
                )
                return

            selections.append(
                {
                    "driver": abbrev,
                    "lap": lap_number,
                    "color": slot["color"],
                }
            )

        if len(selections) == 0:
            messagebox.showinfo("Nessuna selezione", "Seleziona almeno un pilota per il confronto.")
            return

        if len(selections) == 1:
            sel = selections[0]
            self.plot_single_driver_lap(sel["driver"], sel["lap"])
            self.status_var.set(
                f"Confronto non disponibile con un solo pilota. Mostrato {sel['driver']} giro {sel['lap']}."
            )
            return

        self.plot_multi_driver_telemetry(selections)

    def plot_multi_driver_telemetry(self, selections):
        self._clear_axes()
        self._configure_axes_labels()

        legend_lines = []
        legend_labels = []

        for sel in selections[:3]:
            telemetry = self._get_lap_telemetry(sel["driver"], sel["lap"])
            if telemetry is None:
                continue
            line = self._plot_telemetry_series(sel["driver"], sel["lap"], telemetry, sel["color"], add_label=True)
            legend_lines.append(line)
            legend_labels.append(f"{sel['driver']} Lap {sel['lap']}")

        if legend_lines:
            leg = self.ax_speed.legend(
                legend_lines,
                legend_labels,
                loc="upper right",
                facecolor=self.panel_color,
                edgecolor=self.grid_color,
                labelcolor=self.fg_color,
            )
            for text in leg.get_texts():
                text.set_color(self.fg_color)

        title_parts = [f"{sel['driver']} Lap {sel['lap']}" for sel in selections[:3]]
        self.fig.suptitle(
            "Confronto telemetria – " + " vs ".join(title_parts),
            fontsize=12,
            color=self.fg_color,
        )
        self.fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        self.canvas.draw()

        drivers_desc = ", ".join(title_parts)
        self.status_var.set(f"Confronto completato: {drivers_desc}.")

def main():
    root = tk.Tk()
    app = F1TelemetryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
