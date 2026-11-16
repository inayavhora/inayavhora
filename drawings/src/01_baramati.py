"""Study 01: AI-guided sugarcane test plot, Baramati. Reported elements only.
Source: Microsoft Source, "Chasing peak sugar: India's sugar cane farmers use AI ..."."""
import os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from wiredraw import Sheet, GREY

random.seed(7)
s = Sheet(scale=4.3, origin=(290, 236))
P = s.p
L = 64.0                          # one acre is about 64 x 64 m

# ---- the plot: rows run north-south; the near edge is cut as a section through the rows
s.wpoly([(0, 0, 0), (L, 0, 0), (L, 0, L), (0, 0, L)], w=1.3)
for x in [1.5 + 3 * i for i in range(21)]:
    s.wline((x, 0, 0.6), (x, 0, L), w=0.45, col=GREY)
for x in [1.5 + 3 * i for i in range(21)]:            # cane clumps on the cut edge, about 3 m tall
    for dx in (-0.45, 0, 0.45):
        h = 2.6 + random.random() * 0.8
        s.wline((x + dx, 0, L), (x + dx, h, L), w=0.8)
        s.wline((x + dx, h * 0.72, L), (x + dx + 0.9, h * 0.95, L), w=0.55)
        s.wline((x + dx, h * 0.6, L), (x + dx - 0.8, h * 0.85, L), w=0.55)

# weather station location on the plot -> detail A
mx, mz = 18.0, 20.0
s.wline((mx, 0, mz), (mx, 5.0, mz), w=1.4)
s.marker("A", (P(mx, 5, mz)[0] - 26, P(mx, 5, mz)[1] - 8))
s.line((P(mx, 5, mz)[0] - 16, P(mx, 5, mz)[1] - 6), P(mx, 5, mz), 0.6)

# ---- 3 stem sensor on a cane at the cut edge
sx = 1.5 + 3 * 13
a = P(sx, 1.4, L)
s.rect(a[0] - 3, a[1] - 3.5, 6, 5, 0.9)
s.keynote(3, (a[0] + 4, a[1] + 46), (a[0], a[1] + 1.5))

# ---- 4 satellite imagery
sat = (78, 72)
s.rect(sat[0] - 9, sat[1] - 7, 18, 14, 1.0)
s.rect(sat[0] - 34, sat[1] - 5, 20, 10, 0.8); s.rect(sat[0] + 14, sat[1] - 5, 20, 10, 0.8)
for tgt in (P(0, 0, 0), P(0, 0, L)):
    s.line((sat[0], sat[1] + 9), tgt, 0.5, GREY, "2 5")
s.keynote(4, (sat[0] + 52, sat[1] - 8))

# ---- 5 drone spraying
dx, dy, dz = 46.0, 16.0, 30.0
c = P(dx, dy, dz)
s.rect(c[0] - 6, c[1] - 3, 12, 6, 1.0)
for ox in (-14, 14):
    s.line((c[0] + ox * 0.45, c[1]), (c[0] + ox, c[1] - 2), 0.9)
    s.out.append(f'<ellipse cx="{c[0] + ox:.1f}" cy="{c[1] - 3:.1f}" rx="7" ry="1.8" fill="none" stroke="#1c1c1b" stroke-width="0.8"/>')
for gx, gz in ((dx - 4, dz - 4), (dx + 4, dz - 4), (dx + 4, dz + 4), (dx - 4, dz + 4)):
    s.line((c[0], c[1] + 3), P(gx, 0, gz), 0.5, GREY, "1.5 4")
s.keynote(5, (c[0] + 34, c[1] - 16))

# ---- 6 plot size
s.dim((0, 0, L), (L, 0, L), "≈ 64 m", off=(0, 0, 9))
s.dim((L, 0, 0), (L, 0, L), "≈ 64 m", off=(9, 0, 0))
s.keynote(6, (P(L, 0, 0)[0] - 22, P(L, 0, 0)[1] + 40), P(L - 8, 0, 6))

# ---- DETAIL A: weather station and soil sensors, enlarged
s.detail_frame(500, 34, 262, 300, "A", "Weather station + soil sensors")
prev = s.view(24, (626, 268))
mx, mz = 0.0, 0.0
s.wpoly([(-2.2, 0, -2.2), (2.6, 0, -2.2), (2.6, 0, 2.6), (-2.2, 0, 2.6)], w=0.5, col=GREY)
s.wline((mx, 0, mz), (mx, 4.6, mz), w=1.8)
s.wline((mx - 1.5, 4.6, mz), (mx + 1.5, 4.6, mz), w=1.1)
s.circle(P(mx - 1.5, 4.85, mz), 4, 0.9); s.circle(P(mx + 1.5, 4.85, mz), 4, 0.9)   # wind sensors
s.circle(P(mx, 4.95, mz), 3.4, 0.9)                                             # solar radiation
s.box(mx + 0.25, 3.3, mz - 0.25, mx + 0.75, 4.0, mz + 0.25, w=0.9)              # rain gauge
for i in range(5):                                                              # louvred shield
    s.box(mx - 0.8, 2.0 + i * 0.16, mz - 0.22, mx - 0.3, 2.11 + i * 0.16, mz + 0.22, w=0.7)
s.box(mx + 0.6, 0, mz + 0.6, mx + 1.4, 0.4, mz + 1.4, w=0.9)                     # soil sensor head
for dz in (0.75, 1.25):
    s.line(P(mx + 1.0, 0, mz + dz), P(mx + 1.0, -1.4, mz + dz), 0.7, GREY, "2 3")
s.keynote(1, (P(mx, 3.0, mz)[0] - 78, P(mx, 3.0, mz)[1] + 6), P(mx, 3.0, mz))
s.keynote(2, (P(mx + 1.4, 0.2, mz + 1.4)[0] + 44, P(mx + 1.4, 0.2, mz + 1.4)[1] + 8), P(mx + 1.4, 0.2, mz + 1.4))
s.view(*prev)

# ---- legend, results, flow, title
end = s.legend([
    (1, "Weather station", ["Metal mast on each farm. Wind, rain,", "solar radiation, temperature, humidity."]),
    (2, "Soil sensors", ["At the station's base. Moisture, pH,", "electrical conductivity, nitrogen, potassium."]),
    (3, "Stem sensor", ["A small device on a cane stem,", "wired to the soil beneath it."]),
    (4, "Satellite imagery", ["Crop health and stress mapped in shades", "of green: where to water, feed or spray."]),
    (5, "Drone", ["Sprays fertiliser and pesticide.", "Reported on one larger (160-acre) farm."]),
    (6, "Test plot, one acre", ["Farmed with the system beside land", "farmed the usual way."]),
], y=48)
s.notes("Reported on the test plot", [
    "Stalks 30-40% heavier at harvest",
    "About 20% more sucrose",
    "Crop cycle 12 months instead of 18",
    "Less water and fertiliser",
], y=end + 14)

s.flow([
    ["Field data", "sensors, satellite,", "drone, lab soil tests"],
    ["Azure Data Manager", "for Agriculture"],
    ["FarmVibes.ai", "water stress, pests,", "disease"],
    ["Azure OpenAI", "plain daily actions"],
    ["ADT agronomists", "check each alert"],
    ["Agripilot.ai app", "Marathi, Hindi, English"],
], y=612, x1=1170)

s.title_block(1, "AI-guided sugarcane test plots",
              "Baramati, Pune district, Maharashtra, India · Agricultural Development Trust Baramati with Microsoft",
              ["Source: Microsoft Source, “Chasing peak sugar”"], date="November 2026")

out = os.path.join(os.path.dirname(__file__), "..", "01-baramati-sugarcane.svg")
print(s.save(out))
