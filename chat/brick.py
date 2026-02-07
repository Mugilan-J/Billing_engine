import os
from pathlib import Path

import requests
import time
import threading
import psycopg2
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage


def _load_env():
    if os.getenv("DATABASE_URL"):
        return

    current = Path(__file__).resolve()
    for directory in [current.parent, *current.parents]:
        env_file = directory / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
            break


_load_env()

# DB Configuration
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL is not set. Create an .env file with the connection string.")

# 1. Define a Custom Exception
class AuthenticationError(Exception):
    """Custom exception for API key validation failures."""
    pass

class BrickClient:
    def __init__(self, api_key: str, system_prompt: str = "", model: str = "smollm2", billing_url: str = "http://localhost:8080/events"):
        self.api_key = api_key
        self.model = model
        self.billing_url = billing_url
        
        # 2. Validate Key immediately
        # We wrap this in a private method check
        if not self._is_key_valid():
            # Raise our custom error with a clean message
            raise AuthenticationError("Invalid or inactive API Key provided.")

        # If valid, proceed to setup LLM
        self.llm = ChatOllama(model=model)
        self.history = []
        if system_prompt:
            self.history.append(SystemMessage(content=system_prompt))

    def _is_key_valid(self):
        """
        Connects to DB to check if key exists. 
        Returns True if valid, False otherwise.
        Handles DB errors gracefully.
        """
        try:
            with psycopg2.connect(DB_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM api_keys WHERE key_value = %s AND status = 'active'", 
                        (self.api_key,)
                    )
                    return cur.fetchone() is not None
        except psycopg2.OperationalError:
            # If DB is down, we treat it as an auth failure (or you could raise a SystemError)
            raise AuthenticationError("Could not connect to authentication server.")
        except Exception as e:
            raise AuthenticationError(f"System error during auth: {str(e)}")

    def list_models(self):
        return ["smollm2", "llama3", "mistral", "gemma:2b"]

    def _report_billing(self, user_input, response, duration_ms):
        input_tokens = len(user_input) // 4
        output_tokens = len(response) // 4
        
        payload = {
            "user_id": "client_user", 
            "org_id": "default_org",
            "model": self.model,
            "provider": "ollama",
            "api_key_id": self.api_key,
            "type": "chat",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "duration_ms": duration_ms,
            "status": 200
        }

        try:
            requests.post(self.billing_url, json=payload, timeout=2)
        except Exception as e:
            pass # Silent fail for background stats

    def ask(self, query: str) -> str:
        self.history.append(HumanMessage(content=query))
        
        start_time = time.time()
        try:
            ai_msg = self.llm.invoke(self.history)
            response_text = ai_msg.content
        except Exception as e:
            return "⚠️ Error: AI service is currently unavailable."
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        self.history.append(ai_msg)
        
        billing_thread = threading.Thread(
            target=self._report_billing, 
            args=(query, response_text, duration_ms)
        )
        billing_thread.start()

        return response_text