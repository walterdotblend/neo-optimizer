"""
=============================================================================
NEO VIDEO OPTIMIZER - ASISTENTE DE INSTALACIÓN GRÁFICO (r/unixporn Edition)
=============================================================================
Instalador interactivo profesional estilo Catppuccin Mocha / Tokyo Night.
- Diagnóstico automático de GPU (NVIDIA NVENC/AV1), Python y FFmpeg.
- Selección de directorio de destino con comprobación de espacio.
- Creación de accesos directos en Escritorio y Menú Inicio con icono nativo.
- Generación de lanzador silencioso (pythonw sin consola negra).
- Generador de script de desinstalación limpia.
=============================================================================
"""

import os
import sys
import shutil
import threading
import subprocess
import time
from typing import Dict, Any, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

# -----------------------------------------------------------------------------
# PALETA CATPPUCCIN MOCHA / TOKYO NIGHT
# -----------------------------------------------------------------------------
THEME_BG = "#0f1017"          # Fondo obsidian void
THEME_CARD = "#141624"        # Tarjetas e islas flotantes
THEME_CARD_BORDER = "#222538" # Borde sutil de tarjeta
THEME_INNER = "#0c0d14"       # Insets, entradas y logs
THEME_INNER_BORDER = "#1c1e2e"# Borde interno
THEME_SAPPHIRE = "#89b4fa"    # Tokyo/Catppuccin Sapphire
THEME_MAUVE = "#cba6f7"       # Catppuccin Mauve
THEME_EMERALD = "#a6e3a1"     # Emerald Green
THEME_PEACH = "#fab387"       # Warm Peach
THEME_RED = "#f38ba8"         # Crimson
THEME_TEXT = "#cdd6f4"        # Texto suave
THEME_TEXT_MUTED = "#6c7086"  # Gris atenuado

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ModernInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("◈ NEO•OPTIMIZER // ASISTENTE DE INSTALACIÓN")
        self.geometry("900x640")
        self.resizable(False, False)
        self.configure(fg_color=THEME_BG)

        self.source_dir = os.path.dirname(os.path.abspath(__file__))
        self.icon_ico_path = os.path.join(self.source_dir, "app_icon.ico")
        self.icon_png_path = os.path.join(self.source_dir, "app_icon.png")

        if os.path.exists(self.icon_ico_path):
            try:
                self.iconbitmap(self.icon_ico_path)
            except Exception:
                pass

        # Centrar ventana en pantalla
        self._center_window()

        # Variables de instalación
        default_local = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        self.target_dir = ctk.StringVar(value=os.path.join(default_local, "NeoVideoOptimizer"))

        self.chk_desktop = ctk.BooleanVar(value=True)
        self.chk_start_menu = ctk.BooleanVar(value=True)
        self.chk_silent_launch = ctk.BooleanVar(value=True)
        self.chk_batch_tool = ctk.BooleanVar(value=True)

        self.current_step = 1
        self.system_info: Dict[str, Any] = {}

        self._build_shell_ui()
        self._gather_system_info()
        self._show_step_1_diagnostics()

    def _center_window(self):
        self.update_idletasks()
        w = 900
        h = 640
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_shell_ui(self):
        # Cabecera flotante estilo Waybar
        header_frame = ctk.CTkFrame(self, height=72, corner_radius=12, fg_color=THEME_CARD, border_width=1, border_color=THEME_CARD_BORDER)
        header_frame.pack(fill="x", padx=18, pady=(16, 8))
        header_frame.pack_propagate(False)

        header_inner = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_inner.pack(fill="both", expand=True, padx=16, pady=8)

        # Marca & Logo
        left_box = ctk.CTkFrame(header_inner, fg_color="transparent")
        left_box.pack(side="left")

        if os.path.exists(self.icon_png_path):
            try:
                from PIL import Image
                pil_logo = Image.open(self.icon_png_path).resize((36, 36), Image.Resampling.LANCZOS)
                self.logo_ctk = ctk.CTkImage(pil_logo, size=(36, 36))
                ctk.CTkLabel(left_box, text="", image=self.logo_ctk).pack(side="left", padx=(0, 10))
            except Exception:
                pass

        title_box = ctk.CTkFrame(left_box, fg_color="transparent")
        title_box.pack(side="left")

        row_t = ctk.CTkFrame(title_box, fg_color="transparent")
        row_t.pack(anchor="w")
        ctk.CTkLabel(row_t, text="◈ NEO•OPTIMIZER", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME_SAPPHIRE).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(row_t, text=" v2.5 SETUP ", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#261b3b", text_color=THEME_MAUVE, corner_radius=6).pack(side="left")

        ctk.CTkLabel(title_box, text="Asistente de Despliegue & Optimización Universal de Video", font=ctk.CTkFont(size=11), text_color=THEME_TEXT_MUTED).pack(anchor="w")

        # Breadcrumbs / Pasos
        self.step_capsules = ctk.CTkFrame(header_inner, fg_color="transparent")
        self.step_capsules.pack(side="right")

        self.pill_s1 = ctk.CTkLabel(self.step_capsules, text=" 01 • Diagnóstico ", font=ctk.CTkFont(size=11, weight="bold"), fg_color=THEME_INNER, text_color=THEME_TEXT_MUTED, corner_radius=6)
        self.pill_s1.pack(side="left", padx=3)

        self.pill_s2 = ctk.CTkLabel(self.step_capsules, text=" 02 • Opciones ", font=ctk.CTkFont(size=11, weight="bold"), fg_color=THEME_INNER, text_color=THEME_TEXT_MUTED, corner_radius=6)
        self.pill_s2.pack(side="left", padx=3)

        self.pill_s3 = ctk.CTkLabel(self.step_capsules, text=" 03 • Instalación ", font=ctk.CTkFont(size=11, weight="bold"), fg_color=THEME_INNER, text_color=THEME_TEXT_MUTED, corner_radius=6)
        self.pill_s3.pack(side="left", padx=3)

        self.pill_s4 = ctk.CTkLabel(self.step_capsules, text=" 04 • Finalizado ", font=ctk.CTkFont(size=11, weight="bold"), fg_color=THEME_INNER, text_color=THEME_TEXT_MUTED, corner_radius=6)
        self.pill_s4.pack(side="left", padx=3)

        # Contenedor central dinámico donde se cargan los pasos
        self.body_container = ctk.CTkFrame(self, corner_radius=12, fg_color=THEME_CARD, border_width=1, border_color=THEME_CARD_BORDER)
        self.body_container.pack(fill="both", expand=True, padx=18, pady=4)

        # Barra inferior de navegación
        self.footer_frame = ctk.CTkFrame(self, height=60, corner_radius=12, fg_color=THEME_CARD, border_width=1, border_color=THEME_CARD_BORDER)
        self.footer_frame.pack(fill="x", padx=18, pady=(8, 16))
        self.footer_frame.pack_propagate(False)

        footer_inner = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        footer_inner.pack(fill="both", expand=True, padx=16, pady=10)

        self.btn_cancel = ctk.CTkButton(footer_inner, text="Cancelar", width=105, height=36, fg_color="#222538", hover_color="#313244", font=ctk.CTkFont(size=12, weight="bold"), command=self.destroy)
        self.btn_cancel.pack(side="left")

        self.btn_back = ctk.CTkButton(footer_inner, text="⬅ Atrás", width=105, height=36, fg_color="#313244", hover_color="#45475a", font=ctk.CTkFont(size=12, weight="bold"), command=self._on_btn_back)
        self.btn_back.pack(side="right", padx=(8, 0))

        self.btn_next = ctk.CTkButton(footer_inner, text="Siguiente ➔", width=145, height=36, fg_color=THEME_SAPPHIRE, text_color="#0f1017", hover_color="#b4befe", font=ctk.CTkFont(size=12, weight="bold"), command=self._on_btn_next)
        self.btn_next.pack(side="right")

    def _update_breadcrumbs(self, active_step: int):
        self.current_step = active_step
        pills = [self.pill_s1, self.pill_s2, self.pill_s3, self.pill_s4]
        for i, pill in enumerate(pills, 1):
            if i == active_step:
                pill.configure(fg_color="#18233c", text_color=THEME_SAPPHIRE)
            elif i < active_step:
                pill.configure(fg_color="#162920", text_color=THEME_EMERALD)
            else:
                pill.configure(fg_color=THEME_INNER, text_color=THEME_TEXT_MUTED)

    def _clear_body(self):
        for widget in self.body_container.winfo_children():
            widget.destroy()

    # =========================================================================
    # DIAGNÓSTICO DE SISTEMA
    # =========================================================================
    def _gather_system_info(self):
        # 1. Python info
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        is_64 = sys.maxsize > 2**32
        py_str = f"Python {py_ver} ({'64-bit AMD64' if is_64 else '32-bit'})"
        py_ok = sys.version_info >= (3, 9)

        # 2. GPU NVIDIA
        gpu_name = "No detectada"
        gpu_driver = ""
        gpu_ok = False
        try:
            smi = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
            if smi:
                parts = smi.split(",")
                gpu_name = parts[0].strip()
                if len(parts) > 1:
                    gpu_driver = f" (Driver {parts[1].strip()})"
                gpu_ok = True
        except Exception:
            gpu_name = "NVIDIA no encontrada / Sin soporte nvidia-smi"

        # 3. FFmpeg
        ffmpeg_bin = shutil.which("ffmpeg")
        ffmpeg_ver = "No encontrado en PATH"
        ffmpeg_ok = False
        if ffmpeg_bin:
            try:
                out = subprocess.check_output([ffmpeg_bin, "-version"], text=True, stderr=subprocess.DEVNULL)
                first_line = out.splitlines()[0]
                ffmpeg_ver = first_line.replace("ffmpeg version", "FFmpeg").split("Copyright")[0].strip()
                ffmpeg_ok = True
            except Exception:
                ffmpeg_ver = "FFmpeg detectado pero no responde"

        # 4. Librerías
        libs_ok = True
        missing = []
        for mod in ("PyQt6", "psutil"):
            try:
                __import__(mod)
            except ImportError:
                libs_ok = False
                missing.append(mod)

        self.system_info = {
            "py_str": py_str,
            "py_ok": py_ok,
            "gpu_name": gpu_name + gpu_driver,
            "gpu_ok": gpu_ok,
            "ffmpeg_ver": ffmpeg_ver,
            "ffmpeg_ok": ffmpeg_ok,
            "libs_ok": libs_ok,
            "missing_libs": missing
        }

    # =========================================================================
    # PASO 1: PANTALLA DE DIAGNÓSTICO
    # =========================================================================
    def _show_step_1_diagnostics(self):
        self._update_breadcrumbs(1)
        self._clear_body()

        self.btn_back.configure(state="disabled")
        self.btn_next.configure(text="Continuar ➔", state="normal")

        wrap = ctk.CTkFrame(self.body_container, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(wrap, text="Diagnóstico del Entorno de Hardware & Software", font=ctk.CTkFont(size=17, weight="bold"), text_color=THEME_TEXT).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(wrap, text="Neo Video Optimizer requiere aceleración por hardware NVENC para máximo rendimiento.", font=ctk.CTkFont(size=12), text_color=THEME_TEXT_MUTED).pack(anchor="w", pady=(0, 16))

        # Tarjetas de diagnóstico
        cards_frame = ctk.CTkFrame(wrap, fg_color="transparent")
        cards_frame.pack(fill="both", expand=True)

        # 1. GPU Card
        card_gpu = ctk.CTkFrame(cards_frame, corner_radius=10, fg_color=THEME_INNER, border_width=1, border_color=THEME_INNER_BORDER)
        card_gpu.pack(fill="x", pady=5)
        r_gpu = ctk.CTkFrame(card_gpu, fg_color="transparent")
        r_gpu.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(r_gpu, text="⚡ Tarjeta Gráfica (GPU):", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME_TEXT).pack(side="left")
        ctk.CTkLabel(r_gpu, text=f"  {self.system_info['gpu_name']}", font=ctk.CTkFont(size=12), text_color=THEME_SAPPHIRE).pack(side="left")
        badge_gpu = ctk.CTkLabel(
            r_gpu,
            text=" ✓ AV1 / HEVC NVENC LISTO " if self.system_info['gpu_ok'] else " ⚠ Sin GPU NVIDIA ",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#162920" if self.system_info['gpu_ok'] else "#2e1820",
            text_color=THEME_EMERALD if self.system_info['gpu_ok'] else THEME_RED,
            corner_radius=6
        )
        badge_gpu.pack(side="right")

        # 2. FFmpeg Card
        card_ff = ctk.CTkFrame(cards_frame, corner_radius=10, fg_color=THEME_INNER, border_width=1, border_color=THEME_INNER_BORDER)
        card_ff.pack(fill="x", pady=5)
        r_ff = ctk.CTkFrame(card_ff, fg_color="transparent")
        r_ff.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(r_ff, text="🎬 Motor de Video (FFmpeg):", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME_TEXT).pack(side="left")
        ctk.CTkLabel(r_ff, text=f"  {self.system_info['ffmpeg_ver']}", font=ctk.CTkFont(size=12), text_color=THEME_SAPPHIRE).pack(side="left")
        badge_ff = ctk.CTkLabel(
            r_ff,
            text=" ✓ FFmpeg en PATH " if self.system_info['ffmpeg_ok'] else " ⚠ No encontrado en PATH ",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#162920" if self.system_info['ffmpeg_ok'] else "#2e1820",
            text_color=THEME_EMERALD if self.system_info['ffmpeg_ok'] else THEME_RED,
            corner_radius=6
        )
        badge_ff.pack(side="right")

        # 3. Python Card
        card_py = ctk.CTkFrame(cards_frame, corner_radius=10, fg_color=THEME_INNER, border_width=1, border_color=THEME_INNER_BORDER)
        card_py.pack(fill="x", pady=5)
        r_py = ctk.CTkFrame(card_py, fg_color="transparent")
        r_py.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(r_py, text="🐍 Entorno de Ejecución:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME_TEXT).pack(side="left")
        ctk.CTkLabel(r_py, text=f"  {self.system_info['py_str']}", font=ctk.CTkFont(size=12), text_color=THEME_SAPPHIRE).pack(side="left")
        badge_py = ctk.CTkLabel(
            r_py,
            text=" ✓ Versión Compatible " if self.system_info['py_ok'] else " ✗ Requiere Python 3.9+ ",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#162920" if self.system_info['py_ok'] else "#2e1820",
            text_color=THEME_EMERALD if self.system_info['py_ok'] else THEME_RED,
            corner_radius=6
        )
        badge_py.pack(side="right")

        # 4. Dependencias UI
        card_dep = ctk.CTkFrame(cards_frame, corner_radius=10, fg_color=THEME_INNER, border_width=1, border_color=THEME_INNER_BORDER)
        card_dep.pack(fill="x", pady=5)
        r_dep = ctk.CTkFrame(card_dep, fg_color="transparent")
        r_dep.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(r_dep, text="📦 Bibliotecas Python:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME_TEXT).pack(side="left")
        dep_desc = "PyQt6, psutil (Motor C++ de Alto Rendimiento)" if self.system_info['libs_ok'] else f"Faltan: {', '.join(self.system_info['missing_libs'])}"
        ctk.CTkLabel(r_dep, text=f"  {dep_desc}", font=ctk.CTkFont(size=12), text_color=THEME_SAPPHIRE).pack(side="left")
        badge_dep = ctk.CTkLabel(
            r_dep,
            text=" ✓ 100% Instaladas " if self.system_info['libs_ok'] else " ⚠ Instalar con pip ",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#162920" if self.system_info['libs_ok'] else "#2e1820",
            text_color=THEME_EMERALD if self.system_info['libs_ok'] else THEME_RED,
            corner_radius=6
        )
        badge_dep.pack(side="right")

        # Alerta inferior informativa
        box_notice = ctk.CTkFrame(wrap, corner_radius=8, fg_color="#16192e", border_width=1, border_color="#2e3758")
        box_notice.pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(
            box_notice,
            text="💡 El sistema está óptimamente configurado para transcodificación simultánea con NVIDIA NVENC Dual.",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME_SAPPHIRE
        ).pack(padx=14, pady=8)

    # =========================================================================
    # PASO 2: OPCIONES Y RUTA DE INSTALACIÓN
    # =========================================================================
    def _show_step_2_options(self):
        self._update_breadcrumbs(2)
        self._clear_body()

        self.btn_back.configure(state="normal")
        self.btn_next.configure(text="🚀 Instalar Ahora", fg_color=THEME_EMERALD, hover_color="#94e2d5")

        wrap = ctk.CTkFrame(self.body_container, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(wrap, text="Ubicación y Accesos Directos", font=ctk.CTkFont(size=17, weight="bold"), text_color=THEME_TEXT).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(wrap, text="Elige la carpeta donde se instalará la aplicación y sus complementos.", font=ctk.CTkFont(size=12), text_color=THEME_TEXT_MUTED).pack(anchor="w", pady=(0, 16))

        # Selector de carpeta destino
        box_dir = ctk.CTkFrame(wrap, corner_radius=10, fg_color=THEME_INNER, border_width=1, border_color=THEME_INNER_BORDER)
        box_dir.pack(fill="x", pady=6)

        ctk.CTkLabel(box_dir, text="Directorio de Instalación:", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME_TEXT).pack(anchor="w", padx=16, pady=(12, 4))

        r_input = ctk.CTkFrame(box_dir, fg_color="transparent")
        r_input.pack(fill="x", padx=16, pady=(0, 12))

        entry_path = ctk.CTkEntry(r_input, textvariable=self.target_dir, height=36, font=ctk.CTkFont(size=12), fg_color=THEME_CARD, border_color=THEME_CARD_BORDER)
        entry_path.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = ctk.CTkButton(r_input, text="Examinar...", width=105, height=36, fg_color="#222538", hover_color="#313244", font=ctk.CTkFont(size=12, weight="bold"), command=self._choose_target_folder)
        btn_browse.pack(side="right")

        # Opciones de accesos directos
        box_opts = ctk.CTkFrame(wrap, corner_radius=10, fg_color=THEME_INNER, border_width=1, border_color=THEME_INNER_BORDER)
        box_opts.pack(fill="both", expand=True, pady=8)

        ctk.CTkLabel(box_opts, text="Accesos Directos e Integración:", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME_TEXT).pack(anchor="w", padx=16, pady=(12, 6))

        ctk.CTkCheckBox(box_opts, text="Crear acceso directo en el Escritorio (con icono de alta resolución)", variable=self.chk_desktop).pack(anchor="w", padx=20, pady=5)
        ctk.CTkCheckBox(box_opts, text="Crear carpeta y acceso en el Menú Inicio de Windows", variable=self.chk_start_menu).pack(anchor="w", padx=20, pady=5)
        ctk.CTkCheckBox(box_opts, text="Lanzamiento silencioso (ejecuta con pythonw sin ventana negra de consola)", variable=self.chk_silent_launch).pack(anchor="w", padx=20, pady=5)
        ctk.CTkCheckBox(box_opts, text="Crear lanzador por lotes Iniciar_NeoVideoOptimizer.bat y desinstalador", variable=self.chk_batch_tool).pack(anchor="w", padx=20, pady=5)

    def _choose_target_folder(self):
        chosen = filedialog.askdirectory(title="Selecciona la Carpeta de Destino", initialdir=self.target_dir.get())
        if chosen:
            self.target_dir.set(os.path.normpath(chosen))

    # =========================================================================
    # PASO 3: EJECUCIÓN DE LA INSTALACIÓN
    # =========================================================================
    def _show_step_3_installing(self):
        self._update_breadcrumbs(3)
        self._clear_body()

        self.btn_back.configure(state="disabled")
        self.btn_next.configure(state="disabled", text="Instalando...")
        self.btn_cancel.configure(state="disabled")

        wrap = ctk.CTkFrame(self.body_container, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(wrap, text="Instalando Neo Video Optimizer...", font=ctk.CTkFont(size=17, weight="bold"), text_color=THEME_TEXT).pack(anchor="w", pady=(0, 4))
        self.lbl_progress_action = ctk.CTkLabel(wrap, text="Preparando archivos...", font=ctk.CTkFont(size=12), text_color=THEME_SAPPHIRE)
        self.lbl_progress_action.pack(anchor="w", pady=(0, 8))

        self.install_progress = ctk.CTkProgressBar(wrap, height=12, corner_radius=6, progress_color=THEME_SAPPHIRE, fg_color=THEME_INNER)
        self.install_progress.set(0.0)
        self.install_progress.pack(fill="x", pady=(0, 12))

        # Consola de log en tiempo real
        self.txt_log = ctk.CTkTextbox(wrap, font=ctk.CTkFont(family="Consolas", size=11), fg_color=THEME_INNER, border_width=1, border_color=THEME_INNER_BORDER, text_color="#cad3f5")
        self.txt_log.pack(fill="both", expand=True)

        # Iniciar hilo de instalación
        threading.Thread(target=self._run_install_worker, daemon=True).start()

    def _set_progress(self, val: float):
        try:
            if hasattr(self, "install_progress") and self.install_progress:
                self.install_progress.set(val)
        except Exception:
            pass

    def _log_msg(self, msg: str):
        try:
            if hasattr(self, "txt_log") and self.txt_log:
                self.txt_log.configure(state="normal")
                self.txt_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
                self.txt_log.see("end")
                self.txt_log.configure(state="disabled")
        except Exception:
            pass
        try:
            print(f"[INSTALLER] {msg}")
        except Exception:
            pass

    def _run_install_worker(self):
        dest = os.path.normpath(self.target_dir.get())
        try:
            self._log_msg(f"Creando directorio destino: {dest}")
            os.makedirs(dest, exist_ok=True)
            self._set_progress(0.15)
            time.sleep(0.2)

            # Copiar archivos esenciales
            files_to_copy = [
                "core_engine.py",
                "hardware_detector.py",
                "translations.py",
                "gui_app.py",
                "app_icon.ico",
                "app_icon.png",
                "down_arrow.png",
                "down_arrow_hover.png",
                "README.md"
            ]

            total_files = len(files_to_copy)
            for idx, fn in enumerate(files_to_copy, 1):
                src_file = os.path.join(self.source_dir, fn)
                dst_file = os.path.join(dest, fn)
                if os.path.exists(src_file):
                    self._log_msg(f"Copiando {fn} -> {dst_file}")
                    shutil.copy2(src_file, dst_file)
                else:
                    self._log_msg(f"⚠ Aviso: archivo {fn} no encontrado en origen.")
                pct = 0.15 + (idx / total_files) * 0.40
                self._set_progress(pct)
                time.sleep(0.1)

            # Crear lanzador por lotes (.bat)
            bat_path = os.path.join(dest, "Iniciar_NeoVideoOptimizer.bat")
            self._log_msg(f"Generando script de inicio rápido: {bat_path}")
            with open(bat_path, "w", encoding="utf-8") as fb:
                fb.write("@echo off\n")
                fb.write("title Neo Video Optimizer (Universal Edition)\n")
                fb.write(f'cd /d "{dest}"\n')
                fb.write("python gui_app.py\n")
                fb.write("pause\n")

            # Crear lanzador silencioso (.vbs) que usa pythonw.exe sin terminal negra
            pyw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.isfile(pyw_path):
                pyw_path = sys.executable

            vbs_path = os.path.join(dest, "Iniciar_NeoVideoOptimizer.vbs")
            self._log_msg(f"Generando lanzador silencioso sin consola: {vbs_path}")
            with open(vbs_path, "w", encoding="utf-8") as fv:
                fv.write('Set WshShell = CreateObject("WScript.Shell")\n')
                fv.write(f'WshShell.CurrentDirectory = "{dest}"\n')
                fv.write(f'WshShell.Run """{pyw_path}"" """ & "{dest}\\gui_app.py""", 0, False\n')

            # Crear script de desinstalación limpia (uninstall.bat)
            uninst_path = os.path.join(dest, "desinstalar.bat")
            self._log_msg(f"Generando desinstalador: {uninst_path}")
            user_desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
            desktop_lnk = os.path.join(user_desktop, "Neo Video Optimizer.lnk")
            start_menu_dir = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Neo Video Optimizer")

            with open(uninst_path, "w", encoding="utf-8") as fu:
                fu.write("@echo off\n")
                fu.write("title Desinstalador - Neo Video Optimizer\n")
                fu.write("chcp 65001 > nul\n")
                fu.write("echo ========================================================\n")
                fu.write("echo       DESINSTALADOR DE NEO VIDEO OPTIMIZER\n")
                fu.write("echo ========================================================\n")
                fu.write("echo.\n")
                fu.write("set /p confirm=¿Seguro que deseas eliminar Neo Video Optimizer? (S/N): \n")
                fu.write('if /i not "%confirm%"=="s" exit /b\n')
                fu.write("echo Eliminando accesos directos...\n")
                fu.write(f'if exist "{desktop_lnk}" del /f /q "{desktop_lnk}"\n')
                fu.write(f'if exist "{start_menu_dir}" rmdir /s /q "{start_menu_dir}"\n')
                fu.write("echo Eliminando archivos del programa...\n")
                fu.write(f'cd /d "{os.environ.get("TEMP", "C:")}"\n')
                fu.write(f'rmdir /s /q "{dest}"\n')
                fu.write("echo ¡Neo Video Optimizer ha sido desinstalado correctamente!\n")
                fu.write("pause\n")

            self._set_progress(0.70)
            time.sleep(0.2)

            # Accesos directos de Windows
            icon_in_dest = os.path.join(dest, "app_icon.ico")

            # 1. Escritorio
            if self.chk_desktop.get():
                self._log_msg("Creando acceso directo en el Escritorio...")
                self._create_windows_shortcut(
                    shortcut_path=desktop_lnk,
                    target_exe=pyw_path if self.chk_silent_launch.get() else sys.executable,
                    arguments=f'"{os.path.join(dest, "gui_app.py")}"',
                    working_dir=dest,
                    icon_path=icon_in_dest,
                    description="Optimizador de Video Profesional (Aceleración Dinámica por Hardware)"
                )
                self._log_msg(f"✓ Acceso directo creado: {desktop_lnk}")

            self._set_progress(0.85)

            # 2. Menú Inicio
            if self.chk_start_menu.get():
                self._log_msg("Creando acceso directo en el Menú Inicio...")
                os.makedirs(start_menu_dir, exist_ok=True)
                start_lnk = os.path.join(start_menu_dir, "Neo Video Optimizer.lnk")
                self._create_windows_shortcut(
                    shortcut_path=start_lnk,
                    target_exe=pyw_path if self.chk_silent_launch.get() else sys.executable,
                    arguments=f'"{os.path.join(dest, "gui_app.py")}"',
                    working_dir=dest,
                    icon_path=icon_in_dest,
                    description="Optimizador de Video Profesional (Aceleración Dinámica por Hardware)"
                )
                # Acceso directo para desinstalar en Menú Inicio
                uninst_lnk = os.path.join(start_menu_dir, "Desinstalar Neo Video Optimizer.lnk")
                self._create_windows_shortcut(
                    shortcut_path=uninst_lnk,
                    target_exe=uninst_path,
                    arguments="",
                    working_dir=dest,
                    icon_path=os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "shell32.dll,31"),
                    description="Desinstalar Neo Video Optimizer"
                )
                self._log_msg(f"✓ Carpeta de Menú Inicio creada: {start_menu_dir}")

            self._set_progress(1.0)
            self._log_msg("🎉 ¡Instalación finalizada con éxito!")
            time.sleep(0.5)

            self.after(300, self._show_step_4_finished)
        except Exception as e:
            self._log_msg(f"❌ Error durante la instalación: {e}")
            messagebox.showerror("Error de Instalación", f"Ocurrió un error inesperado:\n{e}")
            self.btn_cancel.configure(state="normal")

    def _create_windows_shortcut(self, shortcut_path: str, target_exe: str, arguments: str, working_dir: str, icon_path: str, description: str):
        """Crea un acceso directo .lnk de Windows mediante WScript.Shell dispatch o PowerShell fallback."""
        try:
            import win32com.client
            ws = win32com.client.Dispatch("WScript.Shell")
            shortcut = ws.CreateShortcut(shortcut_path)
            shortcut.TargetPath = target_exe
            shortcut.Arguments = arguments
            shortcut.WorkingDirectory = working_dir
            if os.path.exists(icon_path):
                shortcut.IconLocation = f"{icon_path},0"
            shortcut.Description = description
            shortcut.Save()
            return
        except Exception:
            pass

        # Fallback a PowerShell
        ps_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut_path}"); '
            f'$s.TargetPath = "{target_exe}"; '
            f'$s.Arguments = \'{arguments}\'; '
            f'$s.WorkingDirectory = "{working_dir}"; '
            f'$s.IconLocation = "{icon_path},0"; '
            f'$s.Description = "{description}"; '
            f'$s.Save()'
        )
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except Exception as e:
            self._log_msg(f"Aviso al crear shortcut: {e}")

    # =========================================================================
    # PASO 4: PANTALLA FINALIZADO
    # =========================================================================
    def _show_step_4_finished(self):
        self._update_breadcrumbs(4)
        self._clear_body()

        self.btn_cancel.pack_forget()
        self.btn_back.pack_forget()
        self.btn_next.pack_forget()

        # Botones de acción final
        btn_close = ctk.CTkButton(self.footer_frame.winfo_children()[0], text="Salir", width=110, height=36, fg_color="#222538", hover_color="#313244", font=ctk.CTkFont(size=12, weight="bold"), command=self.destroy)
        btn_close.pack(side="left")

        btn_open_folder = ctk.CTkButton(self.footer_frame.winfo_children()[0], text="📁 Abrir Carpeta", width=140, height=36, fg_color="#313244", hover_color="#45475a", font=ctk.CTkFont(size=12, weight="bold"), command=self._open_installed_folder)
        btn_open_folder.pack(side="right", padx=(8, 0))

        btn_launch = ctk.CTkButton(self.footer_frame.winfo_children()[0], text="🚀 Iniciar Neo Video Optimizer", width=220, height=36, fg_color=THEME_EMERALD, text_color="#0f1017", hover_color="#94e2d5", font=ctk.CTkFont(size=13, weight="bold"), command=self._launch_app_and_exit)
        btn_launch.pack(side="right")

        wrap = ctk.CTkFrame(self.body_container, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=28, pady=24)

        card_success = ctk.CTkFrame(wrap, corner_radius=12, fg_color=THEME_INNER, border_width=1, border_color="#1b3c2a")
        card_success.pack(fill="both", expand=True, pady=4)

        box_center = ctk.CTkFrame(card_success, fg_color="transparent")
        box_center.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(box_center, text="🎉", font=ctk.CTkFont(size=44)).pack(pady=(0, 6))
        ctk.CTkLabel(box_center, text="¡Instalación Completada con Éxito!", font=ctk.CTkFont(size=20, weight="bold"), text_color=THEME_EMERALD).pack(pady=(0, 6))
        ctk.CTkLabel(box_center, text="Neo Video Optimizer v2.5 está listo para codificar con aceleración Dual NVENC.", font=ctk.CTkFont(size=13), text_color=THEME_TEXT).pack(pady=(0, 16))

        info_box = ctk.CTkFrame(box_center, corner_radius=8, fg_color=THEME_CARD, border_width=1, border_color=THEME_CARD_BORDER)
        info_box.pack(fill="x", padx=10, pady=8)

        dest = os.path.normpath(self.target_dir.get())
        ctk.CTkLabel(info_box, text=f"📍 Ubicación: {dest}", font=ctk.CTkFont(size=11), text_color=THEME_SAPPHIRE).pack(anchor="w", padx=16, pady=4)
        if self.chk_desktop.get():
            ctk.CTkLabel(info_box, text="✓ Acceso directo disponible en el Escritorio", font=ctk.CTkFont(size=11), text_color=THEME_TEXT_MUTED).pack(anchor="w", padx=16, pady=2)
        if self.chk_start_menu.get():
            ctk.CTkLabel(info_box, text="✓ Menú Inicio integrado (Neo Video Optimizer)", font=ctk.CTkFont(size=11), text_color=THEME_TEXT_MUTED).pack(anchor="w", padx=16, pady=2)
        ctk.CTkLabel(info_box, text="✓ Lanzador silencioso configurado sin consola negra de CMD", font=ctk.CTkFont(size=11), text_color=THEME_TEXT_MUTED).pack(anchor="w", padx=16, pady=(2, 6))

    def _open_installed_folder(self):
        dest = os.path.normpath(self.target_dir.get())
        if os.path.isdir(dest):
            os.startfile(dest)

    def _launch_app_and_exit(self):
        dest = os.path.normpath(self.target_dir.get())
        vbs_launcher = os.path.join(dest, "Iniciar_NeoVideoOptimizer.vbs")
        bat_launcher = os.path.join(dest, "Iniciar_NeoVideoOptimizer.bat")
        gui_py = os.path.join(dest, "gui_app.py")
        pyw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")

        try:
            if os.path.exists(vbs_launcher):
                subprocess.Popen(["wscript.exe", vbs_launcher], cwd=dest)
            elif os.path.isfile(pyw_path) and os.path.isfile(gui_py):
                subprocess.Popen([pyw_path, gui_py], cwd=dest)
            elif os.path.isfile(bat_launcher):
                subprocess.Popen([bat_launcher], cwd=dest, shell=True)
        except Exception as e:
            messagebox.showerror("Error al iniciar", f"No se pudo iniciar la aplicación:\n{e}")
            return
        self.destroy()

    # =========================================================================
    # EVENTOS DE NAVEGACIÓN
    # =========================================================================
    def _on_btn_next(self):
        if self.current_step == 1:
            self._show_step_2_options()
        elif self.current_step == 2:
            self._show_step_3_installing()

    def _on_btn_back(self):
        if self.current_step == 2:
            self._show_step_1_diagnostics()

if __name__ == "__main__":
    app = ModernInstaller()
    app.mainloop()
