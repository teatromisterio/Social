"""Collect data/*.json into data/content.js (window.CONTENT), newest collection first.

Usage: python3 -I tools/build_data.py
"""
import glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

cards = []
for path in glob.glob(os.path.join(ROOT, "data", "*.json")):
    with open(path, encoding="utf-8") as f:
        card = json.load(f)
    card["items"] = [i for i in card.get("items", [])
                     if os.path.exists(os.path.join(ROOT, i["file"] + (".mp4" if i.get("type") == "video" else ".jpg")))]
    if card["items"]:
        cards.append(card)

cards.sort(key=lambda c: (c.get("date") or "", c.get("created") or ""), reverse=True)

with open(os.path.join(ROOT, "data", "content.js"), "w", encoding="utf-8") as f:
    f.write("/* Сгенерировано tools/build_data.py — не редактировать вручную */\n")
    f.write("window.CONTENT = ")
    json.dump(cards, f, ensure_ascii=False, indent=1)
    f.write(";\n")

items = [i for c in cards for i in c["items"]]
videos = sum(1 for i in items if i.get("type") == "video")
print(f"{len(cards)} collections, {len(items) - videos} images, {videos} videos")
