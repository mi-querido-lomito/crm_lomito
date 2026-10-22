import json
import os
import sys
from urllib.parse import urlsplit, urlunsplit

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


class DesktopBridge:
    def __init__(self, pos_url):
        self.pos_url = pos_url
        self.pos_window = None

    def open_pos(self):
        if self.pos_window is None:
            self.pos_window = webview.create_window(
                "Mi Querido Lomito - Punto de venta",
                self.pos_url,
                width=1100,
                height=800,
                min_size=(360, 600),
                text_select=True,
                confirm_close=False,
            )
        else:
            try:
                self.pos_window.show()
                self.pos_window.restore()
            except Exception:
                pass
        return True


def append_path(url, path):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/") + path, parts.query, parts.fragment))


def webview_storage_path():
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(root, "MiQueridoLomitoCRM", "WebView2")
    os.makedirs(path, exist_ok=True)
    return path


def main():
    base_url = load_url().rstrip("/")
    bridge = DesktopBridge(append_path(base_url, "/ventas/ventana"))

    webview.create_window(
        "Mi Querido Lomito - Ventana general",
        append_path(base_url, "/desktop_session"),
        width=1280,
        height=800,
        min_size=(360, 600),
        text_select=True,
        confirm_close=False,
        js_api=bridge,
    )
    webview.start(private_mode=False, storage_path=webview_storage_path())


if __name__ == "__main__":
    main()
