# Rice three-chromosome RectChr showcase

This example uses the generated real-data-derived gene-density and GC tracks
for `Chr01`-`Chr03`, then adds reproducible simulated biology-oriented tracks.
GWAS is background-dominated, with exactly two major association peaks and only
their two peak-top genes labelled. Fst is summarized in 200 kb bins and shown as a ridgeline directly below
the GC line. Highlights are broad GWAS peak regions, while LinkS endpoints span
500 kb intervals so they render as ribbons rather than thin lines.

Run `bash run.sh` to regenerate the supplementary tracks and create
`rice_three_chr_showcase.svg`.
