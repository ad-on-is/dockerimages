#!/usr/bin/env python3
"""Mirror a Vite SPA (e.g. https://footrue.com) into a static directory.

The site is a client-side-rendered Vite SPA with per-route code splitting:
every tool page returns its own <title>/<meta> HTML shell, but the actual
tool code lives in lazy-loaded JS chunks that are only requested once a
route is visited in the browser.

To produce a complete, servable mirror without running a browser we:

  1. Read sitemap.xml to discover every route, download each page's HTML
     shell and store it at <path>/index.html (clean URLs).
  2. Parse every downloaded HTML/JS/CSS file for asset references and
     recursively download them. This follows Vite's dynamic import()
     chunks and __vite__mapDeps preload arrays, so all lazy chunks end up
     on disk even though no JS is ever executed.
  3. Store everything under OUTPUT_DIR (default /var/www/html).

External (cross-origin) resources such as Google Fonts and the Cloudflare
beacon are deliberately left untouched.
"""

import gzip
import logging
import os
import queue
import re
import threading
import time
from urllib.parse import unquote, urljoin, urlparse, urlsplit
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("CRAWL_URL", "https://footrue.com").rstrip("/")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/var/www/html")
CONCURRENCY = int(os.environ.get("CONCURRENCY", "8"))
INTERVAL = int(os.environ.get("CRAWL_INTERVAL", "0"))  # seconds; 0 = run once
TIMEOUT = int(os.environ.get("HTTP_TIMEOUT", "30"))
USER_AGENT = (
    "Mozilla/5.0 (compatible; FootrueMirror/1.0; +https://footrue.com)"
)

# Any file we might need to mirror. Requiring a path (contains '/') avoids
# false positives such as `foo.bind(bar)` matching a bare `*.bin` suffix.
ASSET_EXT_RE = re.compile(
    r"\.(?:js|mjs|cjs|css|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|eot"
    r"|wasm|mp3|wav|ogg|mp4|webm|json|txt|xml|webmanifest|pdf|zip|bin)$",
    re.IGNORECASE,
)

STRING_RE = re.compile(r"""(["'`])(.*?)\1""", re.DOTALL)
HTML_ATTR_RE = re.compile(r"""(?:src|href|content)\s*=\s*["']([^"']+)["']""", re.I)
SRCSET_RE = re.compile(r"""(?:srcset)\s*=\s*["']([^"']+)["']""", re.I)
CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)(.*?)\1\s*\)""", re.I)
LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.I)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


class Crawler:
    def __init__(self, base_url, outdir, concurrency):
        self.base_url = base_url
        self.outdir = outdir
        self.concurrency = concurrency
        self.host = urlparse(base_url).netloc
        self.q = queue.Queue()
        self.seen = set()
        self.lock = threading.Lock()
        self.count = 0
        self.errors = 0

    # -- URL helpers -----------------------------------------------------

    def same_origin(self, url):
        return urlparse(url).netloc == self.host

    def enqueue(self, url, kind):
        url = url.split("#", 1)[0]
        if not self.same_origin(url):
            return
        with self.lock:
            if url in self.seen:
                return
            self.seen.add(url)
            self.q.put((url, kind))

    # -- Fetch -----------------------------------------------------------

    def fetch(self, url):
        last_err = None
        for attempt in range(3):
            try:
                req = Request(
                    url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept-Encoding": "gzip, deflate",
                    },
                )
                with urlopen(req, timeout=TIMEOUT) as resp:
                    data = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
                        data = gzip.decompress(data)
                    ctype = resp.headers.get("Content-Type", "")
                    return data, resp.geturl(), ctype
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(0.5 * (attempt + 1))
        raise last_err

    # -- Local path resolution ------------------------------------------

    def local_path(self, url, kind):
        path = unquote(urlsplit(url).path)
        if kind == "page":
            if path in ("", "/"):
                return "index.html"
            return path.strip("/") + "/index.html"
        return path.lstrip("/")

    def save(self, url, data, kind):
        rel = self.local_path(url, kind)
        full = os.path.join(self.outdir, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(data)
        return rel

    # -- Reference extraction -------------------------------------------

    def is_asset(self, candidate):
        candidate = candidate.strip().strip('"').strip("'").strip("`")
        if not candidate or candidate.startswith(("data:", "blob:", "javascript:", "#")):
            return False
        # Skip template-literal interpolations like `${u}-part-...pdf`.
        if "${" in candidate or "}" in candidate:
            return False
        if candidate.startswith(("http://", "https://", "//")):
            return False
        if "/" not in candidate:
            return False
        candidate = candidate.split("?", 1)[0].split("#", 1)[0]
        return bool(ASSET_EXT_RE.search(candidate))

    def resolve(self, base_url, ref):
        ref = ref.strip().strip('"').strip("'").strip("`")
        # Vite preload maps reference chunks as bare "assets/..." strings.
        if ref.startswith("assets/"):
            ref = "/" + ref
        return urljoin(base_url, ref)

    def extract_assets(self, url, data, kind):
        path = urlparse(url).path.lower()
        refs = []
        if kind == "page" or path.endswith((".html", ".htm")):
            text = data.decode("utf-8", "replace")
            for m in HTML_ATTR_RE.finditer(text):
                refs.append(m.group(1))
            for m in SRCSET_RE.finditer(text):
                refs.extend(part.strip().split(" ", 1)[0] for part in m.group(1).split(","))
        elif path.endswith((".js", ".mjs", ".cjs")):
            text = data.decode("utf-8", "replace")
            for m in STRING_RE.finditer(text):
                refs.append(m.group(2))
        elif path.endswith(".css"):
            text = data.decode("utf-8", "replace")
            for m in CSS_URL_RE.finditer(text):
                refs.append(m.group(2))
        else:
            return

        for ref in refs:
            if self.is_asset(ref):
                yield self.resolve(url, ref)

    # -- Worker ----------------------------------------------------------

    def worker(self):
        while True:
            item = self.q.get()
            if item is None:
                self.q.task_done()
                return
            url, kind = item
            try:
                data, final_url, ctype = self.fetch(url)
                path = urlparse(final_url).path.lower()
                if kind == "asset" and ctype.startswith("text/html") and not path.endswith((".html", ".htm")):
                    logging.debug("skip SPA fallback for %s", final_url)
                    continue
                rel = self.save(final_url, data, kind)
                for asset_url in self.extract_assets(final_url, data, kind):
                    self.enqueue(asset_url, "asset")
                with self.lock:
                    self.count += 1
                logging.info("saved %s", rel)
            except Exception as exc:  # noqa: BLE001
                with self.lock:
                    self.errors += 1
                logging.error("failed %s: %s", url, exc)
            finally:
                self.q.task_done()

    # -- Driver ----------------------------------------------------------

    def seed(self):
        # Static files worth mirroring verbatim.
        for name in ("robots.txt", "sitemap.xml"):
            self.enqueue(self.base_url + "/" + name, "asset")

        # Home page.
        self.enqueue(self.base_url + "/", "page")

        # Every route listed in the sitemap.
        try:
            data, _, _ = self.fetch(self.base_url + "/sitemap.xml")
            text = data.decode("utf-8", "replace")
            for m in LOC_RE.finditer(text):
                loc = m.group(1).strip()
                if self.same_origin(loc):
                    self.enqueue(loc, "page")
            logging.info("sitemap yielded %d routes", len(self.seen))
        except Exception as exc:  # noqa: BLE001
            logging.warning("could not read sitemap: %s", exc)

    def run(self):
        start = time.time()
        self.seed()
        threads = []
        for _ in range(self.concurrency):
            t = threading.Thread(target=self.worker, daemon=True)
            t.start()
            threads.append(t)
        self.q.join()
        for _ in range(self.concurrency):
            self.q.put(None)
        for t in threads:
            t.join()
        logging.info(
            "done: %d files, %d errors in %.1fs -> %s",
            self.count,
            self.errors,
            time.time() - start,
            self.outdir,
        )


def main():
    setup_logging()
    while True:
        Crawler(BASE_URL, OUTPUT_DIR, CONCURRENCY).run()
        if INTERVAL <= 0:
            break
        logging.info("sleeping %ds before next crawl", INTERVAL)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
