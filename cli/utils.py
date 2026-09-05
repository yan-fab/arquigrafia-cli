# cli/utils.py — Banner, tema marsala e helpers visuais

import sys, io
import pyfiglet
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
from rich import box

# Tema marsala: #7B2D3E ≈ color(88) no terminal 256-cores
MARSALA = "#9B2335"
MARSALA_BRIGHT = "#C72C41"
CREME = "#E8D5C4"
CINZA = "#8B8B8B"
VERDE = "#2ECC71"
VERMELHO = "#E74C3C"
AMARELO = "#F39C12"

# Gradiente vertical inspirado no estilo da imagem de referência
GRADIENT_MARSALA = [
    "#E03E52",  # Linha 1: Marsala Coral Luminoso
    "#C72C41",  # Linha 2: Marsala Vibrante
    "#9B2335",  # Linha 3: Marsala Oficial Arquigrafia
    "#B55361",  # Linha 4: Marsala Suave / Rosé Escuro
    "#D9969F",  # Linha 5: Rosé Pastel
    "#E8D5C4",  # Linha 6: Creme / Base do contorno
]

THEME = Theme({
    "marsala":       MARSALA_BRIGHT,
    "marsala.dim":   MARSALA,
    "marsala.bold":  f"bold {MARSALA_BRIGHT}",
    "bold.marsala":  f"bold {MARSALA_BRIGHT}",
    "creme":         CREME,
    "cinza":         CINZA,
    "ok":            VERDE,
    "erro":          VERMELHO,
    "aviso":         AMARELO,
    "titulo":        f"bold {MARSALA_BRIGHT}",
    "label":         f"bold {CREME}",
    "valor":         CREME,
    "borda":         MARSALA,
})

# Força UTF-8 no terminal Windows para suporte a Unicode
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(theme=THEME, force_terminal=True, highlight=False)


def banner(limpar: bool = True):
    """Exibe o banner estilizado em ansi_shadow com gradiente vertical em marsala/creme."""
    if limpar:
        console.clear()

    largura = console.width or 100
    if largura >= 88:
        texto = "ARQUIGRAFIA"
        art = pyfiglet.figlet_format(texto, font="ansi_shadow", width=160)
    else:
        texto = "ARQUI\nGRAFIA"
        art = pyfiglet.figlet_format(texto, font="ansi_shadow", width=80)

    lines = [l for l in art.splitlines() if l.strip()]

    styled = Text()
    for i, line in enumerate(lines):
        color = GRADIENT_MARSALA[i % len(GRADIENT_MARSALA)]
        styled.append(line + "\n", style=f"bold {color}")

    console.print(Panel(
        styled,
        title="[bold #E8D5C4]◆ [bold #9B2335]ARQUIGRAFIA[/] [bold #E8D5C4]• UPLOADER & ORGANIZER v2.1 ◆[/]",
        subtitle="[#8B8B8B]FAU-USP • Rede Colaborativa de Imagens de Arquitetura[/#8B8B8B]",
        border_style="#9B2335",
        box=box.ROUNDED,
        padding=(0, 1),
    ))


def section(titulo: str):
    """Cabeçalho de seção com borda dupla."""
    console.rule(f"[titulo]  {titulo}  [/]", style="marsala.dim")


def ok(msg: str):
    console.print(f"  [ok]✔[/]  [creme]{msg}[/]")


def erro(msg: str):
    console.print(f"  [erro]✘[/]  [creme]{msg}[/]")


def aviso(msg: str):
    console.print(f"  [aviso]⚠[/]  [creme]{msg}[/]")


def info(label: str, valor: str = ""):
    if valor:
        console.print(f"  [label]{label:<14}[/] [valor]{valor}[/]")
    else:
        console.print(f"  [cinza]ℹ[/]  [creme]{label}[/]")
