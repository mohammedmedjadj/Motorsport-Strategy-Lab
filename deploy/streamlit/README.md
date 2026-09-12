# The demo, deployed

**Live: <https://motorsport-strategy-lab.streamlit.app/>** — Streamlit Community
Cloud, from `main`, entry point `demo/app.py`.

## Why not Hugging Face Spaces

This directory replaced `deploy/huggingface/`, which described a route that no
longer exists. Hugging Face dropped Streamlit from its supported Space SDKs, and
Spaces that run on compute now need a paid plan. The three files that lived here
— a root `app.py` shim, a `requirements.txt` with streamlit appended, and a
README carrying Spaces' YAML front matter — existed only to satisfy Spaces'
insistence on finding `app.py` at the repository root. Community Cloud has no
such requirement, so none of them is needed and keeping them would have meant
keeping instructions for a platform that would reject them.

## What Community Cloud needs, and what it does not

It needs three things: the repository, the branch, and the path to the app.
Nothing has to move to the repository root.

It does **not** need streamlit in `requirements.txt`. The platform installs
Streamlit itself, which is why the root `requirements.txt` can stay as it is —
streamlit is deliberately not a dependency of this project. Running
`pip install -r requirements.txt` should not pull a web framework on someone who
only wants to run the analysis, and `tests/test_demo_app.py` skips itself when
streamlit is absent for the same reason.

The app reads `data/derived/` and imports from `src/`, and all of that is
committed, so the deployment needs no data step and no secrets.

## Appearance

`.streamlit/config.toml` at the repository root is read by Community Cloud, so
the deployed app carries the project's palette rather than Streamlit's defaults.
Those values come from `src/reporting/palette.py`, the same module the report
figures import, and `tests/test_palette.py` fails if the demo, the figures and
the website's CSS ever disagree.

Two things that file cannot do. Streamlit has no way to use the platform font
stack the website uses without shipping font files, so the typeface differs.
And the theme is configuration, not code — changing it is a redeploy, not a
release.

## Redeploying

Community Cloud watches the branch. A push to `main` that touches `demo/`,
`src/`, `data/derived/` or `.streamlit/` redeploys automatically; there is
nothing to run here. If a deploy fails, its log is on the app's page under
*Manage app*, and the usual cause is an import that works locally because the
package is installed in the virtualenv and missing from `requirements.txt`.
