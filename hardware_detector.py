"""
=============================================================================
NEO VIDEO OPTIMIZER - DETECTOR DINÁMICO DE HARDWARE Y CÓDECS
=============================================================================
Detecta automáticamente la tarjeta gráfica del usuario (NVIDIA, Intel Arc,
AMD Radeon o CPU) y determina si soporta AV1 por hardware. Si no es compatible
con AV1, selecciona automáticamente el códec óptimo soportado (HEVC NVENC,
QSV, AMF o SVT-AV1/libx265).
=============================================================================
"""

import os
import sys
import shutil
import subprocess
from typing import Dict, Any, List

def get_ffmpeg_encoders() -> List[str]:
    """Obtiene la lista de códecs de video soportados por el binario FFmpeg en PATH."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return []
    
    encoders = []
    try:
        out = subprocess.check_output([ffmpeg_bin, "-encoders"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0].startswith("V"):
                encoders.append(parts[1])
    except Exception:
        pass
    return encoders

def detect_hardware_profile() -> Dict[str, Any]:
    """
    Analiza la GPU del sistema y determina la mejor configuración de codificación.
    Retorna un diccionario completo con:
      - gpu_name: Nombre comercial de la GPU
      - is_av1_supported: True si la GPU tiene codificador AV1 por hardware
      - recommended_codec: Códec óptimo (av1_nvenc, hevc_nvenc, etc.)
      - recommended_bitrate_1080p: Bitrate sugerido para 1080p
      - recommended_bitrate_720p: Bitrate sugerido para 720p
      - arch_badge: Etiqueta descriptiva (ej. 'Ada Lovelace Dual NVENC')
      - encoder_list: Lista de códecs disponibles en FFmpeg
    """
    encoders = get_ffmpeg_encoders()
    
    gpu_name = "Procesador (CPU / Sin GPU dedicada)"
    gpu_driver = ""
    is_nvidia = False

    # 1. Intentar consultar GPU NVIDIA mediante nvidia-smi
    try:
        smi = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        if smi:
            parts = smi.split(",")
            gpu_name = parts[0].strip()
            if len(parts) > 1:
                gpu_driver = parts[1].strip()
            is_nvidia = True
    except Exception:
        pass

    # 2. Si no es NVIDIA, intentar detectar AMD o Intel mediante PowerShell WMI (Windows)
    if not is_nvidia and os.name == 'nt':
        try:
            ps_cmd = "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"
            out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True, stderr=subprocess.DEVNULL)
            gpus = [line.strip() for line in out.splitlines() if line.strip() and "Citrix" not in line and "Virtual" not in line]
            if gpus:
                gpu_name = gpus[0]
        except Exception:
            pass

    gpu_upper = gpu_name.upper()

    # Valores por defecto para fallback CPU
    is_av1_supported = False
    recommended_codec = "libx265"
    rec_bitrate_1080p = 4000
    rec_bitrate_720p = 2000
    arch_badge = "CPU Software (x265)"
    encoder_type = "Software"

    # Evaluador de Arquitectura y Capacidades
    if is_nvidia or "NVIDIA" in gpu_upper or "GEFORCE" in gpu_upper or "RTX" in gpu_upper:
        encoder_type = "NVIDIA NVENC"
        # Ada Lovelace (RTX Serie 40 y RTX 4000/5000/6000 Ada) -> Soporta AV1 NVENC
        if any(k in gpu_upper for k in ["RTX 40", "4000 ADA", "4500 ADA", "5000 ADA", "6000 ADA", "4090", "4080", "4070", "4060"]):
            if "av1_nvenc" in encoders:
                is_av1_supported = True
                recommended_codec = "av1_nvenc"
                rec_bitrate_1080p = 3500
                rec_bitrate_720p = 1800
                if any(dual in gpu_upper for dual in ["4070 TI", "4070 SUPER", "4080", "4090"]):
                    arch_badge = "NVIDIA Ada Lovelace (Dual AV1 NVENC 8ª Gen)"
                else:
                    arch_badge = "NVIDIA Ada Lovelace (AV1 NVENC 8ª Gen)"
            elif "hevc_nvenc" in encoders:
                recommended_codec = "hevc_nvenc"
                rec_bitrate_1080p = 4500
                rec_bitrate_720p = 2200
                arch_badge = "NVIDIA Ada Lovelace (HEVC NVENC)"
        # Ampere / Turing / Volta (RTX 30, RTX 20, GTX 1660, Titan RTX) -> Soporta HEVC NVENC
        elif any(k in gpu_upper for k in ["RTX 30", "RTX 20", "GTX 16", "TITAN", "QUADRO", "3090", "3080", "3070", "3060", "2080", "2070", "2060"]):
            if "hevc_nvenc" in encoders:
                recommended_codec = "hevc_nvenc"
                rec_bitrate_1080p = 4500
                rec_bitrate_720p = 2200
                arch_badge = "NVIDIA NVENC (HEVC / H.265 - Sin soporte AV1 en hardware)"
            elif "h264_nvenc" in encoders:
                recommended_codec = "h264_nvenc"
                rec_bitrate_1080p = 6500
                rec_bitrate_720p = 3500
                arch_badge = "NVIDIA NVENC (H.264)"
        # Pascal / Maxwell (GTX 1080, 1070, 1060, 980, 970)
        else:
            if "hevc_nvenc" in encoders:
                recommended_codec = "hevc_nvenc"
                rec_bitrate_1080p = 5000
                rec_bitrate_720p = 2500
                arch_badge = "NVIDIA Pascal (HEVC NVENC)"
            elif "h264_nvenc" in encoders:
                recommended_codec = "h264_nvenc"
                rec_bitrate_1080p = 7000
                rec_bitrate_720p = 3800
                arch_badge = "NVIDIA Legacy (H.264 NVENC)"

    elif "ARC" in gpu_upper or "INTEL" in gpu_upper:
        encoder_type = "Intel QSV"
        if "av1_qsv" in encoders and any(a in gpu_upper for a in ["A770", "A750", "A580", "A380", "A310", "ULTRA"]):
            is_av1_supported = True
            recommended_codec = "av1_qsv"
            rec_bitrate_1080p = 3600
            rec_bitrate_720p = 1900
            arch_badge = "Intel Arc Alchemist (AV1 QuickSync)"
        elif "hevc_qsv" in encoders:
            recommended_codec = "hevc_qsv"
            rec_bitrate_1080p = 4600
            rec_bitrate_720p = 2300
            arch_badge = "Intel QuickSync (HEVC)"

    elif "RADEON" in gpu_upper or "AMD" in gpu_upper:
        encoder_type = "AMD AMF"
        if "av1_amf" in encoders and any(r in gpu_upper for r in ["7900", "7800", "7700", "7600", "RX 7"]):
            is_av1_supported = True
            recommended_codec = "av1_amf"
            rec_bitrate_1080p = 3800
            rec_bitrate_720p = 2000
            arch_badge = "AMD RDNA3 (AV1 AMF)"
        elif "hevc_amf" in encoders:
            recommended_codec = "hevc_amf"
            rec_bitrate_1080p = 4800
            rec_bitrate_720p = 2400
            arch_badge = "AMD Radeon (HEVC AMF)"

    # Fallback si no hay soporte por hardware verificado en encoders
    if recommended_codec not in encoders:
        if "libsvtav1" in encoders and os.cpu_count() and os.cpu_count() >= 8:
            is_av1_supported = True
            recommended_codec = "libsvtav1"
            rec_bitrate_1080p = 3200
            rec_bitrate_720p = 1700
            arch_badge = "CPU Multihilo (SVT-AV1 Software)"
        elif "libx265" in encoders:
            recommended_codec = "libx265"
            rec_bitrate_1080p = 4200
            rec_bitrate_720p = 2100
            arch_badge = "CPU Software (x265)"
        elif "libx264" in encoders:
            recommended_codec = "libx264"
            rec_bitrate_1080p = 6000
            rec_bitrate_720p = 3200
            arch_badge = "CPU Software (x264)"

    # Lista de códecs que se deben ofrecer en el combobox del usuario
    available_choices = []
    preferred_order = [
        "av1_nvenc", "hevc_nvenc", "h264_nvenc",
        "av1_qsv", "hevc_qsv",
        "av1_amf", "hevc_amf",
        "libsvtav1", "libx265", "libx264"
    ]
    for c in preferred_order:
        if c in encoders:
            available_choices.append(c)
    if not available_choices:
        available_choices = [recommended_codec]

    return {
        "gpu_name": gpu_name + (f" (Driver {gpu_driver})" if gpu_driver else ""),
        "is_av1_supported": is_av1_supported,
        "recommended_codec": recommended_codec,
        "recommended_bitrate_1080p": rec_bitrate_1080p,
        "recommended_bitrate_720p": rec_bitrate_720p,
        "arch_badge": arch_badge,
        "encoder_type": encoder_type,
        "available_choices": available_choices
    }

if __name__ == "__main__":
    prof = detect_hardware_profile()
    for k, v in prof.items():
        print(f"{k}: {v}")
