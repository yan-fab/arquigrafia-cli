# core/auth.py — Login e sessão requests com cache keyring

import requests
import keyring
from bs4 import BeautifulSoup

SERVICE_NAME = "arquigrafia-uploader"
URL_BASE     = "https://www.arquigrafia.org.br"
URL_LOGIN    = f"{URL_BASE}/users/login"


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


def fazer_login(email: str, senha: str) -> tuple[requests.Session | None, str | None]:
    """
    Realiza o login no Arquigrafia.
    Retorna (session, nome_usuario) em sucesso, ou (None, None) em falha.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
        "Accept-Language": "pt-BR,pt;q=0.9",
    })

    try:
        res = session.get(URL_LOGIN, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        token_input = soup.find("input", {"name": "_token"})
        if not token_input:
            return None, None
        token = token_input["value"]

        res_login = session.post(URL_LOGIN, data={
            "_token": token,
            "login": email,
            "password": senha,
        }, timeout=15, allow_redirects=True)

        # Verifica se logou verificando a home
        res_home = session.get(f"{URL_BASE}/home", timeout=15)
        soup_home = BeautifulSoup(res_home.text, "html.parser")

        for a in soup_home.find_all("a", href=True):
            import re
            if re.search(r"/users/\d+$", a["href"]):
                perfil_url = a["href"] if a["href"].startswith("http") else URL_BASE + a["href"]
                res_p = session.get(perfil_url, timeout=15)
                sp = BeautifulSoup(res_p.text, "html.parser")
                h1 = sp.find("h1")
                nome = h1.text.strip() if h1 else email
                return session, nome

        return None, None

    except Exception as e:
        return None, str(e)


def listar_albums(session: requests.Session) -> dict[str, str]:
    """
    Retorna dict {nome_album: id_album} dos álbuns do usuário.
    """
    URL_UPLOAD = f"{URL_BASE}/photos/upload"
    res = session.get(URL_UPLOAD, timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")
    select = soup.find("select", {"name": "photo_album"})
    albums = {}
    if select:
        for opt in select.find_all("option"):
            val = opt.get("value", "").strip()
            txt = opt.text.strip()
            if val and txt and val != "":
                albums[txt] = val
    return albums
