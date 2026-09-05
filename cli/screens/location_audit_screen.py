# cli/screens/location_audit_screen.py — Tela de auditoria e geolocalização do acervo

import os
import time
import questionary
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich import box

from cli.utils import console, banner, section, ok, erro, aviso, info
from cli.screens.login_screen import QSTYLE
from core.location_auditor import auditar_e_atualizar_acervo


def tela_auditoria_localizacao(session, user_id: str):
    """
    Exibe a interface interativa de auditoria e atualização em lote da localização
    das fotos do usuário no Arquigrafia.
    """
    banner()
    section("AUDITORIA E ATUALIZAÇÃO DE LOCALIZAÇÃO")

    console.print(
        "  [creme]Esta ferramenta audita todas as fotos do seu perfil no Arquigrafia.[/]\n"
        "  [creme]Para cada foto sem mapa cadastrado, o sistema extrai dados internos[/]\n"
        "  [creme](EXIF GPS de arquivos locais ou endereços descritos) e atualiza na nova API.[/]\n"
    )

    escolha = questionary.select(
        "Como deseja auditar a localização das imagens?",
        choices=[
            {
                "name": "1. Auditar na nuvem via metadados internos (Títulos, Descrições e OpenStreetMap)",
                "value": "nuvem"
            },
            {
                "name": "2. Auditar cruzando com pasta local de fotos (Lê EXIF GPS original dos arquivos)",
                "value": "local"
            },
            {
                "name": "3. Voltar ao Menu Principal",
                "value": "voltar"
            }
        ],
        style=QSTYLE,
    ).ask()

    if not escolha or escolha == "voltar":
        return

    pasta_local = None
    if escolha == "local":
        while True:
            caminho_input = questionary.text(
                "Informe o caminho completo da pasta com as fotos originais:",
                style=QSTYLE
            ).ask()

            if not caminho_input:
                return

            caminho_input = caminho_input.strip('"\' ')
            if os.path.isdir(caminho_input):
                pasta_local = caminho_input
                break
            else:
                erro(f"A pasta '{caminho_input}' não existe. Tente novamente.")

    console.print()
    confirma = questionary.confirm(
        "Deseja iniciar a varredura e atualização de localização agora?",
        default=True,
        style=QSTYLE
    ).ask()

    if not confirma:
        aviso("Auditoria cancelada pelo usuário.")
        time.sleep(1.5)
        return

    console.print()
    section("PROCESSANDO AUDITORIA")
    console.print()

    # Tabela de resultados ao vivo
    tabela = Table(box=box.SIMPLE_HEAVY, border_style="marsala.dim", padding=(0, 1))
    tabela.add_column("Foto / Título", style="creme", width=34, overflow="ellipsis")
    tabela.add_column("Método", style="cinza", width=14)
    tabela.add_column("Coordenadas / Local", style="valor", width=36, overflow="ellipsis")
    tabela.add_column("Status", style="label", width=12, justify="center")

    with Progress(
        SpinnerColumn(style="marsala"),
        TextColumn("[marsala]{task.description}[/]"),
        BarColumn(style="color(52)", complete_style="marsala", finished_style="marsala"),
        MofNCompleteColumn(),
        console=console,
        transient=False,
    ) as progress:
        task_busca = progress.add_task("Buscando fotos no perfil do Arquigrafia…", total=None)

        task_processo = None

        def callback_progresso(info_evt):
            nonlocal task_processo
            etapa = info_evt.get("etapa")
            msg = info_evt.get("msg", "")

            if etapa == "buscando_fotos":
                progress.update(task_busca, description=f"[cinza]{msg}[/]")
            elif etapa == "iniciando_auditoria":
                tot = info_evt.get("total", 0)
                progress.update(task_busca, visible=False)
                task_processo = progress.add_task("Atualizando localizações…", total=tot)
            elif etapa == "processando_item":
                if task_processo is not None:
                    idx = info_evt.get("indice", 0)
                    progress.update(
                        task_processo,
                        completed=idx,
                        description=f"[marsala]Auditando:[/] [creme]{info_evt.get('titulo', '')[:25]}[/]"
                    )

        stats = auditar_e_atualizar_acervo(
            session=session,
            user_id=user_id,
            pasta_local=pasta_local,
            callback_progresso=callback_progresso
        )

    # Preenche tabela com as atualizações
    detalhes = stats.get("detalhes", [])
    if detalhes:
        console.print()
        section("RESULTADOS DA AUDITORIA")
        for item in detalhes:
            st = item["status"]
            if st == "sucesso":
                status_str = "[ok]✔ Atualizado[/]"
            elif st == "nao_encontrado":
                status_str = "[cinza]— Sem dados[/]"
            else:
                status_str = "[erro]✘ Erro[/]"

            coords_str = f"{item.get('lat', '')}, {item.get('lon', '')}" if item.get("lat") else "—"
            if item.get("label"):
                coords_str = f"{item['label'][:22]} ({coords_str})"

            metodo_str = "EXIF Local" if item.get("metodo") == "exif_local" else ("Texto/OSM" if item.get("metodo") == "texto_interno" else "—")
            tabela.add_row(item["titulo"], metodo_str, coords_str, status_str)

        console.print(tabela)

    # Resumo Final
    console.print()
    resumo_table = Table(box=box.SIMPLE_HEAVY, show_header=False, border_style="marsala.dim", padding=(0, 2))
    resumo_table.add_column(style="label", width=26)
    resumo_table.add_column(style="valor")

    resumo_table.add_row("Total de fotos no acervo", str(stats["total_fotos"]))
    resumo_table.add_row("Fotos já geolocalizadas", str(stats["ja_localizadas"]))
    resumo_table.add_row("Fotos auditadas (sem local)", str(stats["sem_localizacao"]))
    resumo_table.add_row("✔ Atualizadas via EXIF GPS", str(stats["atualizadas_exif"]))
    resumo_table.add_row("✔ Atualizadas via Texto/OSM", str(stats["atualizadas_texto"]))
    resumo_table.add_row("✘ Não localizadas / Falhas", str(stats["falhas"]))

    console.print(Panel(resumo_table, title="[marsala]RESUMO DA AUDITORIA[/]", border_style="marsala.dim", box=box.DOUBLE))
    console.print()
    ok("Auditoria de localização finalizada!")
    console.print("  [cinza]Pressione ENTER para voltar ao menu principal…[/]")
    input()
