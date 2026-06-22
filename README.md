# FloodStack

**The open-source flood risk quantification pipeline.**

FloodStack is a Python orchestration framework that chains physics-based hydraulic simulation with consequence estimation to produce end-to-end flood risk quantification — at any scale, for any purpose.

> Built on [TRITON](https://triton.ornl.gov) (ORNL) · [RAS Agent](https://github.com/gheistand/ras-agent) (Reep Works) · [SPHERE](https://github.com/Niyam-Projects/sphere) (Niyam Projects)

---

## The Problem

Flood risk quantification today requires stitching together multiple tools with incompatible formats, different compute requirements, and no shared data model. You can run a hydraulic model. You can run a consequence model. But going from raw terrain data to a probabilistic risk curve — at portfolio scale — requires months of manual work and expensive commercial software.

FloodStack is the missing orchestration layer.

---

## How It Works

```
Terrain + Flows
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                   FloodStack Pipeline                │
│                                                     │
│  ┌──────────────┐        ┌─────────────────────┐   │
│  │ TRITON Engine│        │ RAS Agent Engine     │   │
│  │ (fast/GPU)   │        │ (regulatory/HEC-RAS) │   │
│  │              │        │                     │   │
│  │ • Ensembles  │        │ • FEMA FIRM work     │   │
│  │ • Triage     │        │ • NFIP compliance    │   │
│  │ • Pluvial    │        │ • Standard of care   │   │
│  └──────┬───────┘        └──────────┬──────────┘   │
│         │                           │               │
│         └───────────┬───────────────┘               │
│                     │ depth grids                   │
│                     ▼                               │
│          ┌─────────────────────┐                   │
│          │   SPHERE Engine     │                   │
│          │   (consequences)    │                   │
│          │                     │                   │
│          │ • HAZUS methodology │                   │
│          │ • Structure damages │                   │
│          │ • Risk curves       │                   │
│          └──────────┬──────────┘                   │
│                     │                               │
└─────────────────────┼───────────────────────────────┘
                      │
                      ▼
              Risk Output Layer
        (maps · tables · risk curves · reports)
```

**FloodStack picks the right engine for the job:**
- Regulatory deliverable needed? → RAS Agent runs HEC-RAS, SPHERE adds consequences
- Ensemble/climate scenario run? → TRITON at 100x speed, SPHERE quantifies risk distribution
- Portfolio triage? → TRITON fast-pass ranks reaches, RAS Agent runs the ones that matter

---

## Architecture

FloodStack is a thin orchestration layer. Each component is a swappable adapter — bring your own engine, bring your own consequence model.

```
floodstack/
├── pipeline.py        # Orchestration: selects engine, sequences steps
├── engines/
│   ├── triton.py      # TRITON adapter (ORNL GPU-accelerated 2D)
│   ├── hec_ras.py     # RAS Agent / HEC-RAS adapter
│   └── sphere.py      # SPHERE consequence adapter
├── io/
│   └── depth_grid.py  # Common depth grid format (GeoParquet-native)
└── report/
    └── risk_report.py # Unified output layer
```

**Common data model:** depth grids are the currency. Every hydraulic engine produces them; every consequence model consumes them. FloodStack handles the translation.

---

## Use Cases

| Workflow | Hydraulic Engine | Consequence Engine | Output |
|---|---|---|---|
| FIRM revision / LOMR | RAS Agent (HEC-RAS) | SPHERE | Regulatory flood map + consequence summary |
| Portfolio triage | TRITON | — | Reach priority ranking |
| Climate risk curve | TRITON (50 scenarios) | SPHERE | Probabilistic damage distribution |
| Full regulatory + risk | RAS Agent → SPHERE | — | FEMA deliverable + annualized loss estimate |
| Pluvial screening | TRITON | SPHERE | Uninsured stormwater risk exposure |

---

## Status

🚧 **Early framework** — architecture defined, adapters in development.

- [x] Pipeline architecture
- [x] Common depth grid data model
- [ ] TRITON adapter
- [ ] RAS Agent adapter
- [ ] SPHERE adapter
- [ ] Example workflows
- [ ] Documentation

---

## Component Projects

| Tool | Owner | License | Purpose |
|---|---|---|---|
| [TRITON v2](https://triton.ornl.gov) | Oak Ridge National Laboratory | Open source | GPU-accelerated 2D hydraulics |
| [RAS Agent](https://github.com/gheistand/ras-agent) | Reep Works | Apache 2.0 | HEC-RAS automation (regulatory) |
| [SPHERE](https://github.com/Niyam-Projects/sphere) | Niyam Projects | Apache 2.0 | HAZUS flood consequence estimation |

---

## License

Apache 2.0 — same as RAS Agent and SPHERE.

---

## Contributing

FloodStack is being built in the open. If you're working on TRITON, SPHERE, HEC-RAS automation, or flood risk quantification and want to collaborate, open an issue or reach out.

Built by [Reep Works](https://reepworks.com) · *AI for What Matters*
