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
        
        # Used to differentiate between a tutor or student
        self._bias_type: Optional[str] = self.body.get("bias_type")
        self._assessment_id: Optional[int] = self.body.get("assessment_id")
        self._s3_output_key: Optional[str] = self.body.get("s3_output_key")
        self._organization_id: Optional[str] = self.body.get("organization_id")
    
    def get_body(self) ->Optional[dict]:
        return self.body

    def get_bias_type(self) -> Optional[int]:
        return self._bias_type
    
    def get_organization_id(self) ->Optional[int]:
        return self._organization_id

    def get_assessment_id(self) -> Optional[str]:
        return self._assessment_id

    def get_s3_output_key(self) -> Optional[str]:
        return self._s3_output_key
