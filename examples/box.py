"""AR-15 bolt carrier group (carrier, gas key, cam pin and bolt fused into one solid).

Units: inches (1 modeling unit = 1 in).
Axes:  +X = bore axis, pointing toward the muzzle: the bolt face is at the +X end and
            the open rear of the carrier tail is at X = 0.
       +Z = up. The gas key (plate, screws, tab and nozzle tube) sits on top.
       +Y = lateral. The long oblong window passes through the carrier along Y (you
            can see through it from side to side). The +Y side also carries the
            sawtooth band and the side pocket; the cam-pin hole goes through both sides.
Booleans consume both inputs, so every cutter is created fresh and only the returned
Brep is kept. The final Brep is assigned to `result`.
"""
import usd_brep as sm

# ---- carrier ----
CARRIER_R = 0.465            # carrier outside radius (0.93 in OD)
CARRIER_LEN = 5.95
TAIL_BORE_R = 0.36           # hollow rear tail
TAIL_BORE_END = 3.40
FLATS_START = 3.30           # top key-seat flat starts here ...
FLAT_END = 5.55              # ... and ends at a front wall, leaving a full round lip
FLAT_Z = 0.32                # height of the flat (0.67 in wide); sides and bottom stay round

# ---- oblong window (through the carrier along Y) and the cam pin across its front ----
WINDOW_X = (1.35, 3.25)
WINDOW_Z = (-0.02, 0.30)
CAM_PIN_X, CAM_PIN_Z, CAM_PIN_R = 3.18, 0.14, 0.11

# ---- sawtooth band below the window (+Y side) ----
TOOTH_X0, TOOTH_COUNT, TOOTH_PITCH = 1.50, 20, 0.09
TOOTH_Z = (-0.26, -0.06)     # right triangles, square top edge, sloping down
TOOTH_Y0 = 0.385             # cutter start; keeps clear of the tail bore

# ---- gas key: screw plate, raised tab, support web, nozzle tube ----
PLATE_X = (3.45, 4.55)
PLATE_HALF_Y = 0.24
PLATE_Z = (0.30, 0.44)
SCREW_XS = (3.80, 4.20)
TAB_X = (4.45, 4.80)
TAB_HALF_Y = 0.12
TAB_Z = (0.30, 0.58)
WEB_X = (4.45, 5.25)
WEB_HALF_Y = 0.14
WEB_Z = (0.30, 0.52)
NOZZLE_R = 0.115
NOZZLE_X = (4.45, 5.45)
NOZZLE_Z = 0.57

# ---- bolt ----
BOLT_R = 0.29
BOLT_X = (4.00, 6.33)
HEAD_R = 0.3025
HEAD_X = (6.30, 6.65)
LUG_COUNT = 7
LUG_GAP_W = 0.13


def x_cylinder(x0, radius, length, y=0.0, z=0.0):
    """Cylinder along +X occupying X in [x0, x0 + length]."""
    cyl = sm.create_cylinder((0.0, 0.0, 0.0), radius, length)
    sm.rotate(cyl, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0)
    sm.translate(cyl, (x0, y, z))
    return cyl


def y_cylinder(x, y0, z, radius, length):
    """Cylinder along +Y occupying Y in [y0, y0 + length]."""
    cyl = sm.create_cylinder((0.0, 0.0, 0.0), radius, length)
    sm.rotate(cyl, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), -90.0)
    sm.translate(cyl, (x, y0, z))
    return cyl


def rounded_box(origin, lx, ly, lz, radius):
    brep = sm.create_box(origin, lx, ly, lz)
    sm.circular_fillet(brep, radius)
    return brep


# ---- carrier body: round cylinder, hollow tail, one flat key seat on top ----
result = x_cylinder(0.0, CARRIER_R, CARRIER_LEN)
result = sm.boolean_difference(
    result, sm.create_box((FLATS_START, -1.0, FLAT_Z), FLAT_END - FLATS_START, 2.0, 1.0))
result = sm.boolean_difference(
    result, x_cylinder(-0.1, TAIL_BORE_R, TAIL_BORE_END + 0.1))

# ---- oblong window through the carrier along Y, leaving the cam pin across its front ----
window = rounded_box(
    (WINDOW_X[0], -0.70, WINDOW_Z[0]),
    WINDOW_X[1] - WINDOW_X[0], 1.40, WINDOW_Z[1] - WINDOW_Z[0], 0.10)
cam_pin = y_cylinder(CAM_PIN_X, -0.80, CAM_PIN_Z, CAM_PIN_R, 1.60)
window = sm.boolean_difference(window, cam_pin)
result = sm.boolean_difference(result, window)

# ---- sawtooth band on the +Y side, below the window ----
for i in range(TOOTH_COUNT):
    x0 = TOOTH_X0 + i * TOOTH_PITCH
    tri = [
        (x0, TOOTH_Y0, TOOTH_Z[1]),
        (x0 + TOOTH_PITCH - 0.010, TOOTH_Y0, TOOTH_Z[1]),
        (x0 + TOOTH_PITCH - 0.010, TOOTH_Y0, TOOTH_Z[0]),
    ]
    edges = [sm.create_line_segment(tri[k], tri[(k + 1) % 3]) for k in range(3)]
    tooth = sm.linear_sweep(edges, (0.0, 1.0, 0.0), 0.30, cap_ends=True)
    result = sm.boolean_difference(result, tooth)

# ---- +Y side pocket with two small holes, and the small side holes ----
pocket = rounded_box((4.25, 0.36, -0.20), 1.10, 0.50, 0.46, 0.10)
result = sm.boolean_difference(result, pocket)
for z in (0.12, -0.04):
    result = sm.boolean_difference(result, y_cylinder(4.95, 0.20, z, 0.035, 0.40))
result = sm.boolean_difference(result, y_cylinder(3.55, 0.20, 0.02, 0.04, 0.40))

# ---- cam-pin access hole through both flats, under the key plate ----
result = sm.boolean_difference(result, y_cylinder(3.80, -0.60, -0.03, 0.065, 1.20))

# ---- gas key plate with two counterbored hex-socket screws ----
plate = rounded_box(
    (PLATE_X[0], -PLATE_HALF_Y, PLATE_Z[0]), PLATE_X[1] - PLATE_X[0],
    2.0 * PLATE_HALF_Y, PLATE_Z[1] - PLATE_Z[0], 0.03)
result = sm.boolean_union(result, plate)

for sx in SCREW_XS:
    result = sm.boolean_difference(
        result, sm.create_cylinder((sx, 0.0, PLATE_Z[1] - 0.06), 0.115, 0.20))
    result = sm.boolean_union(
        result, sm.create_cylinder((sx, 0.0, PLATE_Z[1] - 0.09), 0.085, 0.10))
    hex_curves = sm.create_regular_polygon((sx, 0.0, PLATE_Z[1] - 0.02), 6, 0.045)
    socket = sm.linear_sweep(hex_curves, (0.0, 0.0, 1.0), 0.10, cap_ends=True)
    result = sm.boolean_difference(result, socket)

# ---- raised tab, support web, nozzle tube ----
tab = rounded_box(
    (TAB_X[0], -TAB_HALF_Y, TAB_Z[0]), TAB_X[1] - TAB_X[0], 2.0 * TAB_HALF_Y,
    TAB_Z[1] - TAB_Z[0], 0.04)
result = sm.boolean_union(result, tab)

web = rounded_box(
    (WEB_X[0], -WEB_HALF_Y, WEB_Z[0]), WEB_X[1] - WEB_X[0], 2.0 * WEB_HALF_Y,
    WEB_Z[1] - WEB_Z[0], 0.04)
result = sm.boolean_union(result, web)

result = sm.boolean_union(
    result, x_cylinder(NOZZLE_X[0], NOZZLE_R, NOZZLE_X[1] - NOZZLE_X[0], 0.0, NOZZLE_Z))
result = sm.boolean_difference(
    result, x_cylinder(NOZZLE_X[1] - 0.60, NOZZLE_R - 0.04, 0.70, 0.0, NOZZLE_Z))

# ---- bolt: body through the carrier front, head with seven lugs ----
result = sm.boolean_union(
    result, x_cylinder(BOLT_X[0], BOLT_R, BOLT_X[1] - BOLT_X[0]))
result = sm.boolean_union(
    result, x_cylinder(HEAD_X[0], HEAD_R, HEAD_X[1] - HEAD_X[0]))

for k in range(LUG_COUNT):
    gap = sm.create_box((HEAD_X[1] - 0.22, -LUG_GAP_W / 2.0, 0.215), 0.30, LUG_GAP_W, 0.15)
    sm.rotate(gap, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 360.0 * k / LUG_COUNT)
    result = sm.boolean_difference(result, gap)

# ---- bolt face: recess and firing-pin hole ----
result = sm.boolean_difference(result, x_cylinder(HEAD_X[1] - 0.08, 0.21, 0.20))
result = sm.boolean_difference(result, x_cylinder(HEAD_X[1] - 0.45, 0.06, 0.60))

mesh = sm.tessellate(result, chord_height_tolerance=0.005)
sm.usd.export_mesh(mesh, "bcg.usda")