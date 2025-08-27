import httpx
import time
from typing import Optional, Dict, Any, Callable, Union


class Http:
    def __init__(
        self,
        base_url: str,
        defaults: Optional[Dict[str, Any]] = None,
        wrapper: Optional[Callable[[httpx.Response], Any]] = None,
        retries: int = 3,
        backoff: float = 0.5,  # wait time between retries
    ):
        self.base_url = base_url.rstrip("/")
        self.defaults = defaults or {}
        self.wrapper = wrapper or (lambda r: (True, r.json()))
        self.client = httpx.Client(base_url=self.base_url, **self.defaults)
        self.retries = retries
        self.backoff = backoff

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        last_error = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = self.client.request(method, endpoint.lstrip("/"), **kwargs)
                resp.raise_for_status()
                return self.wrapper(resp)
            except Exception as e:
                last_error = e
                if attempt < self.retries:
                    time.sleep(self.backoff * attempt)  # simple exponential backoff
                continue
        return False, {"error": str(last_error)}

    def _decorator(self, method: str, endpoint: str, **kwargs):
        def decorator(func: Callable):
            succ, data = self._make_request(method, endpoint, **kwargs)
            return func(succ, data)
        return decorator

    # dual-use (direct call or decorator)
    def get(self, endpoint: str, **kwargs) -> Union[Any, Callable]:
        if kwargs.pop("_decorator", False):
            return self._decorator("GET", endpoint, **kwargs)
        return self._make_request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> Union[Any, Callable]:
        if kwargs.pop("_decorator", False):
            return self._decorator("POST", endpoint, **kwargs)
        return self._make_request("POST", endpoint, **kwargs)

    def close(self):
        self.client.close()
