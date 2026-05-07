"""
geodesic_measure.py
-------------------
Đo chu vi cơ thể bằng geodesic distance thay vì ellipse approximation.

Tại sao chính xác hơn ellipse:
- Ellipse chỉ dùng 4 điểm → bỏ qua chỗ lõm/lồi của body
- Geodesic dùng toàn bộ vòng vertices → đo đúng như thước dây thật

Cách hoạt động:
1. Tìm tất cả vertices tại vị trí Y cần đo (±half_window)
2. Sắp xếp vertices thành vòng khép kín theo góc (x,z)
3. Tính tổng khoảng cách giữa các vertices liền kề
"""

import numpy as np
from typing import Optional


def get_ring_perimeter(
    vertices: np.ndarray,
    faces: np.ndarray,
    y_pos: float,
    half_window: float = 0.012,
    x_threshold: Optional[float] = None,
) -> float:
    """
    Tính chu vi tại vị trí y_pos trên mesh.

    Cách hoạt động:
    1. Lấy vertices trong khoảng y_pos ± half_window
    2. Loại tay nếu x_threshold được chỉ định
    3. Sắp xếp vertices thành vòng theo góc quanh tâm (x,z)
    4. Tính tổng khoảng cách Euclidean giữa các điểm liền kề

    Tại sao sắp xếp theo góc:
    Vertices không có thứ tự → cần sắp xếp thành vòng liên tục
    trước khi tính perimeter. Dùng arctan2 để tính góc quanh tâm.

    Args:
        vertices:     numpy [N, 3] — tọa độ xyz
        faces:        numpy [M, 3] — không dùng trực tiếp nhưng giữ để tương thích
        y_pos:        vị trí Y cần đo (mét)
        half_window:  lấy vertices trong ±half_window mét
        x_threshold:  nếu không None, loại vertices có |x| > x_threshold
                      dùng để loại tay khi đo ngực

    Returns:
        Chu vi tính bằng cm, 0.0 nếu không đủ vertices
    """
    y = vertices[:, 1]

    # Lấy vertices trong cửa sổ Y
    mask = np.abs(y - y_pos) < half_window
    zone = vertices[mask]

    if len(zone) < 6:
        return 0.0

    # Loại tay nếu cần
    if x_threshold is not None:
        zone = zone[np.abs(zone[:, 0]) < x_threshold]
        if len(zone) < 6:
            return 0.0

    # Tính tâm của vòng trong mặt phẳng XZ
    cx = np.mean(zone[:, 0])
    cz = np.mean(zone[:, 2])

    # Tính góc của mỗi vertex quanh tâm
    # arctan2(z-cz, x-cx) → góc từ -π đến π
    angles = np.arctan2(zone[:, 2] - cz, zone[:, 0] - cx)

    # Sắp xếp theo góc → tạo vòng liên tục
    order  = np.argsort(angles)
    ring   = zone[order]

    # Tính perimeter = tổng khoảng cách giữa các điểm liền kề
    # Bao gồm cạnh cuối nối về điểm đầu (vòng khép kín)
    diffs  = np.diff(ring, axis=0)                    # vector giữa điểm liền kề
    dists  = np.sqrt((diffs ** 2).sum(axis=1))        # độ dài mỗi cạnh
    close  = ring[-1] - ring[0]                        # cạnh cuối → đầu
    total  = dists.sum() + np.sqrt((close ** 2).sum()) # tổng

    return float(total * 100)  # mét → cm


def measure_body_geodesic(
    vertices: np.ndarray,
    faces: np.ndarray,
) -> dict[str, float]:
    """
    Đo tất cả số đo cơ thể bằng geodesic method.

    Vị trí đo dựa trên debug thực tế với SMPL mesh:
    - Ngực:  73% chiều cao, loại tay (x_threshold=0.17)
    - Eo:    MIN trong vùng 61-66% chiều cao
    - Hông:  MAX trong vùng 45-49% chiều cao
    - Chiều cao: y.max() - y.min()

    Args:
        vertices: numpy [N, 3] — từ SMPL output
        faces:    numpy [M, 3] — từ SMPL model.faces

    Returns:
        dict với height, chest, waist, hip (đơn vị cm)
    """
    y       = vertices[:, 1]
    y_min   = y.min()
    y_max   = y.max()
    y_range = y_max - y_min

    # Chiều cao
    height = float(y_range * 100)

    # Ngực — đo tại 73% chiều cao, loại tay
    chest_candidates = []
    for pct in [0.71, 0.72, 0.73, 0.74, 0.75]:
        y_pos = y_min + pct * y_range
        val   = get_ring_perimeter(
            vertices, faces, y_pos,
            half_window=0.012,
            x_threshold=0.17,
        )
        if val > 0:
            chest_candidates.append(val)
    chest = max(chest_candidates) if chest_candidates else 0.0

    # Eo — tìm MIN trong vùng 61-66%
    waist_candidates = []
    for pct in [0.61, 0.62, 0.63, 0.64, 0.65, 0.66]:
        y_pos = y_min + pct * y_range
        val   = get_ring_perimeter(
            vertices, faces, y_pos,
            half_window=0.010,
        )
        if val > 0:
            waist_candidates.append(val)
    waist = min(waist_candidates) if waist_candidates else 0.0

    # Hông — tìm MAX trong vùng 45-49%
    hip_candidates = []
    for pct in [0.44, 0.45, 0.46, 0.47, 0.48, 0.49]:
        y_pos = y_min + pct * y_range
        val   = get_ring_perimeter(
            vertices, faces, y_pos,
            half_window=0.012,
        )
        if val > 0:
            hip_candidates.append(val)
    hip = max(hip_candidates) if hip_candidates else 0.0

    return {
        "height": height,
        "chest":  chest,
        "waist":  waist,
        "hip":    hip,
    }