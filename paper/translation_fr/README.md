# Traduction française de travail

`main_fr.tex` traduit `../main.tex` section par section, avec les mêmes macros :
les chiffres viennent de `../numbers.tex`, les figures de `../../reports/figures/`.
La version soumise est l'anglaise. `bib.tex` est la bibliographie de `../main.tex`.

    cd paper/translation_fr && latexmk -pdf main_fr.tex
