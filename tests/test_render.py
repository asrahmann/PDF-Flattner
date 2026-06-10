import pytest

from pdfflatten.render import MAX_RENDER_PIXELS, clamped_scale, page_count


def test_normal_page_scale_unchanged():
    # A letter page at 200 dpi is ~3.7M pixels — far under the budget.
    assert clamped_scale(612, 792, 200) == pytest.approx(200 / 72)


def test_huge_page_scale_is_clamped():
    # The PDF maximum page (200x200 in = 14400x14400 pt) at 200 dpi would be
    # 1.6 billion pixels; the clamp must bring it down to the budget.
    scale = clamped_scale(14400, 14400, 200)
    assert scale < 200 / 72
    pixels = (14400 * scale) * (14400 * scale)
    assert pixels == pytest.approx(MAX_RENDER_PIXELS, rel=0.01)


def test_explicit_budget_overrides_default():
    scale = clamped_scale(612, 792, 200, max_pixels=100_000)
    pixels = (612 * scale) * (792 * scale)
    assert pixels == pytest.approx(100_000, rel=0.01)


def test_zero_sized_page_does_not_crash():
    assert clamped_scale(0, 0, 200) == pytest.approx(200 / 72)


def test_page_count_multi(multi_page_pdf):
    assert page_count(multi_page_pdf.read_bytes()) == 3


def test_page_count_single(base_pdf):
    assert page_count(base_pdf.read_bytes()) == 1
