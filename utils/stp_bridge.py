"""
STP Bridge Module

Configurable bridge to forward karmic feedback signals to InsightFlow.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
from fastapi import HTTPException

# Setup logging
logger = logging.getLogger(__name__)

class STPBridge:
    """STP (Signal Transmission Protocol) Bridge for forwarding signals to InsightFlow"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the STP bridge"""
        self.config = config or {}
        self.insightflow_endpoint = self.config.get(
            "insightflow_endpoint", 
            "http://localhost:8001/api/v1/insightflow/receive"
        )
        self.retry_attempts = self.config.get("retry_attempts", 3)
        self.timeout = self.config.get("timeout", 10)
        self.enabled = self.config.get("enabled", True)
        
    def forward_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Forward karmic feedback signal to InsightFlow
        
        Args:
            signal: Karmic feedback signal to forward
            
        Returns:
            Dict with forwarding result
        """
        if not self.enabled:
            return {
                "status": "skipped",
                "message": "STP bridge is disabled",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        signal_id = signal.get("signal_id", str(uuid.uuid4()))
        
        try:
            # Prepare the payload for InsightFlow
            payload = {
                "transmission_id": str(uuid.uuid4()),
                "source": "karmachain_feedback_engine",
                "signal": signal,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to InsightFlow with retry logic
            response = self._send_with_retry(payload)
            
            # Log successful transmission
            logger.info(f"Signal {signal_id} forwarded to InsightFlow successfully")
            
            return {
                "status": "success",
                "signal_id": signal_id,
                "transmission_id": payload["transmission_id"],
                "response": response,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error forwarding signal {signal_id} to InsightFlow: {str(e)}"
            logger.error(error_msg)
            
            return {
                "status": "error",
                "signal_id": signal_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _send_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send payload with retry logic
        
        Args:
            payload: Payload to send
            
        Returns:
            Dict with response details
        """
        last_exception = Exception("Unknown error")
        
        for attempt in range(self.retry_attempts):
            try:
                response = requests.post(
                    self.insightflow_endpoint,
                    json=payload,
                    timeout=self.timeout
                )
                
                response_data = response.json() if response.content else {}
                
                if response.status_code in [200, 201]:
                    return {
                        "status_code": response.status_code,
                        "response": response_data,
                        "attempt": attempt + 1
                    }
                else:
                    logger.warning(
                        f"Attempt {attempt + 1} failed with status {response.status_code}"
                    )
                    last_exception = HTTPException(
                        status_code=response.status_code,
                        detail=f"InsightFlow returned status {response.status_code}"
                    )
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed with exception: {str(e)}")
                last_exception = e
        
        # If we get here, all attempts failed
        raise last_exception
    
    def batch_forward_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Forward multiple signals in batch
        
        Args:
            signals: List of signals to forward
            
        Returns:
            List of forwarding results
        """
        results = []
        
        for signal in signals:
            result = self.forward_signal(signal)
            results.append(result)
            
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the STP bridge connection
        
        Returns:
            Dict with health status
        """
        try:
            # Send a simple health check ping
            health_payload = {
                "transmission_id": str(uuid.uuid4()),
                "source": "karmachain_feedback_engine",
                "type": "health_check",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                self.insightflow_endpoint,
                json=health_payload,
                timeout=self.timeout
            )
            
            return {
                "status": "healthy" if response.status_code in [200, 201] else "unhealthy",
                "endpoint": self.insightflow_endpoint,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "endpoint": self.insightflow_endpoint,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Global instance
stp_bridge = STPBridge()

# Convenience functions
def forward_karmic_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Forward a karmic signal to InsightFlow"""
    return stp_bridge.forward_signal(signal)

def batch_forward_karmic_signals(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Forward multiple karmic signals to InsightFlow"""
    return stp_bridge.batch_forward_signals(signals)

def check_stp_bridge_health() -> Dict[str, Any]:
    """Check the health of the STP bridge"""
    return stp_bridge.health_check()