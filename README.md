# XPS Figure Studio

Thermo **Avantage** programından export edilen `.xlsx` dosyalarından, akademik
dergilere doğrudan gönderilebilecek kalitede XPS figürleri ve tabloları üretir.
OriginPro ile elle yapılan düzenleme işini tek arayüzde toplar.

## Ne yapar

- **Survey, core-level ve deconvolution** dosyalarını otomatik tanır ve okur.
- Aynı numuneye ait birden fazla dosyayı **tek numunede birleştirir** (merge).
- Birden fazla numuneyi **üst üste** veya **dikey kaydırmalı (stacked)** çizer —
  farklı numunelerin C1s seviyelerini aynı grafikte karşılaştırmak için.
- **Dekonvolüsyon panelleri**: açık halka ham veri, renkli dolgulu bileşenler,
  kırmızı background, siyah envelope, isteğe bağlı residual.
- **Çok panelli figürler**: `a)` `b)` `c)` harflendirmesi, ortak alt legend,
  panel boyutları santimetre cinsinden.
- Her şeyin **rengi, adı ve konumu** arayüzden değiştirilebilir.
- **300 / 600 / 1200 dpi** PNG ve TIFF (LZW), ayrıca PDF, SVG, EPS çıktısı.
- **Tablo sekmesi**: Peak Table verilerinden makale tablosu (Word `.docx`,
  Excel `.xlsx`, CSV, LaTeX) — üç çizgili dergi formatında.

## Kurulum ve çalıştırma

### Windows

`run.bat` dosyasına çift tıklayın. İlk çalıştırmada sanal ortamı kurar ve
gerekli paketleri indirir (birkaç dakika), sonra tarayıcıda açılır.

### macOS / Linux

```bash
chmod +x run.sh     # yalnızca ilk seferde
./run.sh
```

### Elle kurulum

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Gereksinim: **Python 3.10+**.

## Kullanım

### 1 · Veri sekmesi

Avantage `.xlsx` dosyalarını sürükleyip bırakın. Program dosyanın `Titles`
sayfasındaki numune adını okur ve `-core`, `-decon1`, `-survey` gibi ekleri
temizleyerek dosyaları otomatik gruplar.

**Numune** sütununa aynı adı yazdığınız dosyalar birleştirilir. Örneğin:

| Dosya | Numune |
|---|---|
| `LZO-850C-survey.xlsx` | `LZO(850 °C)` |
| `LZO-850C-core.xlsx` | `LZO(850 °C)` |
| `LZO-850C-decon1.xlsx` | `LZO(850 °C)` |

Bir bölge hem dekonvolüsyonlu hem dekonvolüsyonsuz geldiyse **fitli olan**
kullanılır. Çizim sırasını ve numune renklerini bu sekmeden ayarlarsınız.

> **Avantage kenar artefaktı**: Avantage, fit bileşeni ve background
> sütunlarının ilk satırına `0` yazar. Varsayılan olarak bu değerler
> gizlenir; aksi hâlde eğri grafiğin dibine çakılır.

### 2 · Figür sekmesi

Hazır şablonlardan birini seçin (tek panel, 2×2, `5 panel (3 üst + 2 alt
ortalı)` …) ya da satır/sütun sayısını elle verin. Her panel için:

| Panel tipi | Ne yapar |
|---|---|
| **Numune karşılaştırma** | Seçilen numunelerin aynı bölgesini çizer. `Dikey kaydırma = 0` tam üst üste (overlay), `> 0` yığılmış (stacked) grafik verir. |
| **Dekonvolüsyon** | Tek numunenin fitli bölgesini bileşenleriyle çizer. Her bileşenin rengi ve legend'de görünecek adı ayrı ayrı düzenlenir. |

Normalizasyon (maksimum = 1, min-maks, alan = 1), eksen aralığı, tick adımı,
legend konumu, panel içi etiket ve **pik etiketleri/okları** panel bazında
ayarlanır. Survey grafiklerinde `Zn2p`, `La3d` gibi etiketleri eklemek için
_Pik etiketleri / oklar_ tablosunu kullanın: **Etiket BE** yazının bağlanma
enerjisi, **Y** panel içindeki yüksekliği (0–1), **Ok ucu BE** okun işaret
ettiği nokta.

Önizleme anlık güncellenir. Sağ alttan tek tek indirebilir ya da tüm
format/çözünürlük kombinasyonlarını **tek ZIP** olarak alabilirsiniz.

### 3 · Tablo sekmesi

Peak Table verilerinden üç tip tablo üretir:

- **Özet** — numuneler satırda, elementler sütunda; her numune için seçtiğiniz
  parametreler (Peak BE, Weight %, At. %, FWHM, Area) alt satır olarak gelir.
- **Detaylı** — her fit bileşeni ayrı satır; dekonvolüsyon tabloları için.
- **Kimyasal durum atamaları** — Avantage'ın *Chemical State Assessment*
  bloğundan okunan atamalar.

**Veri kaynağı** seçimi önemlidir: aynı numune için hem survey hem core
dosyası yüklüyse, hangisinin Peak Table değerlerinin kullanılacağını belirler.
Makalelerde genellikle **core-level** değerleri raporlanır (varsayılan).

Word çıktısı, dergilerin istediği üç çizgili (dikey çizgisiz) formatta gelir.

## Genel stil (sol panel)

Yazı tipi (Arial varsayılan), yazı boyutu, çizgi/çerçeve kalınlığı, tick yönü
ve uzunluğu, numune ve dolgu renk paletleri buradan ayarlanır ve tüm
panellere uygulanır.

Renk paletleri: Origin klasik, yüksek kontrast, **renk körü dostu
(Okabe-Ito)**, gri tonlama (baskı), viridis.

## Proje yapısı

```
app.py                 Streamlit arayüzü (Veri / Figür / Tablo sekmeleri)
xpsfig/
├── parser.py          Avantage .xlsx okuyucu (bölgeler, Peak Table, kimyasal durum)
├── style.py           matplotlib rcParams, font ve renk paletleri
├── plotting.py        Panel ve figür çizimi (stacked, overlay, deconvolution)
├── tables.py          Tablo oluşturma ve docx / xlsx / LaTeX çıktısı
└── export.py          PNG, TIFF, PDF, SVG, EPS dışa aktarma
```

## Notlar

- Ham veri dosyaları (`.xlsx`) `.gitignore` ile depo dışında tutulur.
- PDF ve SVG çıktılarında yazılar metin olarak gömülür; Illustrator veya
  Inkscape'te sonradan düzenlenebilir.
- Figür boyutu santimetre cinsindendir. Elsevier tek sütun ≈ 9 cm,
  çift sütun ≈ 19 cm; Springer tek sütun ≈ 8.4 cm, çift sütun ≈ 17.4 cm.
