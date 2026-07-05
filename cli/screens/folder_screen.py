# cli/screens/folder_screen.py — Seleção de pasta ou arquivo único

import os
import questionary
from rich.table import Table
from rich import box

from cli.utils import console, section, ok, aviso, erro
from core.uploader import listar_imagens, IMAGENS_EXT

_M = "#9B2335"
_C = "#E8D5C4"

QSTYLE = questionary.Style([
    ("qmark",       f"fg:{_M} bold"),
    ("question",    f"fg:{_C} bold"),
    ("answer",      f"fg:{_M} bold"),
    ("pointer",     f"fg:{_M} bold"),
    ("highlighted", f"fg:{_M} bold"),
])

_ULTIMA_PASTA_FILE = os.path.join(os.path.dirname(__file__), "../../.ultima_pasta.txt")
_ULTIMO_ARQUIVO_FILE = os.path.join(os.path.dirname(__file__), "../../.ultimo_arquivo.txt")


# ── Persistência ───────────────────────────────────────────────────────────────

def _salvar_ultima_pasta(pasta: str):
    try:
        with open(_ULTIMA_PASTA_FILE, "w", encoding="utf-8") as f:
            f.write(pasta)
    except Exception:
        pass


def _ler_ultima_pasta() -> str | None:
    try:
        if os.path.exists(_ULTIMA_PASTA_FILE):
            with open(_ULTIMA_PASTA_FILE, encoding="utf-8") as f:
                p = f.read().strip()
                return p if os.path.isdir(p) else None
    except Exception:
        return None


def _salvar_ultimo_arquivo(arq: str):
    try:
        with open(_ULTIMO_ARQUIVO_FILE, "w", encoding="utf-8") as f:
            f.write(arq)
    except Exception:
        pass


def _ler_ultimo_arquivo() -> str | None:
    try:
        if os.path.exists(_ULTIMO_ARQUIVO_FILE):
            with open(_ULTIMO_ARQUIVO_FILE, encoding="utf-8") as f:
                a = f.read().strip()
                ext = os.path.splitext(a)[1].lower()
                return a if os.path.isfile(a) and ext in IMAGENS_EXT else None
    except Exception:
        return None


# ── Helpers visuais ────────────────────────────────────────────────────────────

def _exibir_conteudo(validas: list, ignorados: list = []):
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column(style="marsala", no_wrap=True)
    table.add_column(style="creme")

    exts = {}
    for img in validas:
        ext = os.path.splitext(img)[1].upper()
        exts[ext] = exts.get(ext, 0) + 1
    ext_str = "  ".join(f"{e}:{n}" for e, n in exts.items())

    table.add_row("Imagens encontradas:", f"{len(validas)}   [{ext_str}]")
    if ignorados:
        table.add_row("Arquivos ignorados:", str(len(ignorados)))

    console.print(table)


# ── Fluxo de arquivo único ─────────────────────────────────────────────────────

def _selecionar_arquivo_unico() -> tuple[str, list]:
    """Pede caminho de um único arquivo de imagem."""
    ultimo = _ler_ultimo_arquivo()

    if ultimo:
        console.print(f"\n  [cinza]Ultimo arquivo:[/] [marsala]{ultimo}[/]")
        usar = questionary.confirm("Usar este arquivo?", default=True, style=QSTYLE).ask()
        if usar:
            ok(f"Arquivo: [marsala]{os.path.basename(ultimo)}[/]")
            _exibir_conteudo([ultimo])
            _salvar_ultimo_arquivo(ultimo)
            return os.path.dirname(ultimo), [ultimo]

    while True:
        caminho = questionary.path(
            "Caminho do arquivo de imagem:",
            style=QSTYLE,
        ).ask()

        if not caminho:
            erro("Nenhum arquivo informado.")
            continue

        caminho = os.path.normpath(caminho)

        if not os.path.isfile(caminho):
            erro(f"Arquivo nao encontrado: {caminho}")
            continue

        ext = os.path.splitext(caminho)[1].lower()
        if ext not in IMAGENS_EXT:
            erro(f"Formato nao suportado: {ext.upper()}. Use: {', '.join(e.upper() for e in IMAGENS_EXT)}")
            continue

        ok(f"Arquivo: [marsala]{os.path.basename(caminho)}[/]")
        _exibir_conteudo([caminho])
        _salvar_ultimo_arquivo(caminho)
        return os.path.dirname(caminho), [caminho]


# ── Fluxo de pasta ─────────────────────────────────────────────────────────────

def _selecionar_pasta() -> tuple[str, list]:
    """Pede caminho de pasta e lista todas as imagens dentro."""
    ultima = _ler_ultima_pasta()

    opcoes = ["Digitar caminho da pasta manualmente"]
    if ultima:
        opcoes.insert(0, f"Ultima pasta usada:  {ultima}")

    escolha = questionary.select(
        "Selecionar pasta:",
        choices=opcoes,
        style=QSTYLE,
    ).ask()

    if ultima and escolha.startswith("Ultima"):
        pasta = ultima
    else:
        while True:
            pasta = questionary.path(
                "Caminho da pasta:",
                only_directories=True,
                style=QSTYLE,
            ).ask()

            if not pasta:
                erro("Nenhuma pasta informada.")
                continue
            pasta = os.path.normpath(pasta)
            if os.path.isdir(pasta):
                break
            erro(f"Pasta nao encontrada: {pasta}")

    console.print()
    validas, ignorados = listar_imagens(pasta)

    if not validas:
        erro("Nenhuma imagem encontrada nesta pasta!")
        tentar = questionary.confirm("Escolher outra pasta?", default=True, style=QSTYLE).ask()
        if tentar:
            return _selecionar_pasta()
        raise SystemExit(0)

    ok(f"Pasta:  [marsala]{pasta}[/]")
    _exibir_conteudo(validas, ignorados)
    _salvar_ultima_pasta(pasta)

    return pasta, validas


# ── Tela principal ─────────────────────────────────────────────────────────────

def tela_pasta() -> tuple[str, list]:
    """
    Ponto de entrada da tela.
    Retorna (pasta_raiz, lista_de_imagens).
    """
    section("SELECAO DE ORIGEM")

    modo = questionary.select(
        "O que deseja enviar?",
        choices=[
            "Pasta inteira   (todas as fotos de uma pasta)",
            "Arquivo unico   (uma foto especifica)",
        ],
        style=QSTYLE,
    ).ask()

    console.print()

    if "unico" in modo:
        return _selecionar_arquivo_unico()
    else:
        return _selecionar_pasta()
