"""Download videos from signed URLs, transcode to H.264 MP4 and make a webp poster.

Usage: python3 -I tools/fetch_videos.py jobs.json
jobs.json: [{"url": "...", "out": "assets/<slug>/<kind>/<lang>/v01"}]
Writes <out>.mp4 (H.264 + AAC, faststart, long side <= 1920) and <out>.webp (poster, width <= 720)
relative to repo root, and prints a JSON list with width/height/duration/size per job.
"""
import json, os, ssl, subprocess, sys, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CA = "/root/.ccr/ca-bundle.crt"


def download(url, dest):
    ctx = ssl.create_default_context(cafile=CA) if os.path.exists(CA) else None
    with urllib.request.urlopen(url, context=ctx, timeout=600) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
         "-of", "json", path], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    video = next(s for s in data["streams"] if s.get("codec_type") == "video")
    has_audio = any(s.get("codec_type") == "audio" for s in data["streams"])
    return video["width"], video["height"], float(data["format"]["duration"]), has_audio


def main(path):
    jobs = json.load(open(path))
    result = []
    for job in jobs:
        out = os.path.join(ROOT, job["out"])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                src = os.path.join(tmp, "src")
                download(job["url"], src)
                _, _, _, has_audio = probe(src)
                cmd = ["ffmpeg", "-y", "-v", "error", "-i", src,
                       "-vf", "scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))',format=yuv420p",
                       "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M",
                       "-profile:v", "high", "-movflags", "+faststart"]
                cmd += ["-c:a", "aac", "-b:a", "160k"] if has_audio else ["-an"]
                subprocess.run(cmd + [out + ".mp4"], check=True)
            w, h, dur, _ = probe(out + ".mp4")
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(min(0.5, dur / 2)), "-i", out + ".mp4",
                            "-frames:v", "1", "-vf", "scale='min(720,iw)':-2", "-quality", "82", out + ".webp"],
                           check=True)
            result.append({"out": job["out"], "ok": True, "w": w, "h": h, "duration": round(dur, 1),
                           "mb": round(os.path.getsize(out + ".mp4") / 1e6, 1)})
        except Exception as e:  # report and continue
            result.append({"out": job["out"], "ok": False, "error": str(e)})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
