# core/tags.py — Gerenciamento do Vocabulário Controlado de Artes e Arquitetura (VCAA - USP)
import os
import sys
import json
import re
import logging

_VCAA_CACHE = None
_VCAA_MULTI_WORDS = None
_VCAA_SINGLE_WORDS = None
_VCAA_VARIATIONS = None

def _get_vcaa_path() -> str:
    """Localiza o arquivo vcaa_tags.json mesmo compilado no PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    candidatos = [
        os.path.join(base_dir, "core", "vcaa_tags.json"),
        os.path.join(base_dir, "vcaa_tags.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "vcaa_tags.json"),
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    return candidatos[0]


def carregar_vcaa() -> dict:
    """Carrega o vocabulário VCAA do JSON com cache em memória e índices de variações."""
    global _VCAA_CACHE, _VCAA_MULTI_WORDS, _VCAA_SINGLE_WORDS, _VCAA_VARIATIONS
    if _VCAA_CACHE is not None:
        return _VCAA_CACHE

    caminho = _get_vcaa_path()
    if not os.path.exists(caminho):
        logging.warning(f"Arquivo VCAA não encontrado em: {caminho}")
        _VCAA_CACHE = {}
        _VCAA_MULTI_WORDS = []
        _VCAA_SINGLE_WORDS = set()
        _VCAA_VARIATIONS = {}
        return _VCAA_CACHE

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            _VCAA_CACHE = json.load(f)

        _VCAA_MULTI_WORDS = sorted(
            [t for t in _VCAA_CACHE.keys() if " " in t],
            key=lambda x: len(x),
            reverse=True,
        )
        _VCAA_SINGLE_WORDS = set(t for t in _VCAA_CACHE.keys() if " " not in t)

        # Mapeamento de variações de singular/plural para o termo oficial
        _VCAA_VARIATIONS = {}
        for termo_key, dados in _VCAA_CACHE.items():
            canonic = dados["term"]
            _VCAA_VARIATIONS[termo_key] = canonic

            # Se termina em 's' (plural comum no thesaurus VCAA, ex: 'fachadas' -> 'fachada')
            if termo_key.endswith("s") and len(termo_key) > 3:
                _VCAA_VARIATIONS.setdefault(termo_key[:-1], canonic)
            if termo_key.endswith("es") and len(termo_key) > 4:
                _VCAA_VARIATIONS.setdefault(termo_key[:-2], canonic)

        logging.info(f"VCAA carregado com sucesso: {len(_VCAA_CACHE)} termos oficiais.")
    except Exception as e:
        logging.error(f"Erro ao carregar VCAA JSON: {e}")
        _VCAA_CACHE = {}
        _VCAA_MULTI_WORDS = []
        _VCAA_SINGLE_WORDS = set()
        _VCAA_VARIATIONS = {}

    return _VCAA_CACHE


def total_termos_vcaa() -> int:
    """Retorna a quantidade de termos no vocabulário VCAA."""
    vcaa = carregar_vcaa()
    return len(vcaa)


def casar_tags_vcaa(texto: str) -> list[str]:
    """
    Analisa um texto (descrição, legendas) e identifica todos os termos
    oficiais pertencentes ao Vocabulário Controlado de Artes e Arquitetura (VCAA da USP).
    Suporta termos compostos e flexões de número (singular/plural).
    """
    carregar_vcaa()
    if not _VCAA_CACHE:
        return []

    texto_lower = texto.lower()
    matches = set()

    # 1. Casamento de termos compostos oficiais (ex: 'fachadas de vidro', 'abóbadas de ogiva')
    for mw in _VCAA_MULTI_WORDS:
        # Tenta a forma exata e variações com/sem 's' no primeiro termo
        padrao = r"\b" + re.escape(mw) + r"\b"
        if re.search(padrao, texto_lower):
            matches.add(_VCAA_CACHE[mw]["term"])
        else:
            # Testa se o texto contém variação no singular (ex: 'fachada de vidro' para 'fachadas de vidro')
            partes = mw.split(" ")
            if partes[0].endswith("s"):
                alt_mw = partes[0][:-1] + " " + " ".join(partes[1:])
                if re.search(r"\b" + re.escape(alt_mw) + r"\b", texto_lower):
                    matches.add(_VCAA_CACHE[mw]["term"])

    # 2. Casamento de termos simples (palavras individuais)
    palavras = re.findall(r"\b[a-zA-ZáàãâéèêíïóôõöúçÁÀÃÂÉÈÊÍÏÓÔÕÖÚÇ\-]+\b", texto_lower)
    for p in palavras:
        if len(p) < 3:
            continue
        if p in _VCAA_VARIATIONS:
            matches.add(_VCAA_VARIATIONS[p])

    return sorted(matches)


def buscar_termos_vcaa(query: str, limite: int = 15) -> list[str]:
    """
    Busca termos no vocabulário VCAA pelo prefixo ou conteúdo para autocompletar e sugestões.
    """
    carregar_vcaa()
    if not _VCAA_CACHE or not query:
        return []

    q = query.strip().lower()
    exatos = []
    prefixos = []
    parciais = []

    for k, v in _VCAA_CACHE.items():
        termo = v["term"]
        if k == q:
            exatos.append(termo)
        elif k.startswith(q):
            prefixos.append(termo)
        elif q in k:
            parciais.append(termo)

        if len(exatos) + len(prefixos) >= limite:
            break

    res = exatos + prefixos + parciais
    return res[:limite]
