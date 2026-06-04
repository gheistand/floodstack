# FloodStack Roadmap

## Phase 0 — Framework (Now)
*Establish the concept, architecture, and foot in the door*

- [x] README and vision
- [x] Architecture document
- [ ] GitHub repo (reepworks/floodstack)
- [ ] Apache 2.0 license
- [ ] Stub package structure with interfaces defined
- [ ] Common DepthGrid data model
- [ ] Basic IO utilities (raster read/write, GeoParquet)
- [ ] Reach out to Troy Schmidt (SPHERE) — collaboration conversation
- [ ] Reach out to Shih-Chieh Kao (TRITON/ORNL) — awareness + interest

## Phase 1 — RAS Agent + SPHERE (Core Loop)
*Prove the integration with the two most mature tools*

- [ ] RAS Agent adapter (HEC-RAS HDF5 → DepthGrid)
- [ ] SPHERE adapter (DepthGrid → ConsequenceResult)
- [ ] Example: LOMR workflow + consequence summary
- [ ] Example: 4 return-period run → annualized loss estimate
- [ ] Unit tests for IO layer
- [ ] NSI (National Structure Inventory) integration
- [ ] Documentation site

**Milestone:** One end-to-end regulatory run producing both a flood map and a consequence table.

## Phase 2 — TRITON Integration
*Add the fast/ensemble engine*

- [ ] TRITON adapter (ASCII/binary → DepthGrid)
- [ ] Ensemble pipeline (N flow scenarios → N depth grids → risk curve)
- [ ] Triage workflow (portfolio screening, reach ranking)
- [ ] Pluvial workflow (gridded runoff hydrograph input)
- [ ] GPU vs. CPU runtime benchmarks
- [ ] Example: 50-scenario climate ensemble → probabilistic risk curve

**Milestone:** Climate risk curve for an Illinois watershed. Open it as a CHAMP pilot.

## Phase 3 — Full Stack + Climate
*Connect the upstream hydrology layer*

- [ ] Google Flood Forecasting adapter (ML flow predictions → flow inputs)
- [ ] Climate scenario pipeline (CMIP6 weather → Google model → TRITON/RAS → SPHERE)
- [ ] Climate-adjusted FIRM outputs
- [ ] Multi-watershed portfolio runs
- [ ] FEMA TMAC / ASFPM regulatory sandbox positioning

**Milestone:** Climate-adjusted flood risk quantification for a CHAMP pilot watershed, publishable as a methodology paper.

---

## Collaboration Targets

| Person | Affiliation | Tool | Ask |
|---|---|---|---|
| Troy Schmidt | Niyam Projects | SPHERE | Adapter co-development; SPHERE as FloodStack consequence module |
| Shih-Chieh Kao | ORNL | TRITON v2 | Awareness + adapter feedback; ORNL as institutional partner |
| Chad Berginnis | ASFPM | Policy | Position FloodStack as open-source methodology for ASFPM sandbox |

---

## Strategic Notes

- **Keep RAS Agent separate.** RAS Agent is regulatory HEC-RAS automation. FloodStack is the pipeline. They are not the same product.
- **Apache 2.0 all the way.** Matching license with SPHERE and RAS Agent is non-negotiable for clean collaboration.
- **CHAMP as the pilot.** Illinois portfolio (5,300+ stream miles) is the proof-of-concept. Internal credibility first, then publish.
- **Reep Works as convener.** The value isn't just the code — it's assembling the community around an open standard for flood risk quantification.
