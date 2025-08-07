"""
title: Groq Starficient
author: https://github.com/kha1n3vol3
author_url: https://github.com/kha1n3vol3
funding_url: https://github.com/kha1n3vol3
version: 0.2

This module exports one public class – ``Pipe`` – that adapts Groq’s
OpenAI-compatible REST API to Open WebUI’s plug-in interface.

The class
• validates input
• strips any WebUI-added `<prefix>.` in front of the model id
• checks the model id against a cached allow-list (prevents 404s)
• sends the request with automatic connection reuse
• returns either the JSON response, an iterator of streamed bytes, or a
  descriptive error string.
                                       █████████████████████████
                                      ████████████████████████
                                     █████████████████████████
                                    █████████████████████████
                                   █████████████████████████
                                  █████████████████████████
                                 █████████████████████████
                                █████████████████████████
                               █████████████████████████
                              █████████████████████████
                             █████████████████████████
                            █████████████████████████
                           █████████████████████████                  ███
                          █████████████████████████                   ████
                         █████████████████████████                   ██████
                        █████████████████████████                   ████████
                        ████████████████████████                   █████████
                       ████████████████████████                  ████████████
                      ████████████████████████                  ██████████████
                     █████████████████████████                 ████████████████
                    █████████████████████████                  █████████████████
                   █████████████████████████                  ███████████████████
                  █████████████████████████                  █████████████████████
                 █████████████████████████                  ███████████████████████
                █████████████████████████                  █████████████████████████
               █████████████████████████                    █████████████████████████
              ████████████████████████                       █████████████████████████
             █████████████████████████                        █████████████████████████
            █████████████████████████                          █████████████████████████
           █████████████████████████                            █████████████████████████
          █████████████████████████                              █████████████████████████
         █████████████████████████                                █████████████████████████
        █████████████████████████                                  █████████████████████████
       █████████████████████████                                    ████████████████████████
      █████████████████████████                                      ████████████████████████
     █████████████████████████                                        ████████████████████████
    █████████████████████████                                          ████████████████████████
   ██████████████████████████                                          █████████████████████████
  ██████████████████████████                                            █████████████████████████
  █████████████████████████                                              █████████████████████████
 █████████████████████████                                                █████████████████████████
█████████████████████████                                                  █████████████████████████
"""

from __future__ import annotations

import logging
import os
from typing import (
    Any,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Union,
)

import requests
from pydantic import BaseModel, Field

# ────────────────────────────────────────────────────────────────────────
# Configuration constants
# ────────────────────────────────────────────────────────────────────────
API_BASE_URL = "https://api.groq.com/openai/v1"
REQUEST_TIMEOUT = 60  # seconds
EXCLUDE_SUBSTRINGS: tuple[str, ...] = ("tts", "whisper")  # never expose
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
LOGGER = logging.getLogger("GroqPipe")


class Pipe:
    """
    Lightweight wrapper around Groq’s ``/chat/completions`` endpoint.

    The class is instantiated once by Open WebUI and then used as a
    long-lived object.  A ``requests.Session`` is therefore kept around for
    TCP connection reuse.
    """

    # ─────────────────────────── secrets / valves ──────────────────────
    class Valves(BaseModel):
        """
        Container object for secrets so WebUI can inspect the schema.
        """

        API_KEY: str = Field(
            default=os.getenv("GROQ_API_KEY", ""),
            description="Create / copy a key at https://console.groq.com/keys",
        )

    # ────────────────────────────── init ───────────────────────────────
    def __init__(self) -> None:
        self.type = "manifold"
        self.id = "groq"  # prefix used by Open WebUI
        self.name = "groq/"
        self.base_url = API_BASE_URL
        self.valves = self.Valves()
        self._session = requests.Session()
        self._model_cache: Optional[List[str]] = None  # populated on demand

    # ──────────────────────────── model list ───────────────────────────
    @staticmethod
    def _hardcoded_models() -> List[str]:
        """
        Return a hand-curated list of models (2024-06).

        Hard-coding avoids a network round-trip on every UI page load and
        still works if Groq’s `/models` endpoint is temporarily down.
        """
        return [
            "allam-2-7b",
            "compound-beta",
            "compound-beta-mini",
            "deepseek-r1-distill-llama-70b",
            "gemma2-9b-it",
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "meta-llama/llama-guard-4-12b",
            "meta-llama/llama-prompt-guard-2-22m",
            "meta-llama/llama-prompt-guard-2-86m",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "mistral-saba-24b",
            "moonshotai/kimi-k2-instruct",
            "qwen/qwen3-32b",
        ]

    def _fetch_models_once(self) -> List[str]:
        """
        Fetch ``GET /models`` exactly once per process, cache the result.

        Falls back to ``_hardcoded_models`` if the request fails.
        Excludes any model containing a substring in ``EXCLUDE_SUBSTRINGS``.
        """
        if self._model_cache is not None:
            return self._model_cache

        try:
            LOGGER.info("Fetching model list from Groq …")
            response = self._session.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.valves.API_KEY}"},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            remote_models = [m["id"] for m in response.json().get("data", [])]
            self._model_cache = [
                m for m in remote_models if not any(x in m for x in EXCLUDE_SUBSTRINGS)
            ]
            LOGGER.info("Cached %d models from Groq.", len(self._model_cache))
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.warning("Model refresh failed (%s); using hard-coded list.", exc)
            self._model_cache = [
                m
                for m in self._hardcoded_models()
                if not any(x in m for x in EXCLUDE_SUBSTRINGS)
            ]

        return self._model_cache

    # Public helper for Open WebUI
    def pipes(self) -> List[Dict[str, str]]:
        """
        Return the model list in Open WebUI’s expected ``[{id, name}, …]`` format.
        """
        return [{"id": m, "name": m} for m in self._fetch_models_once()]

    # ───────────────────────── main request ────────────────────────────
    def pipe(
        self,
        body: Dict[str, Any],
    ) -> Union[
        str,
        Dict[str, Any],
        Generator[bytes, None, None],
        Iterator[bytes],
    ]:
        """
        Execute ``POST /chat/completions``.

        Parameters
        ----------
        body : dict
            The request payload expected by the OpenAI API.

        Returns
        -------
        dict | iterator | str
            • dict: normal non-streamed response
            • iterator / generator: when ``stream`` is ``True``
            • str: human-readable error message
        """

        # ---------- basic validation -----------------------------------
        if "model" not in body or "stream" not in body:
            return "Error: request body must contain 'model' and 'stream'."

        if not self.valves.API_KEY:
            return "Error: GROQ_API_KEY environment variable not set."

        # ---------- strip any '<prefix>.' that WebUI adds --------------
        if "." in body["model"]:
            body["model"] = body["model"].split(".", 1)[1]

        model_name = body["model"]
        allowed_models = self._fetch_models_once()
        if model_name not in allowed_models:
            return (
                f"Error: model '{model_name}' is not supported.\n"
                f"Valid models: {', '.join(allowed_models)}"
            )

        # ---------- perform request ------------------------------------
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.valves.API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            response = self._session.post(
                url=url,
                json=body,
                headers=headers,
                stream=bool(body["stream"]),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.iter_lines() if body["stream"] else response.json()

        except requests.exceptions.HTTPError as exc:
            msg = (
                f"HTTP {response.status_code} calling {url}: {exc}\n" f"{response.text}"
            )
            if response.status_code == 404:
                msg += "\n(404 usually means an unknown model id.)"
            return msg

        except Exception as exc:  # pylint: disable=broad-except
            return f"Unhandled error: {exc}"


# ───────────────────────────── demo / self-test ─────────────────────────────
if __name__ == "__main__":
    pipe = Pipe()

    demo_request = {
        "model": "groq_new.moonshotai/kimi-k2-instruct",  # intentional prefix
        "messages": [{"role": "user", "content": "Hello from demo!"}],
        "stream": False,
    }

    print("Sending demo request …")
    result = pipe.pipe(demo_request)
    print("Result:\n", result)
