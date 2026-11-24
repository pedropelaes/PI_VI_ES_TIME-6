"""
Unit tests for the pure helper functions in ml/scripts/ocr_reader.py.

No EasyOCR instance is created here — needs_ocr_fallback and
merge_jersey_reading are stateless, so they're tested directly.
"""
import pytest

from ml.scripts.ocr_reader import (
    _assemble_easyocr_result,
    merge_jersey_reading,
    needs_ocr_fallback,
)


# ===========================================================================
# needs_ocr_fallback
# ===========================================================================

class TestNeedsOcrFallback:
    def test_yolo_read_nothing_skips_fallback_by_default(self):
        assert needs_ocr_fallback(None) is False

    def test_yolo_read_nothing_triggers_fallback_when_enabled(self):
        assert needs_ocr_fallback(None, fallback_on_empty=True) is True

    def test_any_digit_below_threshold_triggers_fallback(self):
        assert needs_ocr_fallback((8, 0.5)) is True
        assert needs_ocr_fallback((5, 0.45)) is True
        assert needs_ocr_fallback((17, 0.59)) is True

    def test_any_digit_at_or_above_threshold_skips_fallback(self):
        # Threshold is exclusive: conf < threshold triggers, conf >= threshold does not.
        assert needs_ocr_fallback((8, 0.60)) is False
        assert needs_ocr_fallback((6, 0.75)) is False
        assert needs_ocr_fallback((17, 0.90)) is False


# ===========================================================================
# merge_jersey_reading
# ===========================================================================

class TestMergeJerseyReading:
    def test_both_none_returns_none(self):
        assert merge_jersey_reading(None, None) is None

    def test_only_yolo_read_returns_yolo_reading(self):
        result = merge_jersey_reading((10, 0.8), None)
        assert result == (10, 0.8, "yolo")

    def test_only_ocr_read_with_high_confidence_returns_ocr_reading(self):
        num, conf, source = merge_jersey_reading(None, (7, 0.9, 1.0))
        assert (num, source) == (7, "ocr")
        assert conf == pytest.approx(0.9 * 0.6)

    def test_only_ocr_read_below_min_confidence_returns_none(self):
        assert merge_jersey_reading(None, (7, 0.3, 1.0)) is None

    def test_only_ocr_read_penalized_by_low_completeness_returns_none(self):
        # 0.5 * 0.4 = 0.2, below EASYOCR_MIN_CONFIDENCE (0.4)
        assert merge_jersey_reading(None, (7, 0.5, 0.4)) is None

    def test_agreement_boosts_confidence_and_marks_source(self):
        num, conf, source = merge_jersey_reading((8, 0.5), (8, 0.9, 1.0))
        assert (num, source) == (8, "yolo+ocr")
        assert conf > 0.5

    def test_agreement_confidence_is_clamped_to_one(self):
        _, conf, _ = merge_jersey_reading((9, 0.95), (9, 0.99, 1.0))
        assert conf <= 1.0

    def test_agreement_below_min_ocr_confidence_does_not_boost(self):
        # effective_ocr = 0.5 * 0.4 = 0.2, below EASYOCR_MIN_CONFIDENCE (0.4)
        result = merge_jersey_reading((8, 0.5), (8, 0.5, 0.4))
        assert result == (8, 0.5, "yolo")

    def test_disagreement_keeps_yolo_by_default(self):
        result = merge_jersey_reading((8, 0.5), (3, 0.9, 1.0))
        assert result == (8, 0.5, "yolo")

    def test_disagreement_ocr_wins_when_override_enabled_and_more_confident(self):
        num, conf, source = merge_jersey_reading(
            (8, 0.5), (3, 0.9, 1.0), allow_override=True
        )
        assert (num, source) == (3, "ocr")
        assert conf == pytest.approx(0.9 * 0.6)

    def test_disagreement_yolo_wins_when_override_enabled_but_ocr_below_minimum(self):
        # effective_ocr = 0.9 * 0.4 = 0.36, below EASYOCR_MIN_CONFIDENCE (0.4)
        result = merge_jersey_reading(
            (8, 0.5), (3, 0.9, 0.4), allow_override=True
        )
        assert result == (8, 0.5, "yolo")

    def test_disagreement_yolo_wins_when_override_enabled_and_yolo_more_confident(self):
        result = merge_jersey_reading(
            (8, 0.85), (3, 0.5, 1.0), allow_override=True
        )
        assert result == (8, 0.85, "yolo")


# ===========================================================================
# _assemble_easyocr_result (previously untested)
# ===========================================================================

class TestAssembleEasyocrResult:
    def test_no_detections_returns_none(self):
        assert _assemble_easyocr_result([]) is None

    def test_single_detection_returns_full_completeness(self):
        detections = [([[0, 0], [10, 0], [10, 10], [0, 10]], "10", 0.8)]
        assert _assemble_easyocr_result(detections) == (10, 0.8, 1.0)

    def test_fragmented_digits_are_concatenated_left_to_right(self):
        # "1" box centered further left than "0" box
        detections = [
            ([[10, 0], [20, 0], [20, 10], [10, 10]], "0", 0.6),
            ([[0, 0], [5, 0], [5, 10], [0, 10]], "1", 0.9),
        ]
        value, avg_conf, completeness = _assemble_easyocr_result(detections)
        assert value == 10
        assert avg_conf == pytest.approx((0.6 + 0.9) / 2)
        assert completeness == 0.4
