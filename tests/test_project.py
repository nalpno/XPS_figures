"""Project file round trip (save / restore of the figure configuration)."""

from __future__ import annotations

import json

import numpy as np
import pytest

import app


@pytest.fixture
def state() -> dict:
    panel = app.default_panel("C1s")
    panel.update({
        "kind": "decon", "decon_sample": "LZO(850 °C)", "decon_label": "LZO(850 °C)",
        # st.data_editor hands back numpy scalars
        "annotations": [{"text": "Zn2p", "x": np.float64(1021.3), "y": np.float64(0.85),
                         "arrow": np.bool_(True), "target_x": np.float64(1021.3)}],
    })
    return {
        "assign": {"a.xlsx": "LZO(850 °C)"},
        "sample_order": ["LZO(850 °C)"],
        "sample_style": {"LZO(850 °C)": {"color": "#2B5FCB", "be_shift": 0.28,
                                         "linestyle": "--", "linewidth": 1.6}},
        "comp_colors": {"LZO(850 °C)|C1s|C1s Scan A": "#B39DDB"},
        "comp_names": {"LZO(850 °C)|C1s|C1s Scan A": "C–C / C–H"},
        "panels": [panel],
        "layout": {"nrows": 1, "ncols": 1, "width": 9.0, "height": 7.0},
        "preset": "Tek panel",
        "sty_font": "Arial",
        "sty_size": 9.0,
        "sty_lw": 1.2,
        "sty_axw": 1.2,
        "sty_tick": 4.0,
        "sty_tickdir": "in",
        "sty_palette": "Origin (siyah-kırmızı-mavi-yeşil-mor)",
        "sty_fill": "Pastel (Avantage benzeri)",
    }


def test_round_trip_preserves_everything(state):
    restored = app.load_project(app.dump_project(state))
    for key, value in state.items():
        if key == "panels":
            continue                      # compared separately below
        assert restored[key] == value, key


def test_numpy_scalars_are_serialised(state):
    payload = json.loads(app.dump_project(state).decode("utf-8"))
    annotation = payload["state"]["panels"][0]["annotations"][0]
    assert annotation["x"] == 1021.3
    assert annotation["arrow"] is True


def test_charge_shift_and_line_style_survive(state):
    restored = app.load_project(app.dump_project(state))
    entry = restored["sample_style"]["LZO(850 °C)"]
    assert entry["be_shift"] == 0.28
    assert entry["linestyle"] == "--"
    assert entry["linewidth"] == 1.6


def test_renamed_components_survive(state):
    restored = app.load_project(app.dump_project(state))
    assert restored["comp_names"]["LZO(850 °C)|C1s|C1s Scan A"] == "C–C / C–H"


def test_old_project_gains_new_panel_options(state):
    """A project saved before an option existed must still load."""
    payload = json.loads(app.dump_project(state).decode("utf-8"))
    stripped = {k: v for k, v in payload["state"]["panels"][0].items()
                if k in {"region", "kind", "decon_sample"}}
    payload["state"]["panels"] = [stripped]

    restored = app.load_project(json.dumps(payload).encode("utf-8"))
    panel = restored["panels"][0]
    assert panel["region"] == "C1s" and panel["kind"] == "decon"
    assert panel["fill_alpha"] == 0.55          # default filled in
    assert "decon_label_loc" in panel


def test_missing_keys_are_skipped():
    restored = app.load_project(json.dumps({"version": 1, "state": {"preset": "Tek panel"}}).encode())
    assert restored == {"preset": "Tek panel"}


def test_bare_state_without_version_is_accepted(state):
    restored = app.load_project(json.dumps({"preset": "Tek panel"}).encode("utf-8"))
    assert restored["preset"] == "Tek panel"


def test_decon_stack_preset_makes_one_panel_per_sample():
    class FakeDataset:
        regions = {"C1s": None}

    sample_list = [("A", FakeDataset()), ("B", FakeDataset()), ("C", FakeDataset())]
    panels = app.panels_for_preset(app.DECON_STACK_PRESET, sample_list, ["Survey", "C1s"])

    assert len(panels) == 3
    assert [p["decon_sample"] for p in panels] == ["A", "B", "C"]
    assert all(p["kind"] == "decon" for p in panels)
    assert all(p["region"] == "C1s" for p in panels)      # Survey is skipped
    assert [p["decon_label"] for p in panels] == ["A", "B", "C"]


def test_hide_inner_x_labels_keeps_bottom_of_each_column():
    from xpsfig import plotting

    # 2x2 grid, panels laid out sequentially
    panels = [plotting.Panel() for _ in range(4)]
    app.hide_inner_x_labels(panels, ncols=2)
    assert [p.show_xtick_labels for p in panels] == [False, False, True, True]


def test_hide_inner_x_labels_respects_explicit_grid():
    from xpsfig import plotting

    # the 5-panel layout: three on top, two centred below
    panels = [plotting.Panel() for _ in range(5)]
    for panel, grid in zip(panels, app.PRESET_GRIDS["5 panel (3 üst + 2 alt ortalı)"]):
        panel.grid = grid
    app.hide_inner_x_labels(panels, ncols=6)

    # bottom panels sit in columns 1 and 3; the top row spans columns 0, 2 and 4,
    # so each of those columns has its own bottom-most panel
    assert [p.show_xtick_labels for p in panels] == [True, True, True, True, True]


def test_hide_inner_x_labels_single_column_stack():
    from xpsfig import plotting

    panels = [plotting.Panel() for _ in range(4)]
    app.hide_inner_x_labels(panels, ncols=1)
    assert [p.show_xtick_labels for p in panels] == [False, False, False, True]


def test_grid_preset_panel_count():
    panels = app.panels_for_preset("5 panel (3 üst + 2 alt ortalı)", [], ["Survey", "Zn2p"])
    assert len(panels) == 5
    panels = app.panels_for_preset("4 panel (2×2)", [], ["Survey"])
    assert len(panels) == 4
