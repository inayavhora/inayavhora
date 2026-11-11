"""Lay the shower-set parts out on build plates and export ready-to-slice 3MF files."""
import os, numpy as np, trimesh
import shower_set as S

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plates")
os.makedirs(OUT, exist_ok=True)
BED = 220.0   # fits 220 x 220 beds and larger (Ender 3, Prusa MK4, Bambu A1/P1/X1)

def tm(m):
    mm = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=False)

def place(t, x, y):
    t = t.copy(); lo = t.bounds[0]
    t.apply_translation([x - lo[0], y - lo[1], -lo[2]])
    return t

PLATES = {
    "A_trim-body-colour": [
        ("01 Backplate", S.backplate(), 5, 5),
        ("07 Arm flange", S.arm_flange(), 105, 5),
        ("04 Stem adapter", S.stem_adapter(), 175, 10),
        ("02 Shroud", S.shroud(), 105, 75),
        ("03 Lever", S.lever(), 168, 75),
    ],
    "B_shower-head-body-colour": [
        ("08 Shower head", S.head()[0], (BED - 110) / 2, (BED - 110) / 2),
    ],
    "C_inserts-accent-colours": [
        ("05 Insert hot (print red-toned)", S.indicator("hot"), 95, 107),
        ("06 Insert cold (print blue-toned)", S.indicator("cold"), 119, 107),
    ],
}

if __name__ == "__main__":
    for plate, parts in PLATES.items():
        scene = trimesh.Scene()
        for name, m, x, y in parts:
            t = place(tm(m), x, y)
            hi = t.bounds[1]
            assert hi[0] <= BED and hi[1] <= BED, (plate, name, hi)
            scene.add_geometry(t, node_name=name, geom_name=name)
        p = os.path.join(OUT, f"REFLOW-SHOWER_plate-{plate}.3mf")
        scene.export(p)
        back = trimesh.load(p)
        print(p, "objects:", len(back.geometry), "extent:", np.round(back.bounds[1], 1))
