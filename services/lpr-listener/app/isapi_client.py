import requests
from requests.auth import HTTPDigestAuth


class ISAPIClient:
    """Hikvision LPR camera client using ISAPI + HTTP Digest auth."""

    def __init__(self, ip: str, username: str, password: str, port: int = 80):
        self.base = f"http://{ip}:{port}"
        self.auth = HTTPDigestAuth(username, password)
        self.timeout = 5

    def get_plates(self) -> str:
        """Return the raw XML body of recent recognized plates (GET plates channel)."""
        resp = requests.get(f"{self.base}/ISAPI/Traffic/channels/1/vehicleDetect/plates",
                            auth=self.auth, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def test_connection(self) -> bool:
        try:
            resp = requests.get(f"{self.base}/ISAPI/System/deviceInfo",
                                auth=self.auth, timeout=self.timeout)
            return resp.status_code == 200
        except Exception:
            return False
