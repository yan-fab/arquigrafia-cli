# cli/screens/menu_screen.py — Tela de menu principal com dashboard de status

import questionary
from rich.table import Table
from rich.panel import Panel
from rich import box
from cli.utils import console, banner, section
from cli.screens.login_screen import QSTYLE


def tela_menu(nome_usuario: str) -> str:
    """
    Exibe o menu principal com dashboard de status e opções avançadas.
    Retorna a escolha do usuário: 'upload', 'organizar', 'auditar_loc' ou 'sair'.
    """
    banner()

    # Dashboard visual de status do perfil e sistema
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    card_perfil = Panel(
        f"[label]👤 Usuário Ativo:[/] [bold marsala]{nome_usuario}[/]\n"
        f"[label]🌐 Servidor:[/] [cinza]api.arquigrafia.org.br[/] [green]● Conectado[/]",
        title="[bold marsala.dim]PERFIL ARQUIGRAFIA[/]",
        border_style="marsala.dim",
        box=box.ROUNDED,
    )

    card_status = Panel(
        f"[label]⚡ IA BLIP:[/] [cinza]Tags Arquitetônicas VCAA USP[/]\n"
        f"[label]📁 Coleções:[/] [cinza]Criação Automática em Lote Ativa[/]",
        title="[bold marsala.dim]MÓDULOS DO SISTEMA[/]",
        border_style="marsala.dim",
        box=box.ROUNDED,
    )

    grid.add_row(card_perfil, card_status)
    console.print(grid)
    console.print()

    section("PAINEL DE CONTROLE")

    escolha = questionary.select(
        "Selecione a ação desejada:",
        choices=[
            {
                "name": "📤  1. Fazer upload de novas fotos             [IA BLIP + Tags VCAA + GPS]",
                "value": "upload",
            },
            {
                "name": "🗂️   2. Organizar fotos em coleções             [Criação Automática em Lote]",
                "value": "organizar",
            },
            {
                "name": "📍  3. Auditar e atualizar localização no mapa  [GPS EXIF + Dados Internos]",
                "value": "auditar_loc",
            },
            {
                "name": "🚪  4. Encerrar sessão e sair",
                "value": "sair",
            },
        ],
        style=QSTYLE,
    ).ask()

    return escolha
