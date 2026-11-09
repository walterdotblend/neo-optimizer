"""
=============================================================================
◈ NEO•OPTIMIZER // RTX 4070 SUPER LAB - PyQt6 Edition
=============================================================================
Optimizador de Video Profesional Multi-Versión
Inspirado en la estética r/unixporn y temas de GRUB (Catppuccin / Tokyo Night).
- Rendimiento nativo C++ ultra-rápido, redimensionamiento instantáneo sin lag.
- Detección dinámica de GPU (NVIDIA RTX, Intel Arc, AMD Radeon) y auto-configuración
  de códec óptimo (AV1 si es compatible, HEVC u otro si no lo es).
- Soporte internacional (i18n): Inglés por defecto, Español, Francés, Japonés.
  Ajusta automáticamente el idioma por defecto de pistas de audio y subtítulos.
- Selector desplegable (ComboBox) con flecha e indicador interactivo de alta claridad.
- Granularidad por Serie (carpeta) o Video individual.
- Extracción de Bitrate exacta (etiquetas BPS de MKV y fallback de peso).
- Tolerancia a fallos: salto automático de archivos con error y visor de logs.
- Acciones al finalizar (Apagar, Hibernar, Suspender, Cerrar) con cuenta regresiva.
- Soporte para "🚫 Ningún subtítulo por defecto" (-disposition:s:i 0).
- Sin mención de software de terceros.
=============================================================================
"""

import os
import sys
import copy
import time
import re
import stat
import subprocess
import threading
from typing import Dict, List, Any, Optional

import psutil

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QTabWidget, QFrame, QMenu, QDialog, QTextEdit,
    QFileDialog, QMessageBox, QAbstractItemView, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QColor, QBrush, QAction, QPixmap

from core_engine import (
    scan_directory_for_videos,
    build_ffmpeg_encode_command,
    build_standard_filename,
    detect_video_resolution_tag,
    calculate_auto_bitrate,
    estimate_compressed_size_mb,
    find_best_audio_match,
    find_best_sub_match,
    clean_file_metadata_inplace,
    load_history,
    save_history
)
from hardware_detector import detect_hardware_profile
from translations import get_text, TRANSLATIONS

if getattr(sys, 'frozen', False):
    APP_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
ARROW_PNG = os.path.join(APP_DIR, "down_arrow.png").replace("\\", "/")
ARROW_HOVER_PNG = os.path.join(APP_DIR, "down_arrow_hover.png").replace("\\", "/")

# -----------------------------------------------------------------------------
# ESTILOS QSS - TEMA GRUB / R/UNIXPORN (CATPPUCCIN MOCHA / TOKYO NIGHT HYBRID)
# -----------------------------------------------------------------------------
def build_qss_theme() -> str:
    return f"""
/* Reset & Fondo General */
QWidget {{
    background-color: #08090d;
    color: #cdd6f4;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 12px;
}}

/* Tarjetas Flotantes e Islas */
QFrame.CardFrame {{
    background-color: #0f111a;
    border: 1px solid #1c1f30;
    border-radius: 8px;
}}

QFrame.SubCardFrame {{
    background-color: #07080c;
    border: 1px solid #181b29;
    border-radius: 6px;
}}

/* Pestañas Estilo GRUB Boot-Entries */
QTabWidget::pane {{
    border: 1px solid #1c1f30;
    background-color: #0b0c13;
    border-radius: 8px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: #0d0f17;
    color: #6c7086;
    border: 1px solid #1a1c2b;
    border-bottom: none;
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
    font-size: 12px;
}}

QTabBar::tab:selected {{
    background-color: #141724;
    color: #89b4fa;
    border: 1px solid #282d44;
    border-bottom: 2px solid #89b4fa;
}}

QTabBar::tab:hover:!selected {{
    background-color: #10121d;
    color: #cdd6f4;
}}

/* Entradas de Texto */
QLineEdit {{
    background-color: #07080c;
    border: 1px solid #1e2235;
    border-radius: 6px;
    color: #cdd6f4;
    padding: 5px 10px;
    selection-background-color: #2563eb;
}}

QLineEdit:focus {{
    border: 1px solid #89b4fa;
    background-color: #0a0c14;
}}

/* DESPLEGABLES (COMBOBOX) - FLECHA E INDICADOR CLAROS */
QComboBox {{
    background-color: #0c0e16;
    border: 1px solid #2a3048;
    border-radius: 6px;
    color: #cdd6f4;
    padding: 5px 30px 5px 10px;
    font-weight: 600;
}}

QComboBox:hover {{
    border: 1px solid #89b4fa;
    background-color: #121522;
}}

QComboBox:focus {{
    border: 1px solid #89b4fa;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: 1px solid #282d44;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
    background-color: #161928;
}}

QComboBox::drop-down:hover {{
    background-color: #242a42;
}}

QComboBox::down-arrow {{
    image: url("{ARROW_PNG}");
    width: 10px;
    height: 10px;
}}

QComboBox::down-arrow:hover {{
    image: url("{ARROW_HOVER_PNG}");
}}

QComboBox QAbstractItemView {{
    background-color: #0f111a;
    border: 1px solid #282c42;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    color: #cdd6f4;
    outline: none;
    padding: 4px;
}}

/* Casillas de Verificación y Radio Buttons */
QCheckBox, QRadioButton {{
    spacing: 7px;
    color: #cdd6f4;
    font-size: 11px;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid #282c42;
    background-color: #07080c;
    border-radius: 3px;
}}

QRadioButton::indicator {{
    border-radius: 7px;
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border: 1px solid #89b4fa;
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: #89b4fa;
    border: 1px solid #89b4fa;
}}

/* Botones con Acentos Neón */
QPushButton {{
    background-color: #181b29;
    color: #cdd6f4;
    border: 1px solid #282c42;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: #23273c;
    border: 1px solid #3b4263;
}}

QPushButton:pressed {{
    background-color: #12141f;
}}

QPushButton:disabled {{
    background-color: #0d0f17;
    color: #45475a;
    border: 1px solid #141624;
}}

QPushButton#btn_scan {{
    background-color: #89b4fa;
    color: #08090d;
    border: none;
}}

QPushButton#btn_scan:hover {{
    background-color: #b4befe;
}}

QPushButton#btn_start {{
    background-color: #a6e3a1;
    color: #08090d;
    border: none;
}}

QPushButton#btn_start:hover {{
    background-color: #94e2d5;
}}

QPushButton#btn_add_sel {{
    background-color: #cba6f7;
    color: #08090d;
    border: none;
}}

QPushButton#btn_add_sel:hover {{
    background-color: #d5bdfc;
}}

QPushButton#btn_pause {{
    background-color: #f9e2af;
    color: #08090d;
    border: none;
}}

QPushButton#btn_pause:hover {{
    background-color: #f5e0dc;
}}

QPushButton#btn_cancel {{
    background-color: #f38ba8;
    color: #08090d;
    border: none;
}}

QPushButton#btn_cancel:hover {{
    background-color: #eba0ac;
}}

/* Tablas Ultra-Rápidas (QTableWidget) */
QTableWidget {{
    background-color: #07080c;
    alternate-background-color: #0d0f17;
    gridline-color: #141724;
    border: 1px solid #181b29;
    border-radius: 6px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    font-size: 11px;
}}

QHeaderView::section {{
    background-color: #12141f;
    color: #89b4fa;
    padding: 6px;
    border: none;
    border-right: 1px solid #1c1f30;
    border-bottom: 1px solid #1c1f30;
    font-weight: bold;
    font-size: 11px;
}}

/* Barra de Progreso */
QProgressBar {{
    background-color: #07080c;
    border: 1px solid #181b29;
    border-radius: 5px;
    text-align: center;
    color: #cdd6f4;
    font-weight: bold;
    font-size: 10px;
}}

QProgressBar::chunk {{
    background-color: #89b4fa;
    border-radius: 4px;
}}

/* Barras de Desplazamiento Minimalistas */
QScrollBar:vertical {{
    border: none;
    background: #07080c;
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: #252a42;
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #89b4fa;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: #07080c;
    height: 8px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: #252a42;
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #89b4fa;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Menú Contextual */
QMenu {{
    background-color: #0f111a;
    border: 1px solid #282c42;
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
    color: #cdd6f4;
}}

QMenu::item:selected {{
    background-color: #2563eb;
    color: #ffffff;
}}

QMenu::separator {{
    height: 1px;
    background: #1e2235;
    margin: 4px 8px;
}}
"""

# -----------------------------------------------------------------------------
# HILO DE CODIFICACIÓN EN SEGUNDO PLANO (THREAD-SAFE & ZERO UI BLOCK)
# -----------------------------------------------------------------------------
class EncodingThread(QThread):
    progress_updated = pyqtSignal(int, str, str, str)  # job_idx, pct_str, fps_str, time_str
    job_finished = pyqtSignal(int, bool, str)          # job_idx, success, error_detail
    queue_completed = pyqtSignal(int, int)             # done_count, error_count

    def __init__(self, job_queue: List[Dict[str, Any]], var_replace_orig: bool):
        super().__init__()
        self.job_queue = job_queue
        self.var_replace_orig = var_replace_orig
        self._is_running = True
        self._is_paused = False
        self.current_process: Optional[subprocess.Popen] = None
        self._proc_lock = threading.Lock()

    def run(self):
        done_count = 0
        error_count = 0

        for idx, job in enumerate(self.job_queue):
            if not self._is_running:
                break

            if job["status"] in ("Listo", "Completed", "Completado"):
                done_count += 1
                continue

            job["status"] = "Encoding..."
            self.progress_updated.emit(idx, "0%", "Starting...", "")

            orig_path = job["v_meta"]["filepath"]
            out_path = job["output_path"]
            temp_out_path = out_path + ".encoding_tmp.mkv"

            # Limpiar temporal previo
            if os.path.isfile(temp_out_path):
                try:
                    os.remove(temp_out_path)
                except Exception:
                    pass

            v_cfg = job["v_cfg"]
            codec = v_cfg["codec"]
            res = v_cfg["res"]
            try:
                bitrate_kbps = int(v_cfg["bitrate"])
            except (ValueError, TypeError):
                bitrate_kbps = calculate_auto_bitrate(
                    job["v_meta"].get("video_codec", "h264"),
                    job["v_meta"].get("bitrate_kbps", 0),
                    job["v_meta"].get("resolution_tag", "1080p"),
                    codec,
                    res
                )
            burn_sub = v_cfg.get("burn_sub", False)

            cmd = build_ffmpeg_encode_command(
                meta=job["v_meta"],
                output_path=temp_out_path,
                target_codec=codec,
                target_bitrate_kbps=bitrate_kbps,
                preset="p4",
                resolution=res,
                burn_subtitles=burn_sub,
                preferred_audio_pattern=job["cfg"].get("audio_pattern", "English"),
                preferred_audio_rel_idx=job["cfg"].get("audio_rel_idx"),
                preferred_sub_pattern=job["cfg"].get("sub_pattern", "English"),
                preferred_sub_rel_idx=job["cfg"].get("sub_rel_idx"),
                clean_metadata_title=True
            )

            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            duration_sec = job["v_meta"].get("duration_seconds", 0.0)
            success, last_error = self._execute_ffmpeg(cmd, startupinfo, idx, duration_sec)

            if success and os.path.isfile(temp_out_path) and os.path.getsize(temp_out_path) > 1000:
                if self._safe_replace(temp_out_path, out_path):
                    job["status"] = "Completed"
                    job["progress"] = "100%"
                    done_count += 1

                    # Registrar en historial
                    history = load_history(job["d_path"])
                    if "encoded_files" not in history:
                        history["encoded_files"] = {}
                    prev_outputs = history["encoded_files"].get(job["v_meta"]["file_id"], {}).get("outputs", [])
                    if job["out_name"] not in prev_outputs:
                        prev_outputs.append(job["out_name"])
                    history["encoded_files"][job["v_meta"]["file_id"]] = {
                        "original_name": job["v_meta"]["filename"],
                        "output": job["out_name"],
                        "outputs": prev_outputs
                    }
                    save_history(job["d_path"], history)

                    # Reemplazar original si aplica
                    if self.var_replace_orig and os.path.abspath(out_path) != os.path.abspath(orig_path):
                        still_needed = any(
                            other["status"] in ("Pendiente", "Pending", "Encoding...", "Codificando...") and
                            os.path.abspath(other["v_meta"]["filepath"]) == os.path.abspath(orig_path)
                            for other in self.job_queue
                        )
                        if not still_needed:
                            try:
                                os.remove(orig_path)
                            except Exception:
                                pass

                    self.job_finished.emit(idx, True, "")
                else:
                    job["status"] = "Error (Skipped)"
                    job["error_detail"] = "Failed to rename temp file to target output."
                    error_count += 1
                    self.job_finished.emit(idx, False, job["error_detail"])
            else:
                if os.path.isfile(temp_out_path):
                    try:
                        os.remove(temp_out_path)
                    except Exception:
                        pass

                if not self._is_running:
                    job["status"] = "Pending"
                    self.job_finished.emit(idx, False, "Canceled by user.")
                    break

                job["status"] = "Error (Skipped)"
                job["error_detail"] = last_error[-2500:] if last_error else "FFmpeg failed during encoding."
                error_count += 1
                self.job_finished.emit(idx, False, job["error_detail"])

        self.queue_completed.emit(done_count, error_count)

    def _execute_ffmpeg(self, cmd: List[str], startupinfo, job_idx: int, duration_sec: float) -> (bool, str):
        try:
            with self._proc_lock:
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )

            stderr_lines = []
            def read_err(proc):
                try:
                    for line in proc.stderr:
                        stderr_lines.append(line)
                        if len(stderr_lines) > 60:
                            stderr_lines.pop(0)
                except Exception:
                    pass

            t_err = threading.Thread(target=read_err, args=(self.current_process,), daemon=True)
            t_err.start()

            last_fps = "0"
            last_speed = "1.0x"

            while self.current_process and self.current_process.poll() is None:
                line = self.current_process.stdout.readline()
                if not line:
                    continue
                line = line.strip()
                if "=" in line:
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip()
                    if key == "fps":
                        last_fps = val
                    elif key == "speed":
                        last_speed = val
                    elif key == "out_time_ms":
                        try:
                            cur_ms = int(val)
                            cur_sec = cur_ms / 1_000_000.0
                            pct = 0
                            if duration_sec > 0:
                                pct = min(100, int((cur_sec / duration_sec) * 100))
                            pct_str = f"{pct}%"
                            spd_str = f"🚀 {last_fps} FPS • {last_speed}"
                            self.progress_updated.emit(job_idx, pct_str, spd_str, f"{int(cur_sec)}s")
                        except Exception:
                            pass
                    elif key == "progress" and val == "end":
                        self.progress_updated.emit(job_idx, "100%", "Finishing...", "")

            ret_code = self.current_process.wait() if self.current_process else -1
            t_err.join(timeout=1.0)
            last_error = "".join(stderr_lines)
            return (ret_code == 0), last_error

        except Exception as e:
            return False, str(e)
        finally:
            with self._proc_lock:
                self.current_process = None

    def _safe_replace(self, temp_path: str, final_path: str) -> bool:
        max_retries = 8
        for attempt in range(max_retries):
            try:
                if os.path.exists(final_path):
                    try:
                        os.chmod(final_path, stat.S_IWRITE | stat.S_IREAD)
                    except Exception:
                        pass
                    try:
                        os.remove(final_path)
                    except Exception:
                        pass
                os.replace(temp_path, final_path)
                return True
            except PermissionError:
                time.sleep(0.6)
            except Exception:
                time.sleep(0.4)
        return False

    def pause(self):
        if self.current_process:
            try:
                p = psutil.Process(self.current_process.pid)
                p.suspend()
                for c in p.children(recursive=True):
                    c.suspend()
                self._is_paused = True
            except Exception:
                pass

    def resume(self):
        if self.current_process:
            try:
                p = psutil.Process(self.current_process.pid)
                for c in p.children(recursive=True):
                    c.resume()
                p.resume()
                self._is_paused = False
            except Exception:
                pass

    def stop(self):
        self._is_running = False
        if self.current_process:
            try:
                p = psutil.Process(self.current_process.pid)
                for c in p.children(recursive=True):
                    try:
                        c.kill()
                    except Exception:
                        pass
                p.kill()
            except Exception:
                pass

# -----------------------------------------------------------------------------
# DIÁLOGOS (ERRORES Y CUENTA REGRESIVA)
# -----------------------------------------------------------------------------
class ErrorsDialog(QDialog):
    def __init__(self, errors: List[str], lang: str = "en", parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_text(lang, "err_dialog_title"))
        self.resize(880, 540)
        self.setStyleSheet(build_qss_theme())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl_title = QLabel(get_text(lang, "err_dialog_header"))
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f38ba8;")
        layout.addWidget(lbl_title)

        self.txt_edit = QTextEdit()
        self.txt_edit.setReadOnly(True)
        self.txt_edit.setFont(QFont("Consolas", 10))
        self.txt_edit.setStyleSheet("background-color: #07080c; border: 1px solid #1e2235; color: #f8bd96; border-radius: 6px;")
        self.txt_edit.setPlainText("\n\n".join(errors))
        layout.addWidget(self.txt_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(get_text(lang, "err_dialog_close"))
        btn_close.setFixedWidth(120)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

class CountdownDialog(QDialog):
    def __init__(self, action: str, done_count: int, err_count: int, lang: str = "en", parent=None):
        super().__init__(parent)
        self.action = action
        self.lang = lang
        self.setWindowTitle(f"◈ NEO•OPTIMIZER // {action}")
        self.setFixedSize(520, 260)
        self.setStyleSheet(build_qss_theme())
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        color_map = {
            "Shutdown": "#f38ba8", "Apagar": "#f38ba8",
            "Hibernate": "#89b4fa", "Hibernar": "#89b4fa",
            "Sleep": "#cba6f7", "Suspender": "#cba6f7",
            "Close": "#fab387", "Cerrar": "#fab387"
        }
        color_code = "#89b4fa"
        for k, v in color_map.items():
            if k in action:
                color_code = v
                break

        lbl_header = QLabel(f"⚡ {action}")
        lbl_header.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {color_code};")
        lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_header)

        summary_txt = f"Tasks completed: {done_count}" + (f" ({err_count} with error)" if err_count > 0 else "")
        lbl_sum = QLabel(summary_txt)
        lbl_sum.setStyleSheet("color: #6c7086; font-size: 12px;")
        lbl_sum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_sum)

        self.remaining_sec = 30
        self.lbl_timer = QLabel(f"Action executes in {self.remaining_sec} seconds...")
        self.lbl_timer.setStyleSheet("color: #f9e2af; font-size: 14px; font-weight: bold;")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_timer)

        self.bar_timer = QProgressBar()
        self.bar_timer.setRange(0, 30)
        self.bar_timer.setValue(30)
        self.bar_timer.setTextVisible(False)
        self.bar_timer.setFixedHeight(8)
        self.bar_timer.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color_code}; }}")
        layout.addWidget(self.bar_timer)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(get_text(lang, "countdown_cancel"))
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_now = QPushButton(get_text(lang, "countdown_now"))
        btn_now.setFixedHeight(36)
        btn_now.setStyleSheet(f"background-color: {color_code}; color: #08090d; font-weight: bold;")
        btn_now.clicked.connect(self.accept)
        btn_row.addWidget(btn_now)
        layout.addLayout(btn_row)

        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(1000)

    def _on_tick(self):
        self.remaining_sec -= 1
        self.bar_timer.setValue(self.remaining_sec)
        self.lbl_timer.setText(f"Action executes in {self.remaining_sec} seconds...")
        if self.remaining_sec <= 0:
            self.timer.stop()
            self.accept()

# -----------------------------------------------------------------------------
# VENTANA PRINCIPAL (PyQt6 GRUB / UNIXPORN THEME & MULTILANGUAGE)
# -----------------------------------------------------------------------------
class ModernVideoOptimizer(QMainWindow):
    def __init__(self):
        super().__init__()
        # IDIOMA POR DEFECTO: ENGLISH (en)
        self.current_lang = "en"
        
        self.resize(1560, 960)
        self.setMinimumSize(1180, 780)
        self.setStyleSheet(build_qss_theme())

        self._setup_window_icon()
        self._apply_windows_dark_titlebar()

        # Detección dinámica de Hardware
        self.hardware_profile = detect_hardware_profile()

        # Estado del programa
        self.directory_path = ""
        self.scanned_groups: Dict[str, Dict[str, Any]] = {}
        self.series_configs: Dict[str, Dict[str, Any]] = {}
        self.individual_video_configs: Dict[str, Dict[str, Any]] = {}

        self.current_target_id: Optional[str] = None
        self.current_is_video: bool = False
        self._is_loading_ui = False

        self.job_queue: List[Dict[str, Any]] = []
        self.encoding_thread: Optional[EncodingThread] = None
        self.active_version_widgets: List[Dict[str, Any]] = []

        self._build_ui()
        self._retranslate_ui()
        self._load_default_hardware_config()

    def _setup_window_icon(self):
        ico = os.path.join(APP_DIR, "app_icon.ico")
        if os.path.exists(ico):
            self.setWindowIcon(QIcon(ico))

    def _apply_windows_dark_titlebar(self):
        if os.name == 'nt':
            try:
                import ctypes
                hwnd = int(self.winId())
                val = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), 4)
            except Exception:
                pass

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(8)

        # 1. Cabecera Waybar / GRUB Bootloader
        header_card = QFrame()
        header_card.setProperty("class", "CardFrame")
        layout_h = QVBoxLayout(header_card)
        layout_h.setContentsMargins(14, 10, 14, 10)
        layout_h.setSpacing(8)

        row_telemetry = QHBoxLayout()
        row_telemetry.setSpacing(8)

        lbl_brand = QLabel("◈ NEO•OPTIMIZER")
        lbl_brand.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        row_telemetry.addWidget(lbl_brand)

        badge_ver = QLabel(" v3.0 PyQt6 ")
        badge_ver.setStyleSheet("background-color: #261b3b; color: #cba6f7; font-weight: bold; border-radius: 5px; padding: 2px 6px; font-size: 10px;")
        row_telemetry.addWidget(badge_ver)

        row_telemetry.addStretch()

        # Telemetría de GPU Dinámica
        self.lbl_gpu_badge = QLabel()
        self.lbl_gpu_badge.setStyleSheet("background-color: #162920; color: #a6e3a1; font-weight: bold; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
        row_telemetry.addWidget(self.lbl_gpu_badge)

        self.lbl_codec_badge = QLabel()
        self.lbl_codec_badge.setStyleSheet("background-color: #18233c; color: #89b4fa; font-weight: bold; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
        row_telemetry.addWidget(self.lbl_codec_badge)

        self.btn_redetect = QPushButton()
        self.btn_redetect.setStyleSheet("background-color: #161928; color: #94e2d5; border: 1px solid #233544; border-radius: 6px; font-size: 11px; padding: 3px 8px;")
        self.btn_redetect.clicked.connect(self._on_redetect_hardware)
        row_telemetry.addWidget(self.btn_redetect)

        # Selector de Idioma (Language Selector)
        self.lbl_lang = QLabel("🌐 Language:")
        self.lbl_lang.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        row_telemetry.addWidget(self.lbl_lang)

        self.cb_lang = QComboBox()
        self.cb_lang.addItem("English", "en")
        self.cb_lang.addItem("Español", "es")
        self.cb_lang.addItem("Français", "fr")
        self.cb_lang.addItem("日本語", "ja")
        self.cb_lang.setFixedWidth(115)
        self.cb_lang.currentIndexChanged.connect(self._on_language_changed)
        row_telemetry.addWidget(self.cb_lang)

        layout_h.addLayout(row_telemetry)

        # Fila Inferior: Buscador Estilo Rofi / Wofi
        row_search = QHBoxLayout()
        row_search.setSpacing(6)

        self.lbl_dir = QLabel()
        self.lbl_dir.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        row_search.addWidget(self.lbl_dir)

        self.txt_dir = QLineEdit()
        self.txt_dir.setFixedHeight(34)
        row_search.addWidget(self.txt_dir, stretch=1)

        self.btn_browse = QPushButton()
        self.btn_browse.setFixedHeight(34)
        self.btn_browse.clicked.connect(self.choose_directory)
        row_search.addWidget(self.btn_browse)

        self.btn_scan = QPushButton()
        self.btn_scan.setObjectName("btn_scan")
        self.btn_scan.setFixedHeight(34)
        self.btn_scan.setFixedWidth(155)
        self.btn_scan.clicked.connect(self.start_scan)
        row_search.addWidget(self.btn_scan)

        layout_h.addLayout(row_search)
        main_layout.addWidget(header_card)

        # 2. Pestañas de Trabajo (TabWidget)
        self.tabs = QTabWidget()
        self.tab_config = QWidget()
        self.tab_queue = QWidget()
        self.tabs.addTab(self.tab_config, "")
        self.tabs.addTab(self.tab_queue, "")
        main_layout.addWidget(self.tabs, stretch=1)

        self._build_tab_config()
        self._build_tab_queue()

        # 3. Dock Inferior de Control y Telemetría
        dock_card = QFrame()
        dock_card.setProperty("class", "CardFrame")
        layout_d = QVBoxLayout(dock_card)
        layout_d.setContentsMargins(14, 10, 14, 10)
        layout_d.setSpacing(8)

        # Fila de Estado y Velocímetro
        row_status = QHBoxLayout()
        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet("font-weight: bold; color: #89b4fa;")
        row_status.addWidget(self.lbl_status)

        row_status.addStretch()

        self.lbl_speedometer = QLabel()
        self.lbl_speedometer.setStyleSheet("background-color: #07080c; color: #a6e3a1; font-weight: bold; padding: 4px 10px; border-radius: 6px; border: 1px solid #181b29;")
        row_status.addWidget(self.lbl_speedometer)
        layout_d.addLayout(row_status)

        # Barra de Progreso Global
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setValue(0)
        layout_d.addWidget(self.progress_bar)

        # Fila de Botones de Acción (SIN botón redundante de solo no codificados)
        row_actions = QHBoxLayout()
        row_actions.setSpacing(8)

        self.btn_add_sel = QPushButton()
        self.btn_add_sel.setObjectName("btn_add_sel")
        self.btn_add_sel.setFixedHeight(36)
        self.btn_add_sel.setMinimumWidth(100)
        self.btn_add_sel.clicked.connect(self.add_selected_to_queue)
        row_actions.addWidget(self.btn_add_sel)

        self.btn_add_all = QPushButton()
        self.btn_add_all.setFixedHeight(36)
        self.btn_add_all.setMinimumWidth(110)
        self.btn_add_all.clicked.connect(self.add_all_to_queue)
        row_actions.addWidget(self.btn_add_all)

        self.btn_start = QPushButton()
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFixedHeight(36)
        self.btn_start.setMinimumWidth(100)
        self.btn_start.clicked.connect(self.start_encoding)
        row_actions.addWidget(self.btn_start)

        self.btn_pause = QPushButton()
        self.btn_pause.setObjectName("btn_pause")
        self.btn_pause.setFixedHeight(36)
        self.btn_pause.setMinimumWidth(95)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.toggle_pause)
        row_actions.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setMinimumWidth(95)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.stop_encoding)
        row_actions.addWidget(self.btn_cancel)

        row_actions.addStretch()

        self.lbl_after = QLabel()
        self.lbl_after.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        row_actions.addWidget(self.lbl_after)

        self.cb_after_action = QComboBox()
        self.cb_after_action.setFixedHeight(34)
        self.cb_after_action.setFixedWidth(200)
        row_actions.addWidget(self.cb_after_action)

        layout_d.addLayout(row_actions)
        main_layout.addWidget(dock_card)

    def _build_tab_config(self):
        layout = QVBoxLayout(self.tab_config)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row_cards = QHBoxLayout()
        row_cards.setSpacing(8)

        # 1. Tarjeta Perfiles de Versión
        card_v = QFrame()
        card_v.setProperty("class", "CardFrame")
        layout_v = QVBoxLayout(card_v)
        layout_v.setContentsMargins(12, 10, 12, 10)
        layout_v.setSpacing(6)

        header_v = QHBoxLayout()
        header_v.setSpacing(10)
        self.lbl_profiles_title = QLabel()
        self.lbl_profiles_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #89b4fa;")
        header_v.addWidget(self.lbl_profiles_title)

        # Botón Auto Config prominente y evidente en la cabecera de perfiles/versiones
        self.btn_auto_config = QPushButton()
        self.btn_auto_config.setFixedHeight(28)
        self.btn_auto_config.setStyleSheet(
            "background-color: #1e3a5f; color: #89b4fa; border: 1px solid #3b82f6; "
            "border-radius: 6px; font-weight: bold; font-size: 11px; padding: 4px 14px;"
        )
        self.btn_auto_config.clicked.connect(self.auto_configure_all_profiles)
        header_v.addWidget(self.btn_auto_config)

        header_v.addStretch()

        self.btn_add_ver = QPushButton()
        self.btn_add_ver.setFixedHeight(28)
        self.btn_add_ver.clicked.connect(self.add_version_ui)
        header_v.addWidget(self.btn_add_ver)
        layout_v.addLayout(header_v)

        self.scroll_versions = QScrollArea()
        self.scroll_versions.setWidgetResizable(True)
        self.scroll_versions.setFixedHeight(180)
        self.scroll_versions.setStyleSheet("background-color: transparent; border: none;")

        self.widget_versions_container = QWidget()
        self.layout_versions_list = QVBoxLayout(self.widget_versions_container)
        self.layout_versions_list.setContentsMargins(0, 0, 0, 0)
        self.layout_versions_list.setSpacing(6)
        self.layout_versions_list.addStretch()
        self.scroll_versions.setWidget(self.widget_versions_container)
        layout_v.addWidget(self.scroll_versions)

        row_cards.addWidget(card_v, stretch=1)

        # 2. Tarjeta Audio, Subtítulos y Opciones
        card_a = QFrame()
        card_a.setProperty("class", "CardFrame")
        layout_a = QVBoxLayout(card_a)
        layout_a.setContentsMargins(12, 10, 12, 10)
        layout_a.setSpacing(6)

        self.lbl_aud_sub_title = QLabel()
        self.lbl_aud_sub_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #89b4fa;")
        layout_a.addWidget(self.lbl_aud_sub_title)

        # Audio Selector
        r_aud = QHBoxLayout()
        self.rb_aud_track = QRadioButton()
        self.rb_aud_track.setChecked(True)
        self.rb_aud_track.toggled.connect(self._on_settings_change)
        r_aud.addWidget(self.rb_aud_track)

        self.cb_aud_track = QComboBox()
        self.cb_aud_track.setFixedWidth(210)
        self.cb_aud_track.currentIndexChanged.connect(self._on_settings_change)
        r_aud.addWidget(self.cb_aud_track)

        self.rb_aud_name = QRadioButton()
        self.rb_aud_name.toggled.connect(self._on_settings_change)
        r_aud.addWidget(self.rb_aud_name)

        self.txt_aud_name = QLineEdit()
        self.txt_aud_name.setFixedWidth(130)
        self.txt_aud_name.textChanged.connect(self._on_settings_change)
        r_aud.addWidget(self.txt_aud_name)
        r_aud.addStretch()
        layout_a.addLayout(r_aud)

        # Subtítulo Selector
        r_sub = QHBoxLayout()
        self.rb_sub_track = QRadioButton()
        self.rb_sub_track.setChecked(True)
        self.rb_sub_track.toggled.connect(self._on_settings_change)
        r_sub.addWidget(self.rb_sub_track)

        self.cb_sub_track = QComboBox()
        self.cb_sub_track.setFixedWidth(210)
        self.cb_sub_track.currentIndexChanged.connect(self._on_settings_change)
        r_sub.addWidget(self.cb_sub_track)

        self.rb_sub_name = QRadioButton()
        self.rb_sub_name.toggled.connect(self._on_settings_change)
        r_sub.addWidget(self.rb_sub_name)

        self.txt_sub_name = QLineEdit()
        self.txt_sub_name.setFixedWidth(130)
        self.txt_sub_name.textChanged.connect(self._on_settings_change)
        r_sub.addWidget(self.txt_sub_name)
        r_sub.addStretch()
        layout_a.addLayout(r_sub)

        # Subtítulo modo ninguno por defecto
        self.rb_sub_none = QRadioButton()
        self.rb_sub_none.setStyleSheet("color: #f38ba8; font-weight: bold;")
        self.rb_sub_none.toggled.connect(self._on_sub_mode_none_toggled)
        layout_a.addWidget(self.rb_sub_none)

        # Opciones
        r_opts = QHBoxLayout()
        self.chk_skip_done = QCheckBox()
        r_opts.addWidget(self.chk_skip_done)

        self.chk_replace_orig = QCheckBox()
        r_opts.addWidget(self.chk_replace_orig)

        self.chk_only_res = QCheckBox()
        self.chk_only_res.setChecked(True)
        r_opts.addWidget(self.chk_only_res)

        r_opts.addStretch()
        self.btn_clean_meta = QPushButton()
        self.btn_clean_meta.setFixedHeight(26)
        self.btn_clean_meta.clicked.connect(self.clean_metadata_now)
        r_opts.addWidget(self.btn_clean_meta)

        layout_a.addLayout(r_opts)
        row_cards.addWidget(card_a, stretch=1)
        layout.addLayout(row_cards)

        # 3. Banner de Telemetría Polybar / Resumen de Selección
        self.banner_frame = QFrame()
        self.banner_frame.setStyleSheet("background-color: #141724; border: 1px solid #282d44; border-radius: 6px; padding: 4px;")
        layout_b = QHBoxLayout(self.banner_frame)
        layout_b.setContentsMargins(12, 4, 12, 4)

        self.lbl_editing_target = QLabel()
        self.lbl_editing_target.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        layout_b.addWidget(self.lbl_editing_target)

        layout_b.addStretch()

        self.lbl_global_savings = QLabel("📊 Total Size: 0 MB ➜ Est: 0 MB (-0%)")
        self.lbl_global_savings.setStyleSheet("font-weight: bold; color: #89b4fa;")
        layout_b.addWidget(self.lbl_global_savings)

        self.btn_remove_sel = QPushButton()
        self.btn_remove_sel.setFixedHeight(26)
        self.btn_remove_sel.setMinimumWidth(110)
        self.btn_remove_sel.setStyleSheet("background-color: #23273c; color: #f38ba8; border: 1px solid #3b4263; font-size: 11px; padding: 2px 10px;")
        self.btn_remove_sel.clicked.connect(self._ctx_remove_from_tree)
        layout_b.addWidget(self.btn_remove_sel)

        layout.addWidget(self.banner_frame)

        # 4. Tabla de Videos y Series (QTableWidget Ultra-Rápido)
        self.table_lib = QTableWidget()
        self.table_lib.setColumnCount(12)
        self.table_lib.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_lib.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_lib.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_lib.horizontalHeader().setStretchLastSection(True)
        self.table_lib.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table_lib.setColumnWidth(0, 310)
        self.table_lib.setColumnWidth(1, 80)
        self.table_lib.setColumnWidth(2, 95)
        self.table_lib.setColumnWidth(3, 85)
        self.table_lib.setColumnWidth(4, 90)
        self.table_lib.setColumnWidth(5, 95)
        self.table_lib.setColumnWidth(6, 85)
        self.table_lib.setColumnWidth(7, 85)
        self.table_lib.setColumnWidth(8, 85)
        self.table_lib.setColumnWidth(9, 210)
        self.table_lib.setColumnWidth(10, 140)
        self.table_lib.setColumnWidth(11, 140)
        self.table_lib.itemSelectionChanged.connect(self.on_table_select)
        self.table_lib.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_lib.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table_lib, stretch=1)

    def _build_tab_queue(self):
        layout = QVBoxLayout(self.tab_queue)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        bar_q = QHBoxLayout()
        self.lbl_queue_stats = QLabel("📋 Encoding Queue (0 tasks)")
        self.lbl_queue_stats.setStyleSheet("font-weight: bold; font-size: 13px; color: #cba6f7;")
        bar_q.addWidget(self.lbl_queue_stats)

        self.btn_move_up = QPushButton()
        self.btn_move_up.setFixedHeight(28)
        self.btn_move_up.clicked.connect(self.move_queue_item_up)
        bar_q.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton()
        self.btn_move_down.setFixedHeight(28)
        self.btn_move_down.clicked.connect(self.move_queue_item_down)
        bar_q.addWidget(self.btn_move_down)

        self.btn_del_q = QPushButton()
        self.btn_del_q.setFixedHeight(28)
        self.btn_del_q.clicked.connect(self.remove_queue_selected)
        bar_q.addWidget(self.btn_del_q)

        self.btn_err_log = QPushButton()
        self.btn_err_log.setFixedHeight(28)
        self.btn_err_log.clicked.connect(self.show_queue_errors_dialog)
        bar_q.addWidget(self.btn_err_log)

        bar_q.addStretch()

        self.btn_clear_q = QPushButton()
        self.btn_clear_q.setFixedHeight(28)
        self.btn_clear_q.setStyleSheet("background-color: #2e1820; color: #f38ba8; border: 1px solid #4a242d;")
        self.btn_clear_q.clicked.connect(self.clear_queue)
        bar_q.addWidget(self.btn_clear_q)

        layout.addLayout(bar_q)

        self.table_q = QTableWidget()
        self.table_q.setColumnCount(6)
        self.table_q.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_q.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_q.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_q.horizontalHeader().setStretchLastSection(True)
        self.table_q.setColumnWidth(0, 45)
        self.table_q.setColumnWidth(1, 330)
        self.table_q.setColumnWidth(2, 200)
        self.table_q.setColumnWidth(3, 95)
        self.table_q.setColumnWidth(4, 140)
        self.table_q.setColumnWidth(5, 380)
        self.table_q.doubleClicked.connect(self.show_queue_errors_dialog)
        layout.addWidget(self.table_q, stretch=1)

    # =========================================================================
    # INTERNACIONALIZACIÓN (i18n) & CAMBIO DE IDIOMA
    # =========================================================================
    def _on_language_changed(self):
        new_lang = self.cb_lang.currentData()
        if new_lang and new_lang != self.current_lang:
            old_lang = self.current_lang
            self.current_lang = new_lang
            self._retranslate_ui()

            # Actualizar valores por defecto de audio y subtítulos si tenían el valor por defecto anterior
            old_aud_def = get_text(old_lang, "default_audio_search")
            old_sub_def = get_text(old_lang, "default_sub_search")
            new_aud_def = get_text(new_lang, "default_audio_search")
            new_sub_def = get_text(new_lang, "default_sub_search")

            if self.txt_aud_name.text().strip() in (old_aud_def, ""):
                self.txt_aud_name.setText(new_aud_def)
            if self.txt_sub_name.text().strip() in (old_sub_def, ""):
                self.txt_sub_name.setText(new_sub_def)

    def _retranslate_ui(self):
        L = self.current_lang
        self.setWindowTitle(get_text(L, "app_title"))
        self.lbl_lang.setText(get_text(L, "language_selector"))
        self.btn_redetect.setText(get_text(L, "btn_redetect"))

        self.lbl_dir.setText(get_text(L, "dir_label"))
        self.txt_dir.setPlaceholderText(get_text(L, "dir_placeholder"))
        self.btn_browse.setText(get_text(L, "btn_browse"))
        self.btn_scan.setText(get_text(L, "btn_scan"))

        self.tabs.setTabText(0, get_text(L, "tab_library"))
        self.tabs.setTabText(1, get_text(L, "tab_queue"))

        self.lbl_profiles_title.setText(get_text(L, "profiles_title"))
        self.btn_auto_config.setText(get_text(L, "btn_auto_config_header"))
        self.btn_auto_config.setToolTip(get_text(L, "btn_auto_tooltip"))
        self.btn_add_ver.setText(get_text(L, "btn_add_version"))

        self.lbl_aud_sub_title.setText(get_text(L, "audio_sub_title"))
        self.rb_aud_track.setText(get_text(L, "aud_track_radio"))
        self.rb_aud_name.setText(get_text(L, "aud_name_radio"))

        self.rb_sub_track.setText(get_text(L, "sub_track_radio"))
        self.rb_sub_name.setText(get_text(L, "sub_name_radio"))
        self.rb_sub_none.setText(get_text(L, "sub_none_radio"))

        self.chk_skip_done.setText(get_text(L, "chk_skip_done"))
        self.chk_replace_orig.setText(get_text(L, "chk_replace_orig"))
        self.chk_only_res.setText(get_text(L, "chk_only_res"))
        self.btn_clean_meta.setText(get_text(L, "btn_clean_meta"))

        if not self.current_target_id:
            self.lbl_editing_target.setText(get_text(L, "sel_banner_hint"))
        self.btn_remove_sel.setText(get_text(L, "btn_remove_sel"))

        cols = [
            get_text(L, "col_name"),
            get_text(L, "col_type"),
            get_text(L, "col_history"),
            get_text(L, "col_codec_in"),
            get_text(L, "col_bitrate_in"),
            get_text(L, "col_hdr"),
            get_text(L, "col_orig_size"),
            get_text(L, "col_est_size"),
            get_text(L, "col_savings"),
            get_text(L, "col_plan"),
            get_text(L, "col_audio"),
            get_text(L, "col_sub")
        ]
        self.table_lib.setHorizontalHeaderLabels(cols)

        q_cols = [
            get_text(L, "q_col_num"),
            get_text(L, "q_col_file"),
            get_text(L, "q_col_version"),
            get_text(L, "q_col_pct"),
            get_text(L, "q_col_status"),
            get_text(L, "q_col_output")
        ]
        self.table_q.setHorizontalHeaderLabels(q_cols)

        self.btn_move_up.setText(get_text(L, "btn_move_up"))
        self.btn_move_down.setText(get_text(L, "btn_move_down"))
        self.btn_del_q.setText(get_text(L, "btn_del_queue"))
        self.btn_err_log.setText(get_text(L, "btn_err_log"))
        self.btn_clear_q.setText(get_text(L, "btn_clear_queue"))

        self.btn_add_sel.setText(get_text(L, "btn_add"))
        self.btn_add_all.setText(get_text(L, "btn_add_all"))
        self.btn_start.setText(get_text(L, "btn_start"))
        self.btn_pause.setText(get_text(L, "btn_pause"))
        self.btn_cancel.setText(get_text(L, "btn_stop"))
        self.lbl_after.setText(get_text(L, "lbl_on_finish"))

        cur_act = self.cb_after_action.currentIndex()
        self.cb_after_action.clear()
        self.cb_after_action.addItems([
            get_text(L, "on_finish_none"),
            get_text(L, "on_finish_shutdown"),
            get_text(L, "on_finish_hibernate"),
            get_text(L, "on_finish_sleep"),
            get_text(L, "on_finish_close")
        ])
        if cur_act >= 0 and cur_act < self.cb_after_action.count():
            self.cb_after_action.setCurrentIndex(cur_act)

        self.lbl_status.setText(get_text(L, "status_ready"))
        self.lbl_speedometer.setText(get_text(L, "status_speed_inactive"))
        self.lbl_queue_stats.setText(get_text(L, "q_stats", count=len(self.job_queue)))

        for item in self.active_version_widgets:
            if "btn_auto" in item and item["btn_auto"]:
                item["btn_auto"].setText(get_text(L, "btn_auto"))
                item["btn_auto"].setToolTip(get_text(L, "btn_auto_tooltip"))
        self._reindex_version_cards()

    # =========================================================================
    # DETECCIÓN DE HARDWARE & CONFIGURACIÓN
    # =========================================================================
    def _clear_all_version_uis(self):
        """Elimina físicamente todos los marcos de versión del layout."""
        for item in list(self.active_version_widgets):
            if "frame" in item and item["frame"]:
                item["frame"].setParent(None)
                item["frame"].deleteLater()
        self.active_version_widgets.clear()

    def _load_default_hardware_config(self):
        prof = self.hardware_profile
        L = self.current_lang
        self.lbl_gpu_badge.setText(get_text(L, "gpu_detected", gpu=prof["gpu_name"]))

        if prof["is_av1_supported"]:
            self.lbl_codec_badge.setText(get_text(L, "auto_config_av1", codec=prof["recommended_codec"].upper()))
            self.lbl_codec_badge.setStyleSheet("background-color: #18233c; color: #89b4fa; font-weight: bold; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
        else:
            self.lbl_codec_badge.setText(get_text(L, "auto_config_best", codec=prof["recommended_codec"].upper()))
            self.lbl_codec_badge.setStyleSheet("background-color: #291e16; color: #fab387; font-weight: bold; border-radius: 6px; padding: 4px 10px; font-size: 11px;")

        self._is_loading_ui = True
        self._clear_all_version_uis()
        self.add_version_ui(
            default_codec=prof["recommended_codec"],
            default_res="Original",
            default_bitrate=str(prof["recommended_bitrate_1080p"]),
            default_burn=False
        )
        self.txt_aud_name.setText(get_text(L, "default_audio_search"))
        self.txt_sub_name.setText(get_text(L, "default_sub_search"))
        self._is_loading_ui = False

    def _on_redetect_hardware(self):
        """Re-escanea el hardware sin añadir versiones duplicadas ni romper la interfaz."""
        self.hardware_profile = detect_hardware_profile()
        prof = self.hardware_profile
        L = self.current_lang

        self.lbl_gpu_badge.setText(get_text(L, "gpu_detected", gpu=prof["gpu_name"]))
        if prof["is_av1_supported"]:
            self.lbl_codec_badge.setText(get_text(L, "auto_config_av1", codec=prof["recommended_codec"].upper()))
            self.lbl_codec_badge.setStyleSheet("background-color: #18233c; color: #89b4fa; font-weight: bold; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
        else:
            self.lbl_codec_badge.setText(get_text(L, "auto_config_best", codec=prof["recommended_codec"].upper()))
            self.lbl_codec_badge.setStyleSheet("background-color: #291e16; color: #fab387; font-weight: bold; border-radius: 6px; padding: 4px 10px; font-size: 11px;")

        # Actualizar opciones de códecs en las tarjetas existentes sin duplicar
        if self.active_version_widgets:
            for v_item in self.active_version_widgets:
                cb = v_item["codec"]
                curr = cb.currentText()
                cb.blockSignals(True)
                cb.clear()
                cb.addItems(prof.get("available_choices", [prof["recommended_codec"]]))
                idx = cb.findText(curr)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
                else:
                    r_idx = cb.findText(prof["recommended_codec"])
                    cb.setCurrentIndex(r_idx if r_idx >= 0 else 0)
                cb.blockSignals(False)
        else:
            self.add_version_ui(
                default_codec=prof["recommended_codec"],
                default_res="Original",
                default_bitrate=str(prof["recommended_bitrate_1080p"]),
                default_burn=False
            )

        self.lbl_status.setText(f"Hardware re-detected: {prof['arch_badge']}.")

    # =========================================================================
    # GESTOR DINÁMICO DE VERSIONES
    # =========================================================================
    def add_version_ui(self, default_codec="", default_res="720p", default_bitrate="", default_burn=False):
        prof = self.hardware_profile
        L = self.current_lang
        if not default_codec:
            default_codec = prof["recommended_codec"]
        if not default_bitrate:
            default_bitrate = str(prof["recommended_bitrate_720p"]) if default_res == "720p" else str(prof["recommended_bitrate_1080p"])

        v_idx = len(self.active_version_widgets) + 1
        accents = ["#89b4fa", "#cba6f7", "#fab387", "#a6e3a1", "#f5c2e7"]
        accent_color = accents[(v_idx - 1) % len(accents)]

        box = QFrame()
        box.setProperty("class", "SubCardFrame")
        box.setStyleSheet(f"QFrame.SubCardFrame {{ border-left: 3px solid {accent_color}; }}")
        l_box = QVBoxLayout(box)
        l_box.setContentsMargins(10, 6, 10, 6)
        l_box.setSpacing(4)

        r1 = QHBoxLayout()
        suffix = get_text(L, "version_primary") if v_idx == 1 else get_text(L, "version_secondary")
        title_txt = get_text(L, "version_title", idx=v_idx) + suffix
        lbl_t = QLabel(title_txt)
        lbl_t.setStyleSheet(f"font-weight: bold; color: {accent_color}; font-size: 11px;")
        r1.addWidget(lbl_t)
        r1.addStretch()

        btn_del = QPushButton(get_text(L, "btn_del"))
        btn_del.setMinimumWidth(85)
        btn_del.setFixedHeight(24)
        btn_del.setStyleSheet("background-color: #3b1219; color: #f38ba8; font-weight: bold; font-size: 11px; border: 1px solid #5e1f29; border-radius: 5px; padding: 2px 10px;")
        btn_del.clicked.connect(lambda _, b=box: self.remove_version_ui(b))
        btn_del.setVisible(v_idx > 1)
        r1.addWidget(btn_del)
        l_box.addLayout(r1)

        r2 = QHBoxLayout()
        r2.setSpacing(6)

        r2.addWidget(QLabel(get_text(L, "lbl_codec")))
        cb_codec = QComboBox()
        cb_codec.addItems(prof.get("available_choices", [default_codec]))
        idx = cb_codec.findText(default_codec)
        if idx >= 0:
            cb_codec.setCurrentIndex(idx)
        cb_codec.setFixedWidth(140)
        cb_codec.currentIndexChanged.connect(self._on_settings_change)
        r2.addWidget(cb_codec)

        r2.addWidget(QLabel(get_text(L, "lbl_res")))
        cb_res = QComboBox()
        cb_res.addItems(["Original", "4K (2160p)", "1080p", "720p", "480p"])
        r_idx = cb_res.findText(default_res)
        if r_idx >= 0:
            cb_res.setCurrentIndex(r_idx)
        # Ancho ampliado para que '4K (2160p)' entre holgadamente
        cb_res.setFixedWidth(145)
        cb_res.currentIndexChanged.connect(self._on_settings_change)
        r2.addWidget(cb_res)

        r2.addWidget(QLabel(get_text(L, "lbl_bitrate")))
        txt_b = QLineEdit(str(default_bitrate))
        txt_b.setFixedWidth(80)
        txt_b.setPlaceholderText("Auto")
        txt_b.textChanged.connect(self._on_settings_change)
        r2.addWidget(txt_b)

        # Botón AUTO para códec óptimo y bitrate de calidad equivalente
        btn_auto = QPushButton(get_text(L, "btn_auto"))
        btn_auto.setToolTip(get_text(L, "btn_auto_tooltip"))
        btn_auto.setFixedSize(70, 26)
        btn_auto.setStyleSheet("background-color: #1a2a40; color: #89b4fa; border: 1px solid #2b456e; border-radius: 5px; font-weight: bold; font-size: 11px;")
        btn_auto.clicked.connect(lambda _, b=txt_b, c=cb_codec, r=cb_res: self._auto_configure_profile(b, c, r))
        r2.addWidget(btn_auto)

        chk_burn = QCheckBox(get_text(L, "chk_burn"))
        chk_burn.setChecked(default_burn)
        chk_burn.toggled.connect(self._on_settings_change)
        r2.addWidget(chk_burn)

        r2.addStretch()
        l_box.addLayout(r2)

        cnt = self.layout_versions_list.count()
        self.layout_versions_list.insertWidget(cnt - 1, box)

        self.active_version_widgets.append({
            "frame": box,
            "lbl_title": lbl_t,
            "btn_del": btn_del,
            "btn_auto": btn_auto,
            "codec": cb_codec,
            "res": cb_res,
            "bitrate": txt_b,
            "burn_sub": chk_burn
        })

        self._reindex_version_cards()

        if not self._is_loading_ui:
            self._on_settings_change()

    def remove_version_ui(self, frame_to_remove):
        """Elimina la tarjeta de versión seleccionada y reindexa el resto."""
        idx = -1
        for i, item in enumerate(self.active_version_widgets):
            if item["frame"] == frame_to_remove:
                idx = i
                break
        if idx >= 0:
            if len(self.active_version_widgets) <= 1:
                return  # Mantener al menos 1 versión
            item = self.active_version_widgets.pop(idx)
            item["frame"].setParent(None)
            item["frame"].deleteLater()
            self._reindex_version_cards()
            self._on_settings_change()

    def _reindex_version_cards(self):
        """Actualiza títulos, colores y visibilidad de eliminación de las versiones activas."""
        L = self.current_lang
        accents = ["#89b4fa", "#cba6f7", "#fab387", "#a6e3a1", "#f5c2e7"]
        total = len(self.active_version_widgets)

        for idx, item in enumerate(self.active_version_widgets, 1):
            accent_color = accents[(idx - 1) % len(accents)]
            item["frame"].setStyleSheet(f"QFrame.SubCardFrame {{ border-left: 3px solid {accent_color}; }}")
            suffix = get_text(L, "version_primary") if idx == 1 else get_text(L, "version_secondary")
            title_txt = get_text(L, "version_title", idx=idx) + suffix
            item["lbl_title"].setText(title_txt)
            item["lbl_title"].setStyleSheet(f"font-weight: bold; color: {accent_color}; font-size: 11px;")
            if "btn_del" in item and item["btn_del"]:
                item["btn_del"].setText(get_text(L, "btn_del"))
                item["btn_del"].setVisible(total > 1 and idx > 1)

    def auto_configure_all_profiles(self):
        """Auto-configura de inmediato el perfil óptimo de GPU y bitrate de calidad equivalente desde la cabecera."""
        prof = self.hardware_profile
        rec_codec = prof["recommended_codec"]
        if not self.active_version_widgets:
            self.add_version_ui(default_codec=rec_codec, default_res="Original")
        v0 = self.active_version_widgets[0]
        self._auto_configure_profile(v0["bitrate"], v0["codec"], v0["res"])

    def _auto_configure_profile(self, txt_b: QLineEdit, cb_codec: QComboBox, cb_res: QComboBox):
        """Aplica automáticamente el mejor códec para la GPU y el bitrate equivalente manteniendo la calidad."""
        prof = self.hardware_profile
        rec_codec = prof["recommended_codec"]
        L = self.current_lang

        # 1. Establecer el mejor códec por hardware
        idx = cb_codec.findText(rec_codec)
        if idx >= 0:
            cb_codec.setCurrentIndex(idx)

        # 2. Localizar el video de referencia seleccionado (o el primero de la biblioteca)
        selected_meta = None
        selected_rows = self.table_lib.selectionModel().selectedRows()
        for sr in selected_rows:
            it = self.table_lib.item(sr.row(), 0)
            if it:
                tid = it.data(Qt.ItemDataRole.UserRole)
                if tid and tid.startswith("vid_"):
                    v_path = tid[4:]
                    for grp in self.scanned_groups.values():
                        for v in grp.get("videos", []):
                            if v["meta"]["filepath"] == v_path:
                                selected_meta = v["meta"]
                                break
                        if selected_meta:
                            break
            if selected_meta:
                break

        if not selected_meta:
            for grp in self.scanned_groups.values():
                if grp.get("videos"):
                    selected_meta = grp["videos"][0]["meta"]
                    break

        target_res = cb_res.currentText()

        if selected_meta:
            src_c = selected_meta.get("video_codec", "h264")
            src_br = selected_meta.get("bitrate_kbps", 0)
            src_res = selected_meta.get("resolution_tag", "1080p")
            eq_br = calculate_auto_bitrate(src_c, src_br, src_res, rec_codec, target_res)
            txt_b.setText(str(eq_br))
            self.lbl_status.setText(get_text(L, "status_auto_applied", codec=rec_codec.upper(), bitrate=eq_br, src_codec=src_c.upper(), src_bitrate=src_br))
        else:
            txt_b.setText("Auto")
            self.lbl_status.setText(get_text(L, "status_auto_mode"))

        self._on_settings_change()

    def _on_sub_mode_none_toggled(self, checked):
        if checked:
            self._on_settings_change()

    # =========================================================================
    # ESCANEO Y GESTIÓN DE BIBLIOTECA
    # =========================================================================
    def choose_directory(self):
        d = QFileDialog.getExistingDirectory(self, "Select Folder", self.txt_dir.text())
        if d:
            self.txt_dir.setText(os.path.normpath(d))
            self.start_scan()

    def start_scan(self):
        L = self.current_lang
        d = self.txt_dir.text().strip()
        if not d or not os.path.isdir(d):
            QMessageBox.warning(self, "Attention", get_text(L, "msg_select_valid_dir"))
            return

        self.directory_path = d
        self.btn_scan.setEnabled(False)
        self.lbl_status.setText(get_text(L, "status_scanning"))
        QApplication.processEvents()

        def worker():
            try:
                groups = scan_directory_for_videos(d)
                return groups, None
            except Exception as e:
                return {}, str(e)

        groups, err = worker()
        self.btn_scan.setEnabled(True)

        if err:
            QMessageBox.critical(self, "Scan Error", f"Error scanning directory:\n{err}")
            return

        self.scanned_groups = groups
        self._load_saved_folder_configs()
        self._rebuild_full_table()

        total_videos = sum(len(g["videos"]) for g in groups.values())
        self.lbl_status.setText(get_text(L, "msg_scan_complete", folders=len(groups), videos=total_videos))

    def _load_saved_folder_configs(self):
        for d_path, g_info in self.scanned_groups.items():
            cfg_file = os.path.join(d_path, ".folder_optimizer_config.json")
            if os.path.isfile(cfg_file):
                try:
                    import json
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if "folder_config" in data:
                        self.series_configs[d_path] = data["folder_config"]
                    if "individual_configs" in data:
                        for v_path, v_c in data["individual_configs"].items():
                            self.individual_video_configs[v_path] = v_c
                except Exception:
                    pass

    def _save_all_folder_configs(self):
        for d_path in self.scanned_groups.keys():
            s_cfg = self.series_configs.get(d_path, {})
            v_cfgs = {
                v["filepath"]: self.individual_video_configs[v["filepath"]]
                for v in self.scanned_groups[d_path]["videos"]
                if v["filepath"] in self.individual_video_configs
            }
            if s_cfg or v_cfgs:
                try:
                    import json
                    cfg_file = os.path.join(d_path, ".folder_optimizer_config.json")
                    with open(cfg_file, "w", encoding="utf-8") as f:
                        json.dump({"folder_config": s_cfg, "individual_configs": v_cfgs}, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

    def _rebuild_full_table(self):
        L = self.current_lang
        self.table_lib.setRowCount(0)
        row_idx = 0

        for d_path, g_info in self.scanned_groups.items():
            self.table_lib.insertRow(row_idx)
            is_multi = len(self._get_effective_versions_for_folder(d_path)) > 1
            folder_name = f"📁 {os.path.basename(d_path)} ({len(g_info['videos'])})"

            item_folder = QTableWidgetItem(folder_name)
            item_folder.setData(Qt.ItemDataRole.UserRole, f"group_{d_path}")
            item_folder.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            item_folder.setForeground(QColor("#7ec8ff"))
            item_folder.setBackground(QColor("#18223c" if not is_multi else "#241b3c"))
            self.table_lib.setItem(row_idx, 0, item_folder)

            for col_c in range(1, 12):
                it = QTableWidgetItem("" if col_c != 1 else get_text(L, "status_type_folder"))
                it.setBackground(QColor("#18223c" if not is_multi else "#241b3c"))
                it.setForeground(QColor("#7ec8ff"))
                self.table_lib.setItem(row_idx, col_c, it)
            row_idx += 1

            for v_num, v_meta in enumerate(g_info["videos"]):
                self.table_lib.insertRow(row_idx)
                v_path = v_meta["filepath"]
                has_custom = v_path in self.individual_video_configs
                eff_ver = self._get_effective_versions_for_video(d_path, v_path)
                is_v_multi = len(eff_ver) > 1

                bg_color = QColor("#0a0b12" if row_idx % 2 == 0 else "#10121d")
                fg_color = QColor("#cdd6f4")
                if has_custom:
                    fg_color = QColor("#fdba74")
                elif is_v_multi:
                    fg_color = QColor("#f5bde6")

                item_vid = QTableWidgetItem(f"    {v_meta['filename']}")
                item_vid.setData(Qt.ItemDataRole.UserRole, f"vid_{v_path}")
                item_vid.setForeground(fg_color)
                item_vid.setBackground(bg_color)
                if has_custom:
                    item_vid.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table_lib.setItem(row_idx, 0, item_vid)

                status_txt = get_text(L, "status_already_encoded") if v_meta.get("is_already_encoded") else get_text(L, "status_pending")
                stat_col = QColor("#89b4fa" if v_meta.get("is_already_encoded") else "#a6e3a1")

                data_cols = [
                    (v_meta.get("resolution_tag", "Original"), fg_color),
                    (status_txt, stat_col),
                    (v_meta.get("video_codec", "N/A"), fg_color),
                    (f"{v_meta.get('bitrate_kbps', 0)} kbps", fg_color),
                    ("HDR/Dolby" if v_meta.get("is_hdr") else "SDR", QColor("#f9e2af" if v_meta.get("is_hdr") else "#6c7086")),
                    (f"{v_meta.get('size_mb', 0)} MB", fg_color),
                    (f"{self._estimate_v1_size(v_meta, eff_ver)} MB", fg_color),
                    (f"-{self._estimate_savings_pct(v_meta, eff_ver)}%", QColor("#a6e3a1")),
                    (self._format_versions_plan(eff_ver), fg_color),
                    (self._format_audio_plan(d_path, v_meta), fg_color),
                    (self._format_sub_plan(d_path, v_meta), fg_color)
                ]

                for c_i, (txt, colr) in enumerate(data_cols, 1):
                    it = QTableWidgetItem(str(txt))
                    it.setBackground(bg_color)
                    it.setForeground(colr)
                    self.table_lib.setItem(row_idx, c_i, it)
                row_idx += 1

        self._update_global_savings_banner()

    def _get_effective_versions_for_folder(self, d_path: str) -> List[Dict[str, Any]]:
        if d_path in self.series_configs and "versions" in self.series_configs[d_path]:
            return self.series_configs[d_path]["versions"]
        return [self._get_ui_version_data(w) for w in self.active_version_widgets]

    def _get_effective_versions_for_video(self, d_path: str, v_path: str) -> List[Dict[str, Any]]:
        if v_path in self.individual_video_configs and "versions" in self.individual_video_configs[v_path]:
            return self.individual_video_configs[v_path]["versions"]
        return self._get_effective_versions_for_folder(d_path)

    def _get_ui_version_data(self, w: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "codec": w["codec"].currentText(),
            "res": w["res"].currentText(),
            "bitrate": w["bitrate"].text().strip() or "3500",
            "burn_sub": w["burn_sub"].isChecked()
        }

    def _estimate_v1_size(self, v_meta: Dict[str, Any], eff_ver: List[Dict[str, Any]]) -> int:
        if not eff_ver:
            return v_meta.get("size_mb", 0)
        try:
            b = int(eff_ver[0]["bitrate"])
            dur = v_meta.get("duration_seconds", 0)
            return int((b * 1000 * dur) / (8 * 1024 * 1024))
        except Exception:
            return v_meta.get("size_mb", 0)

    def _estimate_savings_pct(self, v_meta: Dict[str, Any], eff_ver: List[Dict[str, Any]]) -> int:
        orig = v_meta.get("size_mb", 0)
        if orig <= 0:
            return 0
        est = self._estimate_v1_size(v_meta, eff_ver)
        if est >= orig:
            return 0
        return int(((orig - est) / orig) * 100)

    def _format_versions_plan(self, eff_ver: List[Dict[str, Any]]) -> str:
        parts = []
        for idx, ver in enumerate(eff_ver, 1):
            burn = " [🔥Sub]" if ver.get("burn_sub") else ""
            parts.append(f"V{idx}:{ver['codec'].replace('_nvenc','').replace('lib','')}({ver['res']}@{ver['bitrate']}k{burn})")
        return " | ".join(parts)

    def _format_audio_plan(self, d_path: str, v_meta: Dict[str, Any]) -> str:
        L = self.current_lang
        cfg = self.individual_video_configs.get(v_meta["filepath"], self.series_configs.get(d_path, {}))
        audios = v_meta.get("audio_streams", [])
        if not audios:
            return get_text(L, "status_aud_no_audio")
        if cfg.get("audio_rel_idx") is not None and 0 <= cfg["audio_rel_idx"] < len(audios):
            return f"Track #{cfg['audio_rel_idx']}"
        pattern = cfg.get("audio_pattern", get_text(L, "default_audio_search"))
        best = find_best_audio_match(audios, pattern)
        return f"Match: {best['language']}" if best else get_text(L, "status_aud_default")

    def _format_sub_plan(self, d_path: str, v_meta: Dict[str, Any]) -> str:
        L = self.current_lang
        cfg = self.individual_video_configs.get(v_meta["filepath"], self.series_configs.get(d_path, {}))
        if cfg.get("sub_rel_idx") == -1 or cfg.get("sub_mode") == "none":
            return get_text(L, "status_sub_none_off")
        subs = v_meta.get("subtitle_streams", [])
        if not subs:
            return get_text(L, "status_sub_no_subs")
        if cfg.get("sub_rel_idx") is not None and 0 <= cfg["sub_rel_idx"] < len(subs):
            return f"Track #{cfg['sub_rel_idx']}"
        pattern = cfg.get("sub_pattern", get_text(L, "default_sub_search"))
        best = find_best_sub_match(subs, pattern)
        return f"Match: {best['language']}" if best else get_text(L, "status_sub_default")

    def _update_global_savings_banner(self):
        L = self.current_lang
        total_orig = 0
        total_est = 0
        for g_info in self.scanned_groups.values():
            for v_meta in g_info["videos"]:
                total_orig += v_meta.get("size_mb", 0)
                eff = self._get_effective_versions_for_video(g_info["dir_path"], v_meta["filepath"])
                total_est += self._estimate_v1_size(v_meta, eff)

        pct = int(((total_orig - total_est) / total_orig) * 100) if total_orig > 0 and total_est < total_orig else 0
        self.lbl_global_savings.setText(get_text(L, "total_weight_est", orig=total_orig, est=total_est, pct=pct))

    # =========================================================================
    # SELECCIÓN Y CONFIGURACIÓN GRANULAR
    # =========================================================================
    def on_table_select(self):
        rows = self.table_lib.selectionModel().selectedRows()
        if not rows:
            return

        L = self.current_lang
        first_row = rows[0].row()
        item = self.table_lib.item(first_row, 0)
        if not item:
            return

        target_id = item.data(Qt.ItemDataRole.UserRole)
        if not target_id:
            return

        self.current_target_id = target_id
        self._is_loading_ui = True

        if target_id.startswith("group_"):
            d_path = target_id[6:]
            self.current_is_video = False
            self.lbl_editing_target.setText(get_text(L, "sel_editing_folder", name=os.path.basename(d_path)))
            cfg = self.series_configs.get(d_path, {})
            self._apply_cfg_to_ui(cfg, d_path=d_path)
        elif target_id.startswith("vid_"):
            v_path = target_id[4:]
            self.current_is_video = True
            v_meta = self._find_video_meta(v_path)
            fn = v_meta["filename"] if v_meta else os.path.basename(v_path)
            d_path = os.path.dirname(v_path)
            self.lbl_editing_target.setText(get_text(L, "sel_editing_video", name=fn))
            cfg = self.individual_video_configs.get(v_path, self.series_configs.get(d_path, {}))
            self._apply_cfg_to_ui(cfg, v_meta=v_meta)

        self._is_loading_ui = False

    def _apply_cfg_to_ui(self, cfg: Dict[str, Any], d_path: str = "", v_meta: Dict[str, Any] = None):
        L = self.current_lang
        self.cb_aud_track.clear()
        self.cb_aud_track.addItem(get_text(L, "aud_auto"))
        self.cb_sub_track.clear()
        self.cb_sub_track.addItem(get_text(L, "sub_none_default"))

        if v_meta:
            for a in v_meta.get("audio_streams", []):
                self.cb_aud_track.addItem(f"Track #{a['rel_index']}: [{a['language']}] {a['codec']} {a['channels']}ch")
            for s in v_meta.get("subtitle_streams", []):
                self.cb_sub_track.addItem(f"Track #{s['rel_index']}: [{s['language']}] {s['title']}")

        if cfg.get("sub_mode") == "none":
            self.rb_sub_none.setChecked(True)
        elif cfg.get("sub_rel_idx") is not None:
            self.rb_sub_track.setChecked(True)
            self.cb_sub_track.setCurrentIndex(cfg["sub_rel_idx"] + 1)
        else:
            self.rb_sub_name.setChecked(True)
            self.txt_sub_name.setText(cfg.get("sub_pattern", get_text(L, "default_sub_search")))

        if cfg.get("audio_rel_idx") is not None:
            self.rb_aud_track.setChecked(True)
            self.cb_aud_track.setCurrentIndex(cfg["audio_rel_idx"] + 1)
        else:
            self.rb_aud_name.setChecked(True)
            self.txt_aud_name.setText(cfg.get("audio_pattern", get_text(L, "default_audio_search")))

        for item in self.active_version_widgets:
            item["frame"].setParent(None)
            item["frame"].deleteLater()
        self.active_version_widgets.clear()

        versions = cfg.get("versions", [])
        if not versions:
            prof = self.hardware_profile
            self.add_version_ui(default_codec=prof["recommended_codec"], default_res="Original", default_bitrate=str(prof["recommended_bitrate_1080p"]))
        else:
            for ver in versions:
                self.add_version_ui(
                    default_codec=ver.get("codec", "av1_nvenc"),
                    default_res=ver.get("res", "Original"),
                    default_bitrate=str(ver.get("bitrate", "3500")),
                    default_burn=ver.get("burn_sub", False)
                )

    def _on_settings_change(self):
        if self._is_loading_ui or not self.current_target_id:
            return

        L = self.current_lang
        cfg = {
            "versions": [self._get_ui_version_data(w) for w in self.active_version_widgets],
            "audio_pattern": self.txt_aud_name.text().strip(),
            "audio_rel_idx": (self.cb_aud_track.currentIndex() - 1) if self.rb_aud_track.isChecked() and self.cb_aud_track.currentIndex() > 0 else None,
            "sub_mode": "none" if self.rb_sub_none.isChecked() else ("track" if self.rb_sub_track.isChecked() else "name"),
            "sub_pattern": self.txt_sub_name.text().strip(),
            "sub_rel_idx": -1 if self.rb_sub_none.isChecked() else ((self.cb_sub_track.currentIndex() - 1) if self.rb_sub_track.isChecked() and self.cb_sub_track.currentIndex() > 0 else None)
        }

        if self.current_target_id.startswith("group_"):
            d_path = self.current_target_id[6:]
            self.series_configs[d_path] = cfg
        elif self.current_target_id.startswith("vid_"):
            v_path = self.current_target_id[4:]
            self.individual_video_configs[v_path] = cfg

        self._update_table_row_data()
        self._save_all_folder_configs()

    def _update_table_row_data(self):
        for r in range(self.table_lib.rowCount()):
            it0 = self.table_lib.item(r, 0)
            if not it0:
                continue
            tid = it0.data(Qt.ItemDataRole.UserRole)
            if not tid:
                continue

            if tid.startswith("vid_"):
                v_path = tid[4:]
                d_path = os.path.dirname(v_path)
                v_meta = self._find_video_meta(v_path)
                if not v_meta:
                    continue

                eff_ver = self._get_effective_versions_for_video(d_path, v_path)
                has_custom = v_path in self.individual_video_configs

                self.table_lib.item(r, 7).setText(f"{self._estimate_v1_size(v_meta, eff_ver)} MB")
                self.table_lib.item(r, 8).setText(f"-{self._estimate_savings_pct(v_meta, eff_ver)}%")
                self.table_lib.item(r, 9).setText(self._format_versions_plan(eff_ver))
                self.table_lib.item(r, 10).setText(self._format_audio_plan(d_path, v_meta))
                self.table_lib.item(r, 11).setText(self._format_sub_plan(d_path, v_meta))

                colr = QColor("#fdba74" if has_custom else ("#f5bde6" if len(eff_ver) > 1 else "#cdd6f4"))
                it0.setForeground(colr)
                if has_custom:
                    it0.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        self._update_global_savings_banner()

    def _find_video_meta(self, v_path: str) -> Optional[Dict[str, Any]]:
        for g in self.scanned_groups.values():
            for v in g["videos"]:
                if v["filepath"] == v_path:
                    return v
        return None

    # =========================================================================
    # MENÚ CONTEXTUAL
    # =========================================================================
    def show_context_menu(self, pos):
        item = self.table_lib.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        a_add = menu.addAction("📥 Add to Queue")
        a_rem = menu.addAction("🗑️ Remove Selected")
        menu.addSeparator()
        a_reset = menu.addAction("🔄 Reset to Folder Profile")

        action = menu.exec(self.table_lib.viewport().mapToGlobal(pos))
        if action == a_add:
            self.add_selected_to_queue()
        elif action == a_rem:
            self._ctx_remove_from_tree()
        elif action == a_reset:
            self._ctx_reset_custom_config()

    def _ctx_remove_from_tree(self):
        rows = self.table_lib.selectionModel().selectedRows()
        if not rows:
            return

        for r in rows:
            it = self.table_lib.item(r.row(), 0)
            if not it:
                continue
            tid = it.data(Qt.ItemDataRole.UserRole)
            if tid.startswith("group_"):
                dp = tid[6:]
                if dp in self.scanned_groups:
                    del self.scanned_groups[dp]
                if dp in self.series_configs:
                    del self.series_configs[dp]
            elif tid.startswith("vid_"):
                vp = tid[4:]
                for dp, gi in self.scanned_groups.items():
                    gi["videos"] = [v for v in gi["videos"] if v["filepath"] != vp]
                if vp in self.individual_video_configs:
                    del self.individual_video_configs[vp]

        empty = [dp for dp, gi in self.scanned_groups.items() if not gi["videos"]]
        for dp in empty:
            del self.scanned_groups[dp]

        self._rebuild_full_table()
        self.lbl_status.setText("Selected items removed from list.")

    def _ctx_reset_custom_config(self):
        rows = self.table_lib.selectionModel().selectedRows()
        for r in rows:
            it = self.table_lib.item(r.row(), 0)
            if it:
                tid = it.data(Qt.ItemDataRole.UserRole)
                if tid.startswith("vid_"):
                    vp = tid[4:]
                    if vp in self.individual_video_configs:
                        del self.individual_video_configs[vp]
        self._update_table_row_data()
        self._save_all_folder_configs()
        self.lbl_status.setText("Settings reset to folder defaults.")

    # =========================================================================
    # COLA DE CODIFICACIÓN (BOTÓN "AGREGAR" SIMPLE)
    # =========================================================================
    def add_selected_to_queue(self):
        """Agrega los elementos seleccionados a la cola."""
        rows = self.table_lib.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Selection", "Please select one or more items from the table.")
            return

        self._save_all_folder_configs()
        only_res = self.chk_only_res.isChecked()
        skip_done = self.chk_skip_done.isChecked()
        added = 0

        for r in rows:
            it = self.table_lib.item(r.row(), 0)
            if not it:
                continue
            tid = it.data(Qt.ItemDataRole.UserRole)
            if tid.startswith("group_"):
                dp = tid[6:]
                gi = self.scanned_groups.get(dp)
                if gi:
                    for v in gi["videos"]:
                        if skip_done and v.get("is_already_encoded"):
                            continue
                        added += self._append_video_to_queue(dp, gi, v, only_res)
            elif tid.startswith("vid_"):
                vp = tid[4:]
                v_meta = self._find_video_meta(vp)
                dp = os.path.dirname(vp)
                gi = self.scanned_groups.get(dp)
                if v_meta and gi:
                    if skip_done and v_meta.get("is_already_encoded"):
                        continue
                    added += self._append_video_to_queue(dp, gi, v_meta, only_res)

        self._refresh_queue_table()
        L = self.current_lang
        self.lbl_status.setText(get_text(L, "msg_added_queue", count=added))
        self.tabs.setCurrentIndex(1)

    def add_all_to_queue(self):
        if not self.scanned_groups:
            QMessageBox.warning(self, "Attention", "Please scan a folder first.")
            return
        self._save_all_folder_configs()
        only_res = self.chk_only_res.isChecked()
        skip_done = self.chk_skip_done.isChecked()
        added = 0
        for dp, gi in self.scanned_groups.items():
            for v in gi["videos"]:
                if skip_done and v.get("is_already_encoded"):
                    continue
                added += self._append_video_to_queue(dp, gi, v, only_res)
        self._refresh_queue_table()
        L = self.current_lang
        self.lbl_status.setText(get_text(L, "msg_added_queue", count=added))
        self.tabs.setCurrentIndex(1)

    def _append_video_to_queue(self, d_path: str, g_info: Dict[str, Any], v_meta: Dict[str, Any], only_res: bool) -> int:
        s_cfg = self.series_configs.get(d_path, {})
        v_cfg = copy.deepcopy(self.individual_video_configs.get(v_meta["filepath"], s_cfg))
        versions = v_cfg.get("versions", [])
        orig_path = v_meta["filepath"]
        added = 0

        for v_num, ver in enumerate(versions):
            ver_copy = copy.deepcopy(ver)
            res_tag = ver_copy.get("res", "Original")
            if res_tag == "Original":
                res_tag = v_meta.get("resolution_tag") or detect_video_resolution_tag(v_meta.get("width", 0), v_meta.get("height", 0))

            # Cálculo de bitrate inteligente si está en Auto, vacío o 0
            raw_br = str(ver_copy.get("bitrate", "")).strip().lower()
            if raw_br == "auto" or not raw_br or raw_br == "0":
                calc_br = calculate_auto_bitrate(
                    v_meta.get("video_codec", "h264"),
                    v_meta.get("bitrate_kbps", 0),
                    v_meta.get("resolution_tag", "1080p"),
                    ver_copy.get("codec", "av1_nvenc"),
                    res_tag
                )
                ver_copy["bitrate"] = str(calc_br)

            codec_clean = ver_copy["codec"].replace("_nvenc", "").replace("lib", "").upper()
            out_name = build_standard_filename(orig_path, res_tag, codec_clean, only_resolution=only_res)
            out_path = os.path.join(d_path, out_name)

            if not any(j["output_path"] == out_path and j["status"] in ("Pending", "Pendiente", "Encoding...") for j in self.job_queue):
                job = {
                    "d_path": d_path,
                    "g_info": g_info,
                    "v_meta": v_meta,
                    "cfg": v_cfg,
                    "v_num": v_num,
                    "v_cfg": ver_copy,
                    "res_tag": res_tag,
                    "out_name": out_name,
                    "output_path": out_path,
                    "status": "Pending",
                    "progress": "0%",
                    "error_detail": ""
                }
                self.job_queue.append(job)
                added += 1
        return added

    def _refresh_queue_table(self):
        L = self.current_lang
        self.table_q.setRowCount(0)
        for idx, job in enumerate(self.job_queue):
            self.table_q.insertRow(idx)
            st = job["status"]

            bg = QColor("#0a0b12" if idx % 2 == 0 else "#10121d")
            fg = QColor("#cdd6f4")
            if "Encoding" in st or "Codificando" in st:
                bg = QColor("#2a2412")
                fg = QColor("#f9e2af")
            elif "Pause" in st or "Pausado" in st:
                bg = QColor("#2a1b12")
                fg = QColor("#fab387")
            elif "Completed" in st or "Listo" in st:
                bg = QColor("#12251a")
                fg = QColor("#a6e3a1")
            elif "Error" in st:
                bg = QColor("#2a1218")
                fg = QColor("#f38ba8")

            ver_label = f"V{job['v_num']+1}: {job['v_cfg']['codec']} ({job['v_cfg']['res']}) @ {job['v_cfg']['bitrate']}k"

            row_data = [
                str(idx + 1),
                job["v_meta"]["filename"],
                ver_label,
                job.get("progress", "0%"),
                st,
                job["out_name"]
            ]

            for c_i, txt in enumerate(row_data):
                it = QTableWidgetItem(txt)
                it.setBackground(bg)
                it.setForeground(fg)
                if c_i in (0, 3, 4):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_q.setItem(idx, c_i, it)

        self.lbl_queue_stats.setText(get_text(L, "q_stats", count=len(self.job_queue)))

    def move_queue_item_up(self):
        rows = self.table_q.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if idx > 0 and self.job_queue[idx]["status"] in ("Pending", "Pendiente") and self.job_queue[idx - 1]["status"] in ("Pending", "Pendiente"):
            self.job_queue[idx], self.job_queue[idx - 1] = self.job_queue[idx - 1], self.job_queue[idx]
            self._refresh_queue_table()
            self.table_q.selectRow(idx - 1)

    def move_queue_item_down(self):
        rows = self.table_q.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if idx < len(self.job_queue) - 1 and self.job_queue[idx]["status"] in ("Pending", "Pendiente") and self.job_queue[idx + 1]["status"] in ("Pending", "Pendiente"):
            self.job_queue[idx], self.job_queue[idx + 1] = self.job_queue[idx + 1], self.job_queue[idx]
            self._refresh_queue_table()
            self.table_q.selectRow(idx + 1)

    def remove_queue_selected(self):
        rows = sorted([r.row() for r in self.table_q.selectionModel().selectedRows()], reverse=True)
        for idx in rows:
            if idx < len(self.job_queue) and "Encoding" not in self.job_queue[idx]["status"]:
                self.job_queue.pop(idx)
        self._refresh_queue_table()

    def clear_queue(self):
        self.job_queue = [j for j in self.job_queue if "Encoding" in j["status"]]
        self._refresh_queue_table()

    def show_queue_errors_dialog(self):
        L = self.current_lang
        errors = [
            f"--- Task #{i+1}: {j['v_meta']['filename']} -> {j['out_name']} ---\n{j['error_detail']}\n"
            for i, j in enumerate(self.job_queue)
            if j.get("error_detail")
        ]
        if not errors:
            QMessageBox.information(self, "Error Log", get_text(L, "msg_no_errors"))
            return
        dlg = ErrorsDialog(errors, lang=L, parent=self)
        dlg.exec()

    # =========================================================================
    # INICIO, PAUSA, DETENCIÓN Y FINALIZACIÓN
    # =========================================================================
    def start_encoding(self):
        L = self.current_lang
        if not self.job_queue:
            QMessageBox.warning(self, "Queue Empty", "No tasks in the queue.")
            return

        pending = [j for j in self.job_queue if j["status"] in ("Pending", "Pendiente")]
        if not pending:
            QMessageBox.information(self, "Done", "All tasks in queue are already completed.")
            return

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)

        self.encoding_thread = EncodingThread(self.job_queue, self.chk_replace_orig.isChecked())
        self.encoding_thread.progress_updated.connect(self._on_encoding_progress)
        self.encoding_thread.job_finished.connect(self._on_job_finished)
        self.encoding_thread.queue_completed.connect(self._on_queue_completed)
        self.encoding_thread.start()

        self.lbl_status.setText(get_text(L, "status_encoding_started"))

    def _on_encoding_progress(self, idx: int, pct_str: str, spd_str: str, time_str: str):
        if idx < self.table_q.rowCount():
            it_pct = self.table_q.item(idx, 3)
            it_st = self.table_q.item(idx, 4)
            if it_pct:
                it_pct.setText(pct_str)
            if it_st:
                it_st.setText(get_text(self.current_lang, "status_encoding"))

        try:
            val = int(pct_str.replace("%", ""))
            self.progress_bar.setValue(val)
        except Exception:
            pass
        self.lbl_speedometer.setText(spd_str)

    def _on_job_finished(self, idx: int, success: bool, err_msg: str):
        self._refresh_queue_table()
        self._rebuild_full_table()

    def _on_queue_completed(self, done_count: int, error_count: int):
        L = self.current_lang
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_pause.setText(get_text(L, "btn_pause"))
        self.progress_bar.setValue(100 if error_count == 0 else self.progress_bar.value())

        if error_count > 0:
            self.lbl_status.setText(get_text(L, "status_queue_done_errors", done=done_count, err=error_count))
        else:
            self.lbl_status.setText(get_text(L, "status_queue_done", count=done_count))

        action_idx = self.cb_after_action.currentIndex()
        if action_idx > 0:
            action_text = self.cb_after_action.currentText()
            dlg = CountdownDialog(action_text, done_count, error_count, lang=L, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._execute_system_action(action_idx)
            else:
                self.cb_after_action.setCurrentIndex(0)
                self.lbl_status.setText("Finish action canceled by user.")
        else:
            if error_count > 0:
                QMessageBox.warning(
                    self, "Queue Finished with Warnings",
                    f"Completed: {done_count} tasks.\nSkipped: {error_count} with errors."
                )
            else:
                QMessageBox.information(self, "Success", f"Processed all {done_count} tasks successfully.")

    def _execute_system_action(self, action_idx: int):
        if action_idx == 1:  # Shutdown
            if os.name == 'nt':
                os.system("shutdown /s /f /t 0")
            else:
                os.system("shutdown -h now")
        elif action_idx == 2:  # Hibernate
            if os.name == 'nt':
                os.system("shutdown /h")
            else:
                os.system("systemctl hibernate")
        elif action_idx == 3:  # Sleep
            if os.name == 'nt':
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            else:
                os.system("systemctl suspend")
        elif action_idx == 4:  # Close
            self.close()

    def toggle_pause(self):
        L = self.current_lang
        if not self.encoding_thread:
            return
        if not self.encoding_thread._is_paused:
            self.encoding_thread.pause()
            self.btn_pause.setText(get_text(L, "btn_resume"))
            self.btn_pause.setStyleSheet("background-color: #a6e3a1; color: #08090d;")
            self.lbl_status.setText("Encoding PAUSED.")
            self.lbl_speedometer.setText(get_text(L, "status_paused"))
        else:
            self.encoding_thread.resume()
            self.btn_pause.setText(get_text(L, "btn_pause"))
            self.btn_pause.setStyleSheet("background-color: #f9e2af; color: #08090d;")
            self.lbl_status.setText("Encoding RESUMED.")

    def stop_encoding(self):
        L = self.current_lang
        if self.encoding_thread:
            self.encoding_thread.stop()
            self.encoding_thread.wait(2000)
            self.encoding_thread = None
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_pause.setText(get_text(L, "btn_pause"))
        self.lbl_status.setText("Encoding stopped.")
        self.lbl_speedometer.setText(get_text(L, "status_speed_inactive"))
        self._refresh_queue_table()

    def clean_metadata_now(self):
        L = self.current_lang
        if not self.scanned_groups:
            QMessageBox.warning(self, "Attention", get_text(L, "msg_select_valid_dir"))
            return

        all_files = [v["filepath"] for g in self.scanned_groups.values() for v in g["videos"]]
        count = 0
        for f in all_files:
            if clean_file_metadata_inplace(f):
                count += 1
        QMessageBox.information(self, "Cleaned", get_text(L, "msg_clean_meta", count=count))

    def closeEvent(self, event):
        if self.encoding_thread and self.encoding_thread.isRunning():
            ret = QMessageBox.question(
                self, "Exit",
                "An encoding task is currently running. Do you want to stop and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ret == QMessageBox.StandardButton.Yes:
                self.stop_encoding()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ModernVideoOptimizer()
    window.show()
    sys.exit(app.exec())
