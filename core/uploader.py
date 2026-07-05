# core/uploader.py — Motor de upload com cálculo de velocidade em KB/s

import os, io, time, re, logging
import requests
from bs4 import BeautifulSoup
from PIL import Image

from core.exif import extrair_exif
from core.geo  import geocodificar
from core.ia   import analisar_imagem, carregar_ia

URL_BASE        = "https://www.arquigrafia.org.br"
URL_UPLOAD_PAGE = f"{URL_BASE}/photos/upload"
URL_UPLOAD_POST = f"{URL_BASE}/photos"
IMAGENS_EXT     = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
MAX_MB          = 10

# Mapa nome completo -> sigla para o campo photo_state
ESTADO_SIGLA = {
    "Acre": "AC", "Alagoas": "AL", "Amapa": "AP", "Amapá": "AP",
    "Amazonas": "AM", "Bahia": "BA", "Ceara": "CE", "Ceará": "CE",
    "Distrito Federal": "DF", "Espirito Santo": "ES", "Espírito Santo": "ES",
    "Goias": "GO", "Goiás": "GO", "Maranhao": "MA", "Maranhão": "MA",
    "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG", "Para": "PA", "Pará": "PA",
    "Paraiba": "PB", "Paraíba": "PB", "Parana": "PR", "Paraná": "PR",
    "Pernambuco": "PE", "Piaui": "PI", "Piauí": "PI",
    "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondonia": "RO", "Rondônia": "RO",
    "Roraima": "RR", "Santa Catarina": "SC", "Sao Paulo": "SP",
    "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO",
}


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


def _get_upload_token(session: requests.Session) -> tuple[str | None, object | None]:
    res = session.get(URL_UPLOAD_PAGE, timeout=20)
    soup = BeautifulSoup(res.text, "html.parser")
    token_el = soup.find("input", {"name": "_token"})
    if not token_el:
        return None, None
    return token_el["value"], soup


def _montar_payload(token: str, soup, nome_foto: str, geo: dict,
                    exif: dict, album_id: str, novo_album: str,
                    config: dict) -> dict:
    estado_nome = geo.get("estado", "")
    estado_sigla = ESTADO_SIGLA.get(estado_nome, estado_nome[:2].upper() if estado_nome else "")

    tags = geo.get("tags", "arquitetura, fotografia")

    payload = {
        "_token":                      token,
        "type":                        "photo",
        "video":                       "",
        "pageSource":                  "",

        "photo_name":                  nome_foto,
        "photo_imageAuthor":           config.get("autor", ""),

        # Localização
        "photo_country":               geo.get("pais", "Brasil"),
        "photo_state":                 estado_sigla,
        "photo_city":                  geo.get("cidade", ""),
        "photo_district":              geo.get("regiao", ""),
        "photo_street":                geo.get("rua", ""),

        # Data da foto
        "photo_imageDate":             exif.get("data_foto", ""),
        "century_image":               "",
        "decade_select_image":         "",

        # Obra/autor da obra
        "photo_workAuthor":            "",
        "work_authors":                "",
        "workDate":                    "",
        "century":                     "",
        "decade_select":               "",

        # Descrição e tags
        "photo_description":           geo.get("descricao", ""),
        "tags_input":                  tags,
        "tags":                        tags,

        # Álbum
        "photo_album":                 album_id,
        "new_album-name":              novo_album if not album_id else "",

        # Licença e autorização
        "photo_authorization_checkbox": "1",
        "photo_allowCommercialUses":   "NO",
        "photo_allowModifications":    "NO",

        "photo_tombo":                 "",
    }
    if config.get("licenca") == "cc_by":
        payload["photo_allowCommercialUses"] = "YES"
        payload["photo_allowModifications"]  = "YES"
    elif config.get("licenca") == "cc_by_nc":
        payload["photo_allowCommercialUses"] = "NO"
        payload["photo_allowModifications"]  = "YES"
    return payload



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
    Envia uma foto para o Arquigrafia.
    callback_status(msg: str) é chamado durante etapas.
    Retorna ResultadoUpload com velocidade em KB/s.
    """
    nome_arq = os.path.basename(caminho)

    try:
        if callback_status: callback_status("Lendo EXIF…")
        exif = extrair_exif(caminho)

        geo = {"pais": "Brasil", "estado": "", "cidade": "", "regiao": "", "descricao": ""}
        if exif["latitude"] and exif["longitude"]:
            if callback_status: callback_status("Geolocalizando…")
            geo = geocodificar(exif["latitude"], exif["longitude"])

        if callback_status: callback_status("Comprimindo…")
        img_bytes = _comprimir(caminho)
        tamanho_kb = len(img_bytes) / 1024

        # ── Análise de IA Visual ──────────────────────────────────────────────
        descricao_ia, tags_ia = analisar_imagem(caminho, geo, callback_status)
        geo["descricao"] = descricao_ia
        geo["tags"]      = ", ".join(tags_ia)
        # ─────────────────────────────────────────────────────────────────────

        if callback_status: callback_status("Obtendo token…")
        token, soup = _get_upload_token(session)
        if not token:
            return ResultadoUpload(nome_arq, False, "—", 0.0, "Token não encontrado")

        nome_foto = _nome_foto(caminho, geo)
        payload   = _montar_payload(token, soup, nome_foto, geo, exif,
                                     album_id, novo_album, config)

        files = {
            "photo": (
                os.path.splitext(nome_arq)[0] + ".jpg",
                img_bytes,
                "image/jpeg",
            )
        }

        if callback_status: callback_status(f"Enviando {tamanho_kb:.0f} KB…")
        t_inicio = time.perf_counter()

        res = session.post(URL_UPLOAD_POST, data=payload, files=files,
                           timeout=60, allow_redirects=True)

        t_fim = time.perf_counter()
        duracao = max(t_fim - t_inicio, 0.001)
        velocidade = tamanho_kb / duracao  # KB/s

        local_str = geo.get("descricao") or geo.get("cidade") or "Sem GPS"

        logging.info(f"HTTP status do upload: {res.status_code} | URL: {res.url}")

        # Status 200, 201, 302 = sucesso real. 500 = possivel bug do servidor mas foto salva.
        sucesso = res.status_code in (200, 201, 302, 500)

        return ResultadoUpload(nome_arq, sucesso, local_str, round(velocidade, 1),
                               http_status=res.status_code)

    except Exception as e:
        logging.error(f"Excecao no upload de {os.path.basename(caminho)}: {e}", exc_info=True)
        return ResultadoUpload(nome_arq, False, "—", 0.0, str(e)[:80])
