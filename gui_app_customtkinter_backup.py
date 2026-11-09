import os
import sys
import threading
import subprocess
import copy
import re
import time
import stat
from typing import Dict, List, Any, Optional

import psutil
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from core_engine import (
    scan_directory_for_videos,
    build_ffmpeg_encode_command,
    build_jellyfin_filename,
    detect_video_resolution_tag,
    estimate_compressed_size_mb,
    find_best_audio_match,
    find_best_sub_match,
    clean_file_metadata_inplace,
    load_history,
    save_history
)

# -----------------------------------------------------------------------------
# TEMA & PALETA CATPPUCCIN MOCHA / TOKYO NIGHT (r/unixporn Rice Theme)
# -----------------------------------------------------------------------------
THEME_BG = "#0f1017"          # Fondo obsidian void
THEME_CARD = "#141624"        # Tarjetas e islas flotantes
THEME_CARD_BORDER = "#222538" # Borde sutil de tarjeta
THEME_INNER = "#0c0d14"       # Insets, entradas de texto y tablas
THEME_INNER_BORDER = "#1c1e2e"# Borde interno sutil
THEME_SAPPHIRE = "#89b4fa"    # Tokyo/Catppuccin Sapphire (Acento primario)
THEME_MAUVE = "#cba6f7"       # Catppuccin Mauve (Acento secundario)
THEME_EMERALD = "#a6e3a1"     # Emerald Green (Éxito / Telemetría GPU)
THEME_PEACH = "#fab387"       # Warm Peach / Ámbar
THEME_RED = "#f38ba8"         # Crimson / Flamingo (Peligro / Errores)
THEME_TEXT = "#cdd6f4"        # Texto blanco suave
THEME_TEXT_MUTED = "#6c7086"  # Gris atenuado

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ModernVideoOptimizer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("◈ NEO•OPTIMIZER // RTX 4070 SUPER LAB")
        self.geometry("1560x990")
        self.minsize(1220, 800)
        self.configure(fg_color=THEME_BG)

        # Cargar icono de aplicación nativo (.ico y .png)
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(self.app_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.app_logo_img = None
        logo_path = os.path.join(self.app_dir, "app_icon.png")
        if os.path.exists(logo_path):
            try:
                from PIL import Image
                pil_img = Image.open(logo_path).resize((32, 32), Image.Resampling.LANCZOS)
                self.app_logo_img = ctk.CTkImage(pil_img, size=(32, 32))
            except Exception:
                self.app_logo_img = None

        # Bandera para evitar que al cargar datos en la UI se disparen eventos de modificación
        self._is_loading_ui = False

        # Estado del programa
        self.directory_path = ctk.StringVar(value="")
        self.scanned_groups: Dict[str, Dict[str, Any]] = {}

        self.series_configs: Dict[str, Dict[str, Any]] = {}
        self.individual_video_configs: Dict[str, Dict[str, Any]] = {}

        self.current_target_id: Optional[str] = None
        self.current_is_video: bool = False

        self.is_encoding = False
        self.is_paused = False
        self.current_process: Optional[subprocess.Popen] = None

        # Opciones globales
        self.var_replace_original = ctk.BooleanVar(value=False)
        self.var_only_new = ctk.BooleanVar(value=False)
        self.var_jellyfin_only_res = ctk.BooleanVar(value=True)
        self.var_after_action = ctk.StringVar(value="Nada (Mantener encendido)")

        # Audio y Subtítulos
        self.audio_mode = ctk.StringVar(value="track")
        self.audio_track_selected = ctk.StringVar(value="Automático")
        self.audio_name_filter = ctk.StringVar(value="Castellano")

        self.sub_mode = ctk.StringVar(value="track")
        self.sub_track_selected = ctk.StringVar(value="Automático")
        self.sub_name_filter = ctk.StringVar(value="Español")

        self.active_version_widgets: List[Dict[str, Any]] = []

        # Cola de codificación
        self.job_queue: List[Dict[str, Any]] = []
        self.queue_lock = threading.Lock()

        self._build_modern_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_app_closing)

    def _on_app_closing(self):
        """Asegura que al cerrar la ventana no quede ningún proceso FFmpeg pausado/zombi bloqueando archivos."""
        if self.is_encoding or self.current_process:
            self.stop_encoding()
        self.destroy()

    def _build_modern_ui(self):
        # 1. Cabecera Waybar / Polybar moderna
        header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=THEME_CARD, border_width=1, border_color=THEME_CARD_BORDER)
        header_frame.pack(fill="x", padx=16, pady=(10, 6))

        # Fila superior: Identidad de Marca y Telemetría de Hardware (Capsules)
        row_telemetry = ctk.CTkFrame(header_frame, fg_color="transparent")
        row_telemetry.pack(fill="x", padx=14, pady=(8, 4))

        brand_frame = ctk.CTkFrame(row_telemetry, fg_color="transparent")
        brand_frame.pack(side="left")

        if self.app_logo_img:
            ctk.CTkLabel(brand_frame, text="", image=self.app_logo_img).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(brand_frame, text="◈ NEO•OPTIMIZER", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME_SAPPHIRE).pack(side="left", padx=(0, 6))
        
        lbl_v_badge = ctk.CTkLabel(brand_frame, text=" v2.5 NVENC ", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#261b3b", text_color=THEME_MAUVE, corner_radius=6)
        lbl_v_badge.pack(side="left", padx=(0, 8))

        lbl_sub_brand = ctk.CTkLabel(brand_frame, text="// RTX 4070 SUPER LAB", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME_TEXT_MUTED)
        lbl_sub_brand.pack(side="left")

        # Cápsulas de Telemetría estilo Waybar (Derecha)
        capsule_frame = ctk.CTkFrame(row_telemetry, fg_color="transparent")
        capsule_frame.pack(side="right")

        pill_gpu = ctk.CTkLabel(capsule_frame, text=" ⚡ RTX 4070 SUPER ", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#162920", text_color=THEME_EMERALD, corner_radius=6)
        pill_gpu.pack(side="left", padx=4)

        pill_av1 = ctk.CTkLabel(capsule_frame, text=" 󰢮 AV1 DUAL NVENC ", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#18233c", text_color=THEME_SAPPHIRE, corner_radius=6)
        pill_av1.pack(side="left", padx=4)

        pill_status = ctk.CTkLabel(capsule_frame, text=" ● NVENC READY ", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#16252b", text_color="#94e2d5", corner_radius=6)
        pill_status.pack(side="left", padx=4)

        # Fila inferior: Barra de búsqueda Rofi/Wofi para Directorio Raíz
        row_search = ctk.CTkFrame(header_frame, fg_color=THEME_INNER, corner_radius=8, border_width=1, border_color=THEME_INNER_BORDER)
        row_search.pack(fill="x", padx=14, pady=(2, 10))

        ctk.CTkLabel(row_search, text=" 📁 Directorio Raíz:", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME_TEXT).pack(side="left", padx=(10, 6), pady=6)
        self.entry_dir = ctk.CTkEntry(row_search, textvariable=self.directory_path, placeholder_text="Selecciona la ruta de la biblioteca o serie... (ej: D:\\Media\\Series)", height=34, font=ctk.CTkFont(size=12), fg_color=THEME_CARD, border_color=THEME_CARD_BORDER)
        self.entry_dir.pack(side="left", fill="x", expand=True, padx=6, pady=6)

        btn_browse = ctk.CTkButton(row_search, text="Examinar", width=95, height=32, fg_color="#222538", hover_color="#313244", font=ctk.CTkFont(size=12, weight="bold"), command=self.choose_directory)
        btn_browse.pack(side="left", padx=4, pady=6)

        btn_scan = ctk.CTkButton(row_search, text="🔍 Escanear Videos", width=155, height=32, fg_color=THEME_SAPPHIRE, text_color="#0f1017", hover_color="#b4befe", font=ctk.CTkFont(size=12, weight="bold"), command=self.start_scan)
        btn_scan.pack(side="left", padx=(4, 10), pady=6)

        # 2. Pestañas Principales (Tabview con estética de workspaces Hyprland/Waybar)
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=12,
            fg_color=THEME_CARD,
            segmented_button_fg_color=THEME_INNER,
            segmented_button_selected_color=THEME_SAPPHIRE,
            segmented_button_selected_hover_color="#b4befe",
            text_color="#0f1017"
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=4)

        self.tab_config = self.tabview.add("󰮯 01 • Biblioteca & Ajustes")
        self.tab_queue = self.tabview.add("󰐍 02 • Cola de Codificación")
        self.tabview._segmented_button.configure(font=ctk.CTkFont(size=13, weight="bold"))

        self._build_tab_config()
        self._build_tab_queue()

        # 4. Pie de Página Común (Dock de Control y Telemetría Flotante)
        bottom_bar = ctk.CTkFrame(self, corner_radius=12, fg_color=THEME_CARD, border_width=1, border_color=THEME_CARD_BORDER)
        bottom_bar.pack(fill="x", padx=16, pady=(4, 10))

        row_status = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        row_status.pack(fill="x", padx=12, pady=(8, 4))

        self.lbl_status = ctk.CTkLabel(row_status, text="● Listo. Selecciona una carpeta y pulsa 'Escanear Videos'.", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME_SAPPHIRE)
        self.lbl_status.pack(side="left")

        # Telemetría de velocidad estilo widget Polybar
        self.speed_capsule = ctk.CTkFrame(row_status, fg_color=THEME_INNER, corner_radius=6, border_width=1, border_color=THEME_INNER_BORDER)
        self.speed_capsule.pack(side="right")
        self.lbl_fps_speed = ctk.CTkLabel(self.speed_capsule, text=" ⚡ Velocidad: Inactivo ", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME_EMERALD)
        self.lbl_fps_speed.pack(padx=6, pady=2)

        self.progress_bar = ctk.CTkProgressBar(bottom_bar, height=10, corner_radius=5, progress_color=THEME_SAPPHIRE, fg_color=THEME_INNER)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=12, pady=(0, 8))

        row_actions = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        row_actions.pack(fill="x", padx=12, pady=(0, 10))

        self.btn_add_queue = ctk.CTkButton(row_actions, text="📥 Agregar Selección", height=38, font=ctk.CTkFont(size=12, weight="bold"), fg_color=THEME_MAUVE, text_color="#0f1017", hover_color="#d5bdfc", command=self.add_selected_to_queue)
        self.btn_add_queue.pack(side="left", padx=(0, 8))

        self.btn_add_new = ctk.CTkButton(row_actions, text="⚡ Agregar Solo NO Codificados", height=38, font=ctk.CTkFont(size=12, weight="bold"), fg_color=THEME_SAPPHIRE, text_color="#0f1017", hover_color="#b4befe", command=self.add_only_new_to_queue)
        self.btn_add_new.pack(side="left", padx=(0, 8))

        self.btn_add_all = ctk.CTkButton(row_actions, text="📥 Agregar TODO", height=38, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#313244", hover_color="#45475a", command=self.add_all_to_queue)
        self.btn_add_all.pack(side="left", padx=(0, 10))

        self.btn_start = ctk.CTkButton(row_actions, text="▶ INICIAR COLA", height=38, font=ctk.CTkFont(size=13, weight="bold"), fg_color=THEME_EMERALD, text_color="#0f1017", hover_color="#94e2d5", command=self.start_encoding)
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_pause = ctk.CTkButton(row_actions, text="⏸ Pausar", height=38, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#f9e2af", text_color="#0f1017", hover_color="#f5e0dc", command=self.toggle_pause, state="disabled")
        self.btn_pause.pack(side="left", padx=(0, 8))

        self.btn_cancel = ctk.CTkButton(row_actions, text="⏹ Detener", height=38, font=ctk.CTkFont(size=13, weight="bold"), fg_color=THEME_RED, text_color="#0f1017", hover_color="#eba0ac", command=self.stop_encoding, state="disabled")
        self.btn_cancel.pack(side="left")

        # Acción al terminar la codificación de toda la cola
        self.frame_after = ctk.CTkFrame(row_actions, fg_color=THEME_INNER, corner_radius=8, border_width=1, border_color=THEME_INNER_BORDER)
        self.frame_after.pack(side="right")

        ctk.CTkLabel(self.frame_after, text="🌙 Al terminar:", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME_TEXT).pack(side="left", padx=(10, 6), pady=4)
        
        self.cb_after_action = ctk.CTkComboBox(
            self.frame_after,
            values=["Nada (Mantener encendido)", "Apagar PC", "Hibernar", "Suspender", "Cerrar programa"],
            variable=self.var_after_action,
            command=self._on_after_action_change,
            width=205,
            height=32,
            font=ctk.CTkFont(size=12),
            dropdown_font=ctk.CTkFont(size=12),
            fg_color=THEME_CARD,
            border_color=THEME_CARD_BORDER
        )
        self.cb_after_action.pack(side="left", padx=(0, 8), pady=3)

        self._is_loading_ui = True
        self.add_version_ui("av1_nvenc", "Original", "3500", False)
        self._is_loading_ui = False

    def _build_tab_config(self):
        center_frame = ctk.CTkFrame(self.tab_config, fg_color="transparent")
        center_frame.pack(fill="x", padx=4, pady=2)

        # Columna Izquierda: Versiones
        self.card_versions = ctk.CTkFrame(center_frame, corner_radius=12, fg_color=THEME_CARD, border_width=1, border_color=THEME_CARD_BORDER)
        self.card_versions.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=2)

        header_v = ctk.CTkFrame(self.card_versions, fg_color="transparent")
        header_v.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(header_v, text="🎯 Versiones Jellyfin (Perfiles RTX)", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME_SAPPHIRE).pack(side="left")
        
        btn_add_v = ctk.CTkButton(header_v, text="➕ Agregar Versión (Ej: 720p)", height=28, fg_color="#222538", hover_color="#313244", font=ctk.CTkFont(size=11, weight="bold"), command=self.add_version_ui)
        btn_add_v.pack(side="right")

        self.scroll_versions = ctk.CTkScrollableFrame(self.card_versions, height=185, fg_color="transparent")
        self.scroll_versions.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        # Columna Derecha: Pistas de Audio y Subtítulos
        card_audio_subs = ctk.CTkFrame(center_frame, corner_radius=12, fg_color=THEME_CARD, border_width=1, border_color=THEME_CARD_BORDER)
        card_audio_subs.pack(side="right", fill="both", expand=True, padx=(6, 0), pady=2)

        ctk.CTkLabel(card_audio_subs, text="🎧 Audio, Subtítulos & Nombres Jellyfin", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME_SAPPHIRE).pack(anchor="w", padx=14, pady=(8, 4))

        # Audio Selector
        frame_a = ctk.CTkFrame(card_audio_subs, fg_color="transparent")
        frame_a.pack(fill="x", padx=14, pady=2)
        ctk.CTkLabel(frame_a, text="Pista de Audio Predeterminada:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")

        r_a = ctk.CTkFrame(frame_a, fg_color="transparent")
        r_a.pack(fill="x", pady=2)
        ctk.CTkRadioButton(r_a, text="1° Por N° de Pista:", variable=self.audio_mode, value="track", command=self._on_settings_change).pack(side="left")
        self.cb_audio_track = ctk.CTkComboBox(r_a, variable=self.audio_track_selected, values=["Automático"], width=230, height=28, fg_color=THEME_INNER, border_color=THEME_INNER_BORDER, command=lambda e: self._on_settings_change())
        self.cb_audio_track.pack(side="left", padx=(6, 12))

        ctk.CTkRadioButton(r_a, text="2° O por Nombre/Idioma:", variable=self.audio_mode, value="name", command=self._on_settings_change).pack(side="left")
        ent_aud = ctk.CTkEntry(r_a, textvariable=self.audio_name_filter, width=120, height=28, fg_color=THEME_INNER, border_color=THEME_INNER_BORDER)
        ent_aud.pack(side="left", padx=6)
        ent_aud.bind("<KeyRelease>", lambda e: self._on_settings_change())

        # Subtítulo Selector
        frame_s = ctk.CTkFrame(card_audio_subs, fg_color="transparent")
        frame_s.pack(fill="x", padx=14, pady=(4, 2))
        ctk.CTkLabel(frame_s, text="Pista de Subtítulo Predeterminada:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")

        r_s1 = ctk.CTkFrame(frame_s, fg_color="transparent")
        r_s1.pack(fill="x", pady=2)
        ctk.CTkRadioButton(r_s1, text="1° Por N° de Pista:", variable=self.sub_mode, value="track", command=self._on_settings_change).pack(side="left")
        self.cb_sub_track = ctk.CTkComboBox(r_s1, variable=self.sub_track_selected, values=["🚫 Ninguno (Desactivado por defecto)"], width=230, height=28, fg_color=THEME_INNER, border_color=THEME_INNER_BORDER, command=self._on_sub_combo_selected)
        self.cb_sub_track.pack(side="left", padx=(6, 12))

        ctk.CTkRadioButton(r_s1, text="2° O por Nombre:", variable=self.sub_mode, value="name", command=self._on_settings_change).pack(side="left")
        ent_sub = ctk.CTkEntry(r_s1, textvariable=self.sub_name_filter, width=120, height=28, fg_color=THEME_INNER, border_color=THEME_INNER_BORDER)
        ent_sub.pack(side="left", padx=6)
        ent_sub.bind("<KeyRelease>", lambda e: (self.sub_mode.set("name"), self._on_settings_change()))

        r_s2 = ctk.CTkFrame(frame_s, fg_color="transparent")
        r_s2.pack(fill="x", pady=(2, 2))
        ctk.CTkRadioButton(
            r_s2,
            text="🚫 Ningún subtítulo por defecto (conserva todas las pistas pero desactivadas al reproducir)",
            variable=self.sub_mode,
            value="none",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME_RED,
            command=self._on_sub_mode_none_selected
        ).pack(side="left")

        # Opciones Jellyfin
        frame_opts = ctk.CTkFrame(card_audio_subs, fg_color="transparent")
        frame_opts.pack(fill="x", padx=14, pady=(6, 4))

        ctk.CTkCheckBox(frame_opts, text="⚡ Omitir ya hechos", variable=self.var_only_new).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(frame_opts, text="🗑️ Reemplazar originales", variable=self.var_replace_original).pack(side="left", padx=(0, 15))

        btn_clean_meta = ctk.CTkButton(
            frame_opts,
            text="🏷️ Limpiar Título VLC",
            height=28,
            fg_color="#222538",
            hover_color="#313244",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.clean_vlc_titles_now
        )
        btn_clean_meta.pack(side="right")

        frame_jelly_opt = ctk.CTkFrame(card_audio_subs, fg_color="transparent")
        frame_jelly_opt.pack(fill="x", padx=14, pady=(2, 6))

        chk_jelly = ctk.CTkCheckBox(
            frame_jelly_opt,
            text="Nombre oficial Jellyfin: solo resolución (ej: 'Pelicula - 1080p.mkv')",
            variable=self.var_jellyfin_only_res,
            font=ctk.CTkFont(size=11)
        )
        chk_jelly.pack(side="left")

        # Banner de Feedback Visual Superior (Cápsula Polybar) + Botones rápidos
        self.selection_banner = ctk.CTkFrame(self.tab_config, corner_radius=8, fg_color="#16192e", border_width=1, border_color="#2e3758")
        self.selection_banner.pack(fill="x", padx=4, pady=(4, 2))

        self.lbl_editing_target = ctk.CTkLabel(
            self.selection_banner,
            text="📍 Clic normal selecciona 1 elemento | Ctrl+Clic o Shift+Clic selecciona varios",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME_TEXT
        )
        self.lbl_editing_target.pack(side="left", padx=12, pady=6)

        self.lbl_global_savings = ctk.CTkLabel(
            self.selection_banner,
            text="📊 Peso Total: 0 MB ➜ Est: 0 MB (-0%)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME_SAPPHIRE
        )
        self.lbl_global_savings.pack(side="right", padx=12, pady=6)

        btn_quitar_sel = ctk.CTkButton(
            self.selection_banner,
            text="🗑️ Quitar Seleccionados",
            width=145,
            height=26,
            fg_color="#313244",
            hover_color=THEME_RED,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._ctx_remove_from_tree
        )
        btn_quitar_sel.pack(side="right", padx=6, pady=4)

        # Tabla de Biblioteca y Resumen
        table_card = ctk.CTkFrame(self.tab_config, corner_radius=12, fg_color=THEME_CARD, border_width=1, border_color=THEME_CARD_BORDER)
        table_card.pack(fill="both", expand=True, padx=4, pady=4)

        tree_frame = ctk.CTkFrame(table_card, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=8, pady=8)

        cols = (
            "kind",
            "status",
            "codec_in",
            "bitrate_in",
            "hdr_in",
            "orig_size",
            "est_size",
            "savings",
            "versions_plan",
            "audio_plan",
            "sub_plan"
        )
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings", selectmode="extended")

        self.tree.heading("#0", text="Carpeta (Serie) / Archivo de Video")
        self.tree.heading("kind", text="Tipo")
        self.tree.heading("status", text="Historial")
        self.tree.heading("codec_in", text="Códec Orig.")
        self.tree.heading("bitrate_in", text="Bitrate Video")
        self.tree.heading("hdr_in", text="HDR / Dolby")
        self.tree.heading("orig_size", text="Peso Orig.")
        self.tree.heading("est_size", text="Peso Est. V1")
        self.tree.heading("savings", text="Reducción %")
        self.tree.heading("versions_plan", text="Plan de Versiones")
        self.tree.heading("audio_plan", text="Audio Resuelto")
        self.tree.heading("sub_plan", text="Sub Resuelto")

        self.tree.column("#0", width=270)
        self.tree.column("kind", width=85, anchor="center")
        self.tree.column("status", width=95, anchor="center")
        self.tree.column("codec_in", width=80, anchor="center")
        self.tree.column("bitrate_in", width=85, anchor="center")
        self.tree.column("hdr_in", width=95, anchor="center")
        self.tree.column("orig_size", width=85, anchor="center")
        self.tree.column("est_size", width=85, anchor="center")
        self.tree.column("savings", width=85, anchor="center")
        self.tree.column("versions_plan", width=200, anchor="w")
        self.tree.column("audio_plan", width=135, anchor="w")
        self.tree.column("sub_plan", width=135, anchor="w")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                        background=THEME_INNER,
                        foreground=THEME_TEXT,
                        fieldbackground=THEME_INNER,
                        rowheight=28,
                        font=("Segoe UI", 9))
        
        # Selección azul vibrante estándar
        style.map("Treeview",
                  background=[('selected', '#2563eb')],
                  foreground=[('selected', '#ffffff')])
        style.configure("Treeview.Heading", background=THEME_CARD, foreground=THEME_SAPPHIRE, font=("Segoe UI", 9, "bold"))

        # DIFERENCIA VISUAL CLARA ENTRE CARPETAS Y VIDEOS + COLORES INTERCALADOS (ZEBRA A / B)
        # 1. Fila de Carpeta / Serie: Navy sutil con texto azul eléctrico vibrante
        self.tree.tag_configure("folder_row", background="#18223c", foreground="#7ec8ff", font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("folder_row_multi", background="#241b3c", foreground="#f5bde6", font=("Segoe UI", 10, "bold"))

        # 2. Filas de Videos (Color A = Par #0f111d, Color B = Impar #141728)
        self.tree.tag_configure("video_even", background="#0f111d", foreground=THEME_TEXT, font=("Segoe UI", 9))
        self.tree.tag_configure("video_odd", background="#141728", foreground=THEME_TEXT, font=("Segoe UI", 9))

        # Variantes con el mismo fondo Zebra A/B pero texto distintivo si tienen perfil individual o multiversión
        self.tree.tag_configure("video_even_custom", background="#0f111d", foreground="#fdba74", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("video_odd_custom", background="#141728", foreground="#fdba74", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("video_even_multi", background="#0f111d", foreground="#f5bde6", font=("Segoe UI", 9))
        self.tree.tag_configure("video_odd_multi", background="#141728", foreground="#f5bde6", font=("Segoe UI", 9))

        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Menú contextual con clic derecho
        self.context_menu = tk.Menu(self, tearoff=0, bg=THEME_CARD, fg=THEME_TEXT, activebackground="#2563eb", activeforeground="#ffffff", font=("Segoe UI", 9))
        self.context_menu.add_command(label="📥 Agregar seleccionados a la Cola", command=self.add_selected_to_queue)
        self.context_menu.add_command(label="⚡ Agregar solo NO codificados de la selección", command=lambda: self.add_selected_to_queue(force_only_new=True))
        self.context_menu.add_command(label="🗑️ Quitar seleccionados de esta lista", command=self._ctx_remove_from_tree)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🔄 Restablecer configuración heredada de su carpeta", command=self._ctx_reset_custom_config)
        
        self.tree.bind("<Button-3>", self.show_context_menu)

    def _build_tab_queue(self):
        bar_q = ctk.CTkFrame(self.tab_queue, fg_color="transparent")
        bar_q.pack(fill="x", padx=10, pady=(8, 4))

        self.lbl_queue_stats = ctk.CTkLabel(bar_q, text="📋 Cola de Codificación (0 tareas)", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME_MAUVE)
        self.lbl_queue_stats.pack(side="left")

        btn_up = ctk.CTkButton(bar_q, text="⬆️ Subir Orden", width=105, height=30, fg_color="#222538", hover_color="#313244", font=ctk.CTkFont(size=11, weight="bold"), command=self.move_queue_item_up)
        btn_up.pack(side="left", padx=(20, 6))

        btn_down = ctk.CTkButton(bar_q, text="⬇️ Bajar Orden", width=105, height=30, fg_color="#222538", hover_color="#313244", font=ctk.CTkFont(size=11, weight="bold"), command=self.move_queue_item_down)
        btn_down.pack(side="left", padx=6)

        btn_del_q = ctk.CTkButton(bar_q, text="✖ Quitar Seleccionados", width=140, height=30, fg_color="#313244", hover_color=THEME_RED, font=ctk.CTkFont(size=11, weight="bold"), command=self.remove_queue_selected)
        btn_del_q.pack(side="left", padx=6)

        btn_err_log = ctk.CTkButton(bar_q, text="🔍 Ver Detalle de Errores", width=155, height=30, fg_color="#222538", hover_color="#313244", font=ctk.CTkFont(size=11, weight="bold"), command=self.show_queue_errors_dialog)
        btn_err_log.pack(side="left", padx=6)

        btn_clear_q = ctk.CTkButton(bar_q, text="🗑️ Vaciar Cola", width=105, height=30, fg_color=THEME_RED, text_color="#0f1017", hover_color="#eba0ac", font=ctk.CTkFont(size=11, weight="bold"), command=self.clear_queue)
        btn_clear_q.pack(side="right", padx=6)

        q_frame = ctk.CTkFrame(self.tab_queue, corner_radius=12, fg_color=THEME_CARD, border_width=1, border_color=THEME_CARD_BORDER)
        q_frame.pack(fill="both", expand=True, padx=4, pady=4)

        q_cols = ("order", "video_name", "version_target", "progress_pct", "status", "output_file")
        self.tree_q = ttk.Treeview(q_frame, columns=q_cols, show="headings", selectmode="extended")

        self.tree_q.heading("order", text="#")
        self.tree_q.heading("video_name", text="Archivo Original")
        self.tree_q.heading("version_target", text="Versión a Generar")
        self.tree_q.heading("progress_pct", text="Progreso %")
        self.tree_q.heading("status", text="Estado")
        self.tree_q.heading("output_file", text="Archivo Destino (Jellyfin)")

        self.tree_q.column("order", width=45, anchor="center")
        self.tree_q.column("video_name", width=320, anchor="w")
        self.tree_q.column("version_target", width=180, anchor="center")
        self.tree_q.column("progress_pct", width=95, anchor="center")
        self.tree_q.column("status", width=140, anchor="center")
        self.tree_q.column("output_file", width=380, anchor="w")

        self.tree_q.tag_configure("pending_even", background="#0f111d", foreground=THEME_TEXT)
        self.tree_q.tag_configure("pending_odd", background="#141728", foreground=THEME_TEXT)
        self.tree_q.tag_configure("processing", background="#2a2412", foreground="#f9e2af", font=("Segoe UI", 9, "bold"))
        self.tree_q.tag_configure("paused", background="#2a1b12", foreground=THEME_PEACH, font=("Segoe UI", 9, "bold"))
        self.tree_q.tag_configure("done", background="#12251a", foreground=THEME_EMERALD)
        self.tree_q.tag_configure("error", background="#2a1218", foreground=THEME_RED, font=("Segoe UI", 9, "bold"))

        scroll_q_y = ttk.Scrollbar(q_frame, orient="vertical", command=self.tree_q.yview)
        self.tree_q.configure(yscrollcommand=scroll_q_y.set)
        self.tree_q.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scroll_q_y.pack(side="right", fill="y", pady=4)

        self.tree_q.bind("<Double-1>", lambda e: self.show_queue_errors_dialog())

    # =========================================================================
    # MENÚ CONTEXTUAL & ACCIONES SOBRE LA TABLA
    # =========================================================================
    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            current_sels = self.tree.selection()
            if row_id not in current_sels:
                self.tree.selection_set(row_id)
                self.on_tree_select(None)
            self.context_menu.post(event.x_root, event.y_root)

    def _ctx_remove_from_tree(self):
        selected_ids = list(self.tree.selection())
        if not selected_ids:
            messagebox.showinfo("Selección", "Primero selecciona uno o más videos o carpetas de la tabla.")
            return

        for item_id in selected_ids:
            if item_id.startswith("group_"):
                d_path = item_id[6:]
                if d_path in self.scanned_groups:
                    del self.scanned_groups[d_path]
                if d_path in self.series_configs:
                    del self.series_configs[d_path]
            elif item_id.startswith("vid_"):
                v_path = item_id[4:]
                for d_path, g_info in self.scanned_groups.items():
                    g_info["videos"] = [v for v in g_info["videos"] if v["filepath"] != v_path]
                if v_path in self.individual_video_configs:
                    del self.individual_video_configs[v_path]

        # Eliminar grupos que hayan quedado vacíos
        empty_groups = [dp for dp, gi in self.scanned_groups.items() if not gi["videos"]]
        for dp in empty_groups:
            del self.scanned_groups[dp]

        self._rebuild_full_tree()
        self.lbl_status.configure(text=f"Se quitaron {len(selected_ids)} elementos de la lista de escaneo.")

    def _ctx_reset_custom_config(self):
        selected_ids = list(self.tree.selection())
        for item_id in selected_ids:
            if item_id.startswith("vid_"):
                v_path = item_id[4:]
                if v_path in self.individual_video_configs:
                    del self.individual_video_configs[v_path]
        self._update_tree_in_place()
        self._save_all_folder_configs()
        self._save_all_folder_configs()
        self.lbl_status.configure(text="Configuración restablecida al perfil de su carpeta y guardada.")

    def _append_video_to_queue(self, d_path: str, g_info: Dict[str, Any], v_meta: Dict[str, Any], only_res_naming: bool) -> int:
        s_cfg = self.series_configs.get(d_path, {})
        v_cfg = copy.deepcopy(self.individual_video_configs.get(v_meta["filepath"], s_cfg))
        versions = v_cfg.get("versions", [])
        orig_path = v_meta["filepath"]
        added = 0

        for v_num, ver in enumerate(versions):
            res_tag = ver["res"]
            if res_tag == "Original":
                res_tag = v_meta.get("resolution_tag") or detect_video_resolution_tag(v_meta.get("width", 0), v_meta.get("height", 0))

            codec_clean = ver["codec"].replace("_nvenc", "").replace("lib", "").upper()
            out_name = build_jellyfin_filename(orig_path, res_tag, codec_clean, only_resolution=only_res_naming)
            out_path = os.path.join(d_path, out_name)

            if not any(item["output_path"] == out_path and item["status"] in ("Pendiente", "Codificando...") for item in self.job_queue):
                job = {
                    "d_path": d_path,
                    "g_info": g_info,
                    "v_meta": v_meta,
                    "cfg": v_cfg,
                    "v_num": v_num,
                    "v_cfg": copy.deepcopy(ver),
                    "res_tag": res_tag,
                    "out_name": out_name,
                    "output_path": out_path,
                    "status": "Pendiente",
                    "progress": "0%",
                    "error_detail": ""
                }
                self.job_queue.append(job)
                added += 1
        return added

    # =========================================================================
    # PAUSAR / REANUDAR
    # =========================================================================
    def toggle_pause(self):
        if not self.is_encoding or not self.current_process:
            return

        try:
            parent = psutil.Process(self.current_process.pid)
            children = parent.children(recursive=True)

            if not self.is_paused:
                parent.suspend()
                for child in children:
                    child.suspend()
                self.is_paused = True
                self.btn_pause.configure(text="▶ Reanudar", fg_color="#a6e3a1")
                self.lbl_status.configure(text="Codificación PAUSADA.")
                self.lbl_fps_speed.configure(text="⏸ PAUSADO", text_color="#f9e2af")
            else:
                for child in children:
                    child.resume()
                parent.resume()
                self.is_paused = False
                self.btn_pause.configure(text="⏸ Pausar", fg_color="#f9e2af")
                self.lbl_status.configure(text="Codificación REANUDADA.")
        except Exception as e:
            print(f"Error al pausar/reanudar: {e}")

    # =========================================================================
    # UI DE VERSIONES & DIRECTORIO
    # =========================================================================
    def add_version_ui(self, default_codec="hevc_nvenc", default_res="720p", default_bitrate="1500", default_burn=False):
        v_idx = len(self.active_version_widgets) + 1
        box = ctk.CTkFrame(self.scroll_versions, corner_radius=8, fg_color=THEME_INNER, border_width=1, border_color=THEME_INNER_BORDER)
        box.pack(fill="x", pady=4, padx=4)

        var_codec = ctk.StringVar(value=default_codec)
        var_res = ctk.StringVar(value=default_res)
        var_bitrate = ctk.StringVar(value=str(default_bitrate))
        var_burn = ctk.BooleanVar(value=default_burn)

        r1 = ctk.CTkFrame(box, fg_color="transparent")
        r1.pack(fill="x", padx=8, pady=(4, 2))

        version_accents = [THEME_SAPPHIRE, THEME_MAUVE, THEME_PEACH, THEME_EMERALD, "#f5c2e7"]
        color_v = version_accents[(v_idx - 1) % len(version_accents)]
        title_text = f"◈ Versión #{v_idx}" + (" (Principal - Dual NVENC)" if v_idx == 1 else " (Adicional / Ligera)")
        ctk.CTkLabel(r1, text=title_text, font=ctk.CTkFont(size=12, weight="bold"), text_color=color_v).pack(side="left")

        if v_idx > 1:
            btn_del = ctk.CTkButton(
                r1,
                text="✖ Eliminar",
                width=75,
                height=22,
                fg_color="#2d1218",
                text_color=THEME_RED,
                hover_color=THEME_RED,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda f=box: self.remove_version_ui(f)
            )
            btn_del.pack(side="right")

        r2 = ctk.CTkFrame(box, fg_color="transparent")
        r2.pack(fill="x", padx=8, pady=(2, 6))

        ctk.CTkLabel(r2, text="Códec:", text_color=THEME_TEXT_MUTED).pack(side="left", padx=2)
        cb_c = ctk.CTkComboBox(r2, variable=var_codec, values=["av1_nvenc", "hevc_nvenc", "h264_nvenc", "libsvtav1", "libx265"], width=120, height=26, fg_color=THEME_CARD, border_color=THEME_CARD_BORDER, command=lambda e: self._on_settings_change())
        cb_c.pack(side="left", padx=3)

        ctk.CTkLabel(r2, text="Res:", text_color=THEME_TEXT_MUTED).pack(side="left", padx=(6, 2))
        cb_r = ctk.CTkComboBox(r2, variable=var_res, values=["Original", "4K (2160p)", "1080p", "720p", "480p"], width=105, height=26, fg_color=THEME_CARD, border_color=THEME_CARD_BORDER, command=lambda e: self._on_settings_change())
        cb_r.pack(side="left", padx=3)

        ctk.CTkLabel(r2, text="Bitrate:", text_color=THEME_TEXT_MUTED).pack(side="left", padx=(6, 2))
        ent_b = ctk.CTkEntry(r2, textvariable=var_bitrate, width=70, height=26, fg_color=THEME_CARD, border_color=THEME_CARD_BORDER)
        ent_b.pack(side="left", padx=3)
        ent_b.bind("<KeyRelease>", lambda e: self._on_settings_change())

        chk_burn = ctk.CTkCheckBox(r2, text="🔥 Quemar Subtítulo", variable=var_burn, font=ctk.CTkFont(size=11), command=self._on_settings_change)
        chk_burn.pack(side="left", padx=(10, 4))

        self.active_version_widgets.append({
            "frame": box,
            "codec": var_codec,
            "res": var_res,
            "bitrate": var_bitrate,
            "burn_sub": var_burn
        })

        if not self._is_loading_ui:
            self._on_settings_change()

    def remove_version_ui(self, frame_to_remove):
        idx = -1
        for i, item in enumerate(self.active_version_widgets):
            if item["frame"] == frame_to_remove:
                idx = i
                break
        if idx > 0:
            self.active_version_widgets[idx]["frame"].destroy()
            self.active_version_widgets.pop(idx)
            if not self._is_loading_ui:
                self._on_settings_change()

    def choose_directory(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de videos o series")
        if folder:
            self.directory_path.set(folder)
            self.start_scan()

    def start_scan(self):
        folder = self.directory_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("Atención", "Por favor selecciona una carpeta válida.")
            return

        self.lbl_status.configure(text="Escaneando y detectando todas las pistas de audio, subtítulos y bitrates...")
        self.tree.delete(*self.tree.get_children())
        self.scanned_groups.clear()
        self.series_configs.clear()
        self.individual_video_configs.clear()

        def scan_worker():
            try:
                data = scan_directory_for_videos(folder)
                self.after(0, lambda: self._scan_finished(data))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Error al escanear: {e}"))

        threading.Thread(target=scan_worker, daemon=True).start()

    def _scan_finished(self, data: Dict[str, Dict[str, Any]]):
        self.scanned_groups = data
        total_videos = sum(len(g["videos"]) for g in data.values())

        if total_videos == 0:
            self.lbl_status.configure(text="No se encontraron videos en la carpeta seleccionada.")
            messagebox.showinfo("Información", "No se encontraron archivos de video compatibles.")
            return

        for d_path, g_info in data.items():
            saved = g_info.get("saved_config") or {}
            def_v = saved.get("versions", [{"codec": "av1_nvenc", "res": "Original", "bitrate": 3500, "burn_sub": False}])
            
            self.series_configs[d_path] = {
                "versions": def_v,
                "audio_mode": saved.get("audio_mode", "track"),
                "audio_name": saved.get("audio_name", "Castellano"),
                "audio_track_idx": saved.get("audio_track_idx", 0),
                "sub_mode": saved.get("sub_mode", "track"),
                "sub_name": saved.get("sub_name", "Español"),
                "sub_track_idx": saved.get("sub_track_idx", 0)
            }

            # Restaurar configuraciones personalizadas por video guardadas previamente en esa carpeta
            hist_v_configs = g_info.get("history", {}).get("video_configs", {})
            for v in g_info.get("videos", []):
                v_name = v["filename"]
                if v_name in hist_v_configs:
                    self.individual_video_configs[v["filepath"]] = copy.deepcopy(hist_v_configs[v_name])

        self._rebuild_full_tree()

        first_group = list(data.keys())[0]
        first_iid = f"group_{first_group}"
        if self.tree.exists(first_iid):
            self.tree.selection_set(first_iid)
            self.tree.focus(first_iid)
        self._load_target_into_ui(first_group, is_video=False)

        total_new = sum(g["new_count"] for g in data.values())
        total_encoded = sum(g["encoded_count"] for g in data.values())
        self.lbl_status.configure(text=f"Escaneo finalizado: {len(data)} carpetas | {total_new} no codificados | {total_encoded} ya codificados.")

    def _save_all_folder_configs(self):
        """Guarda en cada carpeta (.codec_history.json) la configuración de la serie y las configuraciones de cada video."""
        for d_path, g_info in self.scanned_groups.items():
            try:
                history = load_history(d_path)
                s_cfg = self.series_configs.get(d_path)
                if s_cfg:
                    history["last_config"] = copy.deepcopy(s_cfg)
                
                v_configs = history.get("video_configs", {})
                for v in g_info.get("videos", []):
                    v_p = v["filepath"]
                    v_name = v["filename"]
                    if v_p in self.individual_video_configs:
                        v_configs[v_name] = copy.deepcopy(self.individual_video_configs[v_p])
                    elif v_name in v_configs and v_p not in self.individual_video_configs:
                        del v_configs[v_name]
                history["video_configs"] = v_configs
                history["last_saved_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                save_history(d_path, history)
            except Exception as e:
                print(f"Error guardando configuración en {d_path}: {e}")

    def _format_size(self, mb: float) -> str:
        if mb >= 1024:
            return f"{round(mb / 1024.0, 2)} GB"
        return f"{int(mb)} MB"

    def _resolve_audio_description(self, v_meta: Dict[str, Any], cfg: Dict[str, Any]) -> str:
        audios = v_meta.get("audio_streams", [])
        if not audios:
            return "Sin audio"
            
        if cfg.get("audio_mode") == "track":
            idx = cfg.get("audio_track_idx", 0)
            if 0 <= idx < len(audios):
                return f"#{idx} ({audios[idx]['lang_pretty']})"
            return f"#{idx} [No existe]"
        else:
            pat = cfg.get("audio_name", "")
            match = find_best_audio_match(audios, pat)
            if match:
                return f"#{match['rel_index']} {match['lang_pretty']}"
            return "Auto"

    def _resolve_sub_description(self, v_meta: Dict[str, Any], cfg: Dict[str, Any]) -> str:
        subs = v_meta.get("subtitle_streams", [])
        if not subs:
            return "Sin subs"
            
        if cfg.get("sub_mode") == "none" or cfg.get("sub_track_idx") == -1:
            return "🚫 Ninguno (Off)"
        elif cfg.get("sub_mode") == "track":
            idx = cfg.get("sub_track_idx", 0)
            if idx == -1:
                return "🚫 Ninguno (Off)"
            if 0 <= idx < len(subs):
                return f"#{idx} ({subs[idx]['lang_pretty']})"
            return f"#{idx} [No existe]"
        else:
            pat = cfg.get("sub_name", "")
            match = find_best_sub_match(subs, pat)
            if match:
                return f"#{match['rel_index']} {match['lang_pretty']}"
            return "Auto"

    def _compute_row_data_for_video(self, idx: int, v: Dict[str, Any], s_cfg: Dict[str, Any]):
        v_path = v["filepath"]
        has_custom = v_path in self.individual_video_configs
        v_cfg = self.individual_video_configs.get(v_path, s_cfg)
        cur_versions = v_cfg.get("versions", [])

        v1_cfg = cur_versions[0] if cur_versions else {"bitrate": 3500}
        est_v_mb = estimate_compressed_size_mb(
            v.get("duration_sec", 0.0),
            int(v1_cfg.get("bitrate", 3500)),
            v.get("audio_bitrate_kbps", 384)
        )

        orig_v_mb = v["filesize_mb"]
        pct_reduction = 0.0
        if orig_v_mb > 0:
            pct_reduction = round(((orig_v_mb - est_v_mb) / orig_v_mb) * 100.0, 1)

        v_plan = " | ".join([f"V{i+1}: {ver['codec']} ({ver['res']} @ {ver['bitrate']}k{' 🔥' if ver.get('burn_sub') else ''})" for i, ver in enumerate(cur_versions)])
        resolved_audio = self._resolve_audio_description(v, v_cfg)
        resolved_sub = self._resolve_sub_description(v, v_cfg)
        status_v = "✅ Ya codificado" if v.get("is_already_encoded") else "🆕 No codificado"

        # Etiqueta de color Zebra A (par) y Zebra B (impar)
        is_even = (idx % 2 == 0)
        if has_custom:
            tag_v = "video_even_custom" if is_even else "video_odd_custom"
            kind_label = "Video ✏️"
        elif len(cur_versions) > 1:
            tag_v = "video_even_multi" if is_even else "video_odd_multi"
            kind_label = f"Video ({len(cur_versions)}V)"
        else:
            tag_v = "video_even" if is_even else "video_odd"
            kind_label = "Video"

        pct_str = f"-{pct_reduction}%" if pct_reduction > 0 else f"+{abs(pct_reduction)}%"
        codec_v = v.get("video_codec", "-")
        bitrate_v = f"{v['bitrate_kbps']}k" if v.get("bitrate_kbps") else "-"
        hdr_v = v.get("hdr_info", "SDR")
        if any(a.get('is_atmos') for a in v.get('audio_streams', [])):
            hdr_v += " / Atmos"

        vals = (
            kind_label,
            status_v,
            codec_v,
            bitrate_v,
            hdr_v,
            self._format_size(orig_v_mb),
            self._format_size(est_v_mb),
            pct_str,
            v_plan,
            resolved_audio,
            resolved_sub
        )
        return vals, tag_v, est_v_mb

    def _rebuild_full_tree(self):
        """Construye la tabla desde cero (solo al escanear o borrar elementos) con colores Zebra A/B."""
        self.tree.delete(*self.tree.get_children())

        grand_orig_mb = 0.0
        grand_est_mb = 0.0

        for d_path, g_info in self.scanned_groups.items():
            g_name = g_info["group_name"]
            is_series = g_info["is_series"]
            videos = g_info["videos"]

            s_cfg = self.series_configs.get(d_path, {})
            s_versions = s_cfg.get("versions", [])
            tag_group = "folder_row_multi" if len(s_versions) > 1 else "folder_row"
            group_id = f"group_{d_path}"
            status_summary = f"{g_info['new_count']} No codificados / {g_info['encoded_count']} Hechos"
            kind_str = "📂 SERIE" if is_series else "📂 RAÍZ"

            group_orig_mb = sum(v["filesize_mb"] for v in videos)
            group_est_mb = 0.0

            v_plan_str = " | ".join([f"V{i+1}: {v['codec']} ({v['res']} @ {v['bitrate']}k{' 🔥' if v.get('burn_sub') else ''})" for i, v in enumerate(s_versions)])
            a_plan_str = f"Pista #{s_cfg.get('audio_track_idx')}" if s_cfg.get('audio_mode') == 'track' else f"Nombre: '{s_cfg.get('audio_name')}'"
            if s_cfg.get('sub_mode') == 'none' or s_cfg.get('sub_track_idx') == -1:
                s_plan_str = "🚫 Ninguno (Off)"
            elif s_cfg.get('sub_mode') == 'track':
                s_plan_str = f"Pista #{s_cfg.get('sub_track_idx')}"
            else:
                s_plan_str = f"Nombre: '{s_cfg.get('sub_name')}'"

            child_rows = []
            for idx, v in enumerate(videos):
                vid_id = f"vid_{v['filepath']}"
                vals, tag_v, est_v_mb = self._compute_row_data_for_video(idx, v, s_cfg)
                group_est_mb += est_v_mb
                child_rows.append({
                    "id": vid_id,
                    "text": f"   🎬 {v['filename']}",
                    "values": vals,
                    "tags": (tag_v,)
                })

            grand_orig_mb += group_orig_mb
            grand_est_mb += group_est_mb

            grp_pct = 0.0
            if group_orig_mb > 0:
                grp_pct = round(((group_orig_mb - group_est_mb) / group_orig_mb) * 100.0, 1)
            grp_pct_str = f"-{grp_pct}%" if grp_pct > 0 else f"+{abs(grp_pct)}%"

            self.tree.insert("", "end", iid=group_id, text=f"📁 [{g_name.upper()}] ({len(videos)} videos)",
                             values=(
                                 kind_str,
                                 status_summary,
                                 "—",
                                 "—",
                                 "—",
                                 self._format_size(group_orig_mb),
                                 self._format_size(group_est_mb),
                                 grp_pct_str,
                                 v_plan_str,
                                 a_plan_str,
                                 s_plan_str
                             ),
                             tags=(tag_group,), open=True)

            for cr in child_rows:
                self.tree.insert(group_id, "end", iid=cr["id"], text=cr["text"], values=cr["values"], tags=cr["tags"])

        tot_pct = 0.0
        if grand_orig_mb > 0:
            tot_pct = round(((grand_orig_mb - grand_est_mb) / grand_orig_mb) * 100.0, 1)
        self.lbl_global_savings.configure(
            text=f"📊 Peso Total: {self._format_size(grand_orig_mb)} ➜ Est: {self._format_size(grand_est_mb)} (-{tot_pct}% de espacio)"
        )

    def _update_tree_in_place(self):
        """Actualiza los valores de las filas existentes SIN borrar ni perder la selección actual."""
        grand_orig_mb = 0.0
        grand_est_mb = 0.0

        for d_path, g_info in self.scanned_groups.items():
            is_series = g_info["is_series"]
            videos = g_info["videos"]
            s_cfg = self.series_configs.get(d_path, {})
            s_versions = s_cfg.get("versions", [])
            tag_group = "folder_row_multi" if len(s_versions) > 1 else "folder_row"
            group_id = f"group_{d_path}"
            status_summary = f"{g_info['new_count']} No codificados / {g_info['encoded_count']} Hechos"
            kind_str = "📂 SERIE" if is_series else "📂 RAÍZ"

            group_orig_mb = sum(v["filesize_mb"] for v in videos)
            group_est_mb = 0.0

            v_plan_str = " | ".join([f"V{i+1}: {v['codec']} ({v['res']} @ {v['bitrate']}k{' 🔥' if v.get('burn_sub') else ''})" for i, v in enumerate(s_versions)])
            a_plan_str = f"Pista #{s_cfg.get('audio_track_idx')}" if s_cfg.get('audio_mode') == 'track' else f"Nombre: '{s_cfg.get('audio_name')}'"
            if s_cfg.get('sub_mode') == 'none' or s_cfg.get('sub_track_idx') == -1:
                s_plan_str = "🚫 Ninguno (Off)"
            elif s_cfg.get('sub_mode') == 'track':
                s_plan_str = f"Pista #{s_cfg.get('sub_track_idx')}"
            else:
                s_plan_str = f"Nombre: '{s_cfg.get('sub_name')}'"

            for idx, v in enumerate(videos):
                vid_id = f"vid_{v['filepath']}"
                vals, tag_v, est_v_mb = self._compute_row_data_for_video(idx, v, s_cfg)
                group_est_mb += est_v_mb
                if self.tree.exists(vid_id):
                    self.tree.item(vid_id, values=vals, tags=(tag_v,))

            grand_orig_mb += group_orig_mb
            grand_est_mb += group_est_mb

            grp_pct = 0.0
            if group_orig_mb > 0:
                grp_pct = round(((group_orig_mb - group_est_mb) / group_orig_mb) * 100.0, 1)
            grp_pct_str = f"-{grp_pct}%" if grp_pct > 0 else f"+{abs(grp_pct)}%"

            if self.tree.exists(group_id):
                self.tree.item(group_id, values=(
                    kind_str,
                    status_summary,
                    "—",
                    "—",
                    "—",
                    self._format_size(group_orig_mb),
                    self._format_size(group_est_mb),
                    grp_pct_str,
                    v_plan_str,
                    a_plan_str,
                    s_plan_str
                ), tags=(tag_group,))

        tot_pct = 0.0
        if grand_orig_mb > 0:
            tot_pct = round(((grand_orig_mb - grand_est_mb) / grand_orig_mb) * 100.0, 1)
        self.lbl_global_savings.configure(
            text=f"📊 Peso Total: {self._format_size(grand_orig_mb)} ➜ Est: {self._format_size(grand_est_mb)} (-{tot_pct}% de espacio)"
        )

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        if len(selected) > 1:
            # Cargar el primero en la interfaz sin modificar configuraciones
            first_id = selected[0]
            if first_id.startswith("group_"):
                self._load_target_into_ui(first_id[6:], is_video=False, multi_count=len(selected))
            elif first_id.startswith("vid_"):
                self._load_target_into_ui(first_id[4:], is_video=True, multi_count=len(selected))
            return

        item_id = selected[0]
        if item_id.startswith("group_"):
            d_path = item_id[6:]
            self._load_target_into_ui(d_path, is_video=False, multi_count=1)
        elif item_id.startswith("vid_"):
            v_path = item_id[4:]
            self._load_target_into_ui(v_path, is_video=True, multi_count=1)

    def _load_target_into_ui(self, target_id: str, is_video: bool, multi_count: int = 1):
        """Carga los controles superiores sin disparar eventos de guardado ni alterar la tabla."""
        self._is_loading_ui = True
        try:
            self.current_target_id = target_id
            self.current_is_video = is_video

            sample_meta = None
            if is_video:
                for g in self.scanned_groups.values():
                    for v in g["videos"]:
                        if v["filepath"] == target_id:
                            sample_meta = v
                            break
                    if sample_meta:
                        break
                parent_dir = sample_meta["parent_dir"] if sample_meta else ""
                cfg = self.individual_video_configs.get(target_id)
                if not cfg:
                    cfg = copy.deepcopy(self.series_configs.get(parent_dir, {}))

                if multi_count > 1:
                    self.lbl_editing_target.configure(
                        text=f"📍 {multi_count} elementos seleccionados (Con Ctrl/Shift). Si cambias un ajuste arriba se aplicará a los {multi_count}.",
                        text_color="#89b4fa"
                    )
                    self.selection_banner.configure(border_color="#89b4fa")
                else:
                    self.lbl_editing_target.configure(
                        text=f"🎬 Seleccionado Video Individual: {sample_meta['filename'] if sample_meta else target_id}",
                        text_color="#fdba74"
                    )
                    self.selection_banner.configure(border_color="#fdba74")
            else:
                g_info = self.scanned_groups.get(target_id)
                sample_meta = g_info["videos"][0] if g_info and g_info["videos"] else None
                g_title = g_info["group_name"] if g_info else target_id
                self.lbl_editing_target.configure(
                    text=f"📁 Seleccionada Carpeta / Serie: {g_title} (Cambiar ajustes arriba actualizará todos sus videos)",
                    text_color="#a6e3a1"
                )
                self.selection_banner.configure(border_color="#a6e3a1")
                cfg = self.series_configs.get(target_id, {})

            audio_options = []
            if sample_meta and sample_meta.get("audio_streams"):
                for a in sample_meta["audio_streams"]:
                    audio_options.append(f"Pista #{a['rel_index']}: {a['description']}")
            else:
                audio_options = ["Sin pistas de audio"]
            self.cb_audio_track.configure(values=audio_options)

            sub_options = ["🚫 Ninguno (Desactivado por defecto)"]
            if sample_meta and sample_meta.get("subtitle_streams"):
                for s in sample_meta["subtitle_streams"]:
                    sub_options.append(f"Sub #{s['rel_index']}: {s['description']}")
            elif not sample_meta or not sample_meta.get("subtitle_streams"):
                sub_options.append("Sin pistas de subtítulos")
            self.cb_sub_track.configure(values=sub_options)

            self.audio_mode.set(cfg.get("audio_mode", "track"))
            self.audio_name_filter.set(cfg.get("audio_name", "Castellano"))
            a_idx = cfg.get("audio_track_idx", 0)
            if 0 <= a_idx < len(audio_options):
                self.audio_track_selected.set(audio_options[a_idx])
            elif audio_options:
                self.audio_track_selected.set(audio_options[0])

            saved_sub_mode = cfg.get("sub_mode", "track")
            s_idx = cfg.get("sub_track_idx", 0)
            if saved_sub_mode == "none" or s_idx == -1:
                self.sub_mode.set("none")
                self.sub_track_selected.set("🚫 Ninguno (Desactivado por defecto)")
            else:
                self.sub_mode.set(saved_sub_mode)
                found_match = False
                for opt in sub_options:
                    if f"Sub #{s_idx}:" in opt:
                        self.sub_track_selected.set(opt)
                        found_match = True
                        break
                if not found_match:
                    if len(sub_options) > 1:
                        self.sub_track_selected.set(sub_options[1])
                    else:
                        self.sub_track_selected.set(sub_options[0])

            self.sub_name_filter.set(cfg.get("sub_name", "Español"))

            for w in self.active_version_widgets:
                w["frame"].destroy()
            self.active_version_widgets.clear()

            versions = cfg.get("versions", [{"codec": "av1_nvenc", "res": "Original", "bitrate": 3500, "burn_sub": False}])
            for v in versions:
                self.add_version_ui(
                    default_codec=v.get("codec", "av1_nvenc"),
                    default_res=v.get("res", "Original"),
                    default_bitrate=str(v.get("bitrate", 3500)),
                    default_burn=v.get("burn_sub", False)
                )
        finally:
            self._is_loading_ui = False

    def _on_sub_combo_selected(self, choice=None):
        val = self.sub_track_selected.get()
        if "Ninguno" in val:
            self.sub_mode.set("none")
        else:
            self.sub_mode.set("track")
        self._on_settings_change()

    def _on_sub_mode_none_selected(self):
        self.sub_mode.set("none")
        self.sub_track_selected.set("🚫 Ninguno (Desactivado por defecto)")
        self._on_settings_change()

    def _on_settings_change(self):
        """Solo se ejecuta cuando el usuario modifica activamente un control superior."""
        if self._is_loading_ui or not self.current_target_id:
            return

        collected_versions = []
        for w in self.active_version_widgets:
            try:
                b_val = int(w["bitrate"].get())
            except ValueError:
                b_val = 3500

            collected_versions.append({
                "codec": w["codec"].get(),
                "res": w["res"].get(),
                "bitrate": b_val,
                "preset": "p5",
                "burn_sub": w["burn_sub"].get()
            })

        a_str = self.audio_track_selected.get()
        a_idx = 0
        if "Pista #" in a_str:
            try:
                a_idx = int(a_str.split("Pista #")[1].split(":")[0])
            except Exception:
                a_idx = 0

        s_str = self.sub_track_selected.get()
        s_idx = 0
        current_sub_mode = self.sub_mode.get()
        if current_sub_mode == "none" or "Ninguno" in s_str:
            s_idx = -1
            current_sub_mode = "none"
        elif "Sub #" in s_str:
            try:
                s_idx = int(s_str.split("Sub #")[1].split(":")[0])
            except Exception:
                s_idx = 0

        updated_cfg = {
            "versions": collected_versions,
            "audio_mode": self.audio_mode.get(),
            "audio_name": self.audio_name_filter.get().strip(),
            "audio_track_idx": a_idx,
            "sub_mode": current_sub_mode,
            "sub_name": self.sub_name_filter.get().strip(),
            "sub_track_idx": s_idx
        }

        # Aplicar a todos los elementos actualmente seleccionados en el Treeview
        selected_ids = list(self.tree.selection())
        if not selected_ids:
            selected_ids = [f"{'vid' if self.current_is_video else 'group'}_{self.current_target_id}"]

        for item_id in selected_ids:
            if item_id.startswith("group_"):
                d_path = item_id[6:]
                self.series_configs[d_path] = copy.deepcopy(updated_cfg)
                g_info = self.scanned_groups.get(d_path)
                if g_info:
                    for v in g_info["videos"]:
                        v_p = v["filepath"]
                        if v_p in self.individual_video_configs:
                            del self.individual_video_configs[v_p]
            elif item_id.startswith("vid_"):
                v_path = item_id[4:]
                self.individual_video_configs[v_path] = copy.deepcopy(updated_cfg)

        self._update_tree_in_place()
        self._save_all_folder_configs()

    def clean_vlc_titles_now(self):
        if not self.scanned_groups:
            messagebox.showwarning("Atención", "Primero escanea una carpeta.")
            return

        confirm = messagebox.askyesno(
            "Limpiar Título VLC",
            "Esta operación reescribirá rápidamente los metadatos de los videos analizados (sin recodificar video ni audio) "
            "para que VLC y otros reproductores muestren exactamente el nombre del archivo en vez del título antiguo.\n\n"
            "¿Deseas continuar?"
        )
        if not confirm:
            return

        all_vids = []
        for g in self.scanned_groups.values():
            for v in g["videos"]:
                all_vids.append(v["filepath"])

        self.lbl_status.configure(text="Limpiando metadatos de títulos para VLC...")
        
        def worker():
            success_count = 0
            for fp in all_vids:
                if clean_file_metadata_inplace(fp):
                    success_count += 1
            self.after(0, lambda: messagebox.showinfo("Completado", f"Se limpiaron los metadatos de {success_count}/{len(all_vids)} archivos."))
            self.after(0, self.start_scan)

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # GESTIÓN DE COLA (AGREGAR SELECCIÓN, AGREGAR TODO, REORDENAR, QUITAR, LOG ERRORES)
    # =========================================================================
    def add_selected_to_queue(self, force_only_new: bool = False):
        selected_ids = list(self.tree.selection())
        if not selected_ids:
            if force_only_new:
                self.add_only_new_to_queue()
            else:
                self.add_all_to_queue()
            return

        self._save_all_folder_configs()
        only_new = force_only_new or self.var_only_new.get()
        only_res_naming = self.var_jellyfin_only_res.get()
        added_count = 0

        with self.queue_lock:
            for item_id in selected_ids:
                if item_id.startswith("group_"):
                    d_path = item_id[6:]
                    g_info = self.scanned_groups.get(d_path)
                    if g_info:
                        for v_meta in g_info["videos"]:
                            if only_new and v_meta.get("is_already_encoded"):
                                continue
                            added_count += self._append_video_to_queue(d_path, g_info, v_meta, only_res_naming)
                elif item_id.startswith("vid_"):
                    v_path = item_id[4:]
                    for d_path, g_info in self.scanned_groups.items():
                        for v_meta in g_info["videos"]:
                            if v_meta["filepath"] == v_path:
                                if only_new and v_meta.get("is_already_encoded"):
                                    continue
                                added_count += self._append_video_to_queue(d_path, g_info, v_meta, only_res_naming)
                                break

        self._refresh_queue_tree()
        self.lbl_status.configure(text=f"Se agregaron {added_count} tareas nuevas a la cola (configuraciones guardadas).")
        self.tabview.set("󰐍 02 • Cola de Codificación")

    def add_only_new_to_queue(self):
        """Agrega únicamente los videos no codificados / pendientes o que hayan tenido error, excluyendo los ya completados."""
        if not self.scanned_groups:
            messagebox.showwarning("Atención", "Primero escanea una carpeta con videos.")
            return

        self._save_all_folder_configs()
        only_res_naming = self.var_jellyfin_only_res.get()
        added_count = 0

        with self.queue_lock:
            for d_path, g_info in self.scanned_groups.items():
                for v_meta in g_info["videos"]:
                    # Omitir únicamente los videos que ya fueron terminados con éxito
                    if v_meta.get("is_already_encoded"):
                        continue
                    added_count += self._append_video_to_queue(d_path, g_info, v_meta, only_res_naming)

        self._refresh_queue_tree()
        self.lbl_status.configure(text=f"Se agregaron {added_count} tareas no codificadas a la cola (omitiendo ya completados).")
        self.tabview.set("󰐍 02 • Cola de Codificación")

    def add_all_to_queue(self):
        if not self.scanned_groups:
            messagebox.showwarning("Atención", "Primero escanea una carpeta con videos.")
            return

        self._save_all_folder_configs()
        only_new = self.var_only_new.get()
        only_res_naming = self.var_jellyfin_only_res.get()
        added_count = 0

        with self.queue_lock:
            for d_path, g_info in self.scanned_groups.items():
                for v_meta in g_info["videos"]:
                    if only_new and v_meta.get("is_already_encoded"):
                        continue
                    added_count += self._append_video_to_queue(d_path, g_info, v_meta, only_res_naming)

        self._refresh_queue_tree()
        self.lbl_status.configure(text=f"Se agregaron {added_count} tareas de toda la biblioteca a la cola.")
        self.tabview.set("󰐍 02 • Cola de Codificación")

    def _refresh_queue_tree(self):
        prev_sel = self.tree_q.selection()
        self.tree_q.delete(*self.tree_q.get_children())
        
        pending_c = 0
        done_c = 0
        err_c = 0

        with self.queue_lock:
            total_c = len(self.job_queue)
            for idx, job in enumerate(self.job_queue):
                q_id = f"q_{idx}"
                st = job["status"]
                if st == "Codificando...":
                    tag_status = "processing"
                elif st == "Pausado":
                    tag_status = "paused"
                elif st == "Listo":
                    tag_status = "done"
                    done_c += 1
                elif "Error" in st:
                    tag_status = "error"
                    err_c += 1
                else:
                    tag_status = "pending_even" if idx % 2 == 0 else "pending_odd"
                    pending_c += 1

                ver_label = f"V{job['v_num']+1}: {job['v_cfg']['codec']} ({job['v_cfg']['res']})"
                self.tree_q.insert("", "end", iid=q_id, values=(
                    idx + 1,
                    job["v_meta"]["filename"],
                    ver_label,
                    job["progress"],
                    st,
                    job["out_name"]
                ), tags=(tag_status,))

        for s in prev_sel:
            if self.tree_q.exists(s):
                self.tree_q.selection_add(s)

        self.lbl_queue_stats.configure(
            text=f"📋 Cola: {total_c} tareas  |  ⏳ Pendientes: {pending_c}  |  ✅ Listos: {done_c}  |  ❌ Errores (Saltados): {err_c}"
        )

    def show_queue_errors_dialog(self):
        errors = []
        with self.queue_lock:
            for idx, job in enumerate(self.job_queue):
                if job.get("error_detail"):
                    errors.append(f"--- Tarea #{idx+1}: {job['v_meta']['filename']} -> {job['out_name']} ---\n{job['error_detail']}\n")

        if not errors:
            messagebox.showinfo("Registro de Errores", "No se ha registrado ningún error en la cola actual.")
            return

        win = ctk.CTkToplevel(self)
        win.title("◈ NEO•OPTIMIZER // Detalle de Errores Saltados")
        win.geometry("860x520")
        win.configure(fg_color=THEME_BG)
        icon_path = os.path.join(self.app_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                win.iconbitmap(icon_path)
            except Exception:
                pass

        header_box = ctk.CTkFrame(win, fg_color="transparent")
        header_box.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(header_box, text="🔍 Registro de Errores FFmpeg en la Cola", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME_RED).pack(side="left")

        txt = ctk.CTkTextbox(win, font=ctk.CTkFont(family="Consolas", size=11), fg_color=THEME_INNER, border_width=1, border_color=THEME_INNER_BORDER, text_color="#f8bd96")
        txt.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        txt.insert("1.0", "\n".join(errors))
        txt.configure(state="disabled")

        btn_close = ctk.CTkButton(win, text="Cerrar", width=120, height=32, fg_color="#222538", hover_color="#313244", font=ctk.CTkFont(size=12, weight="bold"), command=win.destroy)
        btn_close.pack(pady=(0, 12))

    def move_queue_item_up(self):
        selected = self.tree_q.selection()
        if not selected:
            return
        idx = int(selected[0].split("_")[1])
        with self.queue_lock:
            if idx > 0 and self.job_queue[idx]["status"] == "Pendiente" and self.job_queue[idx - 1]["status"] == "Pendiente":
                self.job_queue[idx], self.job_queue[idx - 1] = self.job_queue[idx - 1], self.job_queue[idx]
        self._refresh_queue_tree()
        self.tree_q.selection_set(f"q_{idx - 1}")

    def move_queue_item_down(self):
        selected = self.tree_q.selection()
        if not selected:
            return
        idx = int(selected[0].split("_")[1])
        with self.queue_lock:
            if idx < len(self.job_queue) - 1 and self.job_queue[idx]["status"] == "Pendiente" and self.job_queue[idx + 1]["status"] == "Pendiente":
                self.job_queue[idx], self.job_queue[idx + 1] = self.job_queue[idx + 1], self.job_queue[idx]
        self._refresh_queue_tree()
        self.tree_q.selection_set(f"q_{idx + 1}")

    def remove_queue_selected(self):
        selected_ids = list(self.tree_q.selection())
        if not selected_ids:
            return
        
        indices = []
        for s in selected_ids:
            try:
                indices.append(int(s.split("_")[1]))
            except Exception:
                pass
        indices.sort(reverse=True)

        with self.queue_lock:
            for idx in indices:
                if 0 <= idx < len(self.job_queue):
                    if self.job_queue[idx]["status"] != "Codificando...":
                        self.job_queue.pop(idx)

        self.tree_q.selection_remove(*self.tree_q.selection())
        self._refresh_queue_tree()
        self.lbl_status.configure(text=f"Se quitaron {len(indices)} tareas de la cola.")

    def clear_queue(self):
        with self.queue_lock:
            self.job_queue = [j for j in self.job_queue if j["status"] == "Codificando..."]
        self._refresh_queue_tree()

    def start_encoding(self):
        self._save_all_folder_configs()
        if not self.job_queue:
            if not self.scanned_groups:
                messagebox.showwarning("Atención", "Primero escanea una carpeta con videos.")
                return
            self.add_all_to_queue()

        if not self.job_queue:
            messagebox.showinfo("Información", "No hay tareas pendientes en la cola.")
            return

        if self.is_encoding:
            return

        if self.var_replace_original.get():
            confirm = messagebox.askyesno(
                "Confirmación de Reemplazo",
                "⚠️ Has seleccionado reemplazar eliminando los originales.\n\n"
                "Al finalizar con éxito TODAS las versiones de cada video, el archivo original antiguo se eliminará.\n"
                "¿Deseas continuar?"
            )
            if not confirm:
                return

        self.is_encoding = True
        self.is_paused = False
        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸ Pausar", fg_color="#f9e2af")
        self.btn_cancel.configure(state="normal")

        threading.Thread(target=self._encoding_queue_pipeline, daemon=True).start()

    def stop_encoding(self):
        if self.is_encoding or self.current_process:
            self.is_encoding = False
            self.is_paused = False
            if self.current_process:
                try:
                    parent = psutil.Process(self.current_process.pid)
                    for child in parent.children(recursive=True):
                        try:
                            child.resume()
                        except Exception:
                            pass
                        child.kill()
                    try:
                        parent.resume()
                    except Exception:
                        pass
                    parent.kill()
                    parent.wait(timeout=3)
                except Exception:
                    try:
                        self.current_process.kill()
                    except Exception:
                        pass

            self.lbl_status.configure(text="Codificación detenida por el usuario.")
            self.lbl_fps_speed.configure(text="🚀 Velocidad: Detenido", text_color="#f38ba8")
            self.btn_start.configure(state="normal")
            self.btn_pause.configure(state="disabled", text="⏸ Pausar")
            self.btn_cancel.configure(state="disabled")

    def _safe_replace_output(self, temp_out_path: str, out_path: str):
        """Reemplaza el archivo de destino de forma segura en Windows, liberando bloqueos de FFmpeg zombis o atributos de solo lectura."""
        out_abs = os.path.normcase(os.path.abspath(out_path))
        cur_pid = self.current_process.pid if self.current_process else -1

        # 1. Si algún proceso ffmpeg.exe huérfano/pausado de otra sesión tiene abierto out_path, cerrarlo
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['pid'] != cur_pid and 'ffmpeg' in (proc.info['name'] or '').lower():
                    cmdline_joined = " ".join(proc.info['cmdline'] or [])
                    if os.path.basename(out_path).lower() in cmdline_joined.lower():
                        try:
                            proc.resume()
                        except Exception:
                            pass
                        proc.kill()
                        proc.wait(timeout=2)
            except Exception:
                pass

        # 2. Quitar atributo de solo lectura si el archivo destino ya existe
        if os.path.exists(out_path):
            try:
                os.chmod(out_path, stat.S_IWRITE)
            except Exception:
                pass

        # 3. Reintentar os.replace hasta 6 veces (dando margen a Windows / Jellyfin / Antivirus para soltar el handle)
        last_exc = None
        for attempt in range(6):
            try:
                os.replace(temp_out_path, out_path)
                return
            except Exception as e:
                last_exc = e
                time.sleep(0.4)
                if os.path.exists(out_path):
                    try:
                        os.chmod(out_path, stat.S_IWRITE)
                    except Exception:
                        pass
        raise last_exc

    def _encoding_queue_pipeline(self):
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        while self.is_encoding:
            job = None
            with self.queue_lock:
                for j in self.job_queue:
                    if j["status"] == "Pendiente":
                        job = j
                        break

            if not job:
                break

            v_meta = job["v_meta"]
            orig_path = v_meta["filepath"]
            cfg = job["cfg"]
            v_cfg = job["v_cfg"]
            out_path = job["output_path"]
            temp_out_path = out_path + ".encoding_tmp.mkv"

            # Verificar que el archivo de entrada realmente exista antes de invocar FFmpeg
            if not os.path.isfile(orig_path):
                job["status"] = "❌ Error (No existe)"
                job["error_detail"] = f"El archivo de origen ya no existe en disco:\n{orig_path}"
                self.after(0, self._refresh_queue_tree)
                continue

            job["status"] = "Codificando..."
            self.after(0, self._refresh_queue_tree)

            burn_str = " + Quemando Subtítulos" if v_cfg.get("burn_sub") else ""
            self.lbl_status.configure(text=f"Codificando: {job['out_name']}{burn_str}")

            pref_audio_pat = cfg.get("audio_name", "") if cfg.get("audio_mode") == "name" else ""
            pref_audio_idx = cfg.get("audio_track_idx") if cfg.get("audio_mode") == "track" else None

            if cfg.get("sub_mode") == "none" or cfg.get("sub_track_idx") == -1:
                pref_sub_pat = ""
                pref_sub_idx = -1
            else:
                pref_sub_pat = cfg.get("sub_name", "") if cfg.get("sub_mode") == "name" else ""
                pref_sub_idx = cfg.get("sub_track_idx") if cfg.get("sub_mode") == "track" else None

            # Codificar siempre hacia archivo temporal seguro (.encoding_tmp.mkv)
            cmd = build_ffmpeg_encode_command(
                meta=v_meta,
                output_path=temp_out_path,
                target_codec=v_cfg["codec"],
                target_bitrate_kbps=v_cfg["bitrate"],
                preset=v_cfg.get("preset", "p5"),
                resolution=v_cfg["res"],
                burn_subtitles=v_cfg.get("burn_sub", False),
                preferred_audio_pattern=pref_audio_pat,
                preferred_audio_rel_idx=pref_audio_idx,
                preferred_sub_pattern=pref_sub_pat,
                preferred_sub_rel_idx=pref_sub_idx,
                clean_metadata_title=True
            )

            success, last_error = self._execute_ffmpeg_with_fps(cmd, startupinfo, job, v_meta.get("duration_sec", 0.0))

            if success and os.path.isfile(temp_out_path) and os.path.getsize(temp_out_path) > 512 * 1024:
                # Reemplazar atómicamente el destino final con el archivo temporal terminado
                try:
                    self._safe_replace_output(temp_out_path, out_path)
                except Exception as e:
                    job["status"] = "❌ Error (Permisos)"
                    job["error_detail"] = f"No se pudo renombrar el archivo temporal a {out_path}: {e}"
                    self.after(0, self._refresh_queue_tree)
                    continue

                job["status"] = "Listo"
                job["progress"] = "100%"
                self.after(0, self._refresh_queue_tree)

                # Registrar en historial (guardando todas las versiones de salida generadas para este archivo)
                history = job["g_info"]["history"]
                if "encoded_files" not in history:
                    history["encoded_files"] = {}
                prev_entry = history["encoded_files"].get(v_meta["file_id"], {})
                prev_outputs = prev_entry.get("outputs", []) if isinstance(prev_entry, dict) else []
                if job["out_name"] not in prev_outputs:
                    prev_outputs.append(job["out_name"])
                history["encoded_files"][v_meta["file_id"]] = {
                    "original_name": v_meta["filename"],
                    "output": job["out_name"],
                    "outputs": prev_outputs
                }
                save_history(job["d_path"], history)

                # Solo eliminar el archivo original si:
                # 1. Está activado Reemplazar originales
                # 2. El nombre destino es distinto del original
                # 3. YA NO QUEDAN otras versiones pendientes en la cola que necesiten ese mismo archivo original
                if self.var_replace_original.get() and os.path.abspath(out_path) != os.path.abspath(orig_path):
                    still_needed = False
                    with self.queue_lock:
                        for other_j in self.job_queue:
                            if other_j["status"] in ("Pendiente", "Codificando...") and os.path.abspath(other_j["v_meta"]["filepath"]) == os.path.abspath(orig_path):
                                still_needed = True
                                break
                    if not still_needed:
                        try:
                            os.remove(orig_path)
                        except Exception as e:
                            print(f"Error borrando original: {e}")
            else:
                # Limpiar archivo temporal incompleto si falló o se canceló
                if os.path.isfile(temp_out_path):
                    try:
                        os.remove(temp_out_path)
                    except Exception:
                        pass

                if not self.is_encoding:
                    job["status"] = "Pendiente"
                    job["progress"] = "0%"
                    self.after(0, self._refresh_queue_tree)
                    break

                # ¡IMPORTANTE! Si da error en un archivo, lo marca como Error (Saltado) y SIGUE con el siguiente en la cola
                err_summary = last_error[-2500:] if last_error else "FFmpeg falló al generar el archivo."
                job["status"] = "❌ Error (Saltado)"
                job["error_detail"] = err_summary
                self.after(0, self._refresh_queue_tree)
                continue

            # Actualizar barra general
            with self.queue_lock:
                total_q = max(1, len(self.job_queue))
                done_q = sum(1 for j in self.job_queue if j["status"] in ("Listo", "❌ Error (Saltado)", "❌ Error (No existe)"))
                self.progress_bar.set(done_q / total_q)

        if self.is_encoding:
            with self.queue_lock:
                err_count = sum(1 for j in self.job_queue if "Error" in j["status"])
                done_count = sum(1 for j in self.job_queue if j["status"] == "Listo")

            self.lbl_fps_speed.configure(text="🚀 Velocidad: Finalizado", text_color="#a6e3a1")
            self.after(0, lambda: self._handle_queue_finished(done_count, err_count))

        self.btn_start.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸ Pausar")
        self.btn_cancel.configure(state="disabled")
        self.is_encoding = False
        self.is_paused = False

    def _on_after_action_change(self, choice=None):
        val = self.var_after_action.get()
        if "Apagar" in val or "Hibernar" in val:
            self.frame_after.configure(border_color="#f38ba8")
        elif "Suspender" in val or "Cerrar" in val:
            self.frame_after.configure(border_color="#f9e2af")
        else:
            self.frame_after.configure(border_color="#313244")

    def _handle_queue_finished(self, done_count: int, err_count: int):
        action = self.var_after_action.get()
        if err_count > 0:
            self.lbl_status.configure(text=f"Cola finalizada: {done_count} listos, {err_count} con error (saltados). Pulsa 'Ver Detalle de Errores'.")
        else:
            self.lbl_status.configure(text=f"¡Completadas con éxito las {done_count} tareas de la cola!")

        if any(keyword in action for keyword in ("Apagar", "Hibernar", "Suspender", "Cerrar")):
            self._start_countdown_and_execute(action, done_count, err_count)
        else:
            if err_count > 0:
                messagebox.showwarning(
                    "Cola Finalizada con Avisos",
                    f"Se completaron {done_count} tareas con éxito.\nSe saltaron {err_count} archivos con error (puedes ver el motivo con el botón '🔍 Ver Detalle de Errores')."
                )
            else:
                messagebox.showinfo("Éxito", f"Se han procesado las {done_count} tareas de la cola correctamente.")

    def _start_countdown_and_execute(self, action: str, done_count: int, err_count: int):
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"◈ NEO•OPTIMIZER // {action}")
        dialog.geometry("520x280")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=THEME_BG)

        icon_path = os.path.join(self.app_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                dialog.iconbitmap(icon_path)
            except Exception:
                pass

        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - 250
            y = self.winfo_y() + (self.winfo_height() // 2) - 135
            dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass

        title_map = {
            "Apagar PC": ("🔌 Apagado del Equipo", "#f38ba8", "apagará"),
            "Hibernar": ("❄️ Hibernación del Equipo", "#89b4fa", "hibernará"),
            "Suspender": ("🌙 Suspensión del Equipo", "#cba6f7", "suspenderá"),
            "Cerrar programa": ("🚪 Cierre del Optimizador", "#fab387", "cerrará")
        }
        header_text, header_color, verb = ("Acción al finalizar", "#89b4fa", "ejecutará")
        for k, v in title_map.items():
            if k in action:
                header_text, header_color, verb = v
                break

        ctk.CTkLabel(dialog, text=header_text, font=ctk.CTkFont(size=18, weight="bold"), text_color=header_color).pack(pady=(16, 2))

        info_text = f"Cola completada: {done_count} tareas listas" + (f" ({err_count} con error)" if err_count > 0 else "")
        ctk.CTkLabel(dialog, text=info_text, font=ctk.CTkFont(size=12), text_color="#a6adc8").pack(pady=(0, 8))

        lbl_timer = ctk.CTkLabel(dialog, text=f"El equipo se {verb} en 30 segundos...", font=ctk.CTkFont(size=15, weight="bold"), text_color="#f9e2af")
        lbl_timer.pack(pady=6)

        prog_bar = ctk.CTkProgressBar(dialog, width=400, height=8, corner_radius=4, progress_color=header_color)
        prog_bar.set(1.0)
        prog_bar.pack(pady=(4, 16))

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=30, pady=(0, 10))

        remaining = [30]
        timer_id = [None]

        def cancel_action():
            if timer_id[0]:
                self.after_cancel(timer_id[0])
            self.var_after_action.set("Nada (Mantener encendido)")
            self._on_after_action_change()
            self.lbl_status.configure(text="Acción al terminar cancelada por el usuario.")
            dialog.destroy()

        def execute_now():
            if timer_id[0]:
                self.after_cancel(timer_id[0])
            dialog.destroy()
            self._do_system_action(action)

        btn_cancel = ctk.CTkButton(btn_row, text="❌ Cancelar", width=140, height=36, fg_color="#313244", hover_color="#45475a", font=ctk.CTkFont(size=12, weight="bold"), command=cancel_action)
        btn_cancel.pack(side="left", padx=10)

        btn_exec = ctk.CTkButton(btn_row, text="⚡ Ejecutar Ahora", width=160, height=36, fg_color=header_color, text_color="#11111b", hover_color="#ffffff", font=ctk.CTkFont(size=12, weight="bold"), command=execute_now)
        btn_exec.pack(side="right", padx=10)

        def tick():
            remaining[0] -= 1
            if remaining[0] <= 0:
                dialog.destroy()
                self._do_system_action(action)
            else:
                lbl_timer.configure(text=f"El equipo se {verb} en {remaining[0]} segundos...")
                prog_bar.set(remaining[0] / 30.0)
                timer_id[0] = self.after(1000, tick)

        timer_id[0] = self.after(1000, tick)
        dialog.protocol("WM_DELETE_WINDOW", cancel_action)
        try:
            dialog.focus_force()
        except Exception:
            pass

    def _do_system_action(self, action: str):
        if "Cerrar" in action:
            self._on_app_closing()
        elif "Apagar" in action:
            if os.name == 'nt':
                subprocess.run(["shutdown", "/s", "/f", "/t", "0"], shell=True)
            else:
                try:
                    subprocess.run(["systemctl", "poweroff"])
                except Exception:
                    subprocess.run(["shutdown", "-h", "now"])
        elif "Hibernar" in action:
            if os.name == 'nt':
                res = subprocess.run(["shutdown", "/h"], shell=True)
                if res.returncode != 0:
                    try:
                        import ctypes
                        ctypes.windll.PowrProf.SetSuspendState(1, 0, 0)
                    except Exception as e:
                        print(f"Error al hibernar: {e}")
            else:
                try:
                    subprocess.run(["systemctl", "hibernate"])
                except Exception:
                    pass
        elif "Suspender" in action:
            if os.name == 'nt':
                try:
                    import ctypes
                    ctypes.windll.PowrProf.SetSuspendState(0, 0, 0)
                except Exception:
                    subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=True)
            else:
                try:
                    subprocess.run(["systemctl", "suspend"])
                except Exception:
                    pass

    def _execute_ffmpeg_with_fps(self, cmd: List[str], startupinfo, job_obj: Dict[str, Any], duration_sec: float) -> (bool, str):
        try:
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                startupinfo=startupinfo,
                bufsize=1
            )

            stderr_lines = []

            def read_stderr_thread(proc):
                try:
                    for s_line in proc.stderr:
                        stderr_lines.append(s_line)
                        if len(stderr_lines) > 200:
                            stderr_lines.pop(0)
                except Exception:
                    pass

            t_err = threading.Thread(target=read_stderr_thread, args=(self.current_process,), daemon=True)
            t_err.start()

            current_fps = "0"
            current_speed = "0x"
            last_reported_pct = -1

            for line in self.current_process.stdout:
                line_clean = line.strip()
                if not line_clean:
                    continue

                if line_clean.startswith("fps="):
                    current_fps = line_clean.split("=")[1].strip()
                elif line_clean.startswith("speed="):
                    current_speed = line_clean.split("=")[1].strip()
                    msg = f"🚀 Velocidad: {current_fps} FPS ({current_speed})"
                    self.lbl_fps_speed.configure(text=msg)
                elif line_clean.startswith("out_time_ms="):
                    try:
                        ms = int(line_clean.split("=")[1].strip())
                        cur_sec = ms / 1000000.0
                        if duration_sec > 0:
                            pct = min(99, int((cur_sec / duration_sec) * 100))
                            if pct != last_reported_pct:
                                last_reported_pct = pct
                                job_obj["progress"] = f"{pct}%"
                                self.after(0, self._refresh_queue_tree)
                    except Exception:
                        pass
                elif line_clean == "progress=end":
                    job_obj["progress"] = "100%"
                    self.after(0, self._refresh_queue_tree)

            self.current_process.wait()
            t_err.join(timeout=2.0)

            retcode = self.current_process.returncode
            if retcode != 0:
                err_text = "".join(stderr_lines)
                return False, err_text
            return True, ""
        except Exception as e:
            return False, str(e)

if __name__ == "__main__":
    app = ModernVideoOptimizer()
    app.mainloop()
