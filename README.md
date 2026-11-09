# ◈ NEO•OPTIMIZER // GRUB RICE EDITION (PyQt6)
### Optimizador de Video Profesional Multi-Versión

Suite de transcodificación de alto rendimiento y arquitectura moderna diseñada para bibliotecas multimedia y streaming local. Reescrita en **PyQt6 (C++)** para un rendimiento instantáneo sin retrasos ni lentitud en redimensionamiento, con estética inspirada en los temas de **GRUB** más aclamados de la comunidad **`r/unixporn`** (Catppuccin Mocha / Tokyo Night) y detección 100% dinámica de GPU y códecs de hardware.

---

## ⚡ Novedades Principales de la Versión PyQt6

### 1. Rendimiento Nativo C++ y Redimensión Instantánea
- Adiós a la lentitud y el retraso al redimensionar la ventana: el motor gráfico de **Qt6** renderiza a 60+ FPS utilizando aceleración de hardware nativa de Windows (Direct3D/OpenGL), sin el redibujado lento de lienzos de Tkinter.
- Soporte nativo para la barra de títulos oscura de Windows 11 (`DWMWA_USE_IMMERSIVE_DARK_MODE`).

### 2. Detección Dinámica de Gráfica y Selección Automática de Códec
- Al iniciar, el programa analiza la GPU del usuario y las capacidades de su binario FFmpeg mediante [hardware_detector.py](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/hardware_detector.py):
  - **NVIDIA Ada Lovelace (RTX Serie 40: 4090, 4080, 4070 SUPER, 4060, etc.)**: Detecta compatibilidad AV1 NVENC de 8ª generación (Doble motor en 4070 SUPER) y auto-configura por defecto **`av1_nvenc`** con bitrate óptimo (3500 kbps para 1080p).
  - **NVIDIA Ampere / Turing / Pascal (RTX 30, RTX 20, GTX 16/10)**: Detecta que no hay soporte AV1 por hardware y auto-configura de inmediato la mejor versión: **`hevc_nvenc`** (H.265) a 4500 kbps.
  - **Intel Arc (Alchemist/Battlemage)**: Auto-configura **`av1_qsv`** o `hevc_qsv`.
  - **AMD Radeon (RDNA3 / RX 7000)**: Auto-configura **`av1_amf`** o `hevc_amf`.
  - **Procesador (CPU / Sin GPU dedicada)**: Auto-configura **`libsvtav1`** (multihilo) o **`libx265`** con presets equilibrados.
- Insignia de telemetría dinámica en la cabecera con botón **"🔄 Re-detectar GPU"** para actualizar el perfil en cualquier momento.

### 3. Estética GRUB Bootloader / r/unixporn (Catppuccin / Tokyo Night)
- Fondo obsidian ultra-profundo (`#08090d`), tarjetas flotantes (`#0f111a`), bordes sutiles (`#1c1f30`) y acentos de color neón (Zafiro `#89b4fa`, Esmeralda `#a6e3a1`, Malva `#cba6f7`, Melocotón `#fab387` y Carmesí `#f38ba8`).
- Pestañas estilo entradas de menú de arranque GRUB:
  - `󰮯 01 • Biblioteca & Ajustes`
  - `󰐍 02 • Cola de Codificación`
- Barra superior Waybar con píldoras de telemetría de hardware en tiempo real.
- Caja de búsqueda de directorio estilo Rofi / Wofi.
- Dock inferior con velocímetro en vivo (`🚀 185 FPS • 4.1x`) y barra de progreso fluida.

### 4. Tablas Ultra-Rápidas (QTableWidget)
- Navegación fluida y desplazamiento instantáneo.
- Patrón cebra alternado (`#0a0b12` / `#10121d`).
- Filas de series y carpetas en azul noche (`#18223c`) con texto celeste vibrante (`#7ec8ff`) e icono `📁`.
- Videos con configuración personalizada en color ámbar (`#fdba74`).
- Videos con multiversión generada en color malva (`#f5bde6`).
- Soporte completo para selección múltiple con `Ctrl` y `Shift`.

### 5. Tolerancia a Fallos y Salto Automático de Errores
- Si un archivo está corrupto o da error en FFmpeg, el proceso no se detiene: el archivo se marca como `Error (Saltado)` y la cola continúa inmediatamente con el siguiente video para aprovechar el tiempo.
- Botón **"🔍 Ver Detalle de Errores"** para ver los registros de FFmpeg en cualquier momento.

### 6. Subtítulos y Audio Inteligentes
- Opción **"🚫 Ningún subtítulo por defecto"**: conserva todas las pistas de subtítulos en el MKV pero desactiva la bandera predeterminada (`-disposition:s:i 0`), evitando subtítulos no deseados en la reproducción inicial.
- Filtro inteligente por nombre o por número de pista para pistas de audio (Castellano, Latino, Inglés, etc.).
- Limpieza opcional de títulos embebidos en metadatos (`clean_file_metadata_inplace`).

### 7. Acciones al Finalizar con Cuenta Regresiva de Seguridad
- Opciones: *Nada*, *Apagar PC*, *Hibernar*, *Suspender* o *Cerrar programa*.
- Ventana interactiva con cuenta regresiva de 30 segundos y aviso acústico, permitiendo al usuario cancelar o ejecutar la acción de inmediato.

---

## 📦 Suite de Instalación y Despliegue

| Archivo | Descripción |
| :--- | :--- |
| [gui_app.py](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/gui_app.py) | **Aplicación principal en PyQt6** con rendimiento C++, redimensión instantánea y diseño r/unixporn GRUB Rice. |
| [hardware_detector.py](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/hardware_detector.py) | **Módulo detector de GPU**: analiza NVIDIA/Intel/AMD/CPU y selecciona automáticamente el códec óptimo. |
| [core_engine.py](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/core_engine.py) | **Motor de codificación**: ffprobe profundo, cálculo exacto de bitrates (BPS), aspect ratio dinámico y comandos FFmpeg. |
| [installer_gui.py](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/installer_gui.py) | **Asistente gráfico interactivo** de instalación para Windows. |
| [instalar.bat](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/instalar.bat) | Script para lanzar el instalador gráfico con un solo clic. |
| [compilar_exe.bat](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/compilar_exe.bat) | Compila la aplicación en un **ejecutable único `.exe` independiente** (`dist/NeoVideoOptimizer.exe`). |
| [desinstalar.bat](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/desinstalar.bat) | Script de desinstalación limpia. |
| [app_icon.ico](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/app_icon.ico) | Icono nativo multi-capa (16px a 256px) para Windows. |

---

## 🚀 Cómo Iniciar

- **Ejecución Directa**: Haz doble clic en [`iniciar_optimizador.bat`](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/iniciar_optimizador.bat) o ejecuta `python gui_app.py`.
- **Instalar con Accesos Directos**: Ejecuta [`instalar.bat`](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/instalar.bat).
- **Generar Ejecutable `.exe` Standalone**: Ejecuta [`compilar_exe.bat`](file:///C:/Users/walyo/.gemini/antigravity/scratch/video_optimizer/compilar_exe.bat).
