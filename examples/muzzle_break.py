"""One-piece slotted muzzle brake. Built with usd_brep.

Units: inches (1 modeling unit = 1 in).
Axes:  +Z = bore axis. Flat, beveled, counterbored muzzle face at Z = LENGTH (up);
       tapered thread end at Z = 0.
       X  = long section axis (2.5 in). The two rounded ends are at +/-X and carry
            three through-slots that exit both rounded ends.
       Y  = short section axis (1.0 in). The flat faces are at +/-Y and carry two
            stacked windows that pass through both flats.
Booleans consume both inputs, so every cutter is created fresh and only the
returned Brep is kept. The final Brep is assigned to `result`.
"""
import usd_brep as sm

# ---- overall body (inches) ----
LENGTH = 2.60
END_R = 0.625            # rounded +/-X ends: radius of the section circle
FLAT_Y = 0.50            # flats at Y = +/-FLAT_Y  (section 1.25 x 1.00)
FLAT_HALF_X = 0.35       # half-width of each flat; 45-degree facets run from here
TOP_BEVEL = 0.12         # outside bevel around the muzzle face

# ---- tapered thread end: cone radius at Z = 0 and growth per inch ----
TAPER_R0 = 0.44
TAPER_SLOPE = 0.21

# ---- bore ----
BORE_R = 0.15
THREAD_BORE_R = 0.27
THREAD_BORE_DEPTH = 1.00
STEP_OUTER_R, STEP_OUTER_DEPTH = 0.30, 0.05
STEP_INNER_R, STEP_INNER_DEPTH = 0.23, 0.10

# ---- three through-slots (along X) ----
SLOT_THICK = 0.40
SLOT_HALF_Y = 0.33
SLOT_TOPS_BELOW_FACE = (0.20, 0.76, 1.32)   # slot top edge, measured down from the muzzle face
SLOT_CORNER_R = 0.13

# ---- two windows (along Y), (top edge below muzzle face, height) ----
WIN_W = 0.46
WINDOWS = ((0.22, 0.40), (0.82, 0.30))
WIN_CORNER_R = 0.09


def rounded_box(origin, lx, ly, lz, radius):
    brep = sm.create_box(origin, lx, ly, lz)
    sm.circular_fillet(brep, radius)
    return brep


# ---- section: hexagon (flats + 45-degree facets) intersected with the end circle ----
fx, fy = FLAT_HALF_X, FLAT_Y
tip = fx + fy            # facet reaches Y = 0 at X = +/-tip
hexagon = [(fx, fy), (-fx, fy), (-tip, 0.0), (-fx, -fy), (fx, -fy), (tip, 0.0)]
pts = [(x, y, 0.0) for x, y in hexagon]
profile = [
    sm.create_line_segment(pts[i], pts[(i + 1) % len(pts)])
    for i in range(len(pts))
]
prism = sm.linear_sweep(profile, (0.0, 0.0, 1.0), LENGTH, cap_ends=True)
round_ends = sm.create_cylinder((0.0, 0.0, 0.0), END_R, LENGTH)
body = sm.boolean_intersection(prism, round_ends)

# ---- outside bevel on the muzzle-face outline only ----
top_edges = [
    e for e in body.edges()
    if e.bounding_box()[0][2] > LENGTH - 1.0e-6
]
sm.fillet_edges(body, top_edges, radius=TOP_BEVEL, xsect_type=0)

# ---- conical taper toward the thread end (flats and facets run out into it) ----
taper = sm.create_cone(
    (0.0, 0.0, 0.0), TAPER_R0, TAPER_R0 + TAPER_SLOPE * LENGTH, LENGTH)
result = sm.boolean_intersection(body, taper)

# ---- three rounded slots through both X ends ----
for below in SLOT_TOPS_BELOW_FACE:
    slot = rounded_box(
        (-1.2, -SLOT_HALF_Y, LENGTH - below - SLOT_THICK),
        2.4, 2.0 * SLOT_HALF_Y, SLOT_THICK, SLOT_CORNER_R)
    result = sm.boolean_difference(result, slot)

# ---- two stacked windows through both Y flats ----
for below, height in WINDOWS:
    window = rounded_box(
        (-WIN_W / 2.0, -1.2, LENGTH - below - height),
        WIN_W, 2.4, height, WIN_CORNER_R)
    result = sm.boolean_difference(result, window)

# ---- bore, stepped muzzle counterbore, rear thread bore ----
bore = sm.create_cylinder((0.0, 0.0, -0.1), BORE_R, LENGTH + 0.2)
result = sm.boolean_difference(result, bore)

step_outer = sm.create_cylinder(
    (0.0, 0.0, LENGTH - STEP_OUTER_DEPTH), STEP_OUTER_R, 0.2)
result = sm.boolean_difference(result, step_outer)

step_inner = sm.create_cylinder(
    (0.0, 0.0, LENGTH - STEP_INNER_DEPTH), STEP_INNER_R, 0.2)
result = sm.boolean_difference(result, step_inner)

thread_bore = sm.create_cylinder(
    (0.0, 0.0, -0.1), THREAD_BORE_R, THREAD_BORE_DEPTH + 0.1)
result = sm.boolean_difference(result, thread_bore)

mesh = sm.tessellate(result, chord_height_tolerance=0.005)
sm.usd.export_mesh(mesh, "mb.usda")