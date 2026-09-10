#!/usr/bin/env python3
"""生成 README 结尾那张 outro.gif。

    python3 assets/make_outro_gif.py

情绪落点，不是流程图（开头那张已经是流程了，结尾再来一张同类会重复）：
散落的碎片从四周飞进来 → 汇聚成一个整体 → 落出一句「吸进来，得化得掉」。

依赖：rsvg-convert、Pillow。产物：仓根 outro.gif。

🔴 中文图硬规矩：CJK 字体放 font-family 第一位；禁 → ✓ ✗ 等符号（都会变豆腐块）。
"""
import math
import os
import glob
import shutil
import subprocess
from PIL import Image

CJK = "'PingFang SC','Hiragino Sans GB','Microsoft YaHei','SimHei','Noto Sans CJK SC',-apple-system,sans-serif"
BG, INK, SUB = "#f8f6f3", "#1a1a1a", "#6a6a6a"
TEAL, STROKE = "#9dd4c7", "#4a4a4a"
W, H = 760, 240
CX, CY = W / 2, 104
RSVG = shutil.which("rsvg-convert") or "/opt/homebrew/bin/rsvg-convert"

GATHER, SETTLE, TEXT, TOTAL = 0, 30, 40, 76
LINE = "吸进来，得化得掉"
SUBLINE = "装了不用，收藏不看，那是吸星大法"

# 12 块碎片：起始角度、距离、大小、色深
SHARDS = [
    (a * 30 + (i * 7 % 23), 300 + (i * 37 % 140), 13 + (i * 5 % 9), 0.35 + (i % 5) * 0.13)
    for i, a in enumerate(range(12))
]


def ease(t):
    """先快后慢，收得住。"""
    t = max(0.0, min(1.0, t))
    return 1 - pow(1 - t, 3)


def frame_svg(f):
    L = []
    A = L.append
    A(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
    A('  <defs><style>')
    A(f'    .big {{ font-family:{CJK}; font-size:30px; font-weight:700; fill:{INK}; }}')
    A(f'    .sml {{ font-family:{CJK}; font-size:14px; fill:{SUB}; }}')
    A('  </style></defs>')
    A(f'  <rect width="{W}" height="{H}" fill="{BG}"/>')

    p = ease((f - GATHER) / max(1, SETTLE - GATHER))       # 汇聚进度

    # 碎片：从四周飞向中心，边飞边缩边转
    for ang, dist, size, dep in SHARDS:
        r = dist * (1 - p)
        rad = math.radians(ang + p * 90)                   # 一边收拢一边旋进来
        x = CX + r * math.cos(rad)
        y = CY + r * 0.55 * math.sin(rad)
        sz = size * (1 - p * 0.55)
        rot = (1 - p) * 180 + p * 0
        op = min(1.0, 0.25 + p * 0.9) * (1 - max(0.0, (f - SETTLE - 8) / 14.0))
        if op <= 0.02:
            continue
        A(f'  <rect x="{x-sz/2:.1f}" y="{y-sz/2:.1f}" width="{sz:.1f}" height="{sz:.1f}" '
          f'rx="3" ry="3" fill="{TEAL}" opacity="{op*dep:.2f}" '
          f'transform="rotate({rot:.1f} {x:.1f} {y:.1f})"/>')

    # 汇聚成的那一个整体：碎片收拢后浮现
    cop = max(0.0, min(1.0, (f - SETTLE + 6) / 12.0))
    if cop > 0:
        s = 46 + 6 * math.sin(max(0, f - SETTLE) * 0.35)   # 轻微呼吸，别死板
        A(f'  <rect x="{CX-s/2:.1f}" y="{CY-s/2:.1f}" width="{s:.1f}" height="{s:.1f}" '
          f'rx="12" ry="12" fill="{TEAL}" stroke="{STROKE}" stroke-width="2.5" opacity="{cop:.2f}"/>')

    # 主文案：逐字出现
    if f >= TEXT:
        n = min(len(LINE), int((f - TEXT) / 1.7) + 1)
        A(f'  <text x="{CX}" y="188" class="big" text-anchor="middle">{LINE[:n]}</text>')

    # 副文案：整句淡入
    sop = max(0.0, min(1.0, (f - TEXT - len(LINE) * 1.7 - 3) / 9.0))
    if sop > 0:
        A(f'  <text x="{CX}" y="218" class="sml" text-anchor="middle" opacity="{sop:.2f}">{SUBLINE}</text>')

    A('</svg>')
    return "\n".join(L)


def _empty_dir(d):
    """逐个删文件 —— 本仓禁用 rm -rf / rmtree。"""
    for p in glob.glob(os.path.join(d, "*")):
        os.remove(p)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    tmp = os.path.join(here, ".outro_frames")
    if os.path.isdir(tmp):
        _empty_dir(tmp)
    else:
        os.makedirs(tmp)

    for f in range(TOTAL):
        svg = os.path.join(tmp, f"o{f:03d}.svg")
        png = os.path.join(tmp, f"o{f:03d}.png")
        with open(svg, "w") as fh:
            fh.write(frame_svg(f))
        subprocess.run([RSVG, "-w", str(W), svg, "-o", png], check=True)

    frames = [Image.open(p).convert("RGB")
              for p in sorted(glob.glob(os.path.join(tmp, "o*.png")))]

    # 🔴 第一帧是静态预览时唯一会被看到的那一帧（社交分享卡 / reduced-motion /
    #    邮件 / 任何不播放动图的地方）。原来第 0 帧只有几个淡碎片，等于一张坏图。
    #    把完成态插到最前面：静态看到的是完整信息，播放时先闪一下完整态再散开重聚，
    #    叙事上也讲得通。
    frames.insert(0, frames[-1])
    n = len(frames)
    # 🔴 循环播放时，人随机看到哪一帧都可能。完成态（文字全出来了）必须
    #    占掉大部分时长，否则截图/瞥一眼时看到的是没信息的中间帧。
    dur = [70] * n
    dur[0] = 120                       # 开场那帧完成态只闪一下，别拖
    for i in range(n - 18, n):         # 完成态整体放慢
        dur[i] = 130
    dur[-1] = 2000                     # 最后一帧长停，循环时主要看到的就是它
    pal = [im.convert("P", palette=Image.ADAPTIVE, colors=32) for im in frames]
    out = os.path.normpath(os.path.join(here, "..", "outro.gif"))
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=dur,
                loop=0, optimize=True, disposal=2)

    _empty_dir(tmp)
    os.rmdir(tmp)
    print(f"outro.gif  {os.path.getsize(out)/1024/1024:.2f} MB  {n} 帧")


if __name__ == "__main__":
    main()
