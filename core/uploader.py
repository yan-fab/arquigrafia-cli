# core/uploader.py — Motor de upload REST API com cálculo de velocidade em KB/s

import os, io, time, re, logging
import requests
from PIL import Image

from core.exif import extrair_exif
from core.geo  import geocodificar
from core.ia   import analisar_imagem
from core.auth import criar_album

URL_API         = "https://api.arquigrafia.org.br"
URL_UPLOAD_POST = f"{URL_API}/api/images"
IMAGENS_EXT     = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
MAX_MB          = 10


def listar_imagens(pasta: str) -> tuple[list[str], list[str]]:
    """Retorna (imagens válidas, arquivos ignorados)."""
    validas, ignorados = [], []
    for arq in sorted(os.listdir(pasta)):
        caminho = os.path.join(pasta, arq)
        if os.path.isfile(caminho):
            if os.path.splitext(arq)[1].lower() in IMAGENS_EXT:
                validas.append(caminho)
            else:
                ignorados.append(arq)
    return validas, ignorados


def _comprimir(caminho: str) -> bytes:
    """Comprime imagem para < 10 MB preservando EXIF."""
    img = Image.open(caminho)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    quality = 92
    img.save(buf, format="JPEG", quality=quality, optimize=True)

    while buf.tell() > MAX_MB * 1024 * 1024 and quality > 40:
        quality -= 8
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)

    buf.seek(0)
    return buf.read()


def _nome_foto(caminho: str, geo: dict) -> str:
    # Se temos localização específica pelo GPS
    if geo.get("local"):
        return geo["local"].title()
    
    # Fallback: nome do arquivo limpo
    base = os.path.splitext(os.path.basename(caminho))[0]
    base = re.sub(r"[_\-]+", " ", base).strip()
    return base.title()


def _formatar_data_iso(data_str: str) -> str:
    """Converte data DD/MM/AAAA para AAAA-MM-DD."""
    if not data_str:
        return ""
    if "/" in data_str:
        partes = data_str.split("/")
        if len(partes) == 3:
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
    return data_str


def _mapear_licenca(tipo: str) -> str:
    """Converte o identificador do CLI para o formato da API."""
    mapa = {
        "visualizacao": "CC BY-NC-ND",
        "cc_by":        "CC BY",
        "cc_by_nc":     "CC BY-NC",
        "cc_by_nc_sa":  "CC BY-NC-SA",
        "cc_by_sa":     "CC BY-SA",
        "cc0":          "CC0",
    }
    return mapa.get(tipo, "CC BY-NC-SA")


class ResultadoUpload:
    def __init__(self, arquivo, sucesso, local, velocidade_kbs, erro=None, http_status=0):
        self.arquivo        = arquivo
        self.sucesso        = sucesso
        self.local          = local
        self.velocidade_kbs = velocidade_kbs
        self.erro           = erro
        self.http_status    = http_status


def enviar_foto(
    session: requests.Session,
    caminho: str,
    config: dict,
    album_id: str = "",
    novo_album: str = "",
    callback_status=None,
) -> ResultadoUpload:
    """
    Envia uma foto para a API REST do Arquigrafia (POST /api/images).
    callback_status(msg: str) é chamado durante as etapas.
    Retorna ResultadoUpload.
    """
    nome_arq = os.path.basename(caminho)
    user_id = config.get("user_id") or getattr(session, "user_id", None)

    try:
        if callback_status: callback_status("Lendo EXIF…")
        exif = extrair_exif(caminho)

        geo = {"pais": "Brasil", "estado": "", "cidade": "", "regiao": "", "descricao": ""}
        if exif.get("latitude") and exif.get("longitude"):
            if callback_status: callback_status("Geolocalizando…")
            geo = geocodificar(exif["latitude"], exif["longitude"])

        if callback_status: callback_status("Comprimindo…")
        img_bytes = _comprimir(caminho)
        tamanho_kb = len(img_bytes) / 1024

        # ── Análise de IA Visual ──────────────────────────────────────────────
        usar_ia = config.get("usar_ia", True)
        descricao_ia, tags_ia = analisar_imagem(caminho, geo, callback_status, usar_ia=usar_ia)
        geo["descricao"] = descricao_ia
        geo["tags"]      = ", ".join(tags_ia)
        # ─────────────────────────────────────────────────────────────────────

        nome_foto = _nome_foto(caminho, geo)
        licenca = _mapear_licenca(config.get("licenca", ""))
        data_iso = _formatar_data_iso(exif.get("data_foto", ""))

        # ── Montagem do Formulário Multipart para /api/images ─────────────────
        form_data = {
            "title": nome_foto,
            "license": licenca,
        }

        if user_id:
            form_data["user_id"] = user_id

        if geo.get("descricao"):
            form_data["description"] = geo["descricao"]

        local_label = geo.get("local") or geo.get("cidade") or ""
        if local_label:
            form_data["location_label"] = local_label

        if exif.get("latitude") and exif.get("longitude"):
            form_data["latitude"] = f"{float(exif['latitude']):.8f}"
            form_data["longitude"] = f"{float(exif['longitude']):.8f}"

        if data_iso:
            form_data["earliest_date"] = data_iso
            form_data["circa"] = "0"

        # Tags/Assuntos como subjects[]
        subjects = []
        if tags_ia:
            subjects.extend(tags_ia)
        elif geo.get("tags"):
            subjects.extend([t.strip() for t in geo["tags"].split(",") if t.strip()])

        # Multipart files
        files = {
            "image": (
                os.path.splitext(nome_arq)[0] + ".jpg",
                img_bytes,
                "image/jpeg",
            )
        }

        # Converte subjects[] para formato multipart
        multipart_data = []
        for k, v in form_data.items():
            multipart_data.append((k, (None, str(v))))
        for sub in subjects:
            multipart_data.append(("subjects[]", (None, str(sub))))

        if callback_status: callback_status(f"Enviando {tamanho_kb:.0f} KB…")
        t_inicio = time.perf_counter()

        # Envia para a API REST oficial
        res = session.post(
            URL_UPLOAD_POST,
            data=multipart_data,
            files=files,
            timeout=60,
        )

        t_fim = time.perf_counter()
        duracao = max(t_fim - t_inicio, 0.001)
        velocidade = tamanho_kb / duracao

        local_str = geo.get("local") or geo.get("cidade") or "Sem GPS"
        logging.info(f"Resposta do upload ({nome_arq}): status={res.status_code}")

        if res.status_code in (200, 201):
            res_json = res.json()
            nova_imagem_id = res_json.get("id") or (res_json.get("data", {}).get("id"))

            # ── Confirmação da Nova Estrutura de Localização via PUT ──────────
            if nova_imagem_id and exif.get("latitude") and exif.get("longitude"):
                try:
                    put_url = f"{URL_API}/api/images/{nova_imagem_id}"
                    put_payload = {
                        "latitude": round(float(exif["latitude"]), 8),
                        "longitude": round(float(exif["longitude"]), 8),
                        "location_label": local_label or local_str,
                    }
                    session.put(put_url, json=put_payload, timeout=15)
                except Exception as eloc:
                    logging.warning(f"Aviso ao persistir localização via PUT: {eloc}")

            # ── Associação ao Álbum se solicitado ─────────────────────────────
            target_album_id = album_id
            if novo_album and not target_album_id:
                if callback_status: callback_status(f"Criando álbum '{novo_album}'…")
                target_album_id = criar_album(session, novo_album)

            if target_album_id and nova_imagem_id:
                if callback_status: callback_status("Vinculando ao álbum…")
                try:
                    alb_url = f"{URL_API}/api/albums/{target_album_id}/images"
                    alb_payload = {"images": [{"image_id": nova_imagem_id}]}
                    res_alb = session.post(alb_url, json=alb_payload, timeout=15)
                    logging.info(f"Associação de foto {nova_imagem_id} ao álbum {target_album_id}: status={res_alb.status_code}")
                except Exception as ea:
                    logging.warning(f"Erro ao associar foto ao álbum: {ea}")

            return ResultadoUpload(nome_arq, True, local_str, round(velocidade, 1),
                                   http_status=res.status_code)
        else:
            try:
                err_msg = res.json().get("message") or res.text[:80]
            except Exception:
                err_msg = res.text[:80]
            logging.error(f"Erro no upload ({res.status_code}): {err_msg}")
            return ResultadoUpload(nome_arq, False, "—", 0.0,
                                   erro=f"HTTP {res.status_code}: {err_msg}",
                                   http_status=res.status_code)

    except Exception as e:
        logging.error(f"Exceção no upload de {os.path.basename(caminho)}: {e}", exc_info=True)
        return ResultadoUpload(nome_arq, False, "—", 0.0, str(e)[:80])
