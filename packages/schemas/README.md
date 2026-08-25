The live OpenAPI document is served by the control plane at `GET /openapi.json`.

A snapshot is stored in [`openapi.json`](openapi.json). Regenerate:

```powershell
python packages/schemas/dump_openapi.py
```
