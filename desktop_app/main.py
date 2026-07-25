import json
import os
import sys

import webview

DEFAULT_URL = "https://crm-lomito.onrender.com"


def config_path():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "lomito_config.json")


def load_url():
    env_url = os.environ.get("LOMITO_APP_URL")
    if env_url:
        return env_url.strip()

    path = config_path()

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            url = (data.get("url") or "").strip()
            if url:
                return url
        except (OSError, ValueError):
            pass

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"url": DEFAULT_URL}, f, indent=2, ensure_ascii=False)
    except OSError:
        pass

    return DEFAULT_URL


def main():
    url = load_url()

    webview.create_window(
        "Mi Querido Lomito - CRM",
        url,
        width=1280,
        height=800,
        min_size=(360, 600),
        text_select=True,
        confirm_close=False,
    )
    webview.start()


if __name__ == "__main__":
    main()
