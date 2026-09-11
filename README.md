# MMF v1.0.18

GitHub-ready release of Miao Market Framework. This package defaults to port `8005`, so it can run alongside an older local MMF instance.

## What changed

- Ticker-aware classification for individual stocks, broad-market ETFs, sector ETFs, and leveraged ETFs.
- SOXL logic is a specialist profile, not the universal template.
- Six-block primary decision layer with expandable evidence.
- Price → volume → breadth → relative strength → possible flow → macro/risk → action narrative.
- Contextual Put/Call, macro causal chain, geopolitical transmission, and OPEX risk.
- Exactly four conditional paths whose planning weights total 100%.
- Review Mode plus complete Chinese/English Markdown export.
- One shared DOM for Chinese and English; daily email follows the selected language.

## Run independently

```bash
cd MMF-1.0.18
cp config/config.env.example config/config.env
python3 start.py
```

Open `http://127.0.0.1:8005/`. The default bind address is `0.0.0.0`, so a phone on the same network can use the Mac's LAN address with port 8005.

## Tests

```bash
PYTHONPYCACHEPREFIX=/tmp/mmf-pycache MPLCONFIGDIR=/tmp/mmf-mpl \
  .venv/bin/python -m unittest discover -s tests -v
```

The implementation specification is in [docs/MMF_v1.0.18_Master_Spec.md](docs/MMF_v1.0.18_Master_Spec.md). Technical documentation and UAT results are in the same directory.
