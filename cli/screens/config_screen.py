# cli/screens/config_screen.py — Configuração de álbum, licença e visibilidade

import questionary
from rich.table import Table
from rich.panel import Panel
from rich import box

from cli.utils import console, section
from core.auth import listar_albums

_M = "#9B2335"
_C = "#E8D5C4"

QSTYLE = questionary.Style([
    ("qmark",       f"fg:{_M} bold"),
    ("question",    f"fg:{_C} bold"),
    ("answer",      f"fg:{_M} bold"),
    ("pointer",     f"fg:{_M} bold"),
    ("highlighted", f"fg:{_M} bold"),
    ("selected",    f"fg:{_M}"),
])


def tela_config(session, total_fotos: int) -> dict:
    """
    Exibe tela de configuração e retorna dict com:
      album_id, novo_album, licenca, autor
    """
    section("CONFIGURAÇÕES DE ENVIO")

    # ── Álbum ──────────────────────────────────────────────
    console.print("\n  [label]── ÁLBUM ──[/]")
    albums = listar_albums(session)

    opcao_album = questionary.select(
        "Selecionar álbum:",
        choices=[
            "Sem álbum",
            "Álbum existente",
            "Criar novo álbum",
        ],
        style=QSTYLE,
    ).ask()

    album_id   = ""
    novo_album = ""

    if opcao_album == "Álbum existente":
        if albums:
            nomes = list(albums.keys())
            escolhido = questionary.select(
                "Escolha o álbum:",
                choices=nomes,
                style=QSTYLE,
            ).ask()
            album_id = albums[escolhido]
            novo_album = ""
        else:
            console.print("  [aviso]Nenhum álbum encontrado. Será criado um novo.[/]")
            novo_album = questionary.text("Nome do novo álbum:", style=QSTYLE).ask() or ""

    elif opcao_album == "Criar novo álbum":
        novo_album = questionary.text("Nome do novo álbum:", style=QSTYLE).ask() or ""

    # ── Licença ────────────────────────────────────────────
    console.print("\n  [label]── LICENÇA ──[/]")
    licenca_str = questionary.select(
        "Licença de uso:",
        choices=[
            "Apenas Visualização",
            "Creative Commons (CC BY)",
            "Creative Commons (CC BY-NC)",
        ],
        style=QSTYLE,
    ).ask()

    licenca_map = {
        "Apenas Visualização":        "visualizacao",
        "Creative Commons (CC BY)":   "cc_by",
        "Creative Commons (CC BY-NC)":"cc_by_nc",
    }
    licenca = licenca_map.get(licenca_str, "visualizacao")

    # ── Resumo ─────────────────────────────────────────────
    console.print()
    table = Table(box=box.SIMPLE_HEAVY, show_header=False,
                  border_style="marsala.dim", padding=(0, 2))
    table.add_column(style="label",  no_wrap=True, width=16)
    table.add_column(style="valor")

    album_label = (
        f"ID {album_id}" if album_id
        else (novo_album or "Sem álbum")
    )
    table.add_row("Álbum",    album_label)
    table.add_row("Licença",  licenca_str)
    table.add_row("Total",    f"{total_fotos} fotos")

    console.print(Panel(table, title="[marsala]RESUMO[/]",
                        border_style="marsala.dim", box=box.DOUBLE))

    confirmar = questionary.confirm(
        "Iniciar upload com essas configurações?",
        default=True,
        style=QSTYLE,
    ).ask()

    if not confirmar:
        raise SystemExit(0)

    return {
        "album_id":   album_id,
        "novo_album": novo_album,
        "licenca":    licenca,
        "autor":      "",
    }
