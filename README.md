# Chaos Battle — fork

**A preserved fork of [Aurora-b1t/chaos_battle](https://github.com/Aurora-b1t/chaos_battle).** The browser client and Python aiohttp server implement a small multiplayer combat game.

[简体中文](README.zh-CN.md) · [Upstream](https://github.com/Aurora-b1t/chaos_battle) · [Deployment notes](DEPLOY.md) · [History](docs/README-history.md)

## Provenance and differences

The original game and architecture belong to the upstream project and its contributors. At the public comparison recorded on **2026-10-17**, this fork's `master` (`3edd102`) had **0 unique commits and was 1 commit behind** upstream `master` (`2a9bea6`). This repository does not claim an independent implementation or currently verified fork-specific features. [Recorded comparison](https://github.com/Aurora-b1t/chaos_battle/compare/2a9bea6ed43a8738a916b2c5d919ceeb71b1092f...Patr1ck2005:3edd1029c08661666d23189c27e12be1792b4234).

## Source and local use

| Path | Role |
|---|---|
| [client/](client/) | Browser UI, game client and existing sprites |
| [server/](server/) | Python game/room/network implementation |
| [run.py](run.py) | Server entry point |
| [requirements.txt](requirements.txt) | aiohttp dependency |

The historical source entry is:

```bash
python -m pip install -r requirements.txt
python run.py
```

The documented address is `http://127.0.0.1:8080/`; the server can bind all interfaces, so review configuration before running it on a shared network. [DEPLOY.md](DEPLOY.md) is an older minimal deployment guide, not production hardening or a currently hosted service.

## Status and license

Upstream-derived historical snapshot. No screenshot, deployment or multiplayer acceptance was recreated for this documentation update. Local changes outside the public baseline are not represented as published fork features.

No repository-wide open-source license is declared in the inspected public snapshot. Retain upstream attribution and ask the relevant rights holder about reuse; no MIT license is added here.
