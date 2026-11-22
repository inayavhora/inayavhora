"""Study 02: Forecast text messages for Kenyan maize farmers. Reported elements only.
Sources: Meteored / YourWeather on Bill Gates's Gates Notes article (16 Nov 2026); DevelopmentAid interview with
TomorrowNow CEO Wanjeri Mbugua; UC Davis Markets, Risk & Resilience brief on KALRO agro-weather SMS."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from wiredraw import Sheet, GREY, INK

s = Sheet(scale=20.0, origin=(300, 150))
P = s.p
C = 4.0                            # forecast grid cell, 4 x 4 km (reported)
N = 3                              # cells drawn each way

# ---- the forecast grid: 4 km cells laid over the ground
s.wpoly([(0, 0, 0), (N * C, 0, 0), (N * C, 0, N * C), (0, 0, N * C)], w=1.3)
for i in range(1, N):
    s.wline((i * C, 0, 0), (i * C, 0, N * C), w=0.6, col=GREY)
    s.wline((0, 0, i * C), (N * C, 0, i * C), w=0.6, col=GREY)
# one cell picked out: every farm whose location falls in it gets that cell's forecast
c0 = C
s.wpoly([(c0, 0, c0), (c0 + C, 0, c0), (c0 + C, 0, c0 + C), (c0, 0, c0 + C)], w=1.6)
for k in range(1, 8):                                   # light hatch inside the picked cell
    t = k * C / 8
    s.wline((c0 + t, 0, c0), (c0, 0, c0 + t), w=0.4, col=GREY)
    s.wline((c0 + C, 0, c0 + t), (c0 + t, 0, c0 + C), w=0.4, col=GREY)
s.keynote(1, (P(N * C, 0, 0)[0] + 30, P(N * C, 0, 0)[1] - 30), P(N * C - 0.9, 0, 0.4))

# ---- 4 farm location (geolocation only)
fl = P(c0 + 2.3, 0, c0 + 1.6)
s.circle(fl, 3.2, 1.2)
s.circle(fl, 0.8, 0, INK, INK)
s.keynote(4, (fl[0] - 70, fl[1] - 40), (fl[0] - 3, fl[1] - 2))

# phone marker -> detail A
s.marker("A", (fl[0] + 62, fl[1] - 44))
s.line((fl[0] + 53, fl[1] - 39), (fl[0] + 3, fl[1] - 2), 0.6)

# ---- 2 ground weather station (symbol; site not reported)
gs = P(-3.5, 0, N * C - 1.0)
top = (gs[0], gs[1] - 46)
s.line(gs, top, 1.4)
s.line((top[0] - 9, top[1]), (top[0] + 9, top[1]), 1.0)
s.rect(gs[0] + 2, gs[1] - 26, 8, 7, 0.9)
s.line((gs[0] - 10, gs[1] + 2), (gs[0] + 10, gs[1] - 2), 0.6, GREY)
s.keynote(2, (gs[0] - 30, gs[1] - 30))

# ---- 3 satellite data
sat = (430, 52)
s.rect(sat[0] - 9, sat[1] - 7, 18, 14, 1.0)
s.rect(sat[0] - 34, sat[1] - 5, 20, 10, 0.8); s.rect(sat[0] + 14, sat[1] - 5, 20, 10, 0.8)
for tgt in (P(0, 0, 0), P(N * C, 0, 0)):
    s.line((sat[0], sat[1] + 9), tgt, 0.5, GREY, "2 5")
s.keynote(3, (sat[0] + 56, sat[1]))

# ---- dimensions: one cell
s.dim((0, 0, N * C), (C, 0, N * C), "4 km", off=(0, 0, 1.4))
s.dim((N * C, 0, 0), (N * C, 0, C), "4 km", off=(1.4, 0, 0))

# ---- DETAIL A: the text message on the farmer's phone (handset type not reported)
s.detail_frame(540, 300, 222, 250, "A", "Text message to the farmer")
px, py, pw, ph = 620, 336, 92, 196
s.rect(px, py, pw, ph, 1.2, rx=12)
s.rect(px + 9, py + 22, pw - 18, 92, 0.8, rx=3)
for i, t in enumerate(["SMS · KALRO", "", "Sow this week.", "", "(sent in the", " farmer's language)"]):
    s.text(px + 15, py + 38 + i * 12.5, t, 8.6, INK if i in (0, 2) else GREY)
for r in range(4):                                       # keypad outline only
    for cidx in range(3):
        s.rect(px + 15 + cidx * 22, py + 124 + r * 15, 18, 10, 0.6, rx=2)
s.keynote(5, (px - 40, py + 66), (px, py + 66))

# ---- legend, results, flow, title
end = s.legend([
    (1, "Forecast grid cell, 4 x 4 km", ["Hyper-local forecast for each cell, made", "with satellite data. Earlier grid: 9 x 9 km."]),
    (2, "Ground weather stations (TAHMO)", ["About 800 automatic stations in Africa; Gates", "funds 100 more. Kenyan sites not reported."]),
    (3, "Satellite data", ["Checked against the ground stations."]),
    (4, "Farm location", ["Geolocation from existing databases,", "no names or ID details. Crop: maize and others."]),
    (5, "Mobile phone, SMS", ["Weekly advice by crop stage and place.", "Survey: 2-4 a month, preferred language."]),
], y=48)
s.notes("Reported results", [
    "About 5.3 million Kenyan farmers reached by SMS",
    "Study, ~10,000 farmers: +12% food produced",
    "One Acre Fund pilot, 5,022 farmers: +6.4%",
    "  (+11% leaving out drought or flood years)",
    "About 56 US cents per farmer enrolled",
], y=end + 10)

s.flow([
    ["Observations", "satellite data,", "TAHMO ground stations"],
    ["TomorrowNow", "hyper-local forecast", "on a 4 km grid"],
    ["Decision tools", "planting window,", "crop stage"],
    ["KALRO", "sends the SMS", "by farm location"],
    ["Farmer's phone", "short text in the", "local language"],
    ["KALRO call centre", "farmers report back;", "not fed into the model"],
], y=612, x1=1170)

s.title_block(2, "Forecast text messages for maize farmers",
              "Kenya (Rift Valley maize belt named in coverage) · TomorrowNow with KALRO, TAHMO and One Acre Fund",
              ["Sources: Meteored on Gates Notes, “How AI is helping Kenyan farmers”;",
               "DevelopmentAid interview with TomorrowNow; UC Davis MRR brief"], date="November 2026")

out = os.path.join(os.path.dirname(__file__), "..", "02-kenya-forecast-sms.svg")
print(s.save(out))
