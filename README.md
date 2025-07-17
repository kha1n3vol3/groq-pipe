# Groq Pipe for Open WebUI

> A lightweight, self-contained connector that lets **[Open WebUI](https://github.com/open-webui/open-webui)** talk to Groq’s OpenAI-compatible Chat Completion API.  
> ‑ Written in 100 % Python, no TTS / Whisper clutter, no external
>  dependencies besides `requests` and `pydantic`.

---

## ✨ Features
|                     | Description |
|---------------------|-------------|
| 🔌 **Plug-and-play** | Drop the file into `open-webui/extensions/` and it appears as a provider. |
| 🚀 **Fast start-up** | Uses a baked-in model list; can refresh it once per process. |
| 🛡️ **Prefix guard** | Strips any UI-added prefix such as `groq.`, `groq_new.` etc.—prevents “404 unknown model”. |
| 🔁 **Connection reuse** | Keeps a single `requests.Session` alive for all calls. |
| 🐍 **PEP-8 ready** | Clean, typed, documented & Pylint-friendly. |
| 📦 **Zero build step** | Pure Python; works on every CPython ≥ 3.8. |

---

## 📦 Installation

```bash
# 1. Clone or download the file
git clone https://github.com/YOUR_USER/groq-open-webui-pipe.git
cd groq-open-webui-pipe

# 2. (Optional) create a venv
python -m venv .venv
source .venv/bin/activate

# 3. Install runtime deps
pip install -r requirements.txt
#   requirements.txt contains only:
#   requests
#   pydantic

# 4. Tell the world about your Groq key
export GROQ_API_KEY="sk-XXXXXXXX"

# 5. Run the self-test
python groq_pipe.py
```

To use it inside **Open WebUI**, copy `groq_pipe.py` into  
`open-webui/extensions/groq_pipe/pipe.py` (or any folder name you
like).  Restart WebUI; Groq will show up in the “Providers” list.

---

## 🚀 Quick example

```python
from groq_pipe import Pipe

pipe = Pipe()

body = {
    "model": "groq_new.moonshotai/kimi-k2-instruct",   # any prefix works
    "messages": [{"role": "user", "content": "Hello Groq!"}],
    "stream": False,
}

reply = pipe.pipe(body)
print(reply)
```

---

## 📑 API Overview

| Method | Purpose |
|--------|---------|
| `Pipe()` | Construct the connector (creates a reusable `requests.Session`). |
| `.pipes()` | Return `[{id, name}, …]` for WebUI’s provider registry. |
| `.pipe(body)` | Perform the `POST /chat/completions` request; returns JSON, an iterator (when `stream=True`), or an error string. |

See the doc-strings in **[groq_pipe.py](groq_pipe.py)** for deep details.

---

## 🏗️ How it works

1.  On first use, `_fetch_models_once()` contacts `GET /models` to obtain
    all available ids, filtering out any that contain `tts` or `whisper`.
    If the call fails (network outage, bad key) a small **hard-coded list**
    is used instead.
2.  The main `.pipe()` method
    - validates that the body has `model` and `stream`,
    - strips any prefix before the first `.`,
    - rejects unknown model ids locally (avoids a 404 round-trip),
    - posts the request with a 60 s timeout, and
    - returns either streamed bytes (`iter_lines`) or parsed JSON.

---

## 🐛 Troubleshooting

| Symptom | Possible cause / fix |
|---------|----------------------|
| `Error: GROQ_API_KEY not set` | Export a key from Groq Console → *Settings → API Keys*. |
| `404 unknown model` | Spelling mistake or the model is not in the cached list—call `curl https://api.groq.com/openai/v1/models` to verify. |
| “Cannot parse” linter error | You are using Python < 3.8. Upgrade :-) |

---

## 📝 License

MIT – do whatever you like, just keep the copyright notice.

---

## 🙏 Acknowledgements

Built on the shoulders of **[Groq](https://console.groq.com)**  
and **[Open WebUI](https://github.com/open-webui/open-webui)** communities.
PRs and suggestions are welcome!
