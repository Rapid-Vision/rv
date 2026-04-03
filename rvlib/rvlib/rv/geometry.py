import bmesh
import bpy
import math
import mathutils
import random
from itertools import combinations
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from .types import AABB, Float2, Float4, Polygon2D


def _cross_2d(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _convex_hull_2d(points: Polygon2D) -> Polygon2D:
    pts = sorted(set((float(p[0]), float(p[1])) for p in points))
    if len(pts) <= 1:
        return pts
    lower = []
    for p in pts:
        while len(lower) >= 2 and _cross_2d(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and _cross_2d(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _polygon_signed_area(points: Polygon2D) -> float:
    area = 0.0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return area * 0.5


def _normalize_polygon_2d(points: Polygon2D) -> Polygon2D:
    normalized = []
    for point in points:
        current = (float(point[0]), float(point[1]))
        if len(normalized) == 0 or current != normalized[-1]:
            normalized.append(current)
    if len(normalized) > 1 and normalized[0] == normalized[-1]:
        normalized.pop()
    return normalized


def _sample_convex_polygon(points: Polygon2D, rng: random.Random) -> Float2:
    p0 = points[0]
    tris = []
    total_area = 0.0
    for i in range(1, len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        area = abs(_cross_2d(p0, p1, p2))
        if area > 1e-12:
            tris.append((p0, p1, p2, area))
            total_area += area
    if total_area <= 0:
        raise ValueError("polygon is degenerate.")

    choice = rng.uniform(0.0, total_area)
    accum = 0.0
    selected = tris[-1]
    for tri in tris:
        accum += tri[3]
        if choice <= accum:
            selected = tri
            break

    a, b, c, _ = selected
    r1 = math.sqrt(rng.random())
    r2 = rng.random()
    ax, ay = a
    bx, by = b
    cx, cy = c
    x = (1 - r1) * ax + r1 * ((1 - r2) * bx + r2 * cx)
    y = (1 - r1) * ay + r1 * ((1 - r2) * by + r2 * cy)
    return (x, y)


def _point_in_convex_polygon(point: Float2, points) -> bool:
    sign = 0
    for i in range(len(points)):
        a = points[i]
        b = points[(i + 1) % len(points)]
        cross = _cross_2d(a, b, point)
        if abs(cross) <= 1e-10:
            continue
        current_sign = 1 if cross > 0 else -1
        if sign == 0:
            sign = current_sign
        elif sign != current_sign:
            return False
    return True


def _point_on_segment_2d(point: Float2, a: Float2, b: Float2, eps: float = 1e-10) -> bool:
    cross = _cross_2d(a, b, point)
    if abs(cross) > eps:
        return False
    min_x = min(a[0], b[0]) - eps
    max_x = max(a[0], b[0]) + eps
    min_y = min(a[1], b[1]) - eps
    max_y = max(a[1], b[1]) + eps
    return min_x <= point[0] <= max_x and min_y <= point[1] <= max_y


def _point_in_polygon(point: Float2, points: Polygon2D) -> bool:
    inside = False
    for i in range(len(points)):
        a = points[i]
        b = points[(i + 1) % len(points)]
        if _point_on_segment_2d(point, a, b):
            return True
        if (a[1] > point[1]) == (b[1] > point[1]):
            continue
        x_intersection = a[0] + (point[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        if x_intersection >= point[0] - 1e-10:
            inside = not inside
    return inside


def _distance_point_segment_2d(point, a, b) -> float:
    px, py = point
    ax, ay = a
    bx, by = b
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    denom = abx * abx + aby * aby
    if denom <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / denom))
    cx = ax + t * abx
    cy = ay + t * aby
    return math.hypot(px - cx, py - cy)


def _distance_to_polygon_edges(point: Float2, points) -> float:
    best = float("inf")
    for i in range(len(points)):
        best = min(
            best,
            _distance_point_segment_2d(point, points[i], points[(i + 1) % len(points)]),
        )
    return best


def _orientation(a: Float2, b: Float2, c: Float2, eps: float = 1e-10) -> int:
    cross = _cross_2d(a, b, c)
    if cross > eps:
        return 1
    if cross < -eps:
        return -1
    return 0


def _segments_intersect_2d(a1: Float2, a2: Float2, b1: Float2, b2: Float2) -> bool:
    o1 = _orientation(a1, a2, b1)
    o2 = _orientation(a1, a2, b2)
    o3 = _orientation(b1, b2, a1)
    o4 = _orientation(b1, b2, a2)

    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _point_on_segment_2d(b1, a1, a2):
        return True
    if o2 == 0 and _point_on_segment_2d(b2, a1, a2):
        return True
    if o3 == 0 and _point_on_segment_2d(a1, b1, b2):
        return True
    if o4 == 0 and _point_on_segment_2d(a2, b1, b2):
        return True
    return False


def _is_simple_polygon(points: Polygon2D) -> bool:
    edges = [(i, (i + 1) % len(points)) for i in range(len(points))]
    for (i1, j1), (i2, j2) in combinations(edges, 2):
        if len({i1, j1, i2, j2}) < 4:
            continue
        if _segments_intersect_2d(points[i1], points[j1], points[i2], points[j2]):
            return False
    return True


def _is_convex_polygon(points: Polygon2D) -> bool:
    direction = 0
    for i in range(len(points)):
        a = points[i]
        b = points[(i + 1) % len(points)]
        c = points[(i + 2) % len(points)]
        turn = _orientation(a, b, c)
        if turn == 0:
            continue
        if direction == 0:
            direction = turn
        elif turn != direction:
            return False
    return direction != 0


def _point_in_triangle_2d(point: Float2, a: Float2, b: Float2, c: Float2) -> bool:
    ab = _orientation(a, b, point)
    bc = _orientation(b, c, point)
    ca = _orientation(c, a, point)
    signs = [value for value in (ab, bc, ca) if value != 0]
    return len(signs) == 0 or all(value > 0 for value in signs) or all(value < 0 for value in signs)


def _triangulate_polygon(points: Polygon2D) -> list[tuple[Float2, Float2, Float2, float]]:
    remaining = list(range(len(points)))
    triangles = []

    while len(remaining) > 3:
        ear_found = False
        for idx, current in enumerate(remaining):
            prev = remaining[idx - 1]
            nxt = remaining[(idx + 1) % len(remaining)]
            a = points[prev]
            b = points[current]
            c = points[nxt]
            cross = _cross_2d(a, b, c)
            if cross <= 1e-10:
                continue
            if any(
                candidate not in {prev, current, nxt}
                and _point_in_triangle_2d(points[candidate], a, b, c)
                for candidate in remaining
            ):
                continue
            area = abs(cross) * 0.5
            if area <= 1e-12:
                continue
            triangles.append((a, b, c, area))
            del remaining[idx]
            ear_found = True
            break
        if not ear_found:
            raise ValueError("polygon is not a simple non-degenerate polygon.")

    a = points[remaining[0]]
    b = points[remaining[1]]
    c = points[remaining[2]]
    area = abs(_cross_2d(a, b, c)) * 0.5
    if area <= 1e-12:
        raise ValueError("polygon is degenerate.")
    triangles.append((a, b, c, area))
    return triangles


def _prepare_polygon_2d(points: Polygon2D) -> tuple[Polygon2D, list[tuple[Float2, Float2, Float2, float]]]:
    normalized = _normalize_polygon_2d(points)
    if len(normalized) < 3:
        raise ValueError("polygon requires at least 3 points.")
    if not _is_simple_polygon(normalized):
        raise ValueError("polygon must be simple and non-self-intersecting.")
    area = _polygon_signed_area(normalized)
    if abs(area) <= 1e-12:
        raise ValueError("polygon is degenerate.")
    if area < 0:
        normalized = list(reversed(normalized))
    return normalized, _triangulate_polygon(normalized)


def _sample_polygon(
    triangles: list[tuple[Float2, Float2, Float2, float]],
    rng: random.Random,
) -> Float2:
    total_area = sum(triangle[3] for triangle in triangles)
    if total_area <= 1e-12:
        raise ValueError("polygon is degenerate.")

    choice = rng.uniform(0.0, total_area)
    accum = 0.0
    selected = triangles[-1]
    for triangle in triangles:
        accum += triangle[3]
        if choice <= accum:
            selected = triangle
            break

    a, b, c, _ = selected
    r1 = math.sqrt(rng.random())
    r2 = rng.random()
    ax, ay = a
    bx, by = b
    cx, cy = c
    x = (1 - r1) * ax + r1 * ((1 - r2) * bx + r2 * cx)
    y = (1 - r1) * ay + r1 * ((1 - r2) * by + r2 * cy)
    return (x, y)


def _random_unit_vector(rng: random.Random) -> Vector:
    z = rng.uniform(-1.0, 1.0)
    theta = rng.uniform(0.0, 2.0 * math.pi)
    t = math.sqrt(max(0.0, 1.0 - z * z))
    return Vector((t * math.cos(theta), t * math.sin(theta), z))


def _points_centroid(points: list[Vector]) -> Vector:
    if len(points) == 0:
        return Vector((0.0, 0.0, 0.0))
    total = Vector((0.0, 0.0, 0.0))
    for p in points:
        total += p
    return total / len(points)


def _aabb_from_points(points: list[Vector]) -> AABB:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def _get_object_world_vertices(obj: bpy.types.Object) -> list[Vector]:
    if obj is None:
        return []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    if obj_eval.type != "MESH":
        return []
    mesh = obj_eval.to_mesh()
    try:
        return [obj_eval.matrix_world @ v.co for v in mesh.vertices]
    finally:
        obj_eval.to_mesh_clear()


def _get_object_world_location(obj: bpy.types.Object) -> Vector:
    if obj is None:
        return Vector((0.0, 0.0, 0.0))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    return obj_eval.matrix_world.translation.copy()


def _get_object_local_vertices(obj: bpy.types.Object) -> list[Vector]:
    if obj is None:
        return []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    if obj_eval.type != "MESH":
        return []
    mesh = obj_eval.to_mesh()
    try:
        return [Vector(v.co) for v in mesh.vertices]
    finally:
        obj_eval.to_mesh_clear()


def _convex_hull_planes(points: list[Vector]) -> list[Float4]:
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    bm.verts.ensure_lookup_table()
    if len(bm.verts) < 4:
        bm.free()
        return []

    hull = bmesh.ops.convex_hull(bm, input=list(bm.verts))
    if len(hull.get("geom", [])) == 0:
        bm.free()
        return []

    bm.normal_update()
    centroid = _points_centroid(points)
    planes = []
    for face in bm.faces:
        n = Vector(face.normal)
        p = Vector(face.verts[0].co)
        d = -n.dot(p)
        if n.dot(centroid) + d > 0:
            n = -n
            d = -d
        planes.append((n.x, n.y, n.z, d))
    bm.free()
    return planes


def _sample_rotation_quaternion(
    rng: random.Random,
    domain_dimension: int,
    rotation_mode: str,
    yaw_min: float,
    yaw_max: float,
) -> mathutils.Quaternion:
    if rotation_mode == "yaw" or domain_dimension == 2:
        yaw_deg = rng.uniform(yaw_min, yaw_max)
        return mathutils.Euler((0.0, 0.0, math.radians(yaw_deg))).to_quaternion()

    u1, u2, u3 = rng.random(), rng.random(), rng.random()
    qx = math.sqrt(1.0 - u1) * math.sin(2.0 * math.pi * u2)
    qy = math.sqrt(1.0 - u1) * math.cos(2.0 * math.pi * u2)
    qz = math.sqrt(u1) * math.sin(2.0 * math.pi * u3)
    qw = math.sqrt(u1) * math.cos(2.0 * math.pi * u3)
    return mathutils.Quaternion((qw, qx, qy, qz))


def _object_world_radius(obj: bpy.types.Object, dimension: int) -> float:
    if obj is None:
        return 0.0

    points = _get_object_world_vertices(obj)
    if len(points) == 0:
        corners = []
        for corner in getattr(obj, "bound_box", []):
            corners.append(obj.matrix_world @ Vector(corner))
        points = corners
    if len(points) == 0:
        dims = getattr(obj, "dimensions", Vector((1.0, 1.0, 1.0)))
        if dimension == 2:
            return 0.5 * math.hypot(dims.x, dims.y)
        return 0.5 * math.sqrt(dims.x * dims.x + dims.y * dims.y + dims.z * dims.z)

    center = obj.matrix_world.translation
    if dimension == 2:
        return max(math.hypot(p.x - center.x, p.y - center.y) for p in points)
    return max((p - center).length for p in points)


def _build_bvh_from_object(
    obj: bpy.types.Object,
    transform: mathutils.Matrix | None = None,
) -> BVHTree | None:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    if obj_eval.type != "MESH":
        return None
    mesh = obj_eval.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        if transform is None:
            transform = obj_eval.matrix_world.copy()
        bmesh.ops.transform(bm, matrix=transform, verts=bm.verts)
        if len(bm.faces) == 0:
            return None
        return BVHTree.FromBMesh(bm, epsilon=0.0)
    finally:
        bm.free()
        obj_eval.to_mesh_clear()


def _mesh_overlaps_any(
    source_obj: bpy.types.Object,
    location: Vector,
    rotation: mathutils.Quaternion,
    scale: float,
    others: list[bpy.types.Object],
) -> bool:
    transform = (
        mathutils.Matrix.Translation(location)
        @ rotation.to_matrix().to_4x4()
        @ mathutils.Matrix.Diagonal((scale, scale, scale, 1.0))
    )
    candidate_bvh = _build_bvh_from_object(source_obj, transform=transform)
    if candidate_bvh is None:
        return False
    for other in others:
        other_bvh = _build_bvh_from_object(other)
        if other_bvh is None:
            continue
        if len(candidate_bvh.overlap(other_bvh)) > 0:
            return True
    return False


def _mesh_object_overlaps_any(
    candidate: bpy.types.Object, others: list[bpy.types.Object]
) -> bool:
    candidate_bvh = _build_bvh_from_object(candidate)
    if candidate_bvh is None:
        return False
    for other in others:
        other_bvh = _build_bvh_from_object(other)
        if other_bvh is None:
            continue
        if len(candidate_bvh.overlap(other_bvh)) > 0:
            return True
    return False
