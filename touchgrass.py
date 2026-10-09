#!/usr/bin/env python3
"""touchgrass: make a one-page paper "field card" with a local open-weight model, then put the phone away.
Facts (sun, moon, season, home-by time) are computed offline; the words come from the model."""
import argparse, datetime as dt, html, json, math, os, re, sys, urllib.request
from string import Template

SYSTEM = ("You write one-page PAPER field cards that get people outdoors and keep phones in pockets. "
          "Rules: never identify, or call safe, any plant, fungus or animal, and never suggest touching or eating them; "
          "only prompt people to notice, compare, listen, count or sketch. Nothing may need a screen. "
          "Use ONLY the facts given; never invent times or weather. Short, concrete, playful. Reply with ONLY JSON: "
          '{"title": str, "mission": str, "look_for": [6 short prompts fitted to season, place and mood], '
          '"listen": str, "no_phone_challenge": str, "bring": [3 items], "sign_off": str}')

DEMO = {"title": "Slow Walk, Loud Eyes", "mission": "Find the oldest-looking tree nearby and sit with it for five minutes.",
        "look_for": ["Something that changed since last week", "Three different greens", "A tiny home: nest, burrow or web",
                     "Something older than you", "A pattern that repeats", "A spot you have never noticed"],
        "listen": "Stand still for one minute and count the separate sounds you can pick out.",
        "no_phone_challenge": "Take the long way back and don't check the time.",
        "bring": ["Water", "A pen", "Something to sit on"], "sign_off": "Demo card: no model was used."}

SCHEMA = {"type": "object", "required": ["title", "mission", "look_for", "listen", "no_phone_challenge", "bring", "sign_off"],
          "properties": {"title": {"type": "string"}, "mission": {"type": "string"}, "listen": {"type": "string"},
                         "look_for": {"type": "array", "items": {"type": "string"}, "minItems": 6, "maxItems": 6},
                         "no_phone_challenge": {"type": "string"}, "sign_off": {"type": "string"},
                         "bring": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3}}}

# A small model can't be trusted to obey a prompt, so safety is also checked in code.
BAD = re.compile(r"\b(eat\w*|tast\w+|lick\w*|edible|poison\w*|forag\w+|touch(?:es|ing)?(?! grass))\b", re.I)

PAGE = Template(r"""<!doctype html><html lang="en"><meta charset="utf-8"><title>$title</title>
<style>
@page{size:A5;margin:10mm}
body{margin:0 auto;max-width:130mm;padding:8mm 4mm;color:#12263a;background:#fff;font:15px/1.5 "Gill Sans","Gill Sans MT",Calibri,"Trebuchet MS",sans-serif}
header{display:flex;gap:12px}
.blaze{width:14px;min-height:56px;background:#1f5fbf;border-radius:2px;flex:none}
h1,.mission{font-family:Rockwell,Clarendon,"Roboto Slab","Bookman Old Style",Georgia,serif}
h1{margin:0;font-size:29px;line-height:1.1}
.when{margin:5px 0 0;font-size:13px}
.note{font-weight:700;margin:10px 0 0}
.mission{font-size:18px;line-height:1.4;margin:14px 0 4px}
h2{font-size:15px;color:#1f5fbf;margin:16px 0 4px}
ul{padding:0;margin:0}li{list-style:none;margin:6px 0;padding-left:24px;text-indent:-24px}
li:before{content:"\2610\00a0\00a0";color:#1f5fbf}
p{margin:3px 0}
footer{margin-top:18px;border-top:2px solid #1f5fbf;padding-top:8px;font-size:12px}
@media print{body{padding:0}}
</style>
<header><div class="blaze"></div><div><h1>$title</h1>
<p class="when">$date. Sun up $sunrise, down $sunset. Moon: $moon. Be home by <b>$home_by</b>.</p></div></header>
<p class="note">$note</p>
<p class="mission">$mission</p>
<h2>Look for</h2><ul>$looks</ul>
<h2>Listen</h2><p>$listen</p>
<h2>No-phone challenge</h2><p>$challenge</p>
<h2>Bring</h2><p>$bring</p>
<footer>$sign_off Notice and enjoy, but don't touch or eat anything you can't identify yourself.</footer>
</html>""")


def fmt(minutes):
    m = int(round(minutes)) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def sun_minutes(lat, lon, day, tz):
    """NOAA solar equations -> (sunrise, sunset) in local minutes, or None in polar day/night."""
    g = 2 * math.pi / 365 * (day.timetuple().tm_yday - 1)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
           + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    la = math.radians(lat)
    c = math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(dec)) - math.tan(la) * math.tan(dec)
    if abs(c) > 1:
        return None
    ha = math.degrees(math.acos(c))
    return 720 - 4 * (lon + ha) - eqt + tz * 60, 720 - 4 * (lon - ha) - eqt + tz * 60


def moon(day):
    age = ((dt.datetime.combine(day, dt.time(12)) - dt.datetime(2000, 1, 6, 18, 14)).total_seconds() / 86400) % 29.530588853
    names = [(1.85, "new moon"), (5.54, "waxing crescent"), (9.22, "first quarter"), (12.91, "waxing gibbous"),
             (16.61, "full moon"), (20.30, "waning gibbous"), (23.99, "last quarter"), (27.68, "waning crescent")]
    return next((n for t, n in names if age < t), "new moon")


def season(lat, month):
    if abs(lat) < 15:
        return "tropical"
    i = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2}.get(month, 3)
    return ["winter", "spring", "summer", "autumn"][(i + 2) % 4 if lat < 0 else i]


def facts(a):
    day = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    now = dt.datetime.now()
    h, m = map(int, a.start.split(":")) if a.start else (now.hour, now.minute)
    start = h * 60 + m
    tz = a.tz if a.tz is not None else now.astimezone().utcoffset().total_seconds() / 3600
    sun = sun_minutes(a.lat, a.lon, day, tz)
    home, note = start + a.minutes, ""
    if sun and sun[1] - 20 < home:  # the model never decides safety-critical times
        home = sun[1] - 20
        note = f"Daylight is short today: be home by {fmt(home)} and bring a light."
    return {"date": day.strftime("%A %d %B"), "season": season(a.lat, day.month), "moon": moon(day),
            "sunrise": fmt(sun[0]) if sun else "n/a", "sunset": fmt(sun[1]) if sun else "n/a",
            "start": fmt(start), "home_by": fmt(home)}, note


def clean(c):
    s = lambda v, n=160: str(v).strip()[:n]
    return {"title": s(c["title"], 60), "mission": s(c["mission"], 200), "look_for": [s(x) for x in c["look_for"]][:6],
            "listen": s(c["listen"]), "no_phone_challenge": s(c["no_phone_challenge"]),
            "bring": [s(x, 40) for x in c["bring"]][:4], "sign_off": s(c["sign_off"], 100)}


def ask(a, f):
    user = (f"Facts: {json.dumps(f)}\nPlace: {a.place}\nMood: {a.mood}\n"
            f"Walking with: {a.companions}\nMinutes available: {a.minutes}")
    body = {"model": a.model, "stream": False, "format": SCHEMA, "options": {"temperature": 0.7},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
    req = urllib.request.Request(a.host.rstrip("/") + "/api/chat", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        text = json.load(r)["message"]["content"]
    card = clean(json.loads(re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()))
    if len(card["look_for"]) < 4 or BAD.search(json.dumps(card)):
        raise ValueError("unusable card")
    return card


def render(c, f, note):
    e = html.escape
    return PAGE.substitute(
        title=e(c["title"]), mission=e(c["mission"]), listen=e(c["listen"]), challenge=e(c["no_phone_challenge"]),
        sign_off=e(c["sign_off"]), bring=e(", ".join(c["bring"])), note=e(note),
        looks="".join(f"<li>{e(x)}</li>" for x in c["look_for"]), **{k: e(v) for k, v in f.items()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--place", default="a nearby park, trail or street with some green")
    p.add_argument("--minutes", type=int, default=60)
    p.add_argument("--mood", default="curious")
    p.add_argument("--with", dest="companions", default="just me")
    p.add_argument("--date", help="YYYY-MM-DD, default today")
    p.add_argument("--start", help="HH:MM, default now")
    p.add_argument("--tz", type=float, help="UTC offset in hours, default this machine's")
    p.add_argument("--model", default=os.environ.get("TOUCHGRASS_MODEL", "gemma3:1b"))
    p.add_argument("--host", default=os.environ.get("TOUCHGRASS_HOST", "http://localhost:11434"))
    p.add_argument("--out", default="field-card.html")
    p.add_argument("--demo", action="store_true", help="skip the model (for testing only)")
    a = p.parse_args()
    f, note = facts(a)
    card = DEMO
    if not a.demo:
        for attempt in range(3):
            try:
                card = ask(a, f)
                break
            except (KeyError, TypeError, ValueError):
                if attempt == 2:
                    sys.exit("The model didn't return a usable card three times. Try a larger one, e.g. --model gemma3:4b.")
            except OSError as err:
                sys.exit(f"Can't get a card from {a.host} ({err}). Start Ollama and run: ollama pull {a.model}")
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(render(card, f, note))
    print(f"Wrote {a.out}. Print it (A5 or half-letter), pocket the phone, go.")


if __name__ == "__main__":
    main()
