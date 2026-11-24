"""
Unit tests for JerseyReader digit assembly and confidence handling.

YOLO inference is mocked so no model weights or GPU are required.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from ml.scripts.jersey_reader import JerseyReader


def _box(x_min: float, cls_id: int, conf: float) -> SimpleNamespace:
    return SimpleNamespace(
        xyxy=[[x_min, 0.0, x_min + 10.0, 20.0]],
        cls=[cls_id],
        conf=[conf],
    )


def _make_reader(results_list: list[list[SimpleNamespace]]) -> JerseyReader:
    reader = JerseyReader(model_path="dummy.pt")
    reader.model = MagicMock(
        return_value=[SimpleNamespace(boxes=boxes) for boxes in results_list]
    )
    return reader


class TestJerseyReader:
    def test_single_digit_eight_below_legacy_threshold_is_kept(self):
        crop = np.zeros((40, 20, 3), dtype=np.uint8)

        reader_batch = _make_reader([[_box(5.0, 8, 0.55)]])
        assert reader_batch.read_batch([crop], target_number=-1) == [[(8, 0.55)]]

        reader_single = _make_reader([[_box(5.0, 8, 0.55)]])
        assert reader_single._read_numbers(crop, target_number=-1) == [(8, 0.55)]

    def test_compound_number_with_eight_is_not_truncated(self):
        crop = np.zeros((40, 20, 3), dtype=np.uint8)
        boxes = [_box(5.0, 1, 0.85), _box(18.0, 8, 0.55)]

        reader_batch = _make_reader([boxes])
        batch_result = reader_batch.read_batch([crop], target_number=-1)
        assert len(batch_result) == 1
        assert batch_result[0][0][0] == 18
        assert batch_result[0][0][1] == pytest.approx(0.70)

        reader_single = _make_reader([boxes])
        single_result = reader_single._read_numbers(crop, target_number=-1)
        assert single_result[0][0] == 18
        assert single_result[0][1] == pytest.approx(0.70)

    def test_digits_are_sorted_left_to_right_by_x_min(self):
        crop = np.zeros((40, 20, 3), dtype=np.uint8)
        boxes = [_box(30.0, 0, 0.90), _box(10.0, 1, 0.80)]

        reader_batch = _make_reader([boxes])
        batch_result = reader_batch.read_batch([crop], target_number=-1)
        assert batch_result[0][0][0] == 10
        assert batch_result[0][0][1] == pytest.approx(0.85)

        reader_single = _make_reader([boxes])
        single_result = reader_single._read_numbers(crop, target_number=-1)
        assert single_result[0][0] == 10
        assert single_result[0][1] == pytest.approx(0.85)

    def test_zero_is_filtered_unless_target_is_zero(self):
        crop = np.zeros((40, 20, 3), dtype=np.uint8)
        boxes = [_box(10.0, 0, 0.92)]

        reader_non_zero = _make_reader([boxes])
        assert reader_non_zero.read_batch([crop], target_number=10) == [[]]

        reader_single_non_zero = _make_reader([boxes])
        assert reader_single_non_zero._read_numbers(crop, target_number=10) == []

        reader_zero_target = _make_reader([boxes])
        assert reader_zero_target.read_batch([crop], target_number=0) == [[(0, 0.92)]]

        reader_single_zero = _make_reader([boxes])
        assert reader_single_zero._read_numbers(crop, target_number=0) == [(0, 0.92)]
