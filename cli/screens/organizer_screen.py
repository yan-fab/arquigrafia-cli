# cli/screens/organizer_screen.py — Tela e fluxo de organização inteligente e automática de coleções

import time
import requests
import questionary
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from cli.utils import console, banner, section, ok, erro, aviso, info
from cli.screens.login_screen import QSTYLE
from core.auth import listar_albums, criar_album
from core.scanner import (
    obter_fotos_em_albuns,
    obter_fotos_do_perfil,
    extrair_titulo_foto,
    extrair_localizacao_foto,
    associar_fotos_ao_album,
)


def _processar_lote_colecoes(
    session: requests.Session,
    albums: dict[str, str],
    grupos: dict[str, list[str]],
):
    """
    Cria automaticamente as coleções para cada grupo (ou reutiliza se já existirem)
    e associa as respectivas fotos via API REST.
    """
    total_grupos = len(grupos)
    total_fotos = sum(len(ids) for ids in grupos.values())
    
    console.print()
    section("PROCESSAMENTO AUTOMÁTICO DE COLEÇÕES")
    console.print(f"  [cinza]Total de coleções a processar:[/] [marsala]{total_grupos}[/]")
    console.print(f"  [cinza]Total de fotos a vincular:[/] [marsala]{total_fotos}[/]\n")

    relatorio = []

    with Progress(
        SpinnerColumn(style="marsala"),
        TextColumn("[marsala]{task.description}[/]"),
        BarColumn(bar_width=30, style="grey35", complete_style="bold #9B2335"),
        TextColumn("[cinza]{task.percentage:>3.0f}%[/]"),
        TextColumn("• {task.completed}/{task.total} coleções"),
        console=console,
    ) as progress:
        task_proc = progress.add_task("Organizando coleções…", total=total_grupos)

        for nome_grupo, photo_ids in grupos.items():
            progress.update(task_proc, description=f"[marsala]{nome_grupo[:32]}[/]")

            # 1. Verifica se já existe um álbum com esse nome
            album_id = None
            for alb_nome, aid in albums.items():
                if alb_nome.strip().lower() == nome_grupo.strip().lower():
                    album_id = aid
                    break

            foi_criado = False
            if not album_id:
                descricao = f"Coleção de imagens de {nome_grupo} no Arquigrafia."
                album_id = criar_album(session, nome_grupo, descricao=descricao)
                if album_id:
                    albums[nome_grupo] = album_id
                    foi_criado = True
                else:
                    relatorio.append({
                        "nome": nome_grupo,
                        "status": "Falha na criação",
                        "total": len(photo_ids),
                        "id": None,
                        "url": "—",
                    })
                    progress.advance(task_proc, 1)
                    continue

            # 2. Associa as fotos ao álbum
            sucesso_assoc = associar_fotos_ao_album(session, album_id, photo_ids)

            status_txt = "Criada e vinculada" if foi_criado else "Vinculada a existente"
            if not sucesso_assoc:
                status_txt += " (Aviso no lote)"

            relatorio.append({
                "nome": nome_grupo,
                "status": status_txt,
                "total": len(photo_ids),
                "id": album_id,
                "url": f"https://arquigrafia.org.br/colecoes/{album_id}",
            })

            progress.advance(task_proc, 1)
            time.sleep(0.1)

    # 3. Tabela final com resumo das coleções criadas
    console.print()
    section("RELATÓRIO DE CRIAÇÃO DE COLEÇÕES")

    tabela = Table(box=box.SIMPLE_HEAVY, border_style="marsala.dim", padding=(0, 1))
    tabela.add_column("Coleção", style="label")
    tabela.add_column("Status", style="cinza")
    tabela.add_column("Fotos", style="marsala", justify="right")
    tabela.add_column("Link no Arquigrafia", style="valor")

    sucessos = 0
    fotos_vinculadas = 0
    for r in relatorio:
        if r["id"]:
            sucessos += 1
            fotos_vinculadas += r["total"]
            tabela.add_row(
                r["nome"][:35],
                f"[green]{r['status']}[/]",
                str(r["total"]),
                r["url"],
            )
        else:
            tabela.add_row(
                r["nome"][:35],
                f"[erro]{r['status']}[/]",
                str(r["total"]),
                "—",
            )

    console.print(tabela)
    console.print()
    ok(f"Processamento concluído! {sucessos} coleções organizadas com {fotos_vinculadas} fotos.")


def tela_organizacao(session: requests.Session, user_id: str):
    """Gerencia toda a interface visual de varredura e organização das fotos via API REST."""
    banner()
    section("ORGANIZAÇÃO INTELIGENTE DE COLEÇÕES")
    console.print()

    # 1. Carrega álbuns do usuário e fotos organizadas
    with Progress(
        SpinnerColumn(),
        TextColumn("[marsala]{task.description}[/]"),
        console=console,
        transient=True,
    ) as progress:
        task_info = progress.add_task("Consultando coleções existentes na API…", total=None)
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

    info(f"Total de {len(todas_fotos)} fotos no perfil | {len(albums)} coleções cadastradas.")

    # 2. Identifica fotos sem álbum
    fotos_sem_album = [f for f in todas_fotos if f.get("id") and f.get("id") not in fotos_organizadas]

    if not fotos_sem_album:
        console.print()
        ok("Todas as fotos do seu perfil já estão organizadas em coleções! 🎉")
        input("\nPressione ENTER para voltar ao menu principal…")
        return

    info(f"Encontradas [marsala]{len(fotos_sem_album)} fotos[/] que ainda não pertencem a nenhuma coleção.\n")

    # 3. Pergunta o critério de agrupamento para formar as coleções
    criterio = questionary.select(
        "Como deseja agrupar as fotos para formar as coleções?",
        choices=[
            {
                "name": "🏷️  Por Título / Nome da Obra (Recomendado — ex: 'Sala São Paulo', 'DOPS', 'Residência...')",
                "value": "titulo",
            },
            {
                "name": "📍  Por Localização / Endereço (ex: 'São Paulo - SP', 'Paraty - RJ')",
                "value": "localizacao",
            },
        ],
        style=QSTYLE,
    ).ask()

    if not criterio:
        return

    # Agrupa fotos de acordo com a escolha
    agrupamento: dict[str, list[str]] = {}
    for f in fotos_sem_album:
        fid = f.get("id")
        if not fid:
            continue
        if criterio == "titulo":
            chave = extrair_titulo_foto(f)
        else:
            chave = extrair_localizacao_foto(f)

        chave = (chave or "Sem Identificação").strip()
        agrupamento.setdefault(chave, []).append(fid)

    # Ordena grupos por quantidade decrescente de fotos
    agrupamento = dict(sorted(agrupamento.items(), key=lambda item: len(item[1]), reverse=True))

    # 4. Exibe tabela com o panorama geral dos grupos encontrados
    console.print()
    section("PANORAMA DE GRUPOS IDENTIFICADOS")
    console.print(f"  [cinza]Grupos formados:[/] [marsala]{len(agrupamento)}[/]\n")

    tabela = Table(box=box.SIMPLE_HEAVY, border_style="marsala.dim", padding=(0, 2))
    tabela.add_column("Grupo / Sugestão de Coleção", style="label")
    tabela.add_column("Fotos", style="marsala", justify="right")
    tabela.add_column("Status no Perfil", style="cinza")

    for nome_g, ids in agrupamento.items():
        ja_existe = any(nome_g.strip().lower() == k.strip().lower() for k in albums.keys())
        status_str = "[green]✓ Álbum já existente[/]" if ja_existe else "[yellow]+ Novo álbum a criar[/]"
        tabela.add_row(nome_g[:40], str(len(ids)), status_str)

    console.print(tabela)
    console.print()

    # 5. Menu principal de ações de organização
    section("OPÇÕES DE ORGANIZAÇÃO")
    escolha_acao = questionary.select(
        "Como deseja proceder com a criação e organização das coleções?",
        choices=[
            {
                "name": "⚡ Criar automaticamente todas as coleções e vincular fotos (Modo Automático)",
                "value": "auto_todos",
            },
            {
                "name": "🎯 Selecionar quais coleções criar automaticamente (Modo Seleção)",
                "value": "auto_selecao",
            },
            {
                "name": "🖐️  Modo Interativo (revisar e escolher grupo a grupo manualmente)",
                "value": "interativo",
            },
            {
                "name": "↩️  Voltar ao menu principal",
                "value": "voltar",
            },
        ],
        style=QSTYLE,
    ).ask()

    if not escolha_acao or escolha_acao == "voltar":
        return

    # -------------------------------------------------------------
    # Opção A: Criação Automática de Todos os Grupos
    # -------------------------------------------------------------
    if escolha_acao == "auto_todos":
        filtro = questionary.select(
            "Quais grupos de fotos deseja incluir no processo automático?",
            choices=[
                {
                    "name": f"1. Todos os grupos ({len(agrupamento)} coleções / {len(fotos_sem_album)} fotos)",
                    "value": 1,
                },
                {
                    "name": f"2. Apenas grupos com 2 ou mais fotos ({len([g for g, ids in agrupamento.items() if len(ids) >= 2])} coleções)",
                    "value": 2,
                },
                {
                    "name": f"3. Apenas grupos com 3 ou mais fotos ({len([g for g, ids in agrupamento.items() if len(ids) >= 3])} coleções)",
                    "value": 3,
                },
            ],
            style=QSTYLE,
        ).ask()

        if not filtro:
            return

        limite = int(filtro)
        grupos_filtrados = {g: ids for g, ids in agrupamento.items() if len(ids) >= limite}

        if not grupos_filtrados:
            aviso("Nenhum grupo atende ao critério de quantidade mínima.")
            input("\nPressione ENTER para voltar ao menu principal…")
            return

        confirma = questionary.confirm(
            f"Deseja iniciar a criação automática de {len(grupos_filtrados)} coleções agora?",
            default=True,
            style=QSTYLE,
        ).ask()

        if confirma:
            _processar_lote_colecoes(session, albums, grupos_filtrados)
        else:
            aviso("Operação cancelada pelo usuário.")

    # -------------------------------------------------------------
    # Opção B: Seleção Específica de Grupos para Criação Automática
    # -------------------------------------------------------------
    elif escolha_acao == "auto_selecao":
        opcoes_check = []
        for g, ids in agrupamento.items():
            ja_existe = any(g.strip().lower() == k.strip().lower() for k in albums.keys())
            tag = "[Álbum Existente]" if ja_existe else "[Novo]"
            opcoes_check.append({
                "name": f"{g[:35]} ({len(ids)} fotos) {tag}",
                "value": g,
                "checked": True,
            })

        selecionados = questionary.checkbox(
            "Marque as coleções que deseja criar/vincular automaticamente (barra de espaço para marcar/desmarcar):",
            choices=opcoes_check,
            style=QSTYLE,
        ).ask()

        if not selecionados:
            aviso("Nenhuma coleção foi selecionada.")
            input("\nPressione ENTER para voltar…")
            return

        grupos_selecionados = {g: agrupamento[g] for g in selecionados}
        _processar_lote_colecoes(session, albums, grupos_selecionados)

    # -------------------------------------------------------------
    # Opção C: Modo Interativo Passo a Passo
    # -------------------------------------------------------------
    elif escolha_acao == "interativo":
        for nome_g, ids in agrupamento.items():
            console.print(f"\n  [marsala.dim]──────────────────────────────────────────────────[/]")
            info(f"Grupo: [label]{nome_g}[/] — [marsala]{len(ids)} fotos[/] sem coleção.")

            aid_existente = None
            for alb_nome, aid in albums.items():
                if alb_nome.strip().lower() == nome_g.strip().lower():
                    aid_existente = aid
                    break

            choices = []
            if aid_existente:
                choices.append({
                    "name": f"✨ Vincular fotos ao álbum existente '{nome_g}'",
                    "value": f"existente:{aid_existente}",
                })
            else:
                choices.append({
                    "name": f"✨ Criar automaticamente nova coleção '{nome_g}'",
                    "value": f"auto_criar:{nome_g}",
                })

            choices.append({
                "name": "📝 Digitar outro nome para nova coleção…",
                "value": "custom",
            })

            # Lista álbuns existentes do perfil
            for aname, aid in albums.items():
                if aid != aid_existente:
                    choices.append({"name": f"📁 Álbum existente: {aname}", "value": f"existente:{aid}"})

            choices.append({"name": "⏭️  [ Pular este grupo ]", "value": "pular"})

            escolha = questionary.select(
                "O que deseja fazer com as fotos deste grupo?",
                choices=choices,
                style=QSTYLE,
            ).ask()

            if not escolha or escolha == "pular":
                aviso(f"Grupo '{nome_g}' pulado.")
                continue

            target_aid = None
            nome_final_album = nome_g

            if escolha.startswith("auto_criar:"):
                console.print(f"  [cinza]Criando nova coleção:[/] [marsala]{nome_g}[/]")
                target_aid = criar_album(session, nome_g, f"Coleção de imagens de {nome_g}.")
                if target_aid:
                    albums[nome_g] = target_aid
                    ok(f"Coleção criada com sucesso! ID: {target_aid}")
                else:
                    erro(f"Falha ao criar coleção '{nome_g}'.")
                    continue

            elif escolha == "custom":
                custom_nome = questionary.text(
                    "Digite o nome da nova coleção:",
                    default=nome_g,
                    style=QSTYLE,
                ).ask()
                if not custom_nome or not custom_nome.strip():
                    aviso("Nome inválido. Grupo pulado.")
                    continue
                custom_nome = custom_nome.strip()
                nome_final_album = custom_nome
                target_aid = criar_album(session, custom_nome, f"Coleção de imagens de {custom_nome}.")
                if target_aid:
                    albums[custom_nome] = target_aid
                    ok(f"Coleção '{custom_nome}' criada com sucesso!")
                else:
                    erro(f"Falha ao criar coleção '{custom_nome}'.")
                    continue

            elif escolha.startswith("existente:"):
                target_aid = escolha.split(":", 1)[1]
                nome_final_album = [k for k, v in albums.items() if v == target_aid][0]

            if target_aid:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[marsala]Vinculando fotos à coleção na API…[/]"),
                    console=console,
                    transient=True,
                ) as progress:
                    task_assoc = progress.add_task("Vinculando…", total=None)
                    ok_assoc = associar_fotos_ao_album(session, target_aid, ids)

                if ok_assoc:
                    ok(f"Todas as {len(ids)} fotos foram vinculadas à coleção '{nome_final_album}'!")
                else:
                    aviso(f"Aviso ao vincular fotos à coleção '{nome_final_album}'.")

        ok("Organização passo a passo finalizada!")

    input("\nPressione ENTER para retornar ao menu principal…")
