# Hashes of the JISA training round's predeclarations

Recorded with SHA-256 in the project record at 2026-10-20T18:58Z, before any run of the round. Two files later received a dated appendix (a clarification and a deviation), each recorded before any result it affects was read; the text before that appendix reproduces the recorded hash. The record is internal: no external registry timestamped it.

| file | recorded SHA-256 | text hashed |
|---|---|---|
| `jisa_X1_X2_X4_seeds_budget_multiclass.md` | `2e4d3aa69d9f9c09e94a049fecde666e42b925cd1584b246fdf4520228a507ea` | up to `## Deviation recorded 2026-10-20`, ending in one newline |
| `jisa_JS01_cic_victim_replication.md` | `34e2b25eea1c5b9dc3ed7db8af51351ff3a013bad34998e550001be9fe1c9176` | up to `## Clarification recorded 2026-10-20`, ending in one newline |
| `jisa_JS02_JS03_size_capacity.md` | `d6d377593e54efcff968a87a7927a3881ef0a505b4f49541c99b9d9f48021e9b` | the whole file |

Check: `python3 -c "import hashlib,sys; b=open(sys.argv[1],'rb').read(); m=sys.argv[2].encode(); i=b.find(m); b=b if i<0 else b[:i].rstrip(b'\n')+b'\n'; print(hashlib.sha256(b).hexdigest())" FILE 'MARKER'`
