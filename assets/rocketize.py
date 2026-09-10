#!/usr/bin/env python3
"""把 Platane/snk 生成的贡献图「贪吃蛇」换成一枚火箭。

    python3 rocketize.py <input.svg> <output.svg>

原理：snk 的蛇身就是 4 个尺寸递减的圆角方块（s0 头 → s3 尾），
每个有独立的 @keyframes 控制 transform 位移。把这 4 个元素换掉、
保留它们原有的动画轨迹，蛇就变成了「火箭 + 三段尾焰」。
不用 fork 整个 snk，也不用维护它的路径算法。

🔴 只动蛇身，绝不碰格子：--c0..--c4 / --ce / --cb 这些颜色变量和
   .c 的样式、rect、keyframes 全部原样保留。脚本末尾会自证这一点。
"""
import io
import re
import sys

# 火箭本体：机身 + 头锥 + 上下尾翼 + 舷窗，朝右飞
ROCKET = (
    '<g class="s s0">'
    '<path d="M1.6,5.6 L9.4,5.6 Q13.6,5.6 15.0,8.0 Q13.6,10.4 9.4,10.4 L1.6,10.4 Z"'
    ' fill="#e6edf3" stroke="#4a5568" stroke-width="0.7"/>'
    '<path d="M4.4,5.6 L2.0,2.4 L6.0,5.6 Z" fill="#e8543f"/>'
    '<path d="M4.4,10.4 L2.0,13.6 L6.0,10.4 Z" fill="#e8543f"/>'
    '<circle cx="10.4" cy="8" r="1.5" fill="#4a5568"/>'
    '<circle cx="10.4" cy="8" r="0.8" fill="#7ec8e3"/>'
    '</g>'
)

# 尾焰：三段渐小渐淡，接在火箭屁股后面
FLAMES = {
    's1': '<ellipse class="s s1" cx="8" cy="8" rx="6.0" ry="4.3" fill="#ff8c42" opacity="0.95"/>',
    's2': '<ellipse class="s s2" cx="8" cy="8" rx="4.6" ry="3.2" fill="#ffc93c" opacity="0.85"/>',
    's3': '<ellipse class="s s3" cx="8" cy="8" rx="3.2" ry="2.2" fill="#ffe9a8" opacity="0.70"/>',
}

GRID_VARS = ["--cb", "--ce", "--c0", "--c1", "--c2", "--c3", "--c4"]


def _root_vars(svg):
    m = re.search(r':root\{([^}]*)\}', svg)
    if not m:
        return {}
    return dict(kv.split(':', 1) for kv in m.group(1).split(';') if ':' in kv)


def rocketize(svg):
    before_vars = _root_vars(svg)
    before_grid = (len(re.findall(r'<rect class="c ', svg)),
                   len(re.findall(r'@keyframes c\d+\{', svg)))

    # 蛇色变量 → 火箭配色（--cs 原本是蛇的纯色，这里只作保留兼容）
    svg = re.sub(r'--cs:[^;}]+', '--cs:#e8543f', svg, count=1)

    # 头：方块 → 火箭
    head = re.search(r'<rect class="s s0"[^>]*/>', svg)
    if not head:
        raise SystemExit("✗ 没找到蛇头（class=\"s s0\"），snk 的输出格式可能变了")
    svg = svg.replace(head.group(0), ROCKET, 1)

    # 身尾：方块 → 尾焰
    for cls, repl in FLAMES.items():
        m = re.search(r'<rect class="s %s"[^>]*/>' % cls, svg)
        if not m:
            raise SystemExit(f"✗ 没找到蛇身 {cls}")
        svg = svg.replace(m.group(0), repl, 1)

    # .s 统一 fill 去掉，让每个元素自己定色
    svg = svg.replace('.s{shape-rendering:geometricPrecision;fill:var(--cs);',
                      '.s{shape-rendering:geometricPrecision;')

    # ── 自证：格子一根汗毛都没动 ──
    after_vars = _root_vars(svg)
    for k in GRID_VARS:
        if before_vars.get(k) != after_vars.get(k):
            raise SystemExit(f"✗ 格子变量 {k} 被改动了：{before_vars.get(k)} → {after_vars.get(k)}")
    after_grid = (len(re.findall(r'<rect class="c ', svg)),
                  len(re.findall(r'@keyframes c\d+\{', svg)))
    if before_grid != after_grid:
        raise SystemExit(f"✗ 格子结构被改动了：{before_grid} → {after_grid}")
    if len(re.findall(r'@keyframes s\d\{', svg)) != 4:
        raise SystemExit("✗ 移动轨迹 keyframes 丢了，火箭会不动")

    print(f"✓ 火箭就位 — 格子 {after_grid[0]} 个 rect / {after_grid[1]} 个 keyframes 未改动")
    return svg


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    io.open(dst, "w", encoding="utf-8").write(
        rocketize(io.open(src, encoding="utf-8").read()))
    print(f"✓ {dst}")


if __name__ == "__main__":
    main()
