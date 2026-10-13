"""Download images from signed URLs, save a full-size JPG for download and a webp preview.

Usage: python3 -I tools/fetch_images.py jobs.json
jobs.json: [{"url": "...", "out": "assets/<slug>/<kind>/<lang>/<n>"}]
Writes <out>.jpg (full size, q92) and <out>.webp (long side 720) relative to repo root,
and prints a JSON list with width/height per job.
"""
import io, json, os, sys, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CA = "/root/.ccr/ca-bundle.crt"


def fetch(url):
    import ssl
    ctx = ssl.create_default_context(cafile=CA) if os.path.exists(CA) else None
    with urllib.request.urlopen(url, context=ctx, timeout=120) as r:
        return r.read()


def main(path):
    jobs = json.load(open(path))
    result = []
    for job in jobs:
        out = os.path.join(ROOT, job["out"])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            im = Image.open(io.BytesIO(fetch(job["url"])))
            im.load()
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (13, 17, 23))
                bg.paste(im, mask=im.split()[-1])
                im = bg
            else:
                im = im.convert("RGB")
            im.save(out + ".jpg", "JPEG", quality=92, optimize=True, progressive=True)
            prev = im.copy()
            prev.thumbnail((720, 720 * 2), Image.LANCZOS)
            prev.save(out + ".webp", "WEBP", quality=82, method=6)
            result.append({"out": job["out"], "w": im.width, "h": im.height, "ok": True})
        except Exception as e:  # report and continue
            result.append({"out": job["out"], "ok": False, "error": str(e)})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
