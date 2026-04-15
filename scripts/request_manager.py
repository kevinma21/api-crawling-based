import requests
import time
import json
import random

class XRequestManager:
    BASE_URL = "https://x.com/i/api/graphql"

    def __init__(self, bearer_token, auth_token, csrf_token, max_retries=5, enable_backoff=True):
        self.bearer_token = bearer_token
        self.auth_token = auth_token
        self.csrf_token = csrf_token
        self.max_retries = max_retries
        self.enable_backoff = enable_backoff

        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "x-csrf-token": self.csrf_token,
            "Cookie": f"auth_token={self.auth_token}; ct0={self.csrf_token};",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://x.com/",
            "Origin": "https://x.com"
        }

    def _calculate_backoff(self, attempt):
        """
        Exponential backoff with jitter.
        Base = 60s, Ratio = 2, Max = 10min
        """
        base = 60
        ratio = 2
        max_time = 600

        if not self.enable_backoff:
            return base

        # exponential backoff with random jitter
        delay = min(ratio * attempt * base + base, max_time)
        jitter = random.uniform(0.8, 1.2)
        return round(delay * jitter, 2)

    def get_graphql(self, endpoint, variables, features, field_toggles):
        """
        Send a GET request to Twitter's hidden GraphQL API.
        Example endpoint: fafowSZBCQYf5-CNIZ04bw/UserTweets
        """
        url = f"{self.BASE_URL}/{endpoint}"

        params = {
            "variables": json.dumps(variables, separators=(",", ":")),
            "features": json.dumps(features, separators=(",", ":")),
            "fieldToggles": json.dumps(field_toggles, separators=(",", ":"))
        }

        attempt = 0
        while attempt < self.max_retries:
            try:
                resp = requests.get(url, headers=self.headers, params=params)

                # Handle normal success
                if resp.status_code == 200:
                    return resp.json()

                # Handle rate-limit
                elif resp.status_code in (420, 429):
                    wait = self._calculate_backoff(attempt)
                    print(f"Rate limit hit (HTTP {resp.status_code}). Sleeping {wait}s...")
                    time.sleep(wait)
                    attempt += 1
                    continue

                # Handle auth error or forbidden
                elif resp.status_code in (401, 403):
                    print(f"Authentication failed (HTTP {resp.status_code}). Check your tokens.")
                    return None

                else:
                    print(f"Unexpected error (HTTP {resp.status_code}): {resp.text[:200]}")
                    time.sleep(3)
                    attempt += 1

            except requests.RequestException as e:
                print(f"Network error: {e}. Retrying...")
                time.sleep(5)
                attempt += 1

        print("Max retries reached. Giving up.")
        return None
