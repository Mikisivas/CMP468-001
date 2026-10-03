"""Live demo feed for the defence. Sends signed GPS pings for moving herds and
incident reports by SMS and USSD to a running Zaman Lafiya server.

  python simulate.py --steps 40 --interval 2
"""
import argparse
import json
import os
import random
import time
import urllib.parse
import urllib.request

import core
import geodata

URL = "http://127.0.0.1:5050"


def post_form(path, data):
    body = urllib.parse.urlencode(data).encode()
    with urllib.request.urlopen(URL + path, data=body, timeout=10) as r:
        return r.read().decode()


def ping(secret, herd_id, lat, lon, heads):
    body = json.dumps({"herd_id": herd_id, "lat": round(lat, 5), "lon": round(lon, 5), "heads": heads}).encode()
    ts = str(time.time())
    req = urllib.request.Request(URL + "/api/herd_ping", data=body, headers={
        "Content-Type": "application/json", "X-Timestamp": ts,
        "X-Signature": core.device_signature(secret, ts.encode() + b"." + body)})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def interpolate(route, t):
    """Position at fraction t (0..1) along a polyline of (lat, lon)."""
    seg = min(int(t * (len(route) - 1)), len(route) - 2)
    f = t * (len(route) - 1) - seg
    (a1, o1), (a2, o2) = route[seg], route[seg + 1]
    return a1 + (a2 - a1) * f, o1 + (o2 - o1) * f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--interval", type=float, default=2.0)
    a = ap.parse_args()
    secret = os.environ.get("ZAMANLAFIYA_DEVICE_SECRET")
    if not secret:
        raise SystemExit("Set ZAMANLAFIYA_DEVICE_SECRET (same value as the server).")
    cfg = core.load_config()
    rnd = random.Random(3)
    guma_farm = next(z for z in core.zones(cfg, "farmland") if z["lga"] == "Guma")
    ring = guma_farm["geom"]["coordinates"][0]
    farm_lat = sum(p[1] for p in ring[:4]) / 4
    farm_lon = sum(p[0] for p in ring[:4]) / 4
    herds = [{"id": f"HERD-{i + 1:02d}", "t": i * 0.12, "heads": rnd.randint(60, 300)} for i in range(5)]
    herds[1]["rogue"] = True       # will walk into Guma farmland
    herds[3]["deviate"] = True     # will leave the stock route
    sms = [("ZL Guma CROP cattle destroyed yam farm near Yelwata", "08031110001"),
           ("ZL Agatu THREAT youths threaten herders at Obagaji market", "08031110002"),
           ("ZL Bokkos RUSTLE 40 cows stolen at night", "08031110003"),
           ("ZL Keana ROUTE farmers blocked access to river", "08031110004"),
           ("ZL Makurdi RUMOUR whatsapp message says attack coming", "08031110005"),
           ("ZL Guma ATTACK gunmen attacked farmers at Tse-Akaa", "08031110001")]
    for step in range(a.steps):
        for h in herds:
            h["t"] = min(1.0, h["t"] + 0.01)
            lat, lon = interpolate(geodata.STOCK_ROUTE, h["t"])
            if h.get("rogue") and step >= a.steps // 3:
                k = min(1.0, (step - a.steps // 3) / 6)
                lat, lon = lat + (farm_lat - lat) * k, lon + (farm_lon - lon) * k
            if h.get("deviate") and step >= a.steps // 2:
                lon += 0.02 * (step - a.steps // 2)
            lat += rnd.uniform(-0.004, 0.004)
            lon += rnd.uniform(-0.004, 0.004)
            ev = ping(secret, h["id"], lat, lon, h["heads"])["events"]
            if ev:
                print(f"step {step:2d} {h['id']}: {ev}")
        if step % 5 == 2 and sms:
            text, phone = sms.pop(0)
            print(f"step {step:2d} SMS from {phone[:6]}***: {text} -> {post_form('/api/sms', {'from': phone, 'text': text})}")
        if step == 8:
            sid = "demo-session"
            for t in ("", "1", "1*Riyom", "1*Riyom*1"):
                reply = post_form("/api/ussd", {"sessionId": sid, "phoneNumber": "08039990000", "text": t})
            print(f"step {step:2d} USSD final reply: {reply}")
        time.sleep(a.interval)
    print("Simulation finished.")


if __name__ == "__main__":
    main()
