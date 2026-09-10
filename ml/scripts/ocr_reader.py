import cv2
import easyocr
import numpy as np
import logging

from ml.scripts.config import (
    OCR_UPSCALE_FACTOR,
    USE_GPU,
    AMBIGUOUS_DIGITS,
    AMBIGUOUS_YOLO_CONFIDENCE_THRESHOLD,
    EASYOCR_MIN_CONFIDENCE,
    EASYOCR_ALONE_VOTE_WEIGHT,
    EASYOCR_AGREEMENT_BONUS,
)

_logger = logging.getLogger(__name__)

# ==========================================================================
# Leitor de fallback baseado em OCR tradicional (EasyOCR).
#
# Só é chamado pelo pipeline quando o modelo YOLO especialista (best.pt,
# ver jersey_reader.py) não encontra nada ou entrega uma leitura de baixa
# "completeness" — ele nunca substitui o modelo customizado, apenas cobre
# os buracos que ele deixa. Por isso usa a API estável `readtext` (por
# imagem) em vez do `readtext_batched`, cuja assinatura muda entre versões
# do EasyOCR: o fallback só roda sobre um subconjunto pequeno de crops,
# então o custo de não batchar é limitado por desenho.
# ==========================================================================


def _assemble_easyocr_result(
    detections: list[tuple[list, str, float]],
) -> tuple[int, float, float] | None:
    """
    detections: saída de reader.readtext (bbox, text, conf) já filtrada
    para strings puramente numéricas e não vazias.
    Retorna (value, avg_conf, completeness) ou None.
    """
    if not detections:
        return None

    if len(detections) == 1:
        _, text, conf = detections[0]
        return (int(text), conf, 1.0)

    # Mais de uma caixa de texto no mesmo crop: o número provavelmente foi
    # partido em fragmentos (ex: "1" e "0" detectados separadamente).
    # Ordena da esquerda para a direita pelo centro X da bbox e concatena,
    # mas com completeness reduzido — leitura menos confiável que uma
    # única string contígua.
    ordered = sorted(detections, key=lambda d: sum(p[0] for p in d[0]) / len(d[0]))
    number_str = "".join(text for _, text, _ in ordered)
    if not number_str:
        return None

    avg_conf = sum(conf for _, _, conf in ordered) / len(ordered)
    return (int(number_str), avg_conf, 0.4)


def needs_ocr_fallback(
    yolo_reading: tuple[int, float] | None,
    ambiguous_digits: frozenset[int] = AMBIGUOUS_DIGITS,
    confidence_threshold: float = AMBIGUOUS_YOLO_CONFIDENCE_THRESHOLD,
) -> bool:
    """
    Decide se um crop deve ser reprocessado pelo EasyOCR.

    True quando:
      (a) o YOLO não leu nada (yolo_reading is None), OU
      (b) o número lido contém algum dígito ambíguo (2/6/8) E a
          confiança média da leitura está abaixo do threshold.
    """
    if yolo_reading is None:
        return True

    number, conf = yolo_reading
    has_ambiguous_digit = any(int(d) in ambiguous_digits for d in str(number))
    return has_ambiguous_digit and conf < confidence_threshold


def merge_jersey_reading(
    yolo_reading: tuple[int, float] | None,
    ocr_reading: tuple[int, float, float] | None,
    min_ocr_confidence: float = EASYOCR_MIN_CONFIDENCE,
    ocr_alone_weight: float = EASYOCR_ALONE_VOTE_WEIGHT,
    agreement_bonus: float = EASYOCR_AGREEMENT_BONUS,
) -> tuple[int, float, str] | None:
    """
    Funde a leitura do YOLO (primário) com a do EasyOCR (fallback).

    Retorna (numero, confianca_final, fonte) ou None se nenhum dos
    dois conseguiu ler. fonte é "yolo", "ocr" ou "yolo+ocr".
    """
    if yolo_reading is None and ocr_reading is None:
        return None

    if yolo_reading is None:
        num, conf, completeness = ocr_reading
        effective = conf * completeness
        if effective < min_ocr_confidence:
            return None
        return (num, effective * ocr_alone_weight, "ocr")

    if ocr_reading is None:
        num, conf = yolo_reading
        return (num, conf, "yolo")

    yolo_num, yolo_conf = yolo_reading
    ocr_num, ocr_conf, ocr_completeness = ocr_reading
    effective_ocr = ocr_conf * ocr_completeness

    if yolo_num == ocr_num:
        return (yolo_num, min(1.0, yolo_conf * agreement_bonus), "yolo+ocr")

    # Discordância: EasyOCR só vence se for suficientemente confiável
    # E melhor que o YOLO — caso contrário mantemos o YOLO, que
    # continua sendo o leitor primário.
    if effective_ocr > yolo_conf and effective_ocr >= min_ocr_confidence:
        return (ocr_num, effective_ocr * ocr_alone_weight, "ocr")

    return (yolo_num, yolo_conf, "yolo")


class TraditionalOcrReader:
    """
    Leitor de fallback baseado em EasyOCR, restrito a dígitos.

    Usado apenas quando o JerseyReader (YOLO especialista) não consegue
    ler o número da camisa com confiança suficiente.
    """

    def __init__(self, use_gpu: bool = USE_GPU) -> None:
        self.use_gpu = use_gpu
        self.upscale_factor = OCR_UPSCALE_FACTOR

        self.reader = easyocr.Reader(["en"], gpu=use_gpu)
        _logger.info("[TraditionalOcrReader] EasyOCR carregado (fallback de OCR).")

    def read_batch(
        self, crops: list[np.ndarray], target_number: int
    ) -> list[list[tuple[int, float, float]]]:
        if not crops:
            return []

        batch_numbers = []
        for crop in crops:
            batch_numbers.append(self._read_single(crop, target_number))

        return batch_numbers

    def _read_single(
        self, crop: np.ndarray, target_number: int
    ) -> list[tuple[int, float, float]]:
        upscaled = cv2.resize(
            crop,
            None,
            fx=self.upscale_factor,
            fy=self.upscale_factor,
            interpolation=cv2.INTER_CUBIC,
        )

        raw_results = self.reader.readtext(
            upscaled,
            allowlist="0123456789",
            detail=1,
        )

        detections = [
            (bbox, text, conf)
            for bbox, text, conf in raw_results
            if text.isdigit()
        ]

        assembled = _assemble_easyocr_result(detections)
        if assembled is None:
            return []

        value, conf, completeness = assembled
        if value == 0 and target_number != 0:
            return []

        return [(value, conf, completeness)]
