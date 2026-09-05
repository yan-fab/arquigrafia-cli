# core/scanner.py — Varredura e organização de coleções/álbuns via API REST

import logging
import requests

URL_API = "https://api.arquigrafia.org.br"


def extrair_id_usuario(session: requests.Session) -> str | None:
    """
    Retorna o UUID do usuário conectado consultando a API /api/me ou a sessão.
    """
    if getattr(session, "user_id", None):
        return session.user_id

    try:
        res = session.get(f"{URL_API}/api/me", timeout=15)
        if res.status_code == 200:
            user_data = res.json().get("user", {})
            uid = user_data.get("id")
            session.user_id = uid
            return uid
    except Exception as e:
        logging.error(f"Erro ao obter ID do usuário via API: {e}")
    return None


def obter_fotos_em_albuns(session: requests.Session, user_id: str) -> set[str]:
    """
    Retorna um conjunto (set) com os IDs de todas as fotos que já pertencem a algum álbum do usuário.
    """
    fotos_organizadas = set()
    try:
        url_albums = f"{URL_API}/api/users/{user_id}/albums"
        res = session.get(url_albums, timeout=15)
        if res.status_code == 200:
            albums_list = res.json()
            if isinstance(albums_list, dict) and "data" in albums_list:
                albums_list = albums_list["data"]

            for alb in albums_list:
                alb_id = alb.get("id")
                # Se já vier lista de imagens no objeto
                imgs = alb.get("images")
                if imgs and isinstance(imgs, list):
                    for img in imgs:
                        if isinstance(img, dict) and "id" in img:
                            fotos_organizadas.add(img["id"])
                        elif isinstance(img, str):
                            fotos_organizadas.add(img)
                elif alb_id:
                    # Busca o detalhe do álbum para listar as imagens
                    res_det = session.get(f"{URL_API}/api/albums/{alb_id}", timeout=15)
                    if res_det.status_code == 200:
                        det_imgs = res_det.json().get("images", [])
                        for img in det_imgs:
                            if isinstance(img, dict) and "id" in img:
                                fotos_organizadas.add(img["id"])
    except Exception as e:
        logging.error(f"Erro ao buscar fotos dos álbuns: {e}")

    return fotos_organizadas


def obter_fotos_do_perfil(session: requests.Session, user_id: str, callback_progresso=None) -> list[dict]:
    """
    Retorna todas as imagens cadastradas pelo usuário consultando as páginas da API,
    garantindo unicidade por ID.
    """
    fotos = []
    vistos = set()
    page = 1
    per_page = 100

    try:
        while True:
            if callback_progresso:
                callback_progresso(f"Buscando página {page} de fotos…")

            url = f"{URL_API}/api/images?user_id={user_id}&per_page={per_page}&page={page}"
            res = session.get(url, timeout=20)
            if res.status_code != 200:
                logging.error(f"Erro ao buscar fotos da página {page}: {res.status_code}")
                break

            data = res.json()
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                fid = item.get("id")
                if fid and fid not in vistos:
                    vistos.add(fid)
                    fotos.append(item)

            # Verifica paginação
            meta = data.get("meta", {})
            last_page = meta.get("last_page", 1)
            if page >= last_page:
                break

            page += 1

    except Exception as e:
        logging.error(f"Exceção ao listar fotos do usuário: {e}")

    return fotos


def extrair_titulo_foto(foto: dict) -> str:
    """
    Extrai o título principal / nome da obra da imagem.
    Prioriza títulos cadastrados; recorre à localização se não houver título.
    """
    titles = foto.get("titles", [])
    if titles and isinstance(titles, list):
        label = titles[0].get("label")
        if label and str(label).strip():
            return str(label).strip()

    t = foto.get("title")
    if t and str(t).strip():
        return str(t).strip()

    # Recorre à localização se não tiver título
    loc = extrair_localizacao_foto(foto)
    if loc and loc != "Sem Localização":
        return loc

    return "Sem Título"


def extrair_localizacao_foto(foto: dict) -> str:
    """Extrai a string de localização da foto a partir de metadados da API."""
    # 1. Tenta campo de localização direta
    loc = foto.get("location")
    if loc and isinstance(loc, dict) and loc.get("label"):
        return loc["label"].strip()

    # 2. Tenta location_label direto
    loc_label = foto.get("location_label")
    if loc_label:
        return loc_label.strip()

    # 3. Tenta lista de locations
    locs = foto.get("locations", [])
    if locs and isinstance(locs, list):
        lbl = locs[0].get("label")
        if lbl and str(lbl).strip():
            return str(lbl).strip()

    # 4. Tenta títulos (que muitas vezes armazenam o nome do local gerado)
    titles = foto.get("titles", [])
    if titles and isinstance(titles, list):
        label = titles[0].get("label")
        if label:
            return label.strip()

    return "Sem Localização"


def associar_fotos_ao_album(session: requests.Session, album_id: str, photo_ids: list[str]) -> bool:
    """
    Associa uma lista de fotos a um álbum via POST /api/albums/{id}/images.
    Divide automaticamente em lotes de 50 para evitar limites de payload da API.
    """
    if not photo_ids:
        return True

    try:
        url = f"{URL_API}/api/albums/{album_id}/images"
        chunk_size = 50
        todos_ok = True

        for i in range(0, len(photo_ids), chunk_size):
            chunk = photo_ids[i:i + chunk_size]
            payload = {
                "images": [{"image_id": pid} for pid in chunk]
            }
            res = session.post(url, json=payload, timeout=25)
            if res.status_code not in (200, 201):
                logging.error(f"Erro ao associar sub-lote ao álbum {album_id} ({res.status_code}): {res.text}")
                todos_ok = False

        return todos_ok
    except Exception as e:
        logging.error(f"Erro ao associar lote de {len(photo_ids)} fotos ao álbum {album_id}: {e}")
        return False


def associar_foto_ao_album(session: requests.Session, photo_id: str, album_id: str) -> bool:
    """Compatibilidade para associar uma única foto."""
    return associar_fotos_ao_album(session, album_id, [photo_id])
