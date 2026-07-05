# main.py — Orquestrador principal do Arquigrafia Uploader CLI

import sys
import os
import time
import csv
import logging
import traceback
from datetime import datetime

# Log em arquivo — sempre na mesma pasta do .exe
_EXE_DIR = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
_LOG_FILE = os.path.join(_EXE_DIR, "upload.log")
logging.basicConfig(
    filename=_LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
    force=True,
)

# Garante que o diretório do projeto está no path (necessário para o .exe)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.progress import (
    Progress, BarColumn, TextColumn, TimeElapsedColumn,
    TimeRemainingColumn, SpinnerColumn, MofNCompleteColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.live import Live
from rich.text import Text
from rich.columns import Columns

from cli.utils import console, banner, section, ok, erro, aviso, info, THEME
from cli.screens.login_screen  import tela_login
from cli.screens.folder_screen import tela_pasta
from cli.screens.config_screen import tela_config
from core.uploader             import enviar_foto
from core.ia                   import carregar_ia


# ──────────────────────────────────────────────────────────────────
# Barra de progresso estilo Flow: blocos gradiente com KB/s e ETA
# ──────────────────────────────────────────────────────────────────
class FlowBarColumn(BarColumn):
    """Barra customizada com blocos █▓▒░ ao estilo Flow TUI."""

    CHARS_FULL  = "█"
    CHARS_FADE  = ["▓", "▒", "░"]

    def render(self, task):
        completed  = task.completed
        total      = task.total or 1
        width      = self.bar_width or 30
        ratio      = min(completed / total, 1.0)
        filled     = int(width * ratio)
        remaining  = width - filled - 1

        bar = Text()
        bar.append("█" * filled,            style="marsala")
        if filled < width:
            bar.append("▓",                 style="marsala.dim")
            fade = min(2, remaining)
            bar.append("▒" * fade,          style="color(52)")
            bar.append("░" * max(remaining - fade, 0), style="color(52)")
        return bar


def _montar_progresso():
    return Progress(
        SpinnerColumn(style="marsala"),
        TextColumn("[marsala]{task.description}[/]"),
        FlowBarColumn(bar_width=32),
        MofNCompleteColumn(),
        TextColumn("[cinza]{task.percentage:>5.1f}%[/]"),
        TextColumn("↑[marsala]{task.fields[velocidade]:>7.1f}[/] KB/s"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        expand=False,
    )


# ──────────────────────────────────────────────────────────────────
# Relatório
# ──────────────────────────────────────────────────────────────────
def _exibir_relatorio(resultados, tempo_total: float, pasta: str):
    section("RELATÓRIO FINAL")

    sucessos = [r for r in resultados if r.sucesso]
    falhas   = [r for r in resultados if not r.sucesso]
    vel_media = (
        sum(r.velocidade_kbs for r in sucessos) / len(sucessos)
        if sucessos else 0
    )

    # Painel de resumo
    table = Table(box=box.SIMPLE_HEAVY, show_header=False,
                  border_style="marsala.dim", padding=(0, 2))
    table.add_column(style="label",  width=18)
    table.add_column(style="valor")

    table.add_row("✔ Enviadas",    str(len(sucessos)))
    table.add_row("✘ Falhas",      str(len(falhas)))
    table.add_row("⏱ Tempo total", f"{tempo_total:.0f} seg")
    table.add_row("↑ Vel. média",  f"{vel_media:.1f} KB/s")
    table.add_row("📁 Pasta",      pasta)

    console.print(Panel(table, title="[marsala]RESUMO[/]",
                        border_style="marsala.dim", box=box.DOUBLE))

    if falhas:
        console.print()
        console.print("  [erro]── FALHAS ──[/]")
        for r in falhas:
            console.print(f"  [erro]✘[/] [creme]{r.arquivo}[/]  [cinza]{r.erro or ''}[/]")

    # Exportar CSV?
    console.print()
    import questionary
    _M = "#9B2335"
    _C = "#E8D5C4"
    QSTYLE = questionary.Style([
        ("qmark", f"fg:{_M} bold"),
        ("question", f"fg:{_C} bold"),
        ("answer", f"fg:{_M} bold"),
    ])

    if questionary.confirm("Exportar relatório (.csv)?", default=False, style=QSTYLE).ask():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_csv = f"relatorio_upload_{ts}.csv"
        with open(nome_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["arquivo", "sucesso", "local", "velocidade_kbs", "erro"])
            for r in resultados:
                writer.writerow([r.arquivo, r.sucesso, r.local, r.velocidade_kbs, r.erro or ""])
        ok(f"Relatório salvo: [marsala]{nome_csv}[/]")


# ──────────────────────────────────────────────────────────────────
# Fluxo principal
# ──────────────────────────────────────────────────────────────────
def main():
    try:
        # 1. Login
        session, nome, email = tela_login()

        # 1.5 Pré-carrega IA em background enquanto usuário configura
        import threading
        _ia_thread = threading.Thread(
            target=carregar_ia,
            kwargs={"callback": lambda m: logging.info(f"[IA] {m}")},
            daemon=True,
        )
        _ia_thread.start()
        logging.info("Thread de pré-carregamento da IA iniciada.")

        # 2. Pasta
        console.print()
        pasta, imagens = tela_pasta()

        # 3. Configurações
        console.print()
        config = tela_config(session, len(imagens))
        config["autor"] = nome  # garante que o nome do autor logado é usado

        # 4. Upload com barra Flow
        section("UPLOAD EM ANDAMENTO")
        console.print()

        resultados  = []
        t_inicio    = time.perf_counter()
        status_atual = ["Preparando…"]

        progresso = _montar_progresso()

        with progresso:
            task_id = progresso.add_task(
                "Enviando…",
                total=len(imagens),
                velocidade=0.0,
            )

            for caminho in imagens:
                nome_arq = os.path.basename(caminho)
                progresso.update(task_id, description=f"[marsala]{nome_arq[:35]}[/]")
                logging.info(f"Iniciando upload: {caminho}")

                def make_cb(tid):
                    def cb(msg):
                        progresso.update(tid, description=f"[cinza]{msg[:35]}[/]")
                        logging.debug(f"  status: {msg}")
                    return cb

                resultado = enviar_foto(
                    session, caminho, config,
                    album_id=config["album_id"],
                    novo_album=config["novo_album"],
                    callback_status=make_cb(task_id),
                )
                logging.info(f"Resultado: sucesso={resultado.sucesso} http_status={getattr(resultado,'http_status','-')} vel={resultado.velocidade_kbs} erro={resultado.erro}")
                resultados.append(resultado)
                progresso.update(
                    task_id,
                    advance=1,
                    velocidade=resultado.velocidade_kbs,
                    description=f"[marsala]{nome_arq[:30]}[/]",
                )

                if resultado.sucesso:
                    ok(f"{nome_arq}  →  {resultado.local}  [cinza]↑ {resultado.velocidade_kbs:.1f} KB/s[/]")
                else:
                    erro(f"{nome_arq}  →  {resultado.erro}")

        tempo_total = time.perf_counter() - t_inicio

        # 5. Relatório final
        console.print()
        _exibir_relatorio(resultados, tempo_total, pasta)

    except KeyboardInterrupt:
        console.print("\n\n  [aviso]Cancelado pelo usuario.[/]")
        sys.exit(0)
    except Exception as e:
        logging.critical(f"ERRO CRITICO: {traceback.format_exc()}")
        console.print(f"\n  [erro]Erro critico: {e}[/]")
        console.print(f"  [cinza]Log salvo em: {_LOG_FILE}[/]")
        input("\n  Pressione ENTER para sair...")
        sys.exit(1)


if __name__ == "__main__":
    main()
