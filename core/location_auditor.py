# core/location_auditor.py — Auditoria e Atualização em Lote de Localização de Imagens

import os
import re
import time
import logging
import requests
from typing import Callable, Optional

from core.exif import extrair_exif
from core.geo import geocodificar, geocodificar_endereco
from core.scanner import obter_fotos_do_perfil

URL_API = "https://api.arquigrafia.org.br"


def indexar_fotos_locais(pasta_local: str) -> dict[str, dict]:
    """
    Varre recursivamente a pasta local buscando fotos com EXIF GPS.
    Retorna mapeamento:
      nome_arquivo_normalizado -> { "caminho": str, "lat": float, "lon": float, "exif": dict }
    """
    indice = {}
    if not pasta_local or not os.path.exists(pasta_local):
        return indice

    extensoes_validas = {".jpg", ".jpeg", ".png", ".webp"}
    for raiz, _, arquivos in os.walk(pasta_local):
        for arq in arquivos:
            ext = os.path.splitext(arq)[1].lower()
            if ext in extensoes_validas:
                caminho_completo = os.path.join(raiz, arq)
                try:
                    exif = extrair_exif(caminho_completo)
                    lat = exif.get("latitude")
                    lon = exif.get("longitude")
                    if lat is not None and lon is not None:
                        chave = os.path.splitext(arq)[0].lower().strip()
                        indice[chave] = {
                            "caminho": caminho_completo,
                            "lat": float(lat),
                            "lon": float(lon),
                            "exif": exif
                        }
                except Exception as e:
                    logging.debug(f"Falha ao ler EXIF de {arq}: {e}")

    logging.info(f"Fotos locais com GPS indexadas: {len(indice)}")
    return indice


def extrair_candidatos_endereco(foto: dict) -> list[str]:
    """
    Analisa os metadados internos de uma imagem no Arquigrafia e extrai
    candidatos a endereço/localidade para busca de geocodificação.
    """
    candidatos = []

    # 1. Títulos
    titles = foto.get("titles", [])
    titulo_principal = ""
    if titles and isinstance(titles, list):
        for t in titles:
            lbl = t.get("label", "").strip()
            if lbl:
                titulo_principal = lbl
                break
    elif foto.get("title"):
        titulo_principal = foto.get("title").strip()

    # 2. Descrições
    descriptions = foto.get("descriptions", [])
    desc_texto = ""
    if descriptions and isinstance(descriptions, list):
        for d in descriptions:
            txt = d.get("text", "").strip()
            if txt:
                desc_texto = txt
                break
    elif foto.get("description"):
        desc_texto = foto.get("description").strip()

    # Extrai padrão comum: "localizada em X - UF" ou "localizada em X"
    if desc_texto:
        match_loc = re.search(r'localizada em ([^.]+)', desc_texto, re.IGNORECASE)
        if match_loc:
            cidade_uf = match_loc.group(1).strip()
            if titulo_principal and cidade_uf:
                candidatos.append(f"{titulo_principal}, {cidade_uf}")
            candidatos.append(cidade_uf)

    # Adiciona título diretamente se for informativo
    if titulo_principal:
        if titulo_principal not in candidatos:
            candidatos.append(titulo_principal)

    # 3. Tags/Assuntos geográficos (cidades, bairros)
    subjects = foto.get("subjects", [])
    termos = []
    for s in subjects:
        term = s.get("term", "").strip() if isinstance(s, dict) else str(s).strip()
        if term and len(term) > 2:
            termos.append(term)

    # Combina título com termos se houver cidade
    if titulo_principal:
        for t in termos:
            cand = f"{titulo_principal}, {t}"
            if cand not in candidatos and len(candidatos) < 5:
                candidatos.append(cand)

    return [c for c in candidatos if len(c) >= 3]


def atualizar_localizacao_imagem(
    session: requests.Session,
    image_id: str,
    lat: float,
    lon: float,
    location_label: str,
    foto_original: Optional[dict] = None
) -> tuple[bool, str]:
    """
    Envia a requisição PUT /api/images/{id} atualizando a localização na nova estrutura.
    Preserva metadados essenciais (título, descrição, assuntos/tags, datas).
    Omite campos nulos para evitar rejeição com HTTP 422.
    """
    url = f"{URL_API}/api/images/{image_id}"

    # Recupera metadados existentes da foto
    title = ""
    description = ""
    subject_ids = []
    earliest_date = None
    latest_date = None
    circa = False

    if foto_original:
        # Título
        titles = foto_original.get("titles", [])
        if titles and isinstance(titles, list):
            title = titles[0].get("label", "")
        if not title:
            title = foto_original.get("title", "")

        # Descrição
        descriptions = foto_original.get("descriptions", [])
        if descriptions and isinstance(descriptions, list):
            description = descriptions[0].get("text", "")
        if not description:
            description = foto_original.get("description", "")

        # Tags (Subjects UUIDs)
        subjects = foto_original.get("subjects", [])
        for s in subjects:
            if isinstance(s, dict) and s.get("id"):
                subject_ids.append(s["id"])

        # Datas
        dates = foto_original.get("dates", [])
        if dates and isinstance(dates, list) and len(dates) > 0:
            d = dates[0]
            earliest_date = d.get("earliest_date")
            if earliest_date and "T" in earliest_date:
                earliest_date = earliest_date.split("T")[0]
            latest_date = d.get("latest_date")
            if latest_date and "T" in latest_date:
                latest_date = latest_date.split("T")[0]
            circa = bool(d.get("circa_earliest_date") or d.get("circa_latest_date"))

    if not title:
        title = location_label[:60] if location_label else "Fotografia"

    payload = {
        "title": title,
        "description": description or None,
        "latitude": round(float(lat), 8),
        "longitude": round(float(lon), 8),
        "location_label": location_label or None,
        "subjects": subject_ids if subject_ids else [],
        "earliest_date": earliest_date,
        "latest_date": latest_date,
        "circa": circa
    }

    # Remove chaves estritamente nulas para satisfazer validação de API (ex: photographer)
    payload_limpo = {k: v for k, v in payload.items() if v is not None or k in ["latitude", "longitude", "location_label"]}

    try:
        res = session.put(url, json=payload_limpo, timeout=20)
        if res.status_code in (200, 201):
            return True, "Localização atualizada com sucesso"
        else:
            try:
                err_json = res.json()
                msg = err_json.get("message") or str(err_json)
            except Exception:
                msg = res.text[:120]
            return False, f"Erro {res.status_code}: {msg}"
    except Exception as e:
        return False, f"Exceção na API: {str(e)}"


def auditar_e_atualizar_acervo(
    session: requests.Session,
    user_id: str,
    pasta_local: Optional[str] = None,
    callback_progresso: Optional[Callable[[dict], None]] = None,
    limite: Optional[int] = None
) -> dict:
    """
    Realiza a auditoria de todas as fotos do perfil.
    Para as que estiverem sem localização, busca dados internos (EXIF local ou metadados de texto)
    e atualiza via PUT /api/images/{id}.
    """
    stats = {
        "total_fotos": 0,
        "sem_localizacao": 0,
        "ja_localizadas": 0,
        "atualizadas_exif": 0,
        "atualizadas_texto": 0,
        "falhas": 0,
        "detalhes": []
    }

    # 1. Indexa pasta local se informada
    indice_local = {}
    if pasta_local and os.path.exists(pasta_local):
        if callback_progresso:
            callback_progresso({"etapa": "indexando_local", "msg": f"Indexando fotos com GPS na pasta: {pasta_local}"})
        indice_local = indexar_fotos_locais(pasta_local)

    # 2. Busca todas as fotos do usuário
    if callback_progresso:
        callback_progresso({"etapa": "buscando_fotos", "msg": "Buscando fotos cadastradas na sua conta Arquigrafia…"})

    todas_fotos = obter_fotos_do_perfil(session, user_id)
    stats["total_fotos"] = len(todas_fotos)

    if limite:
        todas_fotos = todas_fotos[:limite]

    fotos_para_auditar = []
    for f in todas_fotos:
        locs = f.get("locations", [])
        coords = f.get("locationCoordinates")
        if not locs and not coords:
            fotos_para_auditar.append(f)
        else:
            stats["ja_localizadas"] += 1

    stats["sem_localizacao"] = len(fotos_para_auditar)

    if callback_progresso:
        callback_progresso({
            "etapa": "iniciando_auditoria",
            "total": len(fotos_para_auditar),
            "msg": f"Encontradas {len(fotos_para_auditar)} fotos sem localização para auditar."
        })

    # 3. Processa cada foto sem localização
    for i, foto in enumerate(fotos_para_auditar, 1):
        fid = foto.get("id")
        titles = foto.get("titles", [])
        ftitle = titles[0].get("label") if titles else foto.get("title", "(Sem título)")

        item_res = {
            "id": fid,
            "titulo": ftitle,
            "status": "pendente",
            "metodo": None,
            "lat": None,
            "lon": None,
            "label": None,
            "msg": ""
        }

        if callback_progresso:
            callback_progresso({
                "etapa": "processando_item",
                "indice": i,
                "total": len(fotos_para_auditar),
                "id": fid,
                "titulo": ftitle,
                "msg": f"Auditando [{i}/{len(fotos_para_auditar)}]: {ftitle}"
            })

        lat_encontrada = None
        lon_encontrada = None
        label_encontrado = None
        metodo = None

        # Tentativa A: Cruzamento com arquivo local (EXIF GPS nativo)
        if indice_local:
            chave_titulo = ftitle.lower().strip()
            # Tenta busca exata ou parcial
            for chave_arq, dados_arq in indice_local.items():
                if chave_arq in chave_titulo or chave_titulo in chave_arq:
                    lat_encontrada = dados_arq["lat"]
                    lon_encontrada = dados_arq["lon"]
                    metodo = "exif_local"
                    # Reverse geocode para obter o label formatado
                    geo_info = geocodificar(lat_encontrada, lon_encontrada)
                    label_encontrado = geo_info.get("local") or geo_info.get("descricao") or ftitle
                    break

        # Tentativa B: Análise de metadados internos de texto + Geocodificação Nominatim
        if lat_encontrada is None:
            candidatos = extrair_candidatos_endereco(foto)
            for cand in candidatos:
                resultado_geo = geocodificar_endereco(cand)
                if resultado_geo:
                    lat_encontrada, lon_encontrada, label_encontrado = resultado_geo
                    metodo = "texto_interno"
                    break

        # Se encontrou coordenadas, atualiza na API via PUT
        if lat_encontrada is not None and lon_encontrada is not None:
            sucesso, msg_api = atualizar_localizacao_imagem(
                session=session,
                image_id=fid,
                lat=lat_encontrada,
                lon=lon_encontrada,
                location_label=label_encontrado or ftitle,
                foto_original=foto
            )

            item_res["lat"] = lat_encontrada
            item_res["lon"] = lon_encontrada
            item_res["label"] = label_encontrado
            item_res["metodo"] = metodo
            item_res["msg"] = msg_api

            if sucesso:
                item_res["status"] = "sucesso"
                if metodo == "exif_local":
                    stats["atualizadas_exif"] += 1
                else:
                    stats["atualizadas_texto"] += 1
            else:
                item_res["status"] = "falha"
                stats["falhas"] += 1
        else:
            item_res["status"] = "nao_encontrado"
            item_res["msg"] = "Nenhuma coordenada ou endereço identificável nos metadados internos"
            stats["falhas"] += 1

        stats["detalhes"].append(item_res)

    return stats
