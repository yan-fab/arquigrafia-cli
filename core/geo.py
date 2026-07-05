# core/geo.py — Geolocalização com cache local

import json, os, time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

_geolocator = Nominatim(user_agent="arquigrafia_uploader_v2", timeout=10)
_CACHE_FILE  = os.path.join(os.path.dirname(__file__), ".geo_cache.json")
_cache: dict = {}


def _load_cache():
    global _cache
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}


def _save_cache():
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_load_cache()


def geocodificar(lat: float, lon: float) -> dict:
    """
    Retorna dict com:
      - cidade, estado, pais, regiao, descricao
    Usa cache para evitar chamadas repetidas.
    """
    chave = f"{lat:.4f},{lon:.4f}"
    if chave in _cache:
        return _cache[chave]

    resultado = {
        "cidade":    "",
        "estado":    "",
        "pais":      "Brasil",
        "regiao":    "",
        "descricao": "",
        "local":     "",
    }

    try:
        time.sleep(1.1)  # Respeita rate limit do Nominatim
        location = _geolocator.reverse((lat, lon), language="pt-BR")
        if location and location.raw.get("address"):
            addr = location.raw["address"]
            resultado["cidade"]  = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or ""
            resultado["estado"]  = addr.get("state", "")
            resultado["pais"]    = addr.get("country", "Brasil")
            resultado["regiao"]  = addr.get("suburb") or addr.get("neighbourhood") or addr.get("district") or ""
            
            # Ponto de Interesse (POI)
            chaves_poi = ['amenity', 'tourism', 'historic', 'building', 'leisure', 'museum', 'gallery', 'railway', 'station']
            poi_encontrado = None
            for chave in chaves_poi:
                if chave in addr:
                    poi_encontrado = addr[chave]
                    break
            
            if not poi_encontrado:
                rua = addr.get('road', '')
                bairro = addr.get('suburb', addr.get('neighbourhood', ''))
                if rua:
                    poi_encontrado = rua
                    if bairro:
                        poi_encontrado += f", {bairro}"
                else:
                    poi_encontrado = bairro or resultado["cidade"]

            resultado["local"] = poi_encontrado
            
            # Monta descrição legível: "Paraty, Rio de Janeiro"
            partes = [p for p in [resultado["cidade"], resultado["estado"]] if p]
            resultado["descricao"] = ", ".join(partes) if partes else location.address[:80]

    except GeocoderTimedOut:
        resultado["descricao"] = "Timeout na geolocalização"
    except Exception as e:
        resultado["descricao"] = str(e)[:60]

    _cache[chave] = resultado
    _save_cache()
    return resultado
