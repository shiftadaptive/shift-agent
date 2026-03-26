# SHIFT ::: Agent
# Custom Logger Configuration
# (c) 2026 ShiftAdaptive

import logging
import sys
import os
import json
import threading
from datetime import datetime
import requests

class BetterStackHandler(logging.Handler):
    def __init__(self, endpoint, token, service):
        super().__init__()
        self.endpoint = endpoint
        self.token = token
        self.service = service

    def emit(self, record):
        try:
            payload = {
                "dt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "message": record.getMessage(),
                "level": record.levelname,
                "service_name": self.service,
            }
            
            # Capture extra attributes if any
            if hasattr(record, 'extra'):
                payload.update(record.extra)

            # Send in a separate thread to avoid blocking
            threading.Thread(target=self.send, args=(payload,), daemon=True).start()
        except Exception:
            self.handleError(record)

    def send(self, payload):
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            }
            resp = requests.post(self.endpoint, headers=headers, data=json.dumps(payload), timeout=5)
            resp.close()
        except:
            pass

def init_logger():
    # Console handler with custom format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('[AGENT] %(message)s'))
    
    # Root logger for the 'shift' namespace
    logger = logging.getLogger("shift")
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # Better Stack Handler
    endpoint = "https://s2322564.eu-fsn-3.betterstackdata.com"
    token = os.getenv("BETTERSTACK_TOKEN")
    
    if token:
        remote_handler = BetterStackHandler(endpoint, token, "Shift Agent")
        logger.addHandler(remote_handler)
    
    # Prevent propagation to the root logger to avoid duplicate logs in some environments
    logger.propagate = False
    
    return logger

# Convenience instance
log = logging.getLogger("shift")
