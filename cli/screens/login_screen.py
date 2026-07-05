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
    Mostra a tela de login.
    Retorna (session, nome_usuario, email).
    """
    banner()
    section("AUTENTICAÇÃO")

    # Verifica credenciais salvas
    email_salvo, senha_salva = get_saved_credentials()

    if email_salvo and senha_salva:
        console.print(f"\n  [cinza]Conta salva detectada:[/] [marsala]{email_salvo}[/]")
        usar = questionary.confirm(
            "Usar conta salva?", default=True, style=QSTYLE
        ).ask()
        if usar:
            console.print("\n  [cinza]Conectando…[/]")
            session, nome = fazer_login(email_salvo, senha_salva)
            if session:
                ok(f"Conectado como: [marsala]{nome}[/]")
                return session, nome, email_salvo
            else:
                erro("Falha com credenciais salvas. Faça login novamente.")

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

        console.print("\n  [cinza]Conectando ao Arquigrafia…[/]")
        session, nome = fazer_login(email, senha)

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

            return session, nome, email
        else:
            erro("Login falhou. Verifique e-mail e senha.")
            tentar = questionary.confirm("Tentar novamente?", default=True, style=QSTYLE).ask()
            if not tentar:
                raise SystemExit(0)
