# cli/screens/organizer_screen.py — Tela e fluxo de organização interativa de fotos

import questionary
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from cli.utils import console, banner, section, ok, erro, aviso, info
from cli.screens.login_screen import QSTYLE
from core.auth import listar_albums
from core.scanner import (
    obter_fotos_do_perfil,
    verificar_foto_sem_album,
    obter_localizacao_foto,
    associar_foto_ao_album,
)
import time
import requests


def tela_organizacao(session: requests.Session, user_id: str):
    """Gerencia toda a interface visual de varredura e organização das fotos."""
    banner()
    section("ORGANIZAÇÃO DE FOTOS DO PERFIL")
    console.print()

    # 1. Carrega álbuns do usuário e fotos
    with Progress(
        SpinnerColumn(),
        TextColumn("[marsala]{task.description}[/]"),
        console=console,
        transient=True,
    ) as progress:
        task_info = progress.add_task("Obtendo lista de álbuns do perfil…", total=None)
        try:
            albums = listar_albums(session)
            total_albums = len(albums)
        except Exception as e:
            erro(f"Erro ao ler álbuns: {e}")
            time.sleep(3)
            return

        progress.update(task_info, description="Obtendo listagem de fotos do perfil…")
        photo_ids = obter_fotos_do_perfil(session, user_id)

    if not photo_ids:
        aviso("Nenhuma foto encontrada no seu perfil do Arquigrafia.")
        input("\nPressione ENTER para voltar ao menu principal…")
        return

    info(f"Total de {len(photo_ids)} fotos encontradas no perfil.")
    info("Iniciando varredura para identificar fotos sem álbum e localizações…")
    console.print()

    fotos_sem_album = []
    agrupamento = {}  # localizacao -> list de photo_ids

    # 2. Varredura com barra Flow
    with Progress(
        TextColumn("[marsala]Progresso:[/]"),
        BarColumn(bar_width=30, style="grey35", complete_style="bold #9B2335"),
        TextColumn("[cinza]{task.percentage:>3.0f}%[/]"),
        TextColumn("• {task.completed}/{task.total} fotos"),
        console=console,
    ) as progress:
        task_scan = progress.add_task("Varrendo…", total=len(photo_ids))

        for pid in photo_ids:
            progress.update(task_scan, description=f"Analisando foto #{pid}…")
            
            # Verifica se está sem álbum
            sem_album = verificar_foto_sem_album(session, pid, total_albums)
            if sem_album:
                fotos_sem_album.append(pid)
                loc = obter_localizacao_foto(session, pid)
                if loc not in agrupamento:
                    agrupamento[loc] = []
                agrupamento[loc].append(pid)
                
            progress.advance(task_scan, 1)

    console.print()
    section("VARREDURA CONCLUÍDA")

    if not fotos_sem_album:
        ok("Todas as fotos do seu perfil já estão organizadas em álbuns! 🎉")
        input("\nPressione ENTER para voltar ao menu principal…")
        return

    # 3. Exibe tabela com resumo
    console.print(f"  [cinza]Fotos sem álbum encontradas:[/] [marsala]{len(fotos_sem_album)}[/]\n")

    tabela = Table(border_style="marsala.dim", box=None, padding=(0, 2))
    tabela.add_column("Localização", style="creme bold")
    tabela.add_column("Fotos Sem Álbum", style="marsala bold", justify="right")

    for local, ids in agrupamento.items():
        tabela.add_row(local, str(len(ids)))

    console.print(tabela)
    console.print()

    # 4. Interação para cada grupo de localização
    for local, ids in agrupamento.items():
        console.print(f"\n  [marsala.dim]──────────────────────────────────────────────────[/]")
        info(f"Localização: [creme bold]{local}[/] — [marsala]{len(ids)} fotos[/] sem álbum.")

        # Opções do menu: álbuns existentes + pular
        choices = [{"name": name, "value": aid} for name, aid in albums.items()]
        choices.append({"name": "[ Pular esta localização ]", "value": "pular"})

        escolha = questionary.select(
            "Em qual álbum existente deseja adicionar estas fotos?",
            choices=choices,
            style=QSTYLE,
        ).ask()

        if escolha == "pular" or not escolha:
            aviso(f"Grupo '{local}' pulado.")
            continue

        # Realiza a associação com barra de progresso rápida
        nome_album = [k for k, v in albums.items() if v == escolha][0]
        console.print(f"  [cinza]Associando fotos ao álbum:[/] [marsala]{nome_album}[/]")

        sucessos = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[marsala]Associando: {task.description}[/]"),
            console=console,
            transient=True,
        ) as progress:
            task_assoc = progress.add_task(f"0/{len(ids)}", total=len(ids))
            for i, pid in enumerate(ids, 1):
                progress.update(task_assoc, description=f"{i}/{len(ids)} (Foto #{pid})")
                ok_assoc = associar_foto_ao_album(session, pid, escolha)
                if ok_assoc:
                    sucessos += 1
                time.sleep(0.5)  # Evita sobrecarregar o servidor
                progress.advance(task_assoc, 1)

        if sucessos == len(ids):
            ok(f"Todas as {len(ids)} fotos foram adicionadas ao álbum '{nome_album}' com sucesso!")
        else:
            aviso(f"{sucessos} de {len(ids)} fotos adicionadas ao álbum '{nome_album}'.")

    ok("Organização concluída!")
    input("\nPressione ENTER para retornar ao menu principal…")
