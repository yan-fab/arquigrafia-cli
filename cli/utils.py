# cli/utils.py — Banner, tema marsala e helpers visuais

import sys, io
import pyfiglet
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
from rich import box

# Tema marsala: #7B2D3E ≈ color(88) no terminal 256-cores
MARSALA = "color(88)"
MARSALA_BRIGHT = "color(124)"
CREME = "color(224)"
CINZA = "color(245)"
VERDE = "color(34)"
VERMELHO = "color(160)"
AMARELO = "color(178)"

THEME = Theme({
    "marsala":       MARSALA_BRIGHT,
    "marsala.dim":   MARSALA,
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
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(theme=THEME, force_terminal=True, highlight=False)


def banner():
    """Exibe o banner pixel art em marsala."""
    console.clear()
    art = pyfiglet.figlet_format("ARQ\nUPLOADER", font="doom")
    lines = art.split("\n")
    styled = Text()
    for line in lines:
        styled.append(line + "\n", style="marsala")
    console.print(Panel(
        styled,
        title="[marsala.dim][ ARQUIGRAFIA v2.0 ][/]",
        border_style="marsala.dim",
        box=box.DOUBLE,
        padding=(0, 2),
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


def info(label: str, valor: str):
    console.print(f"  [label]{label:<14}[/] [valor]{valor}[/]")
