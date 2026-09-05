# cli/screens/login_screen.py — Tela de login interativa

import questionary
from rich.panel import Panel
from rich import box

from cli.utils import console, banner, section, ok, erro
from core.auth import fazer_login, get_saved_credentials, save_credentials

# Hex marsala para prompt_toolkit (questionary não aceita color(N) do rich)
_M = "#9B2335"  # marsala bright
_C = "#E8D5C4"  # creme

QSTYLE = questionary.Style([
    ("qmark",        f"fg:{_M} bold"),
    ("question",     f"fg:{_C} bold"),
    ("answer",       f"fg:{_M} bold"),
    ("pointer",      f"fg:{_M} bold"),
    ("highlighted",  f"fg:{_M} bold"),
    ("selected",     f"fg:{_M}"),
    ("separator",    f"fg:{_M}"),
    ("instruction",  "fg:gray"),
])


def tela_login() -> tuple:
    """
    Mostra a tela de login inicial.
    Retorna (session, nome_usuario, email, user_id).
    """
    banner()

    console.print(Panel(
        "[creme]Bem-vindo ao cliente oficial do [bold marsala]Arquigrafia[/].\n"
        "Envie fotos com identificação por IA, audite localizações e organize coleções automaticamente.[/]",
        title="[bold #E8D5C4]◆ ACESSO À PLATAFORMA ◆[/]",
        border_style="#9B2335",
        box=box.ROUNDED,
        padding=(0, 1),
    ))
    console.print()
    section("AUTENTICAÇÃO")

    # Verifica credenciais salvas
    email_salvo, senha_salva = get_saved_credentials()

    if email_salvo and senha_salva:
        console.print()
        console.print(Panel(
            f"  [label]Conta Salva:[/] [bold marsala]{email_salvo}[/]\n"
            f"  [cinza]Sessão pronta para autenticação rápida via API REST.[/]",
            title="[bold marsala.dim]CONTA DETECTADA[/]",
            border_style="marsala.dim",
            box=box.ROUNDED,
            padding=(0, 1),
        ))
        console.print()
        usar = questionary.confirm(
            "Deseja entrar com esta conta salva?", default=True, style=QSTYLE
        ).ask()
        if usar:
            session, nome, user_id = fazer_login(email_salvo, senha_salva)
            if session:
                ok(f"Autenticação bem-sucedida! Bem-vindo, [marsala]{nome}[/]")
                return session, nome, email_salvo, user_id
            else:
                erro(f"Falha ao conectar: {nome or 'Credenciais inválidas'}")
                console.print("  [cinza]Faça login novamente com sua senha atualizada.[/]")

    # Login manual
    while True:
        console.print()
        email = questionary.text(
            "E-mail:",
            default=email_salvo or "",
            style=QSTYLE,
        ).ask()

        senha = questionary.password(
            "Senha:",
            style=QSTYLE,
        ).ask()

        if not email or not senha:
            erro("E-mail e senha são obrigatórios.")
            continue

        console.print("\n  [cinza]Conectando à API REST do Arquigrafia…[/]")
        session, nome, user_id = fazer_login(email, senha)

        if session:
            ok(f"Conectado como: [marsala]{nome}[/]")

            salvar = questionary.confirm(
                "Salvar credenciais para próximas sessões?",
                default=True,
                style=QSTYLE,
            ).ask()
            if salvar:
                save_credentials(email, senha)
                ok("Credenciais salvas com segurança.")

            return session, nome, email, user_id
        else:
            erro(f"Login falhou: {nome or 'Verifique e-mail e senha'}")
            tentar = questionary.confirm("Tentar novamente?", default=True, style=QSTYLE).ask()
            if not tentar:
                raise SystemExit(0)
