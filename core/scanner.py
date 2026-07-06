# core/scanner.py — Lógica de varredura de perfil, filtragem de fotos sem álbum e associação

import re
import logging
import requests
from bs4 import BeautifulSoup
from core.auth import listar_albums

URL_BASE = "https://www.arquigrafia.org.br"


def extrair_id_usuario(session: requests.Session) -> str | None:
    """Extrai o ID do usuário conectado a partir da página /home."""
    try:
        res = session.get(f"{URL_BASE}/home", timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = re.search(r"/users/(\d+)$", href)
            if m:
                return m.group(1)
    except Exception as e:
        logging.error(f"Erro ao extrair ID do usuário: {e}")
    return None


def obter_fotos_do_perfil(session: requests.Session, user_id: str) -> list[str]:
    """Retorna uma lista de IDs de todas as fotos do perfil do usuário."""
    try:
        logging.info(f"Buscando fotos do perfil do usuario {user_id}...")
        res = session.get(f"{URL_BASE}/users/{user_id}", timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Filtra os links de edicao das fotos (indica propriedade)
        photo_ids = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = re.search(r"/photos/(\d+)/edit", href)
            if m:
                photo_ids.append(m.group(1))
        
        # Deduplica preservando a ordem (do mais recente ao mais antigo)
        return list(dict.fromkeys(photo_ids))
    except Exception as e:
        logging.error(f"Erro ao obter fotos do perfil: {e}")
        return []


def verificar_foto_sem_album(session: requests.Session, photo_id: str, total_albums_user: int) -> bool:
    """
    Verifica se uma foto específica não está em nenhum álbum.
    Retorna True se estiver sem álbum, False caso contrário.
    """
    try:
        headers = {"X-Requested-With": "XMLHttpRequest"}
        res = session.get(f"{URL_BASE}/albums/get/list/{photo_id}", headers=headers, timeout=15)
        
        # O site retorna apenas os álbuns nos quais a foto NÃO está adicionada.
        # Se o número de checkboxes for igual ao total de álbuns do usuário, ela está sem álbum.
        soup = BeautifulSoup(res.text, "html.parser")
        checkboxes = soup.find_all("input", {"type": "checkbox", "name": "albums[]"})
        
        return len(checkboxes) == total_albums_user
    except Exception as e:
        logging.error(f"Erro ao verificar album da foto {photo_id}: {e}")
        return False


def obter_localizacao_foto(session: requests.Session, photo_id: str) -> str:
    """Acessa a tela de edição da foto para capturar a cidade/estado cadastrados."""
    try:
        res = session.get(f"{URL_BASE}/photos/{photo_id}/edit", timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        
        cidade = ""
        estado = ""
        
        city_inp = soup.find("input", {"name": "photo_city"})
        if city_inp:
            cidade = city_inp.get("value", "").strip()
            
        state_sel = soup.find("select", {"name": "photo_state"})
        if state_sel:
            opt = state_sel.find("option", selected=True)
            if opt and opt.get("value"):
                estado = opt.get("value").strip()
                
        if cidade and estado:
            return f"{cidade} - {estado}"
        elif cidade:
            return cidade
        elif estado:
            return estado
    except Exception as e:
        logging.error(f"Erro ao obter localizacao da foto {photo_id}: {e}")
    return "Sem Localização"


def associar_foto_ao_album(session: requests.Session, photo_id: str, album_id: str) -> bool:
    """Associa uma foto específica ao álbum no site do Arquigrafia."""
    try:
        headers = {"X-Requested-With": "XMLHttpRequest"}
        # 1. Pega o token CSRF atualizado da página de listagem
        res_list = session.get(f"{URL_BASE}/albums/get/list/{photo_id}", headers=headers, timeout=15)
        soup = BeautifulSoup(res_list.text, "html.parser")
        token_el = soup.find("input", {"name": "_token"})
        if not token_el:
            return False
        
        token = token_el["value"]
        
        # 2. Faz o POST de associação
        payload = {
            "_token": token,
            "_photo": photo_id,
            "albums[]": [album_id]
        }
        res_add = session.post(f"{URL_BASE}/albums/photo/add", data=payload, timeout=15)
        return res_add.status_code == 200
    except Exception as e:
        logging.error(f"Erro ao associar foto {photo_id} ao album {album_id}: {e}")
        return False
