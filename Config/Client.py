import json
import logging
import datetime
from typing import Optional
# --- Python logger ---
logging.basicConfig(
    level=logging.INFO, # Adjust to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



class Client:
    def __init__(self, body):
        try:
            self.body = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.info("Unable to parse file")
            self.body = {}

        self.organization_id: Optional[int] = self.body.get("organization_id")
        self.session_token: Optional[str] = self.body.get("session_token")
        self.tutor_id: Optional[int] = self.body.get("tutor_id")
        self.semester_id: Optional[int] = self.body.get("semester_id")
        self.session_id: Optional[int] = self.body.get("session_id")

    def get_orgainzation_id(self) -> Optional[str]:
        return self.organization_id

    def get_session_token(self) ->Optional[str]:
        return self.session_token

    def get_semester_id(self) ->Optional[str]:
        return self.semester_id

    def get_session_id(self) -> Optional[int]:
        return self.session_id
    
    def get_tutor_id(self) -> Optional[int]:
        return self.tutor_id
