# Third-party notices

KnightPit and KnightPitAI project-owned code and generated research data are MIT under their respective `LICENSE` files. Dependencies and assets retain upstream terms: the separate Stockfish worker is GPLv3; Cburnett pieces are GPLv2-or-later. Neither is relicensed as MIT.

The project was developed with GPT-5.6-Luna using Oh My Pi as the coding harness. This workflow disclosure does not change any copyright, license, or upstream attribution.

## Audit record
- Distribution update: 2026-10-21; original dependency audit: 2026-08-24.
- Source of truth: `package-lock.json`, `requirements-cpu.lock`, and `requirements-test.lock`.
- Frontend lockfile registry: npm registry package tarballs and their upstream package metadata.
- Python lockfile interpreter used for metadata audit: Python 3.10.4.

## Frontend inventory

Direct packages resolved in `package-lock.json` (version, license, role, provenance):

| Package | Version | License | Role | Upstream |
| --- | --- | --- | --- | --- |
| react | 19.2.8 | MIT | UI runtime | https://registry.npmjs.org/react |
| react-dom | 19.2.8 | MIT | DOM renderer | https://registry.npmjs.org/react-dom |
| react-router-dom | 7.18.2 | MIT | routing | https://registry.npmjs.org/react-router-dom |
| motion | 12.43.0 | MIT | animation | https://registry.npmjs.org/motion |
| @tailwindcss/vite | 4.3.3 | MIT | Tailwind Vite plugin | https://registry.npmjs.org/@tailwindcss/vite |
| tailwindcss | 4.3.3 | MIT | CSS tooling | https://registry.npmjs.org/tailwindcss |
| @vitejs/plugin-react | 5.2.0 | MIT | Vite React plugin | https://registry.npmjs.org/@vitejs/plugin-react |
| vite | 7.3.6 | MIT | dev server/build | https://registry.npmjs.org/vite |
| typescript | 5.8.3 | Apache-2.0 | type checker/compiler | https://registry.npmjs.org/typescript |
| @types/react | 19.2.18 | MIT | type declarations | https://registry.npmjs.org/@types/react |
| @types/react-dom | 19.2.4 | MIT | type declarations | https://registry.npmjs.org/@types/react-dom |
| @capacitor/core, @capacitor/android, @capacitor/cli | 8.5.3 | MIT | offline native packaging / bridge | https://github.com/ionic-team/capacitor |

The lockfile also resolves transitive build/runtime packages. The following non-MIT licenses are called out explicitly and remain applicable: `caniuse-lite@1.0.30001809` CC-BY-4.0 (browser data), `lightningcss@1.32.0` and its platform packages MPL-2.0 (CSS compiler), `baseline-browser-mapping@2.11.18` Apache-2.0, `detect-libc@2.1.2` Apache-2.0, `electron-to-chromium@1.5.412` ISC, `graceful-fs@4.2.11` ISC, `lru-cache@5.1.1` ISC, `picocolors@1.1.1` ISC, `semver@6.3.1` ISC, `yallist@3.1.1` ISC, `source-map-js@1.2.1` BSD-3-Clause, and `tslib@2.8.1` 0BSD. Other resolved transitive packages are identified by name, version, integrity hash, and registry URL in `package-lock.json`; their upstream license metadata is not collapsed to MIT.

## Bundled font assets

Syne and Fraunces are self-hosted under `public/fonts/` and retain the SIL Open Font License 1.1, not the project MIT license.

| Asset | Copyright / upstream | License |
| --- | --- | --- |
| `syne-variable.ttf` | Copyright 2017 The Syne Project Authors — https://gitlab.com/bonjour-monde/fonderie/syne-typeface | [Syne-OFL.txt](public/fonts/Syne-OFL.txt) |
| `fraunces-latin.woff2`, `fraunces-italic-latin.woff2` | Copyright 2018 The Fraunces Project Authors — https://github.com/undercasetype/Fraunces | [Fraunces-OFL.txt](public/fonts/Fraunces-OFL.txt) |


## Selected Python inventory

Selected dependency summaries from the hashed lockfiles, not a complete resolved inventory. Complete package names, versions and hashes are in `requirements-cpu.lock` and `requirements-test.lock`; complete license notices for installed wheels remain in those distributions. Python environments and wheels are not included in the static deployment.

| Package | Version | License | Role | Upstream |
| --- | --- | --- | --- | --- |
| numpy | 2.2.6 | BSD-3-Clause (binary distributions may bundle additional notices) | network, encoding, training | https://pypi.org/project/numpy/2.2.6/ |
| fastapi | 0.141.1 | MIT | local API | https://pypi.org/project/fastapi/0.141.1/ |
| uvicorn | 0.52.4 | BSD-3-Clause | local ASGI server | https://pypi.org/project/uvicorn/0.52.4/ |
| pytest | 9.1.1 | MIT | test runner | https://pypi.org/project/pytest/9.1.1/ |
| httpx | 0.28.1 | BSD-3-Clause | API tests/client | https://pypi.org/project/httpx/0.28.1/ |
| pydantic | 2.13.4 | MIT | FastAPI validation | https://pypi.org/project/pydantic/2.13.4/ |
| starlette | 1.6.0 | BSD-3-Clause | ASGI framework | https://pypi.org/project/starlette/1.6.0/ |
| anyio | 4.14.2 | MIT | async compatibility | https://pypi.org/project/anyio/4.14.2/ |
| certifi | 2026.7.22 | MPL-2.0 | TLS CA bundle | https://pypi.org/project/certifi/2026.7.22/ |
| idna | 3.19 | BSD-3-Clause | hostname handling | https://pypi.org/project/idna/3.19/ |
| packaging | 26.3 | Apache-2.0/BSD-2-Clause | test tooling | https://pypi.org/project/packaging/26.3/ |
| pluggy | 1.6.0 | MIT | pytest plugin system | https://pypi.org/project/pluggy/1.6.0/ |

NumPy binary distributions carry notices for bundled OpenBLAS, LAPACK and compiler runtimes; these are not project code. Python wheels/environments are not bundled in the browser or Android app.

## Project-owned data policy

Python research outputs remain project-owned and ignored. No external game dataset, tablebase or Stockfish-generated training data is included. The separate offline application engine is deliberately distributed as documented below.

## Public deployment and original artwork

`public/THIRD_PARTY_LICENSES.txt` ships complete original/runtime/font/native notices and links to engine/piece licenses and sources. Home exposes Licenses. AndroidX/Kotlin and Apache Cordova 14.0.1 retain Apache-2.0 terms and upstream copyright/NOTICE records. System WebView is supplied by the device, not redistributed in this APK.

The README demo records the earlier Python opponent, not current playing-strength evidence. Its MP4 has no audio. Documentation media is not copied into the app. No endorsement by Lichess, Chess.com or other platform owners is implied.

The publication audit verifies the approved Stockfish distribution digest manifest, pinned Gradle wrapper and licensed font/demo inventory. Unexpected binaries/personal paths remain rejected. Stockfish remains excluded from Python research source and training outputs.

## Offline Stockfish distribution

Stockfish.js **19.0.1**, lite single-thread, by the Stockfish developers and Nathan Rugg, is bundled unmodified under **GPLv3** in `public/engine/stockfish-19.0.1/`. Upstream: https://github.com/nmrugg/stockfish.js/tree/v19.0.1, revision `0d5dd7944f88c817c07a26bc4fb1905d5f9c46d6`.

JavaScript/WASM, full GPL text, authors, exact-tag complete corresponding source archive, matching lite NNUE network, build/provenance instructions and SHA-256 manifest accompany every browser build/APK. Keep this directory together when redistributing. Complete editable engine source is available locally without requesting it from the author. See `NOTICE.txt`, `COPYING.txt` and `SHA256SUMS`; these engine files are not MIT.

## Filled chess pieces

Twelve unmodified Cburnett SVG sources by **Colin M. L. Burnett**, as used by Lichess, are **GPLv2-or-later**. [Pinned source](https://github.com/lichess-org/lila/tree/f68e0464648bb6ad16f6bf3ee476c6c49dbead41/public/piece/cburnett); attribution evidence: that revision's `COPYING.md`. Editable SVGs, full license and provenance ship in `public/pieces/cburnett/`. No proprietary Chess.com pieces or Lichess branding are included.

## Android entry artwork

`public/entry-art.svg` reuses actual portfolio geometry from QuantaPit/HanPit: crescent, orbits, planets, landscape and botanical drawings, recolored in KnightPit's navy/gold/mineral palette. Taurus adapts [NOIRLab Taurus Pattern](https://noirlab.edu/public/products/line-art/taurus-pattern/), credited to NOIRLab with its Sky & Telescope constellation-pattern context, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Geometry, scale, colors and presentation are modified; no photograph/logo or endorsement is included. Attribution and legal links also ship in `public/THIRD_PARTY_LICENSES.txt`.

