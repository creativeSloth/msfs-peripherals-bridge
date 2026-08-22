# Documentation — where to find what

First time here and looking for a guide? Find your task in the table, open the
one document it points to. The lists further down are the full catalog with a
one-line description each.

> 🇩🇪 marks a document still written in German. The install path a newcomer needs
> first — **[QUICKSTART.md](QUICKSTART.md)** — is in English.

## I want to…

| I want to… | Open |
|---|---|
| **Install the software and start it** — no Linux/Python knowledge, copy-paste only | **[QUICKSTART.md](QUICKSTART.md)** |
| Set up a fresh machine in full — udev, the Wine bridge, all the details | [INSTALL.md](INSTALL.md) |
| Use **hardware that isn't one of the supported devices** — detect, register, teach, map it | [geraete-workflow.md](geraete-workflow.md) 🇩🇪 |
| **Reuse an existing SPAD.neXt profile** — pull its mapping semantics into ours | [spadnext-import.md](spadnext-import.md) |
| Run it day-to-day and tune a mapping live | [running.md](running.md) |
| Look up a **command** | [cheatsheet.md](cheatsheet.md) |
| Look up a **SimVar / event** for a mapping | [simvars-reference.md](simvars-reference.md) |
| Understand **how the bridge works** | [bridge-concept.md](bridge-concept.md) |

---

## 📘 Guides — step by step

| Document | For whom / what |
|---|---|
| **[QUICKSTART.md](QUICKSTART.md)** | **Start here.** Beginners, copy-paste only: clone → `./install.sh` → start the app; the rest is buttons. |
| [INSTALL.md](INSTALL.md) | The full setup for a fresh machine: udev, registering your own hardware, the Wine bridge. Read this when QUICKSTART isn't enough. |
| [geraete-workflow.md](geraete-workflow.md) 🇩🇪 | Adding a **new/foreign device** from scratch: detect → register → teach its inputs/outputs → (calibrate) → map. |
| [running.md](running.md) | Running & iterating: what runs natively vs. in Wine/Proton, finding your Proton prefix/version, tuning a mapping live. |

Helper scripts the guides use: `install.sh` (one-shot setup) · `tools/find-prefix.sh`
(locate your MSFS prefix) · `tools/install-udev-rules.sh` (unlock devices — the
app's "Enable devices…" button runs this for you).

## 📚 Reference — look things up

| Document | What it covers |
|---|---|
| [cheatsheet.md](cheatsheet.md) | Every user-facing command as a copy-paste line. |
| [simvars-reference.md](simvars-reference.md) | Catalog of SimVars/events/LVars used when mapping aircraft. |

## 💡 Concept & background — *not needed to install*

How and why things are designed. Skip these if you just want to get running.

| Document | What it covers |
|---|---|
| [bridge-concept.md](bridge-concept.md) | **How the bridge works** — short explainer with diagrams. A good first read for the curious. |
| [geraete-baukasten-konzept.md](geraete-baukasten-konzept.md) 🇩🇪 | Vision (draft, not built): users assemble their own devices from building blocks. |
| [gauges-design.md](gauges-design.md) 🇩🇪 | Design notes for the gauges tab (round instruments). |

## ➕ Optional companion tools — *only if you use them*

Separate programs, not required by this project.

| Document | What it covers |
|---|---|
| [spadnext-install.md](spadnext-install.md) 🇩🇪 | Installing SPAD.neXt into the MSFS Proton prefix. |
| [spadnext-import.md](spadnext-import.md) | Reuse an existing SPAD.neXt profile: extract its mapping semantics into ours (`tools/spadnext_import.py`). |
| [littlenavmap-install.md](littlenavmap-install.md) 🇩🇪 | Installing Little Navmap. |
| [justflight-bundle-install.md](justflight-bundle-install.md) 🇩🇪 | Installing a JustFlight aircraft bundle *(personal notes for this machine)*. |

## 🗂 Internal

Not guides — project memory and scratch notes.

- [memory/](memory/) — knowledge base (status, decisions, measurements).
- [research/](research/) — scratch notes.
