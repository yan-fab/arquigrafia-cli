# cli/screens/menu_screen.py — Tela de menu principal

import questionary
from cli.utils import console, banner, section
from cli.screens.login_screen import QSTYLE


def tela_menu(nome_usuario: str) -> str:
    """
    Exibe o menu principal após o login.
    Retorna a escolha do usuário: 'upload', 'organizar' ou 'sair'.
    """
    banner()
    console.print(f"  [cinza]Usuário:[/] [marsala]{nome_usuario}[/]\n")
    section("MENU PRINCIPAL")
    
    escolha = questionary.select(
        "Selecione a ação desejada:",
        choices=[
            {"name": "1. Fazer upload de novas fotos", "value": "upload"},
            {"name": "2. Organizar fotos sem álbum do perfil", "value": "organizar"},
            {"name": "3. Sair", "value": "sair"},
        ],
        style=QSTYLE,
    ).ask()
    
    return escolha
