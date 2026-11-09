import subprocess
import json
import os
import sys
import shutil
import re
from typing import Dict, List, Optional, Any

VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.ts', '.m2ts', '.webm'}
HISTORY_FILENAME = ".codec_history.json"

LANG_MAP = {
    "spa": "Español",
    "es": "Español",
    "esp": "Español",
    "lat": "Latino",
    "es-419": "Latino",
    "eng": "Inglés",
    "en": "Inglés",
    "fre": "Francés",
    "fra": "Francés",
    "fr": "Francés",
    "ger": "Alemán",
    "deu": "Alemán",
    "de": "Alemán",
    "ita": "Italiano",
    "it": "Italiano",
    "por": "Portugués",
    "pt": "Portugués",
    "jpn": "Japonés",
    "ja": "Japonés",
    "rus": "Ruso",
    "ru": "Ruso",
    "chi": "Chino",
    "zho": "Chino",
    "zh": "Chino",
    "und": "Sin idioma",
}

def normalize_lang(code: str) -> str:
    if not code:
        return "Sin idioma"
    code_clean = code.strip().lower()
    return LANG_MAP.get(code_clean, code.upper())

def get_file_quick_id(filepath: str) -> str:
    try:
        size = os.path.getsize(filepath)
        return f"{os.path.basename(filepath)}_{size}"
    except Exception:
        return os.path.basename(filepath)

def load_history(folder_path: str) -> Dict[str, Any]:
    hist_file = os.path.join(folder_path, HISTORY_FILENAME)
    if os.path.isfile(hist_file):
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(folder_path: str, history: Dict[str, Any]):
    hist_file = os.path.join(folder_path, HISTORY_FILENAME)
    try:
        with open(hist_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"No se pudo guardar el historial en {folder_path}: {e}")

def extract_stream_bitrate_bps(stream: Optional[Dict[str, Any]]) -> int:
    """Extrae el bitrate real de la pista leyendo bit_rate directo o tags BPS de Matroska/MKV."""
    if not stream:
        return 0
    # 1. Campo directo bit_rate
    if "bit_rate" in stream:
        try:
            val = int(stream["bit_rate"])
            if val > 0:
                return val
        except (ValueError, TypeError):
            pass

    # 2. Etiquetas MKV (BPS, BPS-eng, BPS-jpn, etc.)
    tags = stream.get("tags", {})
    for k, v in tags.items():
        k_up = k.upper()
        if k_up == "BPS" or k_up.startswith("BPS-"):
            try:
                val = int(str(v).strip())
                if val > 0:
                    return val
            except (ValueError, TypeError):
                pass
    return 0

def detect_video_resolution_tag(width: int, height: int) -> str:
    """
    Detecta la categoría de resolución estándar considerando relaciones de aspecto cinematográficas
    (ej: 2.39:1 / 2.35:1 / 21:9 donde las barras negras vienen recortadas, ej: 1920x800, 3840x1600).
    """
    if width <= 0 or height <= 0:
        return "1080p"
    max_d = max(width, height)
    min_d = min(width, height)
    if max_d >= 2500 or min_d >= 1350:
        return "2160p"
    elif max_d >= 1600 or min_d >= 800:
        return "1080p"
    elif max_d >= 1050 or min_d >= 540:
        return "720p"
    else:
        return "480p"

def get_video_metadata(filepath: str) -> Optional[Dict[str, Any]]:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        filepath
    ]
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            startupinfo=startupinfo,
            check=True
        )
        data = json.loads(result.stdout)
    except Exception as e:
        print(f"Error analizando {filepath}: {e}")
        return None

    streams = data.get("streams", [])
    format_info = data.get("format", {})
    format_tags = format_info.get("tags", {})
    internal_title = format_tags.get("title") or format_tags.get("TITLE") or ""

    video_stream = next((s for s in streams if s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic", 0) == 0), None)
    if not video_stream:
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)

    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]

    # Calcular Bitrate de Audio por pista (usando tags BPS si es MKV)
    total_audio_bitrate_kbps = 0
    for a in audio_streams:
        a_bps = extract_stream_bitrate_bps(a)
        if a_bps > 0:
            total_audio_bitrate_kbps += a_bps // 1000
        else:
            codec_a = a.get("codec_name", "").lower()
            channels = a.get("channels", 2)
            if codec_a in ["flac", "truehd", "dts", "pcm_s16le", "pcm_s24le"]:
                total_audio_bitrate_kbps += 1400 if channels > 2 else 850
            else:
                total_audio_bitrate_kbps += 448 if channels > 2 else 192

    if total_audio_bitrate_kbps == 0 and audio_streams:
        total_audio_bitrate_kbps = 256

    # Calcular Bitrate de Video exacto
    v_bitrate_bps = extract_stream_bitrate_bps(video_stream)
    fmt_bps = 0
    if "bit_rate" in format_info:
        try:
            fmt_bps = int(format_info["bit_rate"])
        except (ValueError, TypeError):
            fmt_bps = 0

    # Si la etiqueta BPS del stream es mayor que el bitrate físico total del archivo (etiqueta antigua heredada tras recodificar), ignorarla
    if fmt_bps > 0 and (v_bitrate_bps == 0 or v_bitrate_bps > fmt_bps):
        estimated_v_bps = fmt_bps - (total_audio_bitrate_kbps * 1000)
        v_bitrate_bps = max(fmt_bps // 2, estimated_v_bps)

    # HDR / Dolby Vision
    hdr_info = "SDR"
    if video_stream:
        color_transfer = video_stream.get("color_transfer", "")
        color_primaries = video_stream.get("color_primaries", "")
        side_data = video_stream.get("side_data_list", [])
        
        has_dovi = any("DOVI" in str(sd.get("side_data_type", "")) or "Dolby Vision" in str(sd.get("side_data_type", "")) for sd in side_data)
        
        if has_dovi:
            hdr_info = "Dolby Vision"
        elif color_transfer in ["smpte2084", "arib-std-b67"]:
            hdr_info = "HDR10 / HLG"
        elif "bt2020" in color_primaries:
            hdr_info = "Wide Gamut / HDR"

    # Audios
    audios = []
    for rel_idx, s in enumerate(audio_streams):
        tags = s.get("tags", {})
        raw_lang = tags.get("language") or tags.get("LANGUAGE") or tags.get("lang") or ""
        lang_pretty = normalize_lang(raw_lang)
        title = tags.get("title") or tags.get("TITLE") or tags.get("handler_name") or tags.get("HANDLER_NAME") or ""
        codec = s.get("codec_name", "")
        channels = s.get("channels", 2)
        global_stream_idx = s.get("index")
        profile = s.get("profile", "")
        
        is_atmos = "atmos" in title.lower() or "atmos" in profile.lower()
        
        desc = f"Audio #{rel_idx} [{lang_pretty}] {codec.upper()} {channels}ch"
        if title and title != "ISO Media file produced by Google Inc.":
            desc += f" - {title}"
        if is_atmos:
            desc += " (Dolby Atmos)"
            
        audios.append({
            "rel_index": rel_idx,
            "global_index": global_stream_idx,
            "raw_lang": raw_lang,
            "lang_pretty": lang_pretty,
            "title": title,
            "codec": codec,
            "channels": channels,
            "is_atmos": is_atmos,
            "is_default": s.get("disposition", {}).get("default", 0) == 1,
            "description": desc
        })

    # Subtítulos
    subtitles = []
    for rel_idx, s in enumerate(subtitle_streams):
        tags = s.get("tags", {})
        raw_lang = tags.get("language") or tags.get("LANGUAGE") or tags.get("lang") or ""
        lang_pretty = normalize_lang(raw_lang)
        title = tags.get("title") or tags.get("TITLE") or tags.get("handler_name") or tags.get("HANDLER_NAME") or ""
        codec = s.get("codec_name", "")
        global_stream_idx = s.get("index")
        
        is_forced = s.get("disposition", {}).get("forced", 0) == 1 or "forced" in title.lower() or "forzado" in title.lower()
        
        desc = f"Sub #{rel_idx} [{lang_pretty}] {codec.upper()}"
        if is_forced:
            desc += " [FORZADO]"
        if title and title != "ISO Media file produced by Google Inc.":
            desc += f" - {title}"
            
        subtitles.append({
            "rel_index": rel_idx,
            "global_index": global_stream_idx,
            "raw_lang": raw_lang,
            "lang_pretty": lang_pretty,
            "title": title,
            "codec": codec,
            "is_forced": is_forced,
            "is_default": s.get("disposition", {}).get("default", 0) == 1,
            "description": desc
        })

    duration = float(format_info.get("duration", 0.0) or 0.0)

    return {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "internal_title": internal_title,
        "filesize_mb": round(os.path.getsize(filepath) / (1024 * 1024), 2),
        "duration_sec": duration,
        "video_codec": video_stream.get("codec_name", "desconocido") if video_stream else "ninguno",
        "video_profile": video_stream.get("profile", "") if video_stream else "",
        "pix_fmt": video_stream.get("pix_fmt", "") if video_stream else "",
        "color_transfer": video_stream.get("color_transfer", "") if video_stream else "",
        "color_primaries": video_stream.get("color_primaries", "") if video_stream else "",
        "color_space": video_stream.get("color_space", "") if video_stream else "",
        "width": video_stream.get("width", 0) if video_stream else 0,
        "height": video_stream.get("height", 0) if video_stream else 0,
        "resolution_tag": detect_video_resolution_tag(video_stream.get("width", 0), video_stream.get("height", 0)) if video_stream else "1080p",
        "bitrate_kbps": int(v_bitrate_bps / 1000) if v_bitrate_bps else 0,
        "audio_bitrate_kbps": total_audio_bitrate_kbps,
        "hdr_info": hdr_info,
        "audio_streams": audios,
        "subtitle_streams": subtitles,
        "file_id": get_file_quick_id(filepath)
    }

def estimate_compressed_size_mb(duration_sec: float, target_video_bitrate_kbps: int, audio_bitrate_kbps: int = 384) -> float:
    if duration_sec <= 0:
        return 0.0
    total_kbps = target_video_bitrate_kbps + audio_bitrate_kbps
    est_mb = (total_kbps * duration_sec) / 8192.0
    return round(est_mb, 1)

def calculate_auto_bitrate(
    src_codec: str,
    src_bitrate_kbps: int,
    src_res_tag: str,
    target_codec: str,
    target_res_tag: str
) -> int:
    """
    Calcula dinámicamente el bitrate equivalente óptimo para mantener la calidad visual
    del video fuente al transcodificar a un nuevo códec (AV1, HEVC, H264) y resolución.
    
    Ejemplo: H.264 @ 6000 kbps transcodificado a AV1 resulta en ~3000 kbps (50%) con calidad idéntica.
    """
    s_codec = (src_codec or "h264").lower().strip()
    t_codec = (target_codec or "av1_nvenc").lower().strip()
    
    # Referencias estándar si no hay bitrate detectado en la fuente
    baseline_bitrates = {
        "4K": 14000,
        "2160p": 14000,
        "1080p": 5500,
        "720p": 2800,
        "480p": 1400
    }
    
    if "4K" in src_res_tag or "2160p" in src_res_tag:
        clean_src_res = "4K"
    elif "1080p" in src_res_tag:
        clean_src_res = "1080p"
    elif "720p" in src_res_tag:
        clean_src_res = "720p"
    elif "480p" in src_res_tag:
        clean_src_res = "480p"
    else:
        clean_src_res = "1080p"

    base_kbps = src_bitrate_kbps if (src_bitrate_kbps and src_bitrate_kbps > 300) else baseline_bitrates.get(clean_src_res, 5500)

    # Identificar familia de códec de origen
    if "av1" in s_codec or "av01" in s_codec:
        src_family = "av1"
    elif "hevc" in s_codec or "h265" in s_codec or "265" in s_codec or "vp9" in s_codec:
        src_family = "hevc"
    else:
        src_family = "h264"

    # Identificar familia de códec de destino
    if "av1" in t_codec:
        tgt_family = "av1"
    elif "hevc" in t_codec or "265" in t_codec:
        tgt_family = "hevc"
    else:
        tgt_family = "h264"

    # Multiplicador de eficiencia relativa manteniendo calidad perceptual idéntica
    efficiency_table = {
        ("h264", "av1"): 0.50,
        ("h264", "hevc"): 0.65,
        ("h264", "h264"): 0.85,
        
        ("hevc", "av1"): 0.75,
        ("hevc", "hevc"): 0.85,
        ("hevc", "h264"): 1.40,
        
        ("av1", "av1"): 0.85,
        ("av1", "hevc"): 1.25,
        ("av1", "h264"): 1.80
    }
    
    ratio = efficiency_table.get((src_family, tgt_family), 0.65)
    est_kbps = float(base_kbps) * ratio

    # Factor de escala por cambio de resolución
    target_res = (target_res_tag or "").strip()
    if target_res and target_res != "Original":
        if "4K" in target_res or "2160p" in target_res:
            res_ratio_map = {"4K": 1.0, "1080p": 2.2, "720p": 3.8, "480p": 6.0}
            est_kbps *= res_ratio_map.get(clean_src_res, 1.0)
        elif "1080p" in target_res:
            res_ratio_map = {"4K": 0.45, "1080p": 1.0, "720p": 1.8, "480p": 3.0}
            est_kbps *= res_ratio_map.get(clean_src_res, 1.0)
        elif "720p" in target_res:
            res_ratio_map = {"4K": 0.25, "1080p": 0.55, "720p": 1.0, "480p": 1.6}
            est_kbps *= res_ratio_map.get(clean_src_res, 1.0)
        elif "480p" in target_res:
            res_ratio_map = {"4K": 0.15, "1080p": 0.35, "720p": 0.60, "480p": 1.0}
            est_kbps *= res_ratio_map.get(clean_src_res, 1.0)

    # Límites seguros de bitrate según resolución final
    effective_res = target_res if (target_res and target_res != "Original") else clean_src_res
    if "4K" in effective_res or "2160p" in effective_res:
        min_kbps, max_kbps = 4500, 25000
    elif "1080p" in effective_res:
        min_kbps, max_kbps = 1800, 10000
    elif "720p" in effective_res:
        min_kbps, max_kbps = 1000, 5000
    else:
        min_kbps, max_kbps = 600, 2500

    clamped = max(min_kbps, min(int(est_kbps), max_kbps))
    return int(round(clamped / 50.0) * 50)

def find_best_audio_match(audios: List[Dict[str, Any]], pattern: str) -> Optional[Dict[str, Any]]:
    if not audios:
        return None
    if not pattern:
        return audios[0]
        
    p = pattern.strip().lower()
    for a in audios:
        if p == a["raw_lang"].lower() or p == a["lang_pretty"].lower() or p == a["title"].lower():
            return a
            
    for a in audios:
        haystack = f"{a['raw_lang']} {a['lang_pretty']} {a['title']} {a['description']}".lower()
        if p in haystack:
            return a
            
    return audios[0]

def find_best_sub_match(subtitles: List[Dict[str, Any]], pattern: str) -> Optional[Dict[str, Any]]:
    if not subtitles:
        return None
    if not pattern:
        return subtitles[0]
        
    p = pattern.strip().lower()
    for s in subtitles:
        if p == s["raw_lang"].lower() or p == s["lang_pretty"].lower() or p == s["title"].lower():
            return s
            
    for s in subtitles:
        haystack = f"{s['raw_lang']} {s['lang_pretty']} {s['title']} {s['description']}".lower()
        if p in haystack:
            return s
            
    return subtitles[0]

def scan_directory_for_videos(root_dir: str) -> Dict[str, Dict[str, Any]]:
    groups: Dict[str, Dict[str, Any]] = {}

    for dirpath, _, filenames in os.walk(root_dir):
        if "_optimizado" in dirpath or ".temp" in dirpath:
            continue

        # Ignorar archivos temporales de codificación
        video_files = [
            f for f in filenames
            if os.path.splitext(f.lower())[1] in VIDEO_EXTENSIONS
            and not f.endswith(".encoding_tmp.mkv")
            and not f.endswith(".temp_meta.mkv")
        ]
        if not video_files:
            continue

        history = load_history(dirpath)
        encoded_files_map = history.get("encoded_files", {})
        saved_config = history.get("last_config", None)

        # Conjunto de nombres de salida y archivos originales ya registrados en el historial
        known_outputs = set()
        known_original_names = set()
        for entry in encoded_files_map.values():
            if isinstance(entry, dict):
                if entry.get("output"):
                    known_outputs.add(entry["output"].lower())
                for out_item in entry.get("outputs", []):
                    known_outputs.add(out_item.lower())
                if entry.get("original_name"):
                    known_original_names.add(entry["original_name"].lower())

        # Mapa de nombres base existentes para detectar pares (Original <-> Versión generada)
        existing_stems = set()
        for vf in video_files:
            stem, _ = os.path.splitext(vf)
            if not re.search(r'\s+-\s+(4K|2160p|1080p|720p|480p)(\s+(AV1|HEVC|H264))?$', stem, flags=re.IGNORECASE):
                existing_stems.add(stem.strip().lower())

        # Identificar qué nombres base ya tienen una versión codificada terminada (> 1MB) en esta misma carpeta
        stems_with_completed_version = set()
        for vf in video_files:
            stem, _ = os.path.splitext(vf)
            m_ver = re.search(r'^(.*?)\s+-\s+(4K|2160p|1080p|720p|480p)(\s+(AV1|HEVC|H264))?$', stem, flags=re.IGNORECASE)
            if m_ver:
                base_st = m_ver.group(1).strip().lower()
                full_vfp = os.path.join(dirpath, vf)
                # Si el archivo de versión mide más de 1MB y está registrado o es av1/hevc, se considera versión terminada
                try:
                    if os.path.getsize(full_vfp) > 1024 * 1024:
                        stems_with_completed_version.add(base_st)
                except Exception:
                    pass

        is_subfolder = os.path.abspath(dirpath) != os.path.abspath(root_dir)
        group_name = os.path.basename(dirpath) if is_subfolder else "Películas / Carpeta Raíz"

        group_info = {
            "group_name": group_name,
            "dir_path": dirpath,
            "is_series": is_subfolder,
            "history": history,
            "saved_config": saved_config,
            "videos": [],
            "new_count": 0,
            "encoded_count": 0,
            "total_size_mb": 0.0
        }

        # Ordenar poniendo siempre primero los archivos originales antes que las versiones "- 1080p / - 720p"
        sorted_files = sorted(
            video_files,
            key=lambda x: (bool(re.search(r'\s+-\s+(4K|2160p|1080p|720p|480p)', x, flags=re.IGNORECASE)), x.lower())
        )

        for vf in sorted_files:
            full_path = os.path.join(dirpath, vf)
            meta = get_video_metadata(full_path)
            if meta:
                file_id = meta["file_id"]
                stem, _ = os.path.splitext(vf)
                clean_stem = re.sub(r'\s+-\s+(4K|2160p|1080p|720p|480p).*$', '', stem, flags=re.IGNORECASE).strip().lower()
                is_version_tag_file = (clean_stem != stem.strip().lower()) and (clean_stem in existing_stems)

                # Un video se considera "ya codificado" si:
                # 1. Su file_id o nombre está en el mapa de archivos codificados
                # 2. Es un archivo de salida registrado en el historial
                # 3. O es el archivo de origen original que no se borró y su versión codificada ya existe terminada al lado
                # 4. O es un archivo de versión generada (-1080p, etc.) con codec moderno
                is_already_encoded = (
                    file_id in encoded_files_map
                    or vf in encoded_files_map
                    or vf.lower() in known_original_names
                    or vf.lower() in known_outputs
                    or (clean_stem in stems_with_completed_version)
                    or (is_version_tag_file and meta.get("video_codec") in ("av1", "hevc"))
                )
                meta["is_already_encoded"] = is_already_encoded
                if is_already_encoded:
                    group_info["encoded_count"] += 1
                else:
                    group_info["new_count"] += 1
                meta["series_group"] = group_name
                meta["parent_dir"] = dirpath
                group_info["total_size_mb"] += meta["filesize_mb"]
                group_info["videos"].append(meta)

        if group_info["videos"]:
            groups[dirpath] = group_info

    return groups

def build_standard_filename(original_filepath: str, resolution_tag: str, codec_tag: str = "", only_resolution: bool = True) -> str:
    """
    Genera el nombre limpio multi-versión para bibliotecas multimedia:
    Movies/Movie (2019)/Movie (2019) - 1080p.mkv
    Si el archivo fuente ya contenía un sufijo como '- 1080p' o '- 1080p AV1', lo elimina
    y lo reemplaza por la resolución seleccionada ('- 720p.mkv').
    """
    base, _ = os.path.splitext(os.path.basename(original_filepath))
    base = " ".join(base.split())
    
    # Limpiar recursivamente cualquier etiqueta de resolución o códec existente al final del nombre
    while True:
        cleaned = re.sub(r'\s+-\s+(4K|2160p|1080p|720p|480p)(\s+(AV1|HEVC|H264|x265|x264))?$', '', base, flags=re.IGNORECASE).strip()
        if cleaned == base:
            break
        base = cleaned

    clean_base = base
    res_clean = resolution_tag.replace("4K (2160p)", "2160p").strip()
    if only_resolution or not codec_tag:
        version_label = res_clean
    else:
        version_label = f"{res_clean} {codec_tag}".strip()

    return f"{clean_base} - {version_label}.mkv"

# Alias retrocompatible
build_jellyfin_filename = build_standard_filename

def build_ffmpeg_encode_command(
    meta: Dict[str, Any],
    output_path: str,
    target_codec: str,
    target_bitrate_kbps: int,
    preset: str,
    resolution: str,
    burn_subtitles: bool,
    preferred_audio_pattern: str,
    preferred_audio_rel_idx: Optional[int],
    preferred_sub_pattern: str,
    preferred_sub_rel_idx: Optional[int],
    clean_metadata_title: bool = True
) -> List[str]:
    cmd = ["ffmpeg", "-y", "-progress", "pipe:1", "-nostats"]
    subtitles = meta.get("subtitle_streams", [])
    
    selected_sub_rel = preferred_sub_rel_idx
    if selected_sub_rel == -1:
        # Modo: Sin subtítulo por defecto
        selected_sub_rel = -1
    elif selected_sub_rel is None and preferred_sub_pattern and subtitles:
        best_s = find_best_sub_match(subtitles, preferred_sub_pattern)
        if best_s:
            selected_sub_rel = best_s["rel_index"]

    if burn_subtitles and selected_sub_rel is None and subtitles:
        selected_sub_rel = 0

    vf_filters = []
    
    # Escala de resolución respetando aspect ratio no estándar (Cinemascope 2.39:1, 21:9, 4:3, etc.)
    # evitando deformaciones y sin agrandar si el video original ya es de menor resolución
    if resolution == "1080p":
        vf_filters.append("scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2")
    elif resolution == "720p":
        vf_filters.append("scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2")
    elif resolution == "480p":
        vf_filters.append("scale='min(854,iw)':'min(480,ih)':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2")
    elif resolution == "4K (2160p)":
        vf_filters.append("scale='min(3840,iw)':'min(2160,ih)':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2")

    # Quemado de subtítulo con libass
    if burn_subtitles and selected_sub_rel is not None and 0 <= selected_sub_rel < len(subtitles):
        escaped_file = meta["filepath"].replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        vf_filters.append(f"subtitles='{escaped_file}':si={selected_sub_rel}")

    cmd.extend(["-i", meta["filepath"]])

    # Mapeo de streams (solo el stream de video principal, evitando portadas adjuntas)
    cmd.extend(["-map", "0:v:0"])
    cmd.extend(["-map", "0:a?"])
    if not burn_subtitles:
        cmd.extend(["-map", "0:s?"])

    # Limpiar título interno (usando el nombre final sin extensión temporal) y etiquetas BPS heredadas del stream de video
    if clean_metadata_title:
        final_base = os.path.basename(output_path).replace(".encoding_tmp.mkv", "")
        clean_name = os.path.splitext(final_base)[0]
        cmd.extend(["-metadata", f"title={clean_name}"])
    cmd.extend([
        "-metadata:s:v:0", "BPS=",
        "-metadata:s:v:0", "BPS-eng=",
        "-metadata:s:v:0", "NUMBER_OF_BYTES=",
        "-metadata:s:v:0", "NUMBER_OF_BYTES-eng="
    ])

    if vf_filters:
        cmd.extend(["-vf", ",".join(vf_filters)])

    # Video Codec: SINTAXIS EXACTA FFmpeg NVENC
    if "nvenc" in target_codec:
        cmd.extend(["-c:v", target_codec])
        cmd.extend(["-preset", preset])
        cmd.extend(["-tune", "hq"])
        cmd.extend(["-spatial-aq", "1"])
        cmd.extend(["-temporal-aq", "1"])
        cmd.extend(["-b:v", f"{target_bitrate_kbps}k"])
        cmd.extend(["-maxrate", f"{int(target_bitrate_kbps * 1.5)}k"])
        cmd.extend(["-bufsize", f"{target_bitrate_kbps * 2}k"])
    elif "qsv" in target_codec:
        cmd.extend(["-c:v", target_codec, "-b:v", f"{target_bitrate_kbps}k", "-preset", "medium"])
    elif "amf" in target_codec:
        cmd.extend(["-c:v", target_codec, "-b:v", f"{target_bitrate_kbps}k", "-quality", "quality"])
    elif "libsvtav1" in target_codec:
        cmd.extend(["-c:v", "libsvtav1", "-b:v", f"{target_bitrate_kbps}k", "-preset", "6"])
    elif "libx265" in target_codec:
        cmd.extend(["-c:v", "libx265", "-b:v", f"{target_bitrate_kbps}k", "-preset", "medium"])
    else:
        cmd.extend(["-c:v", target_codec, "-b:v", f"{target_bitrate_kbps}k"])

    # Selección de formato de píxel 100% compatible con hardware NVENC (convierte yuv444p10le -> p010le y yuv444p -> yuv420p)
    src_pix_fmt = (meta.get("pix_fmt") or "").lower()
    is_10bit = ("10" in src_pix_fmt) or ("12" in src_pix_fmt)
    if target_codec == "h264_nvenc":
        target_pix_fmt = "yuv420p"
    elif "nvenc" in target_codec:
        target_pix_fmt = "p010le" if is_10bit else "yuv420p"
    else:
        target_pix_fmt = "yuv420p10le" if is_10bit else "yuv420p"
    cmd.extend(["-pix_fmt", target_pix_fmt])

    # HDR / Colorimetría Pass-through
    if not burn_subtitles:
        if meta.get("color_transfer"):
            cmd.extend(["-color_trc", meta["color_transfer"]])
        if meta.get("color_primaries"):
            cmd.extend(["-color_primaries", meta["color_primaries"]])
        if meta.get("color_space"):
            cmd.extend(["-colorspace", meta["color_space"]])

    # Audio y subs en pass-through sin tocar Atmos
    cmd.extend(["-c:a", "copy"])
    if not burn_subtitles:
        cmd.extend(["-c:s", "copy"])

    # Disposición de Audio Default
    audios = meta.get("audio_streams", [])
    selected_audio_rel = preferred_audio_rel_idx
    if selected_audio_rel is None and preferred_audio_pattern and audios:
        best_a = find_best_audio_match(audios, preferred_audio_pattern)
        if best_a:
            selected_audio_rel = best_a["rel_index"]

    if selected_audio_rel is not None and 0 <= selected_audio_rel < len(audios):
        for i in range(len(audios)):
            if i == selected_audio_rel:
                cmd.extend([f"-disposition:a:{i}", "default"])
            else:
                cmd.extend([f"-disposition:a:{i}", "0"])

    # Disposición de Subtítulo Default
    if not burn_subtitles and subtitles:
        if selected_sub_rel == -1:
            for i in range(len(subtitles)):
                cmd.extend([f"-disposition:s:{i}", "0"])
        elif selected_sub_rel is not None and 0 <= selected_sub_rel < len(subtitles):
            for i in range(len(subtitles)):
                if i == selected_sub_rel:
                    cmd.extend([f"-disposition:s:{i}", "default"])
                else:
                    cmd.extend([f"-disposition:s:{i}", "0"])

    cmd.extend(["-f", "matroska", output_path])
    return cmd

def clean_file_metadata_inplace(filepath: str) -> bool:
    clean_title = os.path.splitext(os.path.basename(filepath))[0]
    temp_out = filepath + ".temp_meta.mkv"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", filepath,
        "-map", "0",
        "-c", "copy",
        "-metadata", f"title={clean_title}",
        "-f", "matroska",
        temp_out
    ]
    
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        res = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo)
        if res.returncode == 0 and os.path.isfile(temp_out) and os.path.getsize(temp_out) > 1024:
            os.replace(temp_out, filepath)
            return True
        else:
            if os.path.isfile(temp_out):
                os.remove(temp_out)
            return False
    except Exception as e:
        print(f"Error limpiando metadatos de {filepath}: {e}")
        if os.path.isfile(temp_out):
            os.remove(temp_out)
        return False
