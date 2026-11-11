# REFLOW Shower Set — build & print notes

One complete wall shower. Everything you see and touch is printed in recycled filament; everything that holds mains water pressure stays certified metal.

## The system

| # | Part | Made how | Notes |
|---|---|---|---|
| A | In-wall single-lever mixer valve, 35 mm ceramic-disc cartridge | **Buy — WaterMark certified** | Roughed-in by a licensed plumber. Its own trim is discarded. |
| B | Brass wall arm, ½" BSP male outlet, downturned end | **Buy** | Into the existing ½" lugged wall elbow. |
| C | ½" shower washer with filter screen | **Buy** | Seats in the head, below the thread. |
| D | 9 L/min flow restrictor (½") | **Buy — WELS** | Sits in the arm outlet / washer. Keeps the set at 3-star flow. |
| 01 | Backplate Ø90 | Print | Silicone well on the back; 2 × 8g countersunk screws + plugs, 68 mm vertical centres. |
| 02 | Shroud | Print | Slides over the cartridge bonnet, gripped by a 2 mm O-ring (ID ≈ 44 mm). |
| 03 | Lever | Print | Takes the stem adapter; M4 × 6 grub screw from the side. |
| 04 | Stem adapter | Print | Matches your cartridge stem — the only part that changes between valve brands. |
| 05/06 | Hot / cold inserts | Print | Press into the backplate. Hot is on the **left** as you face the wall. |
| 07 | Arm flange Ø62 | Print | Slides over the arm, 2 mm O-ring (ID ≈ 20 mm) holds it to the wall. |
| 08 | Shower head Ø110 | Print | ½" BSP female thread; 111 × 1.3 mm nozzles. |

The printed head is downstream of the valve: it only ever sees flowing pressure, and it drains empty when the mixer is off. No printed part carries static mains pressure.

## Before you print: measure your valve
Open `shower_set.py` and set the INTERFACE block at the top:
`BONNET_OD`, `BONNET_PROJ` (bonnet proud of the tile), `STEM_PROJ`, `STEM_TEETH` / `STEM_OD` (or `STEM_DFLAT` for a D-flat stem), `ARM_OD`.
Run `python3 shower_set.py` to regenerate every STL so they all still fit each other. Print the stem adapter first as a fit test — it takes 10 minutes.

## Material & settings (0.4 mm nozzle)
Recycled **PETG** throughout. Not PLA — it softens around 55 °C and a shower is hot and wet.

| Part | Layer | Walls | Infill | Orientation |
|---|---|---|---|---|
| Backplate | 0.20 | 4 | 30 % | back down |
| Shroud | 0.16 | 5 | 40 % | front face down |
| Lever | 0.16 | 5 | 50 % gyroid | wall side down |
| Stem adapter | 0.12 | 6 | 100 % | either end |
| Inserts | 0.12 | — | 100 % | flat |
| Arm flange | 0.20 | 4 | 30 % | front face down |
| Shower head | 0.16 | 4 | 30 % | face down; 45° inner roof, no supports |

Clear any skinned nozzle with a 1.2 mm drill bit. PTFE tape on the arm thread; hand-tighten the head, no wrench.

## Installing
1. Plumber rough-in: valve A and wall elbow; tiling done.
2. Bed backplate in neutral-cure silicone, screw home, press in inserts.
3. Push the shroud over the bonnet until it meets the backplate.
4. Adapter onto the stem, lever onto the adapter, nip the grub screw.
5. Flange over the arm, arm into the elbow (PTFE), flange to the wall.
6. Washer + restrictor, then the head.

## Before you sell
Tapware and showers sold in Australia need WELS registration, and products connected to the water supply generally need WaterMark certification. The trim and head here are prototypes / personal-use until tested; the valve and arm should already carry their own certification.
