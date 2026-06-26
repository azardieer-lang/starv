# OSINT Recon Tool

A lightweight command-line OSINT tool that gathers publicly available information about a person using only their full name.

## Features

- **Web Search** — Queries DuckDuckGo and Bing for the target name and returns titles, URLs, and snippets.
- **Social Media Scan** — Checks presence on LinkedIn, X (Twitter), GitHub, Instagram, Facebook, and Reddit.
- **Formatted Output** — Uses the `rich` library for clean, color-coded tables in the terminal.
- **Error Handling** — Gracefully handles timeouts, blocks, and connection errors.

## Requirements

- Python 3.8+
- `requests`, `beautifulsoup4`, `rich`

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python osint_tool.py
```

Enter the target's full name when prompted.

## Disclaimer

This tool is for educational and authorized research purposes only. Always comply with applicable laws and platform terms of service.
