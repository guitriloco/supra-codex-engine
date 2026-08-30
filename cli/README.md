# Supra-Codex CLI

The **Supra-Codex CLI** is the developer's front door to the Supra-Codex
engine — sovereign, local-first orchestration for web scraping, AI
enrichment (via Xerebro + Ollama), and distributed node management, all from
your terminal. No third-party APIs, no vendor lock-in.

## Install

From this directory (`supra-codex-engine/cli`):

```bash
pip install .
```

This installs the `supra` command and its dependencies (Typer, Rich, httpx).
For development:

```bash
pip install -e ".[dev]"
```

## Configuration

Config lives at `~/.supra-codex/config.json` and is auto-created with
defaults on first run.

```bash
supra config show                 # print current config
supra config set api_base_url http://192.168.1.50:8000
supra config set timeout_seconds 120
```

The default `api_base_url` is `http://localhost:8000` — point it at your
engine instance (or a remote node's public API) as needed.

## Usage

```bash
supra status                       # engine health check
supra scrape https://example.com   # scrape a URL
supra pipeline run https://example.com            # scrape + Xerebro AI enrich
supra pipeline run <url> --prompt "Extract the price" --model llama3.2
supra nodes list                   # list registered compute nodes
supra marketplace search price     # search Nectar Marketplace
supra marketplace list --installed # only installed modules
supra marketplace info <module_id>
supra marketplace install <module_id>
supra marketplace uninstall <module_id>
```

`supra pipeline run <url> --json` emits the raw engine result as JSON for
scripting and piping into other tools. `supra marketplace search <query>` is
the natural filter on module name, description, category, or author.

## About

- **Sovereign compute** — everything runs on your own hardware.
- **Zero API lock-in** — no mandatory third-party services.
- **Local-first AI** — Xerebro reasoning stays on your machine via Ollama.
- **CLI-first developer experience** — fast, scriptable, composable.
