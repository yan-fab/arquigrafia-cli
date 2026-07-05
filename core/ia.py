# core/ia.py — Motor de IA Visual (BLIP + tradução) para análise arquitetônica
# Carregamento lazy: importações pesadas só ocorrem quando analyze_image() é chamado.

import os
import re
import logging
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ─── Cache global para reutilizar o modelo entre fotos ───────────────────────
_processor  = None
_captioner  = None
_translator = None
_ia_pronta  = False
_ia_tentou  = False          # evita tentar carregar de novo se já falhou

STOP_WORDS = {
    "uma", "um", "com", "ao", "na", "no", "em", "para", "por",
    "dos", "das", "aos", "nas", "nos", "que", "de", "da", "do",
    "sobre", "sob", "entre", "frente", "como", "são", "estão",
    "isso", "este", "esta", "ele", "ela", "seu", "sua",
}

PROMPT_BLIP = "an architectural photo of a building featuring"


def carregar_ia(callback=None) -> bool:
    """
    Carrega BLIP e deep_translator na memória.
    callback(msg) é chamado com mensagens de progresso.
    Retorna True se bem-sucedido.
    """
    global _processor, _captioner, _translator, _ia_pronta, _ia_tentou

    if _ia_pronta:
        return True
    if _ia_tentou:
        return False

    _ia_tentou = True

    try:
        if callback:
            callback("Carregando IA visual…")
        logging.info("Iniciando carregamento do modelo BLIP...")

        from transformers import BlipProcessor, BlipForConditionalGeneration
        from deep_translator import GoogleTranslator

        _processor  = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        _captioner  = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base"
        )
        _translator = GoogleTranslator(source="en", target="pt")

        _ia_pronta = True
        logging.info("Modelo BLIP carregado com sucesso.")
        return True

    except Exception as e:
        logging.warning(f"Falha ao carregar IA: {e}")
        if callback:
            callback("IA indisponível — usando GPS")
        return False


def analisar_imagem(caminho: str, geo: dict, callback=None) -> tuple[str, list[str]]:
    """
    Analisa a imagem com BLIP e gera descrição + tags visuais.
    Sempre retorna (descricao_str, lista_tags) mesmo se a IA falhar.
    """
    cidade  = geo.get("cidade", "")
    estado  = geo.get("estado", "")
    regiao  = geo.get("regiao", "")
    local   = geo.get("local", "") or regiao

    # Descrição base (sem IA)
    if local and cidade:
        desc_base = f"Fotografia arquitetônica de {local}, {cidade} – {estado}."
    elif cidade:
        desc_base = f"Fotografia arquitetônica em {cidade} – {estado}."
    else:
        desc_base = "Fotografia arquitetônica."

    tags_base = _gerar_tags_geo(geo)

    # Tenta enriquecer com IA
    if not _ia_pronta:
        if not carregar_ia(callback):
            return desc_base, tags_base

    try:
        if callback:
            callback("IA analisando estrutura…")

        from PIL import Image as PILImage

        raw = PILImage.open(caminho).convert("RGB")
        inputs = _processor(raw, text=PROMPT_BLIP, return_tensors="pt")
        out    = _captioner.generate(**inputs, max_new_tokens=40)
        texto_en = _processor.decode(out[0], skip_special_tokens=True)

        # Remove o prefixo do prompt, deixa só a parte nova
        if texto_en.startswith(PROMPT_BLIP):
            texto_en = texto_en[len(PROMPT_BLIP):].strip()

        texto_pt = _translator.translate(texto_en)
        if texto_pt:
            texto_pt = texto_pt.capitalize()
            if not texto_pt.endswith("."):
                texto_pt += "."
        else:
            texto_pt = ""

        logging.info(f"IA desc: EN='{texto_en}' PT='{texto_pt}'")

        # Tags visuais extraídas da descrição
        tags_ia = _extrair_tags(texto_pt)

        # Mescla e deduplica
        todas_tags = sorted(set(tags_base + tags_ia))

        # Descrição final
        desc_final = desc_base
        if texto_pt:
            desc_final = desc_base.rstrip(".") + f". {texto_pt}"

        return desc_final, todas_tags

    except Exception as e:
        logging.warning(f"Erro IA ao analisar {os.path.basename(caminho)}: {e}")
        return desc_base, tags_base


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _gerar_tags_geo(geo: dict) -> list[str]:
    tags = ["arquitetura", "fotografia"]

    for campo in ("cidade", "estado", "regiao"):
        val = geo.get(campo, "")
        if val:
            tags.append(val.lower())

    return sorted(set(tags))


def _extrair_tags(texto: str) -> list[str]:
    palavras = re.findall(
        r"\b[a-zA-ZáàãâéèêíïóôõöúçÁÀÃÂÉÈÊÍÏÓÔÕÖÚÇ]+\b",
        texto.lower()
    )
    return [p for p in palavras if len(p) >= 4 and p not in STOP_WORDS]
