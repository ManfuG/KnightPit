# Third-party notices

KnightPit and KnightPitAI project-owned source code, tests, configuration, and project-generated self-play data are released under the MIT License in `LICENSE` and `KnightPitAI/LICENSE`. This statement does not relicense dependencies. Every dependency keeps its upstream terms; no dependency source is vendored in this repository.

The project was developed with GPT-5.6-Luna using Oh My Pi as the coding harness. This workflow disclosure does not change any copyright, license, or upstream attribution.

## Audit record
- Audit date: 2026-08-24.
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

The lockfile also resolves transitive build/runtime packages. The following non-MIT licenses are called out explicitly and remain applicable: `caniuse-lite@1.0.30001809` CC-BY-4.0 (browser data), `lightningcss@1.32.0` and its platform packages MPL-2.0 (CSS compiler), `baseline-browser-mapping@2.11.18` Apache-2.0, `detect-libc@2.1.2` Apache-2.0, `electron-to-chromium@1.5.412` ISC, `graceful-fs@4.2.11` ISC, `lru-cache@5.1.1` ISC, `picocolors@1.1.1` ISC, `semver@6.3.1` ISC, `yallist@3.1.1` ISC, `source-map-js@1.2.1` BSD-3-Clause, and `tslib@2.8.1` 0BSD. Other resolved transitive packages are identified by name, version, integrity hash, and registry URL in `package-lock.json`; their upstream license metadata is not collapsed to MIT.

## Chess piece assets

`public/pieces/spatial/*.svg` contains adapted Spatial chess piece artwork by Maurizio Monge, sourced from [maurimo/chess-art](https://github.com/maurimo/chess-art). The SVGs are color-customized and compacted for the frontend, but remain third-party assets and are not relicensed as KnightPit source code. The upstream repository publishes the artwork under the MIT License; the complete attribution and license text is kept in `public/pieces/spatial/LICENSE`.

MIT License

Copyright (c) Maurizio Monge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Python inventory

Resolved from the hashed lockfiles (package, version, license, role, provenance):

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

NumPy binary distributions carry their own notices for bundled OpenBLAS, LAPACK and compiler runtimes; those notices are not project code and are not relicensed by this repository. The project does not vendor any Python or JavaScript dependency source.

## Project-owned data policy

The chess rules environment, generated replay records, campaign metrics, and generated checkpoints are project-owned outputs and are MIT when distributed as project artifacts. No external game dataset, Stockfish source/binary/WASM/evaluation, tablebase, or copied dependency source is included. Generated artifacts remain ignored and must be regenerated from the documented commands.
