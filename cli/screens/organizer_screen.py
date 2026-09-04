# cli/screens/organizer_screen.py — Tela e fluxo de organização interativa de fotos

import questionary
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from cli.utils import console, banner, section, ok, erro, aviso, info
from cli.screens.login_screen import QSTYLE
from core.auth import listar_albums
from core.scanner import (
    obter_fotos_em_albuns,
    obter_fotos_do_perfil,
    extrair_localizacao_foto,
    associar_fotos_ao_album,
)
import time
import requests


def tela_organizacao(session: requests.Session, user_id: str):
    """Gerencia toda a interface visual de varredura e organização das fotos via API REST."""
    banner()
    section("ORGANIZAÇÃO DE FOTOS DO PERFIL")
    console.print()

    # 1. Carrega álbuns do usuário e fotos organizadas
    with Progress(
        SpinnerColumn(),
        TextColumn("[marsala]{task.description}[/]"),
        console=console,
        transient=True,
    ) as progress:
        task_info = progress.add_task("Consultando coleções e álbuns na API…", total=None)
        try:
            albums = listar_albums(session, user_id)
            fotos_organizadas = obter_fotos_em_albuns(session, user_id)
        except Exception as e:
            erro(f"Erro ao ler álbuns: {e}")
            time.sleep(3)
            return

        progress.update(task_info, description="Buscando fotos cadastradas no seu perfil…")
        def cb_fetch(msg):
            progress.update(task_info, description=msg)
        todas_fotos = obter_fotos_do_perfil(session, user_id, callback_progresso=cb_fetch)

    if not todas_fotos:
        aviso("Nenhuma foto encontrada no seu perfil do Arquigrafia.")
        input("\nPressione ENTER para voltar ao menu principal…")
        return

    info(f"Total de {len(todas_fotos)} fotos encontradas no perfil.")
    info("Identificando fotos sem álbum e agrupando por localização…")
    console.print()

    # 2. Identifica fotos sem álbum e agrupa por localização
    fotos_sem_album = []
    agrupamento = {}  # localizacao -> list de photo_ids

    with Progress(
        TextColumn("[marsala]Progresso:[/]"),
        BarColumn(bar_width=30, style="grey35", complete_style="bold #9B2335"),
        TextColumn("[cinza]{task.percentage:>3.0f}%[/]"),
        TextColumn("• {task.completed}/{task.total} fotos"),
        console=console,
    ) as progress:
        task_scan = progress.add_task("Agrupando…", total=len(todas_fotos))

        for f in todas_fotos:
            pid = f.get("id")
            if pid and pid not in fotos_organizadas:
                fotos_sem_album.append(f)
                local = extrair_localizacao_foto(f)
                if local not in agrupamento:
                    agrupamento[local] = []
                agrupamento[local].append(pid)

            progress.advance(task_scan, 1)

    console.print()
    section("VARREDURA CONCLUÍDA")

    if not fotos_sem_album:
        ok("Todas as fotos do seu perfil já estão organizadas em álbuns! 🎉")
        input("\nPressione ENTER para voltar ao menu principal…")
        return

    # 3. Exibe tabela com resumo das localizações
    console.print(f"  [cinza]Fotos sem álbum encontradas:[/] [marsala]{len(fotos_sem_album)}[/]\n")

    tabela = Table(border_style="marsala.dim", box=None, padding=(0, 2))
    tabela.add_column("Localização", style="label")
    tabela.add_column("Fotos Sem Álbum", style="marsala", justify="right")

    for local, ids in agrupamento.items():
        tabela.add_row(local, str(len(ids)))

    console.print(tabela)
    console.print()

    # 4. Interação para cada grupo de localização
    for local, ids in agrupamento.items():
        console.print(f"\n  [marsala.dim]──────────────────────────────────────────────────[/]")
        info(f"Localização: [label]{local}[/] — [marsala]{len(ids)} fotos[/] sem álbum.")

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

        nome_album = [k for k, v in albums.items() if v == escolha][0]
        console.print(f"  [cinza]Associando {len(ids)} fotos ao álbum:[/] [marsala]{nome_album}[/]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[marsala]Enviando lote para a API REST…[/]"),
            console=console,
            transient=True,
        ) as progress:
            task_assoc = progress.add_task("Associando…", total=None)
            # Associação direta via REST em lote (blocos de até 50 fotos)
            chunk_size = 50
            sucesso_total = True
            for i in range(0, len(ids), chunk_size):
                sub_lote = ids[i:i + chunk_size]
                ok_assoc = associar_fotos_ao_album(session, escolha, sub_lote)
                if not ok_assoc:
                    sucesso_total = False

        if sucesso_total:
            ok(f"Todas as {len(ids)} fotos foram adicionadas ao álbum '{nome_album}' com sucesso!")
        else:
            aviso(f"Algumas fotos do grupo '{local}' podem não ter sido associadas. Verifique na plataforma.")

    ok("Organização concluída!")
    input("\nPressione ENTER para retornar ao menu principal…")
