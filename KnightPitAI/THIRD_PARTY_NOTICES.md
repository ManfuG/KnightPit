# Third-party notices

`KnightPitAI` source code, tests, configuration, and project-generated self-play/campaign data are MIT under `LICENSE`. Dependencies retain their upstream terms; this project does not copy or vendor dependency source and does not present the dependency tree as MIT.

## Audit record

- Lock sources: `requirements-cpu.lock` and `requirements-test.lock`, generated with `uv pip compile --generate-hashes`.
- Audit date: 2026-08-23.
- Python metadata interpreter: Python 3.10.4.

## Resolved Python inventory

| Package | Version | License | Role | Upstream |
| --- | --- | --- | --- | --- |
| NumPy | 2.2.6 | BSD-3-Clause plus bundled-component notices | encoding, network, training | https://pypi.org/project/numpy/2.2.6/ |
| FastAPI | 0.141.1 | MIT | optional local inference API | https://pypi.org/project/fastapi/0.141.1/ |
| Uvicorn | 0.51.0 | BSD-3-Clause | local ASGI server | https://pypi.org/project/uvicorn/0.51.0/ |
| pytest | 8.4.2 | MIT | tests | https://pypi.org/project/pytest/8.4.2/ |
| httpx | 0.28.1 | BSD-3-Clause | API tests/client | https://pypi.org/project/httpx/0.28.1/ |
| pydantic | 2.13.4 | MIT | request validation | https://pypi.org/project/pydantic/2.13.4/ |
| Starlette | 1.6.0 | BSD-3-Clause | ASGI foundation | https://pypi.org/project/starlette/1.6.0/ |
| AnyIO | 4.14.2 | MIT | async compatibility | https://pypi.org/project/anyio/4.14.2/ |
| certifi | 2026.7.22 | MPL-2.0 | TLS CA bundle | https://pypi.org/project/certifi/2026.7.22/ |
| idna | 3.19 | BSD-3-Clause | hostname handling | https://pypi.org/project/idna/3.19/ |
| packaging | 26.3 | Apache-2.0/BSD-2-Clause | test support | https://pypi.org/project/packaging/26.3/ |
| pluggy | 1.6.0 | MIT | pytest plugin support | https://pypi.org/project/pluggy/1.6.0/ |

NumPy wheels may bundle OpenBLAS, LAPACK, libgfortran and libquadmath; their upstream notices and licenses remain applicable to those binary distributions. The lockfiles contain the complete resolved dependency set and hashes.

## Exclusions

No Stockfish code, binary, WASM, evaluation, tablebase, external game dataset, or copied dependency source is included. The chess rules, replay records, and generated campaign metrics/checkpoints are project-owned MIT artifacts when distributed, and generated outputs remain ignored by the publication rules.

## Development disclosure

KnightPitAI was developed with GPT-5.6-Luna using Oh My Pi as the coding harness. This workflow disclosure does not change the MIT license or any upstream dependency terms.
