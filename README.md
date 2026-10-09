# Touch Grass Field Cards

A local open-weight model writes you a one-page **paper** walk card. You print it, pocket the phone, and go. The screen's whole job is the 30 seconds before you leave.

Built for the [Hacktoberfest Open-Source AI Challenge, Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05).

Open [`examples/sample-card.html`](examples/sample-card.html) to see a card (generated with `--demo`, so no model wrote it).

## Quickstart

Needs Python 3.8+ (standard library only) and [Ollama](https://ollama.com) 0.5 or newer (for structured outputs).

```bash
ollama pull gemma3:1b
python touchgrass.py --lat 40.66 --lon -73.97 --minutes 60 --mood calm --with "two kids" --place "Prospect Park"
# open field-card.html, print it (A5 or half-letter), go outside
```

| Flag | Meaning |
|---|---|
| `--lat --lon` | where you're walking (never sent anywhere but your own machine) |
| `--minutes`, `--start`, `--date` | how long, when you leave, which day |
| `--mood`, `--with`, `--place` | flavour for the prompts |
| `--model` | any model your local server has pulled (`TOUCHGRASS_MODEL`) |
| `--host` | any Ollama-compatible endpoint (`TOUCHGRASS_HOST`) |
| `--out` | output file path (default `field-card.html`) |
| `--demo` | skip the model; emit a sample card for testing |

## How it works

- **Facts from math.** Sunrise, sunset, moon phase and season come from NOAA solar equations in about 15 lines, offline. The "home by" time is computed in code, never by the model.
- **Words from the model.** The facts go to a local model as ground truth (default `gemma3:1b`, small enough for a plain laptop; try `--model gemma3:4b` for richer cards). Output is constrained to a JSON schema, then validated, clipped and retried up to three times.
- **Safe by design.** The model only prompts you to notice, count, listen and compare. It never identifies or recommends touching or eating plants, fungi or animals, and a word check in code rejects any card that tries.
- **Swap the voice.** The whole personality is the `SYSTEM` string at the top of `touchgrass.py`. Fork it for a birder edition or a kid edition.

## License

[MIT](LICENSE)
