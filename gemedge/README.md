# GemEdge Data Extraction

Phase 1 creates the runnable scraper project structure for extracting awarded procurement data from India's Government e-Marketplace portal.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Checks

Run the Phase 1 setup validation from this directory:

```bash
python main.py --check
```

Expected output:

```text
Setup OK
```

## Project Layout

```text
gemedge/
├── config.py
├── browser.py
├── logger.py
├── checkpointing.py
├── scraper.py
├── cleaner.py
├── insights.py
├── main.py
├── requirements.txt
├── README.md
├── checkpoints/
│   └── .gitkeep
├── data/
│   └── raw/
│       └── .gitkeep
└── output/
    └── .gitkeep
```

