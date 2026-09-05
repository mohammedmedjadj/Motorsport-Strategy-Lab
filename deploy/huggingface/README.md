---
title: Motorsport Strategy Lab
emoji: 🏁
colorFrom: red
colorTo: gray
sdk: streamlit
sdk_version: 1.61.1
app_file: app.py
pinned: false
license: cc-by-nc-sa-4.0
short_description: Race strategy across F1, WEC, IMSA and ELMS — seven classes, one protocol
---

# Deploying the demo to Hugging Face Spaces

The three files in this directory are what a Space needs and this repository
does not. Copy them to the Space root; do not move them here.

The reason for the split: Spaces insists on `app.py` and `requirements.txt` at
the repository root, and streamlit is deliberately *not* a dependency of this
project — `pip install -r requirements.txt` should not pull a web framework for
someone who only wants to run the analysis. `tests/test_demo_app.py` skips
itself when streamlit is absent, which is the same decision.

## Steps

1. Create a Space at [huggingface.co/new-space](https://huggingface.co/new-space).
   SDK: **Streamlit**. Hardware: the free CPU tier is enough — the simulator is
   vectorised NumPy and touches no GPU.

2. Push this repository to it:

   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/motorsport-strategy-lab
   git push space main
   ```

   The Space needs the whole repository, not just `demo/`. The app reads
   `data/derived/` and imports from `src/`, and all of that is committed.

3. Copy the three files from this directory to the Space root and push again:

   ```bash
   cp deploy/huggingface/app.py .
   cp deploy/huggingface/requirements.txt .
   cp deploy/huggingface/README.md .
   git add app.py requirements.txt README.md
   git commit -m "Space configuration"
   git push space main
   ```

   That last `cp` overwrites the project README **in the Space only**, which is
   what Spaces reads its YAML configuration from. Do not commit any of this to
   the GitHub repository — the YAML header would render as raw text there, and
   the root `app.py` and `requirements.txt` would be wrong for everyone else.

   A cleaner alternative if you would rather not overwrite anything: keep a
   separate branch for the Space (`git checkout -b space`, apply the three
   copies there, `git push space space:main`) and never merge it.

4. The build takes a few minutes. If it fails, the log is under the Space's
   *Logs* tab, and the usual cause is a missing file rather than a missing
   package — check that `data/derived/` came across.

5. Once it is live, put the URL in the README and on the
   [website](../../docs/index.html), next to the repository link.

## What the Space will show

Seven panels, one per modelled class: Formula 1, WEC Hypercar, IMSA GTP, IMSA
GTD, IMSA GTD PRO, ELMS LMP2 and ELMS LMP2 Pro/Am. Each runs the same simulator
and the same fitted models the reports use — there is no simplified version
built for display.

It needs no secrets and makes no network calls. Everything it reads is committed.
