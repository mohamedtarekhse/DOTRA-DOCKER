import requests
from requests_auth import DigestAuth


class ISAPIClient:
    """Hikvision LPR camera client using ISAPI + HTTP Digest auth."""

    def __init__(self, ip: str, username: str, password: str, port: int = 80):
        self.base = f"http://{ip}:{port}"
        self.auth = DigestAuth(username, password)
        self.timeout = 5

    def get_plate_recognition_url(self) -> str:
        """ISAPI path to configure/config the ANPR engine."""
        return "/ISAPI/Traffic/channels/1/vehicleDetect/plates"

    def get_snapshot(self) -> bytes:
        """Capture a JPEG snapshot from the camera."""
        resp = requests.get(f"{self.base}/ISAPI/Streaming/channels/101/picture",
                            auth=self.auth, timeout=self.timeout)
        resp.raise_for_status()
        return resp.content

    def test_connection(self) -> bool:
        try:
            resp = requests.get(f"{self.base}/ISAPI/System/deviceInfo",
                                auth=self.auth, timeout=self.timeout)
            return resp.status_code == 200
        except Exception:
            return False
