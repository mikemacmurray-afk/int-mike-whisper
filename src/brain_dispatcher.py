import os
import json
import time
import logging
import requests

logger = logging.getLogger(__name__)

DAILY_BRAIN_URL = os.environ.get("DAILY_BRAIN_URL", "http://localhost:4321/api/inbox")
OFFLINE_QUEUE_PATH = os.path.expanduser(
    os.environ.get("DAILY_BRAIN_QUEUE_PATH", "~/.mikewhisper_brain_queue.jsonl")
)

def dispatch_to_daily_brain(text: str):
    """Sends voice transcription to Daily Brain API with offline buffering."""
    try:
        requests.post(
            DAILY_BRAIN_URL,
            json={
                "source": "whisper_voice",
                "raw_text": text
            },
            timeout=2.0
        )
        logger.info("Successfully dispatched transcription to Daily Brain API.")
    except Exception as e:
        logger.warning(f"Daily Brain API unreachable ({e}). Buffering to {OFFLINE_QUEUE_PATH}...")
        try:
            with open(OFFLINE_QUEUE_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "source": "whisper_voice",
                    "raw_text": text,
                    "timestamp": time.time()
                }) + "\n")
            logger.info("Successfully buffered transcription offline.")
        except Exception as write_err:
            logger.error(f"Failed to buffer transcription to offline queue: {write_err}")
