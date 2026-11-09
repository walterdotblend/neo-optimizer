"""
Generador de icono estilizado r/unixporn (Catppuccin Mocha / Tokyo Night)
Crea app_icon.ico y app_icon.png para el Optimizador de Video Profesional.
"""
from PIL import Image, ImageDraw
import os

def create_unixporn_icon(output_dir: str):
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Fondo cuadrado redondeado estilo dock/app de Hyprland/macOS
    pad = 24
    bg_radius = 110
    
    # Sombra sutil exterior
    for offset in range(16, 0, -2):
        alpha = int(12 * (1 - offset / 16))
        draw.rounded_rectangle(
            [pad - offset/2, pad - offset/2 + 8, size - pad + offset/2, size - pad + offset/2 + 8],
            radius=bg_radius,
            fill=(10, 10, 18, alpha)
        )

    # Base oscura Catppuccin Mantle / Crust (#11111b - #181825)
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=bg_radius,
        fill=(20, 22, 34, 255),
        outline=(49, 50, 68, 255),
        width=4
    )

    # Borde interior con brillo neón superior (degradado sutil simulado con líneas)
    draw.rounded_rectangle(
        [pad + 4, pad + 4, size - pad - 4, pad + 18],
        radius=bg_radius - 4,
        fill=(137, 180, 250, 28)
    )

    cx, cy = size // 2, size // 2

    # 2. Anillo de carrete de video / engranaje cyberpunk neón (Sapphire #89b4fa / Cyan #89dceb)
    r_outer = 160
    r_inner = 110
    draw.ellipse(
        [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
        outline=(137, 180, 250, 240),
        width=10
    )
    draw.ellipse(
        [cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
        outline=(203, 166, 247, 200),
        width=6
    )

    # 3. Marcas orbitales de carrete cinematográfico (4 círculos perforados)
    film_holes_radius = 135
    import math
    for angle_deg in [0, 60, 120, 180, 240, 300]:
        rad = math.radians(angle_deg)
        hx = cx + film_holes_radius * math.cos(rad)
        hy = cy + film_holes_radius * math.sin(rad)
        hr = 16
        draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(30, 32, 48, 255), outline=(137, 220, 235, 230), width=3)

    # 4. Rayo / Flecha de aceleración NVENC central (Verde Menta Neón #a6e3a1 y Peach #fab387)
    # Triángulo de reproducción / rayo estilizado de aceleración RTX
    bolt_points = [
        (cx - 20, cy - 90),
        (cx + 45, cy - 90),
        (cx + 10, cy - 10),
        (cx + 70, cy - 10),
        (cx - 45, cy + 95),
        (cx - 10, cy + 15),
        (cx - 55, cy + 15)
    ]
    
    # Resplandor exterior del rayo
    draw.polygon(bolt_points, fill=(166, 227, 161, 255), outline=(148, 226, 213, 255))
    
    # Núcleo brillante interior
    inner_bolt = [
        (cx - 15, cy - 75),
        (cx + 30, cy - 75),
        (cx + 5, cy - 15),
        (cx + 50, cy - 15),
        (cx - 30, cy + 75),
        (cx - 8, cy + 10),
        (cx - 40, cy + 10)
    ]
    draw.polygon(inner_bolt, fill=(245, 224, 220, 230))

    # 5. Guardar PNG
    png_path = os.path.join(output_dir, "app_icon.png")
    img.save(png_path, format="PNG")
    print(f"Icono PNG creado: {png_path}")

    # 6. Guardar ICO multi-tamaño para Windows (16, 24, 32, 48, 64, 128, 256)
    ico_path = os.path.join(output_dir, "app_icon.ico")
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=icon_sizes)
    print(f"Icono ICO creado: {ico_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    create_unixporn_icon(current_dir)
