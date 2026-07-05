# core/exif.py — Extração de GPS, data e metadados EXIF

import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime


def _get_exif_data(image: Image.Image) -> dict:
    exif_data = {}
    try:
        raw = image._getexif()
        if raw:
            for tag_id, value in raw.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value
    except Exception:
        pass
    return exif_data


def _get_gps_info(exif_data: dict) -> dict:
    gps_info = {}
    raw_gps = exif_data.get("GPSInfo", {})
    for key, val in raw_gps.items():
        tag = GPSTAGS.get(key, key)
        gps_info[tag] = val
    return gps_info


def _to_decimal(dms, ref) -> float | None:
    try:
        d = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        dec = d + m / 60 + s / 3600
        if ref in ("S", "W"):
            dec = -dec
        return dec
    except Exception:
        return None


def extrair_exif(caminho: str) -> dict:
    """
    Retorna dict com:
      - latitude, longitude (float ou None)
      - data_foto (str "DD/MM/YYYY" ou "")
      - largura, altura (int)
    """
    resultado = {
        "latitude":   None,
        "longitude":  None,
        "data_foto":  "",
        "largura":    0,
        "altura":     0,
        "tamanho_mb": 0.0,
    }

    try:
        img = Image.open(caminho)
        resultado["largura"], resultado["altura"] = img.size
        resultado["tamanho_mb"] = round(os.path.getsize(caminho) / 1024 / 1024, 2)

        exif = _get_exif_data(img)

        # Data
        data_raw = exif.get("DateTimeOriginal") or exif.get("DateTime") or ""
        if data_raw:
            try:
                dt = datetime.strptime(data_raw, "%Y:%m:%d %H:%M:%S")
                resultado["data_foto"] = dt.strftime("%d/%m/%Y")
            except Exception:
                pass

        # GPS
        gps = _get_gps_info(exif)
        if gps.get("GPSLatitude") and gps.get("GPSLongitude"):
            lat = _to_decimal(gps["GPSLatitude"],  gps.get("GPSLatitudeRef",  "N"))
            lon = _to_decimal(gps["GPSLongitude"], gps.get("GPSLongitudeRef", "E"))
            resultado["latitude"]  = lat
            resultado["longitude"] = lon

    except Exception:
        pass

    return resultado
