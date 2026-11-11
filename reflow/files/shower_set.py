"""
REFLOW SHOWER SET — a complete wall shower, designed as one system.

What stays certified (bought, installed by a licensed plumber):
  - In-wall single-lever mixer valve with 35 mm ceramic-disc cartridge (WaterMark)
  - Brass wall arm, 1/2" BSP male outlet, with a downturned end
  - 1/2" shower washer with filter screen + 9 L/min flow restrictor (WELS)
What is printed (recycled PETG): everything you see and touch —
  backplate, shroud, lever, stem adapter, hot/cold inserts, arm flange, shower head.

Printed parts never hold mains pressure: the head is downstream of the valve,
so it only sees flowing pressure, and is empty whenever the valve is closed.

All units mm. Every part is modelled in its print orientation (no supports).
MEASURE YOUR VALVE and set the INTERFACE values below before printing.
"""
import math, os
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection

SEG = 128
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")

# ---------------- INTERFACE — measure your rough-in and edit these -------------
BONNET_OD      = 44.0   # cartridge bonnet / body nut the shroud slides over
BONNET_PROJ    = 40.0   # how far the bonnet stands proud of the finished tile
STEM_PROJ      = 22.0   # how far the cartridge stem stands proud of the bonnet face
WALL_HOLE      = 46.0   # opening the backplate must cover is less than this + 2*20
STEM_TEETH     = 20     # cartridge stem spline (set 0 for a D-flat stem)
STEM_OD        = 8.0    # stem outside diameter
STEM_DFLAT     = 6.5    # only used when STEM_TEETH == 0
ARM_OD         = 21.0   # brass shower arm outside diameter (1/2" pipe ~ 21)
CORD           = 2.0    # O-ring cord used for slip-on grip (shroud + flange)
CLR            = 0.25   # print clearance

def cyl(h, r1, r2=None, seg=SEG):
    return Manifold.cylinder(h, r1, r1 if r2 is None else r2, seg)

def save(m, name):
    os.makedirs(OUT, exist_ok=True)
    mesh = m.to_mesh()
    t = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)
    t.export(os.path.join(OUT, name + ".stl"))
    return t

def oring_groove(bore_r, z, cord=CORD):
    """Internal O-ring groove with a 45-degree upper face (prints unsupported)."""
    depth = cord * 0.8
    g = cyl(cord, bore_r + depth).translate([0, 0, z])
    g = g + cyl(depth, bore_r + depth, bore_r).translate([0, 0, z + cord - 0.01])
    return g

# ----------------------------------------------------------- shared "soft disc" form
def soft_disc(r, h, ch):
    """Flat back on the bed, chamfered front edge — the family profile."""
    return cyl(h - ch, r) + cyl(ch, r, r - ch).translate([0, 0, h - ch - 0.01])

# ----------------------------------------------------------- 1. MIXER BACKPLATE
PLATE_R, PLATE_H = 45.0, 9.0
def backplate():
    p = soft_disc(PLATE_R, PLATE_H, 3.0)
    p = p - cyl(PLATE_H + 2, BONNET_OD / 2 + 1.2).translate([0, 0, -1])        # bonnet clearance
    p = p - (cyl(1.5, PLATE_R - 3) - cyl(1.5, BONNET_OD / 2 + 5)).translate([0, 0, -0.01])  # silicone well
    for z in (-34, 34):                                                         # fixing screws, vertical
        p = p - cyl(20, 2.2).translate([0, z, -1])
        p = p - cyl(2.8, 2.2, 4.6).translate([0, z, PLATE_H - 2.79])
    for x in (-35.5, 35.5):                                                     # hot / cold insert pockets
        p = p - cyl(1.61, 3.3).translate([x, 0, PLATE_H - 1.6])
    return p

def indicator(kind):
    i = cyl(1.4, 3.1) + cyl(0.5, 3.1, 2.7).translate([0, 0, 1.39])
    return i

# ----------------------------------------------------------- 2. MIXER SHROUD
SHROUD_OD = BONNET_OD + 8.0
SHROUD_L  = BONNET_PROJ - PLATE_H + 4.0 + 1.0       # sits on backplate face, 1 mm past bonnet, 4 mm front wall
def shroud():
    r_in = BONNET_OD / 2 + CLR
    s = cyl(SHROUD_L - 2, SHROUD_OD / 2).translate([0, 0, 2]) + cyl(2, SHROUD_OD / 2 - 1.6, SHROUD_OD / 2).translate([0, 0, 0])
    s = s - cyl(SHROUD_L, r_in).translate([0, 0, 4.0])                    # 4 mm front wall
    s = s - cyl(10, 11.0).translate([0, 0, -1])                            # stem swing opening (cartridge tilts)
    s = s - oring_groove(r_in, SHROUD_L - 9.0)                              # slip-on grip near open end
    return s   # front face is z=0 (print face-down)

# ----------------------------------------------------------- 3. LEVER + 4. STEM ADAPTER
HEX_AF, HEX_DEPTH = 12.0, 14.0
def hex_prism(af, h):
    r = af / 2 / math.cos(math.pi / 6)
    return Manifold.extrude(CrossSection.circle(r, 6), h)

def lever():
    hub  = cyl(24, 17.5, 16.0)
    tip  = Manifold.sphere(1, SEG).scale([8.5, 7, 5]).translate([0, 78, 19])
    crown = Manifold.sphere(1, SEG).scale([10, 10, 3.5]).translate([0, 0, 21])
    L = Manifold.batch_hull([hub, tip, crown])
    L = L - Manifold.sphere(1, SEG).scale([26, 30, 8]).translate([0, 60, -1.5])   # finger relief under paddle
    L = L - hex_prism(HEX_AF + 2 * CLR, HEX_DEPTH + 0.01).translate([0, 0, -0.01])
    L = L - cyl(20, 1.65, 1.65, 32).rotate([0, 90, 0]).translate([0, 0, 7])    # M4 grub, tapped, from the side
    return L   # wall side is z=0; paddle along +y

def stem_adapter():
    a = hex_prism(HEX_AF, HEX_DEPTH)
    if STEM_TEETH:
        n = STEM_TEETH * 4; ro = STEM_OD / 2 + 0.12; ri = ro - 0.45; pts = []
        for i in range(n):
            ang = 2 * math.pi * i / n; r = ro if i % 4 in (0, 1) else ri
            pts.append((r * math.cos(ang), r * math.sin(ang)))
        bore = Manifold.extrude(CrossSection([pts]), HEX_DEPTH - 2)
    else:
        bore = (cyl(HEX_DEPTH - 2, STEM_OD / 2 + 0.12) - Manifold.cube([20, 20, 40]).translate([STEM_DFLAT - STEM_OD / 2, -10, -5]))
    a = a - bore.translate([0, 0, -0.01])
    a = a - cyl(20, 2.2, 2.2, 32).rotate([0, 90, 0]).translate([0, 0, 7])      # grub passes through to the stem
    return a

# ----------------------------------------------------------- 5. ARM FLANGE
def arm_flange():
    f = soft_disc(31, 16, 2.5).mirror([0, 0, 1]).translate([0, 0, 16])        # front face on bed
    f = f - cyl(10, 25).translate([0, 0, 8])                                   # covers the lugged elbow
    f = f - cyl(20, ARM_OD / 2 + CLR).translate([0, 0, -1])
    f = f - oring_groove(ARM_OD / 2 + CLR, 2.5)
    return f   # front face z=0

# ----------------------------------------------------------- 6. SHOWER HEAD
BSP_PITCH = 25.4 / 14
def bsp_female(length):
    major, minor = 20.955 + 0.35, 18.631 + 0.35
    rr, e = (major + minor) / 4, (major - minor) / 4
    turns = length / BSP_PITCH
    return Manifold.extrude(CrossSection.circle(rr, SEG).translate([e, 0]), length, int(turns * 48), 360 * turns)

HEAD_R, HEAD_TOP, THREAD_L = 55.0, 76.0, 15.0
def head():
    R, FACE = HEAD_R, 3.0
    outer = soft_disc(R, 12, 2.5).mirror([0, 0, 1]).translate([0, 0, 12])
    outer = outer + cyl(40, R, 14).translate([0, 0, 11.99]) + cyl(HEAD_TOP - 51.5, 14, 13.5).translate([0, 0, 51.5])
    cav_top_r = 6.5
    cavity = cyl(5, R - 5).translate([0, 0, FACE]) + cyl((R - 5) - cav_top_r, R - 5, cav_top_r).translate([0, 0, FACE + 5 - 0.01])
    h = outer - cavity
    roof_z = lambda r: FACE + 5 + (R - 5 - r)
    for i in range(6):                                                          # pressure pillars
        a = i * math.pi / 3; x, y = 30 * math.cos(a), 30 * math.sin(a)
        h = h + (cyl(roof_z(27.6) + 1.5 - FACE + 0.5, 2.4).translate([x, y, FACE - 0.5]) ^ outer)
    seat_z = HEAD_TOP - THREAD_L - 2.6
    h = h - cyl(seat_z - 40 + 0.01, cav_top_r).translate([0, 0, 40])            # inlet bore
    h = h - cyl(2.61, 10.1).translate([0, 0, seat_z])                           # washer + screen seat
    h = h - bsp_female(THREAD_L).translate([0, 0, HEAD_TOP - THREAD_L + 0.01])
    h = h - cyl(1.6, 11.0, 11.6).translate([0, 0, HEAD_TOP - 1.59])             # lead-in
    golden, holes = math.pi * (3 - math.sqrt(5)), []
    for k in range(1, 500):
        r = 4.2 * math.sqrt(k)
        if r > R - 9: break
        x, y = r * math.cos(k * golden), r * math.sin(k * golden)
        if any(math.hypot(x - 30 * math.cos(i * math.pi / 3), y - 30 * math.sin(i * math.pi / 3)) < 4.6 for i in range(6)):
            continue
        holes.append(cyl(FACE + 2, 0.65, 0.65, 16).translate([x, y, -1]))
    h = h - Manifold.compose(holes)
    return h, len(holes)

# ----------------------------------------------------------- off-the-shelf stand-ins (render only)
def valve_proxy():
    """Certified rough-in, as seen from the room: bonnet + cartridge stem."""
    b = cyl(BONNET_PROJ, BONNET_OD / 2) + cyl(STEM_PROJ, STEM_OD / 2).translate([0, 0, BONNET_PROJ])
    return b

def arm_proxy(reach=300, drop=45, bend=38):
    r = ARM_OD / 2
    straight = cyl(reach - bend, r).rotate([-90, 0, 0])                         # along +y from wall
    tor = Manifold.revolve(CrossSection.circle(r, 48).translate([bend, 0]), 64, 90)  # quarter torus
    tor = tor.rotate([0, -90, 0]).translate([0, reach - bend, -bend])
    down = cyl(drop, r).translate([0, reach, -bend - drop])
    return straight + tor + down, (0, reach, -bend - drop)

# ----------------------------------------------------------- assembly in the room
MIX_Z, ARM_Z = 0.0, 650.0   # mixer centre and arm-outlet height (compressed for the render)
def assembly(explode=0.0):
    """Wall face is the plane y=0, room is +y, z up. Returns list of (name, manifold)."""
    to_wall = lambda m: m.rotate([-90, 0, 0])         # print +z  ->  room +y
    face_out = lambda m: m.rotate([90, 0, 0])         # print z=0 front -> faces room, part extends to wall
    e = explode
    parts = []
    parts.append(("valve", valve_proxy().rotate([-90, 0, 0]).translate([0, -0.0 - e * 0.0, MIX_Z])))
    parts.append(("backplate", to_wall(backplate()).translate([0, e * 0.6, MIX_Z])))
    for x, k in ((35.5, "hot"), (-35.5, "cold")):   # hot on the left as you face the wall
        parts.append((k, to_wall(indicator(k)).translate([x, PLATE_H - 1.6 + e * 0.9, MIX_Z])))
    sh_front = PLATE_H + SHROUD_L
    parts.append(("shroud", face_out(shroud()).translate([0, sh_front + e * 1.5, MIX_Z])))
    lev = lever()                                     # paddle +y in print -> points down when mounted
    lev_y = BONNET_PROJ + STEM_PROJ - (HEX_DEPTH - 2) - 0.5   # adapter seats on the stem, clear of the shroud
    parts.append(("adapter", to_wall(stem_adapter()).translate([0, lev_y + e * 2.3, MIX_Z])))
    parts.append(("lever", to_wall(lev).translate([0, lev_y + e * 3.0, MIX_Z])))
    arm, end = arm_proxy()
    parts.append(("arm", arm.translate([0, e * 0.0, ARM_Z])))
    parts.append(("flange", face_out(arm_flange()).translate([0, 16 + e * 0.8, ARM_Z])))
    hd, _ = head()
    top = ARM_Z + end[2] + THREAD_L - 1.0
    parts.append(("head", hd.translate([0, end[1], top - HEAD_TOP - e * 0.8])))
    return parts

PRINTED = {
    "REFLOW-SHOWER_01_backplate": backplate,
    "REFLOW-SHOWER_02_shroud": shroud,
    "REFLOW-SHOWER_03_lever": lever,
    "REFLOW-SHOWER_04_stem-adapter": stem_adapter,
    "REFLOW-SHOWER_05_insert-hot": lambda: indicator("hot"),
    "REFLOW-SHOWER_06_insert-cold": lambda: indicator("cold"),
    "REFLOW-SHOWER_07_arm-flange": arm_flange,
    "REFLOW-SHOWER_08_head": lambda: head()[0],
}

if __name__ == "__main__":
    for name, fn in PRINTED.items():
        m = fn(); t = save(m, name)
        ext = t.bounds[1] - t.bounds[0]
        print(f"{name:34s} watertight={t.is_watertight} vol={t.volume/1000:6.1f}cm3 "
              f"size={'x'.join(f'{v:.1f}' for v in ext)}mm zmin={t.bounds[0][2]:.2f}")
    print("nozzles:", head()[1])
