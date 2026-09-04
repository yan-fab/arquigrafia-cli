# core/auth.py — Autenticação OAuth 2.0 e API REST do Arquigrafia

import requests
import keyring
import logging

SERVICE_NAME  = "arquigrafia-uploader"
URL_API       = "https://api.arquigrafia.org.br"
CLIENT_ID     = "1"
CLIENT_SECRET = "y08fuIOyXvzWINuPAUaCUlofvOdwDQIhnt3jykHx"


def get_saved_credentials():
    """Recupera credenciais salvas pelo keyring."""
    email = keyring.get_password(SERVICE_NAME, "email")
    senha = keyring.get_password(SERVICE_NAME, "senha")
    return email, senha


def save_credentials(email: str, senha: str):
    """Salva credenciais com segurança no keyring do SO."""
    keyring.set_password(SERVICE_NAME, "email", email)
    keyring.set_password(SERVICE_NAME, "senha", senha)


def clear_credentials():
    try:
        keyring.delete_password(SERVICE_NAME, "email")
        keyring.delete_password(SERVICE_NAME, "senha")
    except Exception:
        pass


def fazer_login(email: str, senha: str) -> tuple[requests.Session | None, str | None, str | None]:
    """
    Realiza o login na API REST do Arquigrafia via OAuth 2.0.
    Retorna (session, nome_usuario, user_id) em sucesso, ou (None, erro, None) em falha.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "ArquigrafiaCLI/2.0",
        "Accept": "application/json",
    })

    payload = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": email,
        "password": senha,
        "scope": "*",
    }

    try:
        logging.info(f"Tentando autenticação OAuth 2.0 para: {email}")
        res = session.post(f"{URL_API}/oauth/token", json=payload, timeout=20)
        
        if res.status_code == 200:
            data = res.json()
            access_token = data.get("access_token")
            token_type = data.get("token_type", "Bearer")
            
            session.headers.update({
                "Authorization": f"{token_type} {access_token}"
            })
            
            # Obtém dados do usuário conectado
            res_me = session.get(f"{URL_API}/api/me", timeout=15)
            nome = email
            user_id = None
            
            if res_me.status_code == 200:
                user_info = res_me.json().get("user", {})
                user_id = user_info.get("id")
                nome = user_info.get("name") or email
                logging.info(f"Usuário autenticado com sucesso: {nome} (ID: {user_id})")
            else:
                logging.warning(f"Não foi possível obter dados completos do /api/me: {res_me.text}")

            session.user_id = user_id
            session.user_name = nome
            session.user_email = email
            return session, nome, user_id
        else:
            try:
                err_data = res.json()
                msg = err_data.get("message") or err_data.get("error_description") or res.text
            except Exception:
                msg = res.text
            logging.error(f"Falha de autenticação ({res.status_code}): {msg}")
            return None, msg, None

    except Exception as e:
        logging.error(f"Erro na conexão com API Arquigrafia: {e}")
        return None, str(e), None


def listar_albums(session: requests.Session, user_id: str = None) -> dict[str, str]:
    """
    Retorna dict {nome_album: id_album_uuid} das coleções/álbuns do usuário.
    """
    uid = user_id or getattr(session, "user_id", None)
    if not uid:
        logging.warning("User ID ausente para listar álbuns.")
        return {}

    try:
        url = f"{URL_API}/api/users/{uid}/albums"
        res = session.get(url, timeout=15)
        if res.status_code == 200:
            albums_data = res.json()
            # Pode vir como lista de dicionários
            albums = {}
            if isinstance(albums_data, list):
                for alb in albums_data:
                    title = alb.get("title")
                    aid = alb.get("id")
                    if title and aid:
                        albums[title] = aid
            elif isinstance(albums_data, dict) and "data" in albums_data:
                for alb in albums_data["data"]:
                    title = alb.get("title")
                    aid = alb.get("id")
                    if title and aid:
                        albums[title] = aid
            return albums
        else:
            logging.error(f"Erro ao buscar álbuns ({res.status_code}): {res.text}")
            return {}
    except Exception as e:
        logging.error(f"Exceção ao listar álbuns: {e}")
        return {}


def criar_album(session: requests.Session, titulo: str, descricao: str = "", is_private: bool = False) -> str | None:
    """
    Cria uma nova coleção/álbum via API e retorna seu UUID.
    """
    try:
        url = f"{URL_API}/api/albums/"
        payload = {
            "title": titulo,
            "description": descricao,
            "is_private": is_private,
        }
        res = session.post(url, json=payload, timeout=15)
        if res.status_code in (200, 201):
            data = res.json()
            # Retorna o id criado
            album_id = data.get("id") or (data.get("data", {}).get("id"))
            logging.info(f"Álbum '{titulo}' criado com sucesso: {album_id}")
            return album_id
        else:
            logging.error(f"Falha ao criar álbum ({res.status_code}): {res.text}")
            return None
    except Exception as e:
        logging.error(f"Exceção ao criar álbum: {e}")
        return None
