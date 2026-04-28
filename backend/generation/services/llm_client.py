# generation/services/llm_client.py
# -----------------------------------
# Handles communication with the local Ollama LLM.
#
# WHY WE SWITCHED FROM LANGCHAIN TO REQUESTS:
# The langchain Ollama wrapper accepts num_predict but silently
# ignores it in some versions — causing long fields like
# discussion_summary to be truncated mid-sentence.
#
# Using requests directly gives us guaranteed control over:
#   - num_predict (max tokens to generate)
#   - temperature
#   - timeout
#
# We still import langchain in the dataclass for compatibility,
# but the actual LLM call uses requests.

import requests
from dataclasses import dataclass


@dataclass
class LLMConfig:
    base_url:    str
    model:       str   = "llama3"
    temperature: float = 0.2


class OllamaLLMClient:

    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg

    def generate_text(self, prompt: str, max_tokens: int = 200) -> str:
        """
        Sends a prompt to Ollama and returns the response text.

        Uses the Ollama REST API directly via requests — this guarantees
        that num_predict (max tokens) is actually respected, unlike the
        langchain wrapper which sometimes ignores it.

        Parameters:
            prompt     - the text prompt to send
            max_tokens - how many tokens the LLM can generate
                         200 for normal fields (2-4 sentences)
                         500 for long fields like discussion_summary

        The request times out after 600 seconds (10 minutes).
        This is intentional — Llama3 running locally can be slow,
        especially for the first call when the model is loading.
        """
        url = f"{self.cfg.base_url}/api/generate"

        payload = {
            "model":  self.cfg.model,
            "prompt": prompt,
            "stream": False,          # wait for full response, don't stream
            "options": {
                "temperature": self.cfg.temperature,
                "num_predict": max_tokens,   # guaranteed to be respected
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=600)
            response.raise_for_status()
            return response.json().get("response", "").strip()

        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Ollama timed out after 600 seconds. "
                f"Make sure the model '{self.cfg.model}' is loaded. "
                f"Try running: ollama run {self.cfg.model}"
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.cfg.base_url}. "
                f"Make sure Ollama is running."
            )
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}")