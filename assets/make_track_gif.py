#!/usr/bin/env python3
"""通用双轨对比动图生成器 —— 每个仓的核心矛盾都能用这个结构讲清楚。

    python3 assets/make_track_gif.py <配置.json> <输出.gif>

结构固定：上轨是「没有它的样子」（一路走到坏结局，然后发作、散架），
下轨是「有它的样子」（一路走到好结局，纹丝不动）。
xxoo 的 story.gif（吸星大法 vs 北冥神功）就是这个模子刻出来的。

配置长这样：
{
  "top":    {"title": "吸星大法", "sub": "吸进来，化不掉", "badge": "症状：…",
             "nodes": [["外面的东西", null], ["吸进来", null], ["堆在体内", "越堆越多"], …],
             "meltdown": true},
  "bottom": {"title": "北冥神功", "sub": "吸进来，化得掉", "badge": "产出：…",
             "nodes": [...]},
  "footer": "差别不在吸了多少，在化没化掉",
  "melt_label": "走火入魔"
}

🔴 中文图硬规矩：CJK 字体放 font-family 第一位；禁 → ✓ ✗ 等符号（都会变豆腐块）。
🔴 第一帧是静态预览时唯一会被看到的那一帧（社交卡 / reduced-motion / 邮件）——
   所以把「两轨都画完、还没发作」那一帧插到最前面，绝不能让它是空白。
"""
import glob
import json
import math
import os
import shutil
import subprocess
import sys
from PIL import Image

CJK = "'PingFang SC','Hiragino Sans GB','Microsoft YaHei','SimHei','Noto Sans CJK SC',-apple-system,sans-serif"
BG, STROKE, ARROW = "#f8f6f3", "#4a4a4a", "#5a5a5a"
GRAY, BLUE, TEAL, BEIGE, RED = "#e8e6e3", "#a8c5e6", "#9dd4c7", "#f4e4c1", "#e0a08f"
BURN, CHAR = "#c0392b", "#7b241c"
XS, W, H = [40, 220, 400, 580, 760], 140, 66
BUILD, FADE, SHAKE, MELT, TOTAL = [0, 9, 17, 25, 33], 7, 44, 64, 100
OUT_W = 680
RSVG = shutil.which("rsvg-convert") or "/opt/homebrew/bin/rsvg-convert"

# 上轨走向坏结局：中性 → 进来 → 开始堆积 → 更糟 → 完蛋
TOP_COLORS = [GRAY, BLUE, BEIGE, BEIGE, RED]
# 下轨走向好结局
BOT_COLORS = [GRAY, BLUE, TEAL, TEAL, TEAL]


def lerp_hex(a, b, t):
    t = max(0.0, min(1.0, t))
    ca = tuple(int(a[i:i + 2], 16) for i in (1, 3, 5))
    cb = tuple(int(b[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def frame_svg(f, cfg):
    L = []
    A = L.append
    A('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540">')
    A(f'  <defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
      f'<polygon points="0 0, 8 4, 0 8" fill="{ARROW}"/></marker>')
    A('    <style>')
    A(f'      .n {{ font-family:{CJK}; font-size:15px; font-weight:600; fill:#1a1a1a; }}')
    A(f'      .t {{ font-family:{CJK}; font-size:19px; font-weight:700; fill:#1a1a1a; }}')
    A(f'      .s {{ font-family:{CJK}; font-size:13px; fill:#6a6a6a; }}')
    A(f'      .f {{ font-family:{CJK}; font-size:14px; font-weight:600; fill:#5a5a5a; }}')
    A('    </style></defs>')
    A(f'  <rect width="960" height="540" fill="{BG}"/>')

    def track(y, spec, colors, shake):
        title, sub = esc(spec["title"]), esc(spec.get("sub", ""))
        A(f'  <text x="40" y="{y-26}" class="t">{title}</text>')
        A(f'  <text x="{40+len(spec["title"])*20+14}" y="{y-26}" class="s">{sub}</text>')
        # 箭头在框下层；发作期上轨箭头淡出＝链路断了
        for i in range(4):
            aop = max(0.0, min(1.0, (f - BUILD[i + 1] + 3) / FADE))
            if shake and f >= SHAKE + 4:
                aop *= max(0.12, 1.0 - (f - SHAKE - 4) / 10.0)
            if aop > 0.02:
                A(f'  <line x1="{XS[i]+W}" y1="{y+H/2}" x2="{XS[i+1]-9}" y2="{y+H/2}" '
                  f'stroke="{ARROW}" stroke-width="2.2" marker-end="url(#ar)" opacity="{aop:.2f}"/>')
        for i, node in enumerate(spec["nodes"][:5]):
            lbl, sub2 = (node + [None])[:2] if isinstance(node, list) else (node, None)
            op = max(0.0, min(1.0, (f - BUILD[i]) / FADE))
            if op <= 0:
                continue
            dx = dy = rot = 0.0
            fill = colors[i]
            if shake and f >= SHAKE and i >= 2:
                t = f - SHAKE
                ramp = min(1.0, t / 8.0)
                amp = [0, 0, 6.0, 9.0, 13.0][i] * ramp
                dx = amp * math.sin(t * 1.9 + i * 2.1)
                dy = amp * 0.45 * math.sin(t * 2.7 + i * 1.3)
                rot = [0, 0, 1.2, 1.8, 2.6][i] * ramp * math.sin(t * 1.6 + i)
            if shake and f >= MELT:
                m = min(1.0, (f - MELT) / 22.0)
                fill = lerp_hex(lerp_hex(colors[i], BURN, min(1.0, m * 1.8)), CHAR,
                                max(0.0, m - 0.55) / 0.45)
                if i >= 2:
                    boost = 1.0 + m * 3.2
                    dx *= boost
                    dy *= boost
                    rot *= 1.0 + m * 4.0
                    dx += (XS[2] + 150 - XS[i]) * m * 0.30      # 往中间挤，撞成一团
                    op *= 1.0 - m * 0.25
            x, yy = XS[i] + dx, y + dy
            cx, cy = x + W / 2, yy + H / 2
            A(f'  <g opacity="{op:.2f}" transform="rotate({rot:.2f} {cx:.1f} {cy:.1f})">')
            A(f'    <rect x="{x:.1f}" y="{yy:.1f}" width="{W}" height="{H}" rx="12" ry="12" '
              f'fill="{fill}" stroke="{STROKE}" stroke-width="2.5"/>')
            if sub2 is None:
                A(f'    <text x="{cx:.1f}" y="{cy+6:.1f}" class="n" text-anchor="middle">{esc(lbl)}</text>')
            else:
                A(f'    <text x="{cx:.1f}" y="{cy-3:.1f}" class="n" text-anchor="middle">{esc(lbl)}</text>')
                A(f'    <text x="{cx:.1f}" y="{cy+17:.1f}" class="s" text-anchor="middle">{esc(sub2)}</text>')
            A('  </g>')
        bop = max(0.0, min(1.0, (f - 40) / 8))
        if bop > 0:
            A(f'  <text x="40" y="{y+H+34}" class="f" opacity="{bop:.2f}">{esc(spec.get("badge",""))}</text>')
        if shake and f >= MELT + 4 and cfg.get("melt_label"):
            m = min(1.0, (f - MELT - 4) / 14.0)
            jx = 5.0 * m * math.sin((f - MELT) * 2.3)
            jy = 3.0 * m * math.sin((f - MELT) * 3.1)
            A(f'  <text x="{700+jx:.1f}" y="{y-22+jy:.1f}" text-anchor="middle" '
              f'font-family="{CJK}" font-size="{20+12*m:.1f}px" font-weight="700" '
              f'fill="{BURN}" opacity="{0.55+0.45*m:.2f}">{esc(cfg["melt_label"])}</text>')

    track(120, cfg["top"], TOP_COLORS, cfg["top"].get("meltdown", True))
    track(340, cfg["bottom"], BOT_COLORS, False)
    A('  <line x1="40" y1="252" x2="920" y2="252" stroke="#d8d4cf" stroke-width="1.5" stroke-dasharray="6 5"/>')
    fop = max(0.0, min(1.0, (f - 50) / 8))
    if fop > 0 and cfg.get("footer"):
        A(f'  <text x="480" y="516" class="s" text-anchor="middle" opacity="{fop:.2f}">{esc(cfg["footer"])}</text>')
    A('</svg>')
    return "\n".join(L)


def _empty_dir(d):
    """逐个删 —— 本仓禁用 rm -rf / rmtree。"""
    for p in glob.glob(os.path.join(d, "*")):
        os.remove(p)


def build(cfg, out_path):
    tmp = os.path.join(os.path.dirname(os.path.abspath(out_path)), ".track_frames")
    if os.path.isdir(tmp):
        _empty_dir(tmp)
    else:
        os.makedirs(tmp)

    keep = [f for f in range(TOTAL) if f >= 40 or f % 2 == 0]
    for f in keep:
        svg = os.path.join(tmp, f"f{f:03d}.svg")
        png = os.path.join(tmp, f"f{f:03d}.png")
        with open(svg, "w") as fh:
            fh.write(frame_svg(f, cfg))
        subprocess.run([RSVG, "-w", str(OUT_W), svg, "-o", png], check=True)

    frames = [Image.open(p).convert("RGB")
              for p in sorted(glob.glob(os.path.join(tmp, "f*.png")))]
    # 第一帧＝两轨都画完、还没发作（静态预览时信息量最大的那一帧）
    idx = next((i for i, f in enumerate(keep) if f >= SHAKE - 1), len(keep) - 1)
    frames.insert(0, frames[idx])
    n = len(frames)
    dur = [70] * n
    dur[0] = 120
    for i in range(n - 18, n):
        dur[i] = 85
    pal = [im.convert("P", palette=Image.ADAPTIVE, colors=32) for im in frames]
    pal[0].save(out_path, save_all=True, append_images=pal[1:], duration=dur,
                loop=0, optimize=True, disposal=2)

    _empty_dir(tmp)
    os.rmdir(tmp)
    return n, os.path.getsize(out_path)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    n, size = build(cfg, sys.argv[2])
    print(f"{os.path.basename(sys.argv[2])}  {size/1024/1024:.2f} MB  {n} 帧")


if __name__ == "__main__":
    main()
