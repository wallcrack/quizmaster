"""
生成示例用的占位图片（最小化有效 PNG）。
无需任何第三方库，纯 Python 标准库实现。
"""
import struct
import zlib
from pathlib import Path


def create_png(filepath: str, width: int = 400, height: int = 200,
               r: int = 70, g: int = 130, b: int = 180, label: str = ""):
    """创建一个简单的纯色 + 文字标签的 PNG 图片。"""

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        """构建 PNG chunk"""
        chunk_data = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(chunk_data) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + chunk_data + crc

    # PNG signature
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)

    # IDAT chunk — create raw image data
    raw_data = b""
    for y in range(height):
        raw_data += b"\x00"  # filter: none
        for x in range(width):
            # Simple gradient with label area
            if label and 30 < y < 170 and 50 < x < width - 50:
                # Light area for text visibility
                raw_data += bytes([min(r + 80, 255), min(g + 80, 255), min(b + 80, 255)])
            else:
                # Gradient color
                factor = y / max(height - 1, 1)
                raw_data += bytes([
                    int(r + (255 - r) * factor * 0.3),
                    int(g + (100 - g) * factor * 0.3),
                    int(b + (b // 2) * factor * 0.3),
                ])

    compressed = zlib.compress(raw_data)
    idat = chunk(b"IDAT", compressed)

    # IEND chunk
    iend = chunk(b"IEND", b"")

    with open(filepath, "wb") as f:
        f.write(signature + ihdr + idat + iend)


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent

    images = [
        ("python_logo.png", "Python Logo"),
        ("network_topology.png", "Network Topology"),
        ("tcp_handshake.png", "TCP 3-Way Handshake"),
        ("git_workflow.png", "Git Workflow"),
        ("microservices_vs_monolith.png", "Microservices vs Monolith"),
        ("cpu_architecture.png", "CPU Architecture"),
        ("https_flow.png", "HTTPS Flow"),
    ]

    for filename, label in images:
        filepath = output_dir / filename
        # Use different colors for different images
        colors = {
            "python_logo.png": (55, 118, 179),
            "network_topology.png": (46, 134, 87),
            "tcp_handshake.png": (192, 57, 43),
            "git_workflow.png": (240, 81, 51),
            "microservices_vs_monolith.png": (142, 68, 173),
            "cpu_architecture.png": (41, 128, 185),
            "https_flow.png": (39, 174, 96),
        }
        color = colors.get(filename, (100, 100, 100))
        create_png(str(filepath), width=500, height=260,
                   r=color[0], g=color[1], b=color[2], label=label)
        print(f"  Created: {filename}")

    print(f"\nDone! {len(images)} placeholder images generated.")
