"""XPS Figure Studio - Avantage .xlsx dosyalarından yayın kalitesinde figür ve tablo.

Çalıştırmak için:  streamlit run app.py
"""

from __future__ import annotations

import io
import re
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from xpsfig import export, parser, plotting, style, tables

st.set_page_config(page_title="XPS Figure Studio", page_icon="📈", layout="wide")

PRESETS = {
    "Tek panel": {"nrows": 1, "ncols": 1, "width": 9.0, "height": 7.0},
    "2 panel (yan yana)": {"nrows": 1, "ncols": 2, "width": 17.0, "height": 7.0},
    "4 panel (2×2)": {"nrows": 2, "ncols": 2, "width": 17.0, "height": 13.0},
    "4 panel (yan yana)": {"nrows": 1, "ncols": 4, "width": 19.0, "height": 6.5},
    "5 panel (3 üst + 2 alt ortalı)": {"nrows": 2, "ncols": 6, "width": 18.0, "height": 13.0},
    "6 panel (2×3)": {"nrows": 2, "ncols": 3, "width": 18.0, "height": 12.0},
}

PRESET_GRIDS = {
    "5 panel (3 üst + 2 alt ortalı)": [
        (0, 0, 1, 2), (0, 2, 1, 2), (0, 4, 1, 2), (1, 1, 1, 2), (1, 3, 1, 2),
    ],
}

LETTERS = "abcdefghijklmnop"
LEGEND_LOCS = [
    "upper right", "upper left", "lower right", "lower left",
    "center right", "center left", "upper center", "lower center", "best",
]


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------
def init_state() -> None:
    defaults = {
        "datasets": {},        # filename -> Dataset
        "assign": {},          # filename -> sample label
        "sample_order": [],    # ordered sample labels
        "sample_style": {},    # label -> {"color", "linewidth", "linestyle"}
        "comp_colors": {},     # "sample|region|component" -> hex
        "comp_names": {},      # "sample|region|component" -> display name
        "panels": [],
        "layout": dict(PRESETS["Tek panel"]),
        "preset": "Tek panel",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


@st.cache_data(show_spinner=False)
def parse_bytes(name: str, data: bytes, drop_zeros: bool) -> parser.Dataset:
    return parser.load_workbook_dataset(io.BytesIO(data), label=None, drop_zeros=drop_zeros)


def guess_sample_name(dataset: parser.Dataset, filename: str) -> str:
    """Strip Avantage's export suffixes so survey/core/decon files group together."""
    base = dataset.title or re.sub(r"\.xlsx?$", "", filename, flags=re.IGNORECASE)
    base = re.sub(r"[-_ ]*(decon\w*|core|survey|wide|fit\d*)\s*$", "", base, flags=re.IGNORECASE)
    return base.strip(" -_") or filename


def samples() -> list[tuple[str, parser.Dataset]]:
    """Merged datasets in user order, only for labels that still have files."""
    groups: dict[str, list[parser.Dataset]] = {}
    for filename, label in st.session_state.assign.items():
        ds = st.session_state.datasets.get(filename)
        if ds is not None and label:
            groups.setdefault(label, []).append(ds)

    ordered = [l for l in st.session_state.sample_order if l in groups]
    ordered += [l for l in groups if l not in ordered]
    st.session_state.sample_order = ordered
    return [(label, parser.merge_datasets(groups[label], label)) for label in ordered]


def sample_color(label: str, index: int, palette: str) -> str:
    entry = st.session_state.sample_style.setdefault(label, {})
    if "color" not in entry:
        entry["color"] = style.line_colors(palette, index + 1)[index]
    return entry["color"]


def all_regions(sample_list: list[tuple[str, parser.Dataset]]) -> list[str]:
    names: list[str] = []
    for _, ds in sample_list:
        for region in ds.region_names:
            if region not in names:
                names.append(region)
    return names


# ---------------------------------------------------------------------------
# sidebar: global style
# ---------------------------------------------------------------------------
def sidebar_style() -> dict[str, Any]:
    st.sidebar.header("🎨 Genel stil")

    fonts = style.available_fonts()
    font = st.sidebar.selectbox("Yazı tipi", fonts, index=0)
    if not style.font_is_installed(font):
        st.sidebar.caption(f"⚠️ {font} sistemde kurulu değil; en yakın alternatif kullanılacak.")

    c1, c2 = st.sidebar.columns(2)
    base_size = c1.number_input("Yazı boyutu (pt)", 5.0, 20.0, 9.0, 0.5)
    line_width = c2.number_input("Çizgi kalınlığı", 0.3, 4.0, 1.2, 0.1)
    axes_width = c1.number_input("Çerçeve kalınlığı", 0.3, 4.0, 1.2, 0.1)
    tick_length = c2.number_input("Tick uzunluğu", 1.0, 10.0, 4.0, 0.5)
    tick_dir = st.sidebar.radio("Tick yönü", ["in", "out", "inout"], horizontal=True, index=0)

    palette = st.sidebar.selectbox("Numune renk paleti", list(style.LINE_PALETTES),
                                   index=list(style.LINE_PALETTES).index(style.DEFAULT_LINE_PALETTE))
    fill_palette = st.sidebar.selectbox("Dekonvolüsyon dolgu paleti", list(style.FILL_PALETTES),
                                        index=list(style.FILL_PALETTES).index(style.DEFAULT_FILL_PALETTE))

    if st.sidebar.button("🔄 Renkleri paletten yenile", width="stretch"):
        for entry in st.session_state.sample_style.values():
            entry.pop("color", None)
        st.session_state.comp_colors.clear()
        st.rerun()

    style.apply_style(font, base_size, line_width, axes_width, tick_length, tick_dir)
    return {
        "font": font, "base_size": base_size, "line_width": line_width,
        "palette": palette, "fill_palette": fill_palette,
    }


# ---------------------------------------------------------------------------
# tab 1: data
# ---------------------------------------------------------------------------
def tab_data() -> None:
    st.subheader("1 · Avantage .xlsx dosyalarını yükleyin")
    st.caption(
        "Survey, core ve deconvolution dosyalarını birlikte yükleyebilirsiniz. "
        "Aynı **numune adını** taşıyan dosyalar tek bir numune olarak birleştirilir "
        "(dekonvolüsyonlu bölge, dekonvolüsyonsuz olanın yerine geçer)."
    )

    drop_zeros = st.checkbox(
        "Avantage kenar artefaktını temizle (fit kanallarındaki sıfır değerleri gizle)",
        value=True,
        help="Avantage bileşen/arka plan sütunlarının ilk satırına 0 yazar; "
             "temizlenmezse eğri grafiğin dibine çakılır.",
    )

    uploaded = st.file_uploader(
        "Dosyalar", type=["xlsx", "xlsm"], accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded:
        for file in uploaded:
            if file.name in st.session_state.datasets:
                continue
            try:
                ds = parse_bytes(file.name, file.getvalue(), drop_zeros)
            except Exception as exc:                      # noqa: BLE001
                st.error(f"**{file.name}** okunamadı: {exc}")
                continue
            st.session_state.datasets[file.name] = ds
            st.session_state.assign[file.name] = guess_sample_name(ds, file.name)

    if not st.session_state.datasets:
        st.info("Henüz dosya yüklenmedi.")
        return

    st.divider()
    st.subheader("2 · Numune gruplaması ve isimlendirme")
    st.caption("**Numune** sütununa aynı adı yazdığınız dosyalar birleştirilir. "
               "Grafik ve tablolarda bu ad görünür.")

    rows = []
    for filename, ds in st.session_state.datasets.items():
        rows.append({
            "Dosya": filename,
            "Numune": st.session_state.assign.get(filename, ""),
            "Bölgeler": ", ".join(ds.region_names) or "—",
            "Fit bileşeni": sum(len(r.components) for r in ds.regions.values()),
            "Peak Table satırı": len(ds.peaks),
        })
    edited = st.data_editor(
        pd.DataFrame(rows),
        column_config={
            "Dosya": st.column_config.TextColumn(disabled=True, width="medium"),
            "Numune": st.column_config.TextColumn(required=True, width="medium"),
            "Bölgeler": st.column_config.TextColumn(disabled=True, width="medium"),
            "Fit bileşeni": st.column_config.NumberColumn(disabled=True, width="small"),
            "Peak Table satırı": st.column_config.NumberColumn(disabled=True, width="small"),
        },
        hide_index=True, width="stretch", key="file_editor",
    )
    for record in edited.to_dict("records"):
        st.session_state.assign[record["Dosya"]] = str(record["Numune"]).strip()

    sample_list = samples()
    if not sample_list:
        return

    st.divider()
    st.subheader("3 · Sıra ve renkler")

    order_labels = st.multiselect(
        "Çizim sırası (alttan üste)", [l for l, _ in sample_list],
        default=st.session_state.sample_order,
        help="Yığılmış grafiklerde ilk numune en altta yer alır.",
    )
    if order_labels and order_labels != st.session_state.sample_order:
        st.session_state.sample_order = order_labels
        st.rerun()

    cols = st.columns(min(5, len(sample_list)))
    for i, (label, ds) in enumerate(sample_list):
        with cols[i % len(cols)]:
            current = sample_color(label, i, st.session_state["_palette"])
            picked = st.color_picker(label, current, key=f"color_{label}")
            st.session_state.sample_style[label]["color"] = picked
            st.caption(f"{len(ds.regions)} bölge · {len(ds.peaks)} pik")

    with st.expander("📋 Ölçüm parametreleri (Avantage metadata)"):
        for label, ds in sample_list:
            st.markdown(f"**{label}**")
            meta_rows = []
            for region_name, region in ds.regions.items():
                meta_rows.append({"Bölge": region_name, "Nokta": len(region.energy),
                                  "Aralık (eV)": f"{region.energy_range[1]:.1f} – {region.energy_range[0]:.1f}",
                                  **{k: v for k, v in region.metadata.items() if k != "Source File"}})
            if meta_rows:
                st.dataframe(pd.DataFrame(meta_rows), hide_index=True, width="stretch")

    if st.button("🗑️ Tüm dosyaları temizle"):
        for key in ("datasets", "assign", "sample_order", "sample_style", "comp_colors", "comp_names", "panels"):
            st.session_state[key] = type(st.session_state[key])()
        st.rerun()


# ---------------------------------------------------------------------------
# tab 2: figure builder
# ---------------------------------------------------------------------------
def default_panel(region: str) -> dict[str, Any]:
    return {
        "region": region,
        "kind": "stack",
        "samples": [],
        "decon_sample": None,
        "normalize": "Yok (ham şiddet)",
        "offset": 0.55,
        "auto_x": True,
        "xmin": 0.0,
        "xmax": 1000.0,
        "xtick_step": 0.0,
        "inner_label": region if region != "Survey" else "",
        "xlabel": "Binding Energy (eV)",
        "ylabel": "Intensity (a.u.)",
        "label_mode": "legend",
        "legend_mode": "none",
        "legend_loc": "upper right",
        "legend_ncol": 1,
        "show_residual": False,
        "fill_alpha": 0.55,
        "show_bg": True,
        "show_env": True,
        "show_raw": True,
        "marker_size": 12.0,
        "decon_label": "",
        "decon_label_loc": "lower left",
        "annotations": [],
    }


def build_panel(cfg: dict[str, Any], sample_list, opts) -> tuple[plotting.Panel, list[float] | None]:
    lookup = dict(sample_list)
    region_name = cfg["region"]

    panel = plotting.Panel(
        kind=cfg["kind"],
        inner_label=cfg["inner_label"],
        xlabel=cfg["xlabel"],
        ylabel=cfg["ylabel"],
        xtick_step=cfg["xtick_step"] or None,
        legend_mode=cfg["legend_mode"],
        legend_loc=cfg["legend_loc"],
        legend_ncol=int(cfg["legend_ncol"]),
        label_mode=cfg["label_mode"],
        annotations=cfg.get("annotations", []),
    )
    if not cfg["auto_x"]:
        panel.xlim = (max(cfg["xmin"], cfg["xmax"]), min(cfg["xmin"], cfg["xmax"]))

    offsets = None

    if cfg["kind"] == "decon":
        label = cfg.get("decon_sample")
        ds = lookup.get(label)
        region = ds.regions.get(region_name) if ds else None
        if region is not None:
            comps = []
            for j, series in enumerate(region.components):
                key = f"{label}|{region_name}|{series.name}"
                color = st.session_state.comp_colors.setdefault(
                    key, style.fill_colors(opts["fill_palette"], j + 1)[j])
                name = st.session_state.comp_names.get(key, series.name)
                comps.append((name, series.y, color))
            bg = region.by_kind(parser.BACKGROUND)
            env = region.by_kind(parser.ENVELOPE)
            res = region.by_kind(parser.RESIDUAL)
            raw = region.raw
            panel.decon = plotting.DeconCurves(
                x=region.energy,
                raw=raw.y if (raw and cfg["show_raw"]) else None,
                components=comps,
                background=bg[0].y if (bg and cfg["show_bg"]) else None,
                envelope=env[0].y if (env and cfg["show_env"]) else None,
                residual=res[0].y if (res and cfg["show_residual"]) else None,
                sample_label=cfg.get("decon_label", ""),
                label_loc=cfg.get("decon_label_loc", "lower left"),
            )
        return panel, None

    mode = plotting.NORMALIZATIONS[cfg["normalize"]]
    ys = []
    for label in cfg["samples"]:
        ds = lookup.get(label)
        region = ds.regions.get(region_name) if ds else None
        if region is None or region.raw is None:
            continue
        y = plotting.normalize(region.raw.y, mode)
        entry = st.session_state.sample_style.get(label, {})
        panel.curves.append(plotting.Curve(
            x=region.energy, y=y, label=label,
            color=entry.get("color", "#000000"),
            linewidth=entry.get("linewidth", opts["line_width"]),
            linestyle=entry.get("linestyle", "-"),
        ))
        ys.append(y)

    if ys and cfg["offset"] > 0:
        offsets = plotting.stack_offsets(ys, cfg["offset"])
    if cfg["label_mode"] != "legend":
        panel.legend_mode = "none" if cfg["label_mode"] != "legend" else panel.legend_mode
    return panel, offsets


def panel_editor(index: int, cfg: dict[str, Any], sample_list, regions, opts) -> None:
    labels = [l for l, _ in sample_list]

    cfg["region"] = st.selectbox(
        "Bölge", regions, index=regions.index(cfg["region"]) if cfg["region"] in regions else 0,
        key=f"p{index}_region",
    )
    cfg["kind"] = st.radio(
        "Panel tipi", ["stack", "decon"], horizontal=True,
        format_func=lambda k: "Numune karşılaştırma" if k == "stack" else "Dekonvolüsyon",
        index=0 if cfg["kind"] == "stack" else 1, key=f"p{index}_kind",
    )

    if cfg["kind"] == "stack":
        cfg["samples"] = st.multiselect(
            "Numuneler", labels,
            default=[s for s in cfg["samples"] if s in labels] or labels,
            key=f"p{index}_samples",
        )
        c1, c2 = st.columns(2)
        cfg["normalize"] = c1.selectbox(
            "Normalizasyon", list(plotting.NORMALIZATIONS),
            index=list(plotting.NORMALIZATIONS).index(cfg["normalize"]), key=f"p{index}_norm",
        )
        cfg["offset"] = c2.slider(
            "Dikey kaydırma", 0.0, 2.0, float(cfg["offset"]), 0.05, key=f"p{index}_offset",
            help="0 = tam üst üste çizim (overlay).",
        )
        cfg["label_mode"] = st.radio(
            "Numune etiketi", ["legend", "inline", "none"], horizontal=True,
            format_func={"legend": "Legend", "inline": "Eğri yanında", "none": "Yok"}.get,
            index=["legend", "inline", "none"].index(cfg["label_mode"]), key=f"p{index}_labelmode",
        )
    else:
        options = [l for l in labels if cfg["region"] in dict(sample_list)[l].regions]
        if not options:
            st.warning("Bu bölge için yüklenmiş numune yok.")
            return
        current = cfg.get("decon_sample")
        cfg["decon_sample"] = st.selectbox(
            "Numune", options,
            index=options.index(current) if current in options else 0, key=f"p{index}_dsample",
        )
        c1, c2, c3, c4 = st.columns(4)
        cfg["show_raw"] = c1.checkbox("Ham veri", cfg["show_raw"], key=f"p{index}_raw")
        cfg["show_bg"] = c2.checkbox("Background", cfg["show_bg"], key=f"p{index}_bg")
        cfg["show_env"] = c3.checkbox("Envelope", cfg["show_env"], key=f"p{index}_env")
        cfg["show_residual"] = c4.checkbox("Residual", cfg["show_residual"], key=f"p{index}_res")
        cfg["fill_alpha"] = st.slider("Dolgu saydamlığı", 0.1, 1.0, float(cfg["fill_alpha"]), 0.05,
                                      key=f"p{index}_alpha")
        cfg["marker_size"] = st.slider("Ham veri sembol boyutu", 2.0, 40.0,
                                       float(cfg["marker_size"]), 1.0, key=f"p{index}_ms")
        c1, c2 = st.columns([2, 1])
        cfg["decon_label"] = c1.text_input(
            "Panel içi numune etiketi", cfg.get("decon_label", ""), key=f"p{index}_dlabel",
            placeholder="ör. LZO(850 °C)",
        )
        locs = ["lower left", "lower right", "upper left", "upper right"]
        cfg["decon_label_loc"] = c2.selectbox(
            "Konum", locs, index=locs.index(cfg.get("decon_label_loc", "lower left")),
            key=f"p{index}_dlabelloc",
        )

        ds = dict(sample_list)[cfg["decon_sample"]]
        region = ds.regions.get(cfg["region"])
        if region and region.components:
            st.markdown("**Bileşen renkleri ve isimleri**")
            for j, series in enumerate(region.components):
                key = f"{cfg['decon_sample']}|{cfg['region']}|{series.name}"
                default_color = st.session_state.comp_colors.setdefault(
                    key, style.fill_colors(opts["fill_palette"], j + 1)[j])
                cc1, cc2 = st.columns([1, 3])
                st.session_state.comp_colors[key] = cc1.color_picker(
                    " ", default_color, key=f"p{index}_cc{j}", label_visibility="collapsed")
                st.session_state.comp_names[key] = cc2.text_input(
                    " ", st.session_state.comp_names.get(key, series.name),
                    key=f"p{index}_cn{j}", label_visibility="collapsed")
        elif region:
            st.info("Bu bölgede fit bileşeni yok — dekonvolüsyon dosyasını yükleyin.")

    st.markdown("**Eksenler**")
    cfg["auto_x"] = st.checkbox("X aralığı otomatik", cfg["auto_x"], key=f"p{index}_autox")
    if not cfg["auto_x"]:
        c1, c2, c3 = st.columns(3)
        cfg["xmax"] = c1.number_input("Sol kenar (yüksek BE)", value=float(cfg["xmax"]), key=f"p{index}_xmax")
        cfg["xmin"] = c2.number_input("Sağ kenar (düşük BE)", value=float(cfg["xmin"]), key=f"p{index}_xmin")
        cfg["xtick_step"] = c3.number_input("Tick aralığı (0=oto)", value=float(cfg["xtick_step"]),
                                            min_value=0.0, key=f"p{index}_xstep")
    c1, c2 = st.columns(2)
    cfg["xlabel"] = c1.text_input("X başlığı", cfg["xlabel"], key=f"p{index}_xlabel")
    cfg["ylabel"] = c2.text_input("Y başlığı", cfg["ylabel"], key=f"p{index}_ylabel")
    cfg["inner_label"] = st.text_input("Panel içi etiket", cfg["inner_label"], key=f"p{index}_inner")

    c1, c2, c3 = st.columns(3)
    cfg["legend_mode"] = c1.selectbox(
        "Legend", ["none", "inside", "outside"],
        format_func={"none": "Yok", "inside": "Panel içinde", "outside": "Panel dışında"}.get,
        index=["none", "inside", "outside"].index(cfg["legend_mode"]), key=f"p{index}_legmode",
    )
    cfg["legend_loc"] = c2.selectbox("Legend konumu", LEGEND_LOCS,
                                     index=LEGEND_LOCS.index(cfg["legend_loc"]), key=f"p{index}_legloc")
    cfg["legend_ncol"] = c3.number_input("Legend sütunu", 1, 6, int(cfg["legend_ncol"]), key=f"p{index}_legncol")

    with st.expander("🔖 Pik etiketleri / oklar"):
        st.caption("Survey grafiklerinde Zn2p, La3d gibi etiketleri yerleştirmek için. "
                   "**BE** = etiketin bağlanma enerjisi, **Y** = panel içi yükseklik (0–1).")
        ann_df = pd.DataFrame(cfg.get("annotations") or
                              [{"text": "", "x": 0.0, "y": 0.9, "arrow": True, "target_x": 0.0}])
        edited = st.data_editor(
            ann_df, num_rows="dynamic", hide_index=True, width="stretch",
            column_config={
                "text": st.column_config.TextColumn("Etiket"),
                "x": st.column_config.NumberColumn("Etiket BE", format="%.1f"),
                "y": st.column_config.NumberColumn("Y (0-1)", format="%.2f"),
                "arrow": st.column_config.CheckboxColumn("Ok"),
                "target_x": st.column_config.NumberColumn("Ok ucu BE", format="%.1f"),
            },
            key=f"p{index}_ann",
        )
        cfg["annotations"] = [
            {**row, "target_y": row.get("y", 0.9) - 0.12, "coords": "data-axes"}
            for row in edited.to_dict("records") if str(row.get("text", "")).strip()
        ]


def tab_figure(opts) -> None:
    sample_list = samples()
    if not sample_list:
        st.info("Önce **Veri** sekmesinden dosya yükleyin.")
        return
    regions = all_regions(sample_list)
    if not regions:
        st.warning("Yüklenen dosyalarda çizilebilir bölge bulunamadı.")
        return

    left, right = st.columns([1.05, 1.35], gap="large")

    with left:
        st.subheader("Düzen")
        preset = st.selectbox("Hazır şablon", list(PRESETS),
                              index=list(PRESETS).index(st.session_state.preset))
        if preset != st.session_state.preset:
            st.session_state.preset = preset
            st.session_state.layout = dict(PRESETS[preset])
            count = len(PRESET_GRIDS.get(preset, [])) or PRESETS[preset]["nrows"] * PRESETS[preset]["ncols"]
            st.session_state.panels = [default_panel(regions[min(i, len(regions) - 1)]) for i in range(count)]
            st.rerun()

        layout = st.session_state.layout
        c1, c2, c3, c4 = st.columns(4)
        layout["nrows"] = c1.number_input("Satır", 1, 6, int(layout["nrows"]))
        layout["ncols"] = c2.number_input("Sütun", 1, 8, int(layout["ncols"]))
        layout["width"] = c3.number_input("Genişlik (cm)", 4.0, 40.0, float(layout["width"]), 0.5)
        layout["height"] = c4.number_input("Yükseklik (cm)", 3.0, 40.0, float(layout["height"]), 0.5)

        c1, c2 = st.columns(2)
        if c1.button("➕ Panel ekle", width="stretch"):
            st.session_state.panels.append(default_panel(regions[0]))
            st.rerun()
        if c2.button("➖ Son paneli sil", width="stretch",
                     disabled=len(st.session_state.panels) <= 1):
            st.session_state.panels.pop()
            st.rerun()

        if not st.session_state.panels:
            st.session_state.panels = [default_panel(regions[0])]

        c1, c2, c3, c4 = st.columns(4)
        letter_template = c1.selectbox("Panel harfi", ["{letter})", "({letter})", "{letter}", "yok"], index=0)
        letter_outside = c2.checkbox("Harf panel dışında", False)
        letter_bold = c3.checkbox("Kalın harf", False)
        shared_legend = c4.checkbox("Ortak alt legend", len(st.session_state.panels) > 1)
        c1, c2 = st.columns(2)
        wspace = c1.slider("Yatay boşluk", 0.0, 1.0, 0.30, 0.02)
        hspace = c2.slider("Dikey boşluk", 0.0, 1.2, 0.38, 0.02)

        st.divider()
        tabs = st.tabs([f"Panel {LETTERS[i]}" for i in range(len(st.session_state.panels))])
        for i, tab in enumerate(tabs):
            with tab:
                panel_editor(i, st.session_state.panels[i], sample_list, regions, opts)

    # ---- build figure -----------------------------------------------------
    panels, offsets_map = [], {}
    for i, cfg in enumerate(st.session_state.panels):
        panel, offsets = build_panel(cfg, sample_list, opts)
        panel.letter = "" if letter_template == "yok" else LETTERS[i]
        grids = PRESET_GRIDS.get(st.session_state.preset)
        if grids and i < len(grids):
            panel.grid = grids[i]
        panels.append(panel)
        if offsets is not None:
            offsets_map[i] = offsets

    legend_entries = []
    if shared_legend:
        used = []
        for cfg in st.session_state.panels:
            for label in (cfg["samples"] if cfg["kind"] == "stack" else [cfg.get("decon_sample")]):
                if label and label not in used:
                    used.append(label)
        legend_entries = [(l, st.session_state.sample_style.get(l, {}).get("color", "#000000")) for l in used]

    spec = plotting.FigureSpec(
        panels=panels,
        nrows=int(layout["nrows"]), ncols=int(layout["ncols"]),
        width_cm=float(layout["width"]), height_cm=float(layout["height"]),
        letter_template="{letter}" if letter_template == "yok" else letter_template,
        letter_weight="bold" if letter_bold else "normal",
        letter_outside=letter_outside,
        shared_legend=shared_legend, shared_legend_entries=legend_entries,
        shared_legend_ncol=max(1, len(legend_entries)),
        wspace=wspace, hspace=hspace,
    )

    decon_opts = {}
    for cfg in st.session_state.panels:
        if cfg["kind"] == "decon":
            decon_opts = {
                "fill_alpha": cfg["fill_alpha"],
                "raw_marker_size": cfg["marker_size"],
                "show_residual": cfg["show_residual"],
            }
            break

    try:
        fig = plotting.render_figure(spec, decon_options=decon_opts, stack_offsets_map=offsets_map)
    except Exception as exc:                              # noqa: BLE001
        right.error(f"Figür oluşturulamadı: {exc}")
        return

    with right:
        st.subheader("Önizleme")
        st.pyplot(fig, width="stretch")
        st.caption(f"Gerçek boyut: {layout['width']:.1f} × {layout['height']:.1f} cm "
                   f"({layout['width'] / 2.54:.2f} × {layout['height'] / 2.54:.2f} inç)")
        export_block(fig, "figure")


def export_block(fig, default_name: str) -> None:
    st.divider()
    st.subheader("Dışa aktar")
    c1, c2 = st.columns(2)
    basename = c1.text_input("Dosya adı", default_name, key=f"exp_name_{default_name}")
    transparent = c2.checkbox("Saydam arka plan", False, key=f"exp_tr_{default_name}")

    formats = st.multiselect("Formatlar", list(export.FORMATS), default=["PNG", "TIFF", "PDF"],
                             key=f"exp_fmt_{default_name}")
    dpis = st.multiselect("Çözünürlük (raster formatlar için)", export.DPI_CHOICES,
                          default=[300, 600], key=f"exp_dpi_{default_name}")

    if not formats:
        return

    cols = st.columns(min(4, len(formats)))
    for i, fmt in enumerate(formats):
        with cols[i % len(cols)]:
            info = export.FORMATS[fmt]
            if info["vector"]:
                st.download_button(
                    f"⬇️ {fmt}", export.figure_bytes(fig, fmt, 300, transparent),
                    export.suggest_filename(basename, fmt), info["mime"],
                    key=f"dl_{default_name}_{fmt}", width="stretch",
                )
            else:
                for dpi in dpis or [300]:
                    st.download_button(
                        f"⬇️ {fmt} {dpi}dpi", export.figure_bytes(fig, fmt, dpi, transparent),
                        export.suggest_filename(basename, fmt, dpi), info["mime"],
                        key=f"dl_{default_name}_{fmt}_{dpi}", width="stretch",
                    )

    st.download_button(
        "📦 Hepsini ZIP olarak indir",
        export.bundle(fig, basename, formats, dpis or [300], transparent),
        f"{basename}.zip", "application/zip",
        key=f"dl_zip_{default_name}", width="stretch", type="primary",
    )


# ---------------------------------------------------------------------------
# tab 3: tables
# ---------------------------------------------------------------------------
def table_export_block(df: pd.DataFrame, default_caption: str) -> None:
    st.divider()
    caption = st.text_input("Tablo başlığı", default_caption, key="tbl_caption")

    c1, c2, c3 = st.columns(3)
    docx_font = c1.selectbox("Word yazı tipi", ["Times New Roman", "Arial", "Calibri"], index=0)
    docx_size = c2.number_input("Word yazı boyutu", 6.0, 14.0, 9.0, 0.5)
    merge_names = c3.checkbox("Tekrarlayan numune adını gizle", True)

    c1, c2, c3 = st.columns(3)
    try:
        c1.download_button(
            "⬇️ Word (.docx)", tables.to_docx(df, caption, docx_font, docx_size, merge_names),
            "xps_table.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch", type="primary",
        )
    except ImportError:
        c1.warning("python-docx kurulu değil (`pip install python-docx`).")

    c2.download_button(
        "⬇️ Excel (.xlsx)", tables.to_xlsx(df, "XPS Table", caption, merge_names),
        "xps_table.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    c3.download_button(
        "⬇️ CSV", df.to_csv().encode("utf-8-sig"), "xps_table.csv", "text/csv",
        width="stretch",
    )

    with st.expander("LaTeX kodu"):
        st.code(tables.to_latex(df, caption), language="latex")


def tab_tables() -> None:
    sample_list = samples()
    if not sample_list:
        st.info("Önce **Veri** sekmesinden dosya yükleyin.")
        return

    datasets = [ds for _, ds in sample_list]
    labels = [l for l, _ in sample_list]
    if not any(ds.peaks for ds in datasets):
        st.warning("Yüklenen dosyalarda **Peak Table** sayfası bulunamadı.")
        return

    mode = st.radio(
        "Tablo tipi", ["summary", "detailed", "chemical"], horizontal=True,
        format_func={"summary": "Özet (numune × element)",
                     "detailed": "Detaylı (her fit bileşeni ayrı satır)",
                     "chemical": "Kimyasal durum atamaları"}.get,
    )

    if mode == "chemical":
        df = tables.chemical_state_table(datasets, labels)
        if df.empty:
            st.warning("Dosyalarda **Chemical State Assessment** bloğu bulunamadı.")
            return
        st.dataframe(df, hide_index=True, width="stretch")
        table_export_block(df, "Table X Chemical state assignments")
        return

    default_source = "core" if any(p.source == "core" for ds in datasets for p in ds.peaks) else "any"
    source = st.radio(
        "Veri kaynağı", list(tables.SOURCE_CHOICES), horizontal=True,
        format_func=tables.SOURCE_CHOICES.get,
        index=list(tables.SOURCE_CHOICES).index("fit" if mode == "detailed" else default_source),
        help="Aynı numune için hem survey hem core hem de dekonvolüsyon dosyası "
             "yüklediyseniz hangi Peak Table satırlarının kullanılacağını seçer.",
    )

    available = tables.element_order(datasets, source)
    c1, c2 = st.columns([2, 2])
    elements = c1.multiselect("Elementler / bölgeler", available, default=available)
    metric_labels = {key: label for key, (label, _) in tables.METRICS.items()}

    if mode == "summary":
        metrics = c2.multiselect(
            "Satırlar (parametreler)", list(tables.METRICS), default=tables.DEFAULT_METRICS,
            format_func=metric_labels.get,
        )
        peak_choice = st.radio(
            "Bir element için birden fazla pik varsa", ["main", "first"], horizontal=True,
            format_func={"main": "En şiddetli piki kullan", "first": "İlk piki kullan"}.get,
        )
        df = tables.summary_table(datasets, elements, metrics or tables.DEFAULT_METRICS,
                                  labels, peak_choice, source)
    else:
        metrics = c2.multiselect(
            "Sütunlar (parametreler)", list(tables.METRICS),
            default=["peak_be", "fwhm", "area_p", "weight_pct", "atomic_pct"],
            format_func=metric_labels.get,
        )
        df = tables.detailed_table(datasets, metrics or ["peak_be"], labels, elements, source)

    if df.empty:
        st.warning("Seçimlerle eşleşen veri yok.")
        return

    st.dataframe(df, width="stretch")

    default_caption = (
        f"Table 1 Binding energy (BE, eV) and weight (%) values of "
        f"{', '.join(labels[:4])}{' ...' if len(labels) > 4 else ''} samples"
    )
    table_export_block(df, default_caption)

    with st.expander("Ham Peak Table verisi"):
        raw_rows = []
        for label, ds in sample_list:
            for peak in ds.peaks:
                raw_rows.append({
                    "Numune": label, "Ad": peak.name, "Element": peak.element,
                    "Bileşen": peak.component or "", "Peak BE": peak.peak_be,
                    "FWHM": peak.fwhm, "Height": peak.height, "Area (P)": peak.area_p,
                    "Weight %": peak.weight_pct, "At. %": peak.atomic_pct,
                })
        st.dataframe(pd.DataFrame(raw_rows), hide_index=True, width="stretch")


# ---------------------------------------------------------------------------
def main() -> None:
    init_state()
    st.title("📈 XPS Figure Studio")
    st.caption("Thermo Avantage `.xlsx` çıktılarından yayın kalitesinde figür ve tablo üretir.")

    opts = sidebar_style()
    st.session_state["_palette"] = opts["palette"]

    tab1, tab2, tab3 = st.tabs(["📂 Veri", "📈 Figür", "📊 Tablo"])
    with tab1:
        tab_data()
    with tab2:
        tab_figure(opts)
    with tab3:
        tab_tables()


if __name__ == "__main__":
    main()
