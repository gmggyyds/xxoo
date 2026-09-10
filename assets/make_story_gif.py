#!/usr/bin/env python3
"""重新生成 README 里那张 story.gif（吸星大法 vs 北冥神功）。

    python3 assets/make_story_gif.py

依赖：rsvg-convert（brew install librsvg）、Pillow。
产物：仓根 story.gif（760x428，72 帧，32 色，约 0.95MB）。

🔴 中文图的两条硬规矩（踩过）：
   1. CJK 字体必须放 font-family **第一位**，否则 rsvg/cairosvg 出图汉字全是豆腐块。
   2. 禁用 → ✓ ✗ ｜ 等符号，同样变豆腐。要箭头就画 <marker>。
"""
import math
import os
import shutil
import subprocess
import glob
from PIL import Image

CJK = "'PingFang SC','Hiragino Sans GB','Microsoft YaHei','SimHei','Noto Sans CJK SC',-apple-system,sans-serif"
BG, STROKE, ARROW = "#f8f6f3", "#4a4a4a", "#5a5a5a"          # Style 6 Claude Official
BLUE, TEAL, BEIGE, GRAY, RED = "#a8c5e6", "#9dd4c7", "#f4e4c1", "#e8e6e3", "#e0a08f"
XS, W, H = [40, 220, 400, 580, 760], 140, 66
BUILD, FADE, SHAKE, MELT, TOTAL = [0, 9, 17, 25, 33], 7, 44, 64, 100
RSVG = shutil.which("rsvg-convert") or "/opt/homebrew/bin/rsvg-convert"
OUT_W = 680          # README 里按 100% 宽显示，680 足够且省一半体积
BURN, CHAR = "#c0392b", "#7b241c"          # 走火入魔：烧红 → 焦黑红


def lerp_hex(a, b, t):
    """两个 #rrggbb 之间插值，t∈[0,1]。走火入魔时把节点烧红用。"""
    t = max(0.0, min(1.0, t))
    ca = tuple(int(a[i:i+2], 16) for i in (1, 3, 5))
    cb = tuple(int(b[i:i+2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))

TOP = [("外面的东西", None, GRAY), ("吸进来", None, BLUE), ("堆在体内", "越堆越多", BEIGE),
       ("互相冲撞", "不知道听谁的", BEIGE), ("一运功就废", "入魔", RED)]
BOT = [("外面的东西", None, GRAY), ("吸进来", None, BLUE), ("逐环对照", "拿我的业务去验", TEAL),
       ("化成我的", "删 改 沿用", TEAL), ("我自己的版本", "别人没有的那部分", TEAL)]


def frame_svg(f):
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

    def track(y, title, sub, nodes, badge, shake):
        A(f'  <text x="40" y="{y-26}" class="t">{title}</text>')
        A(f'  <text x="{40+len(title)*20+14}" y="{y-26}" class="s">{sub}</text>')
        # 箭头画在框下层；发作期上轨箭头淡出 = 链路断了
        for i in range(4):
            aop = max(0.0, min(1.0, (f - BUILD[i + 1] + 3) / FADE))
            if shake and f >= SHAKE + 4:
                aop *= max(0.12, 1.0 - (f - SHAKE - 4) / 10.0)
            if aop > 0.02:
                A(f'  <line x1="{XS[i]+W}" y1="{y+H/2}" x2="{XS[i+1]-9}" y2="{y+H/2}" '
                  f'stroke="{ARROW}" stroke-width="2.2" marker-end="url(#ar)" opacity="{aop:.2f}"/>')
        for i, (lbl, sub2, c) in enumerate(nodes):
            op = max(0.0, min(1.0, (f - BUILD[i]) / FADE))
            if op <= 0:
                continue
            dx = dy = rot = 0.0
            fill = c
            if shake and f >= SHAKE and i >= 2:
                t = f - SHAKE
                ramp = min(1.0, t / 8.0)
                amp = [0, 0, 6.0, 9.0, 13.0][i] * ramp
                dx = amp * math.sin(t * 1.9 + i * 2.1)
                dy = amp * 0.45 * math.sin(t * 2.7 + i * 1.3)
                rot = [0, 0, 1.2, 1.8, 2.6][i] * ramp * math.sin(t * 1.6 + i)
            # 走火入魔：烧红 → 焦黑，抖幅失控，整排往中间塌
            if shake and f >= MELT:
                m = min(1.0, (f - MELT) / 22.0)
                fill = lerp_hex(lerp_hex(c, BURN, min(1.0, m * 1.8)), CHAR, max(0.0, m - 0.55) / 0.45)
                if i >= 2:
                    t = f - SHAKE
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
                A(f'    <text x="{cx:.1f}" y="{cy+6:.1f}" class="n" text-anchor="middle">{lbl}</text>')
            else:
                A(f'    <text x="{cx:.1f}" y="{cy-3:.1f}" class="n" text-anchor="middle">{lbl}</text>')
                A(f'    <text x="{cx:.1f}" y="{cy+17:.1f}" class="s" text-anchor="middle">{sub2}</text>')
            A('  </g>')
        bop = max(0.0, min(1.0, (f - 40) / 8))
        if bop > 0:
            A(f'  <text x="40" y="{y+H+34}" class="f" opacity="{bop:.2f}">{badge}</text>')
        # 走火入魔：红色标记跟着抖，字号越抖越大
        if shake and f >= MELT + 4:
            m = min(1.0, (f - MELT - 4) / 14.0)
            jx = 5.0 * m * math.sin((f - MELT) * 2.3)
            jy = 3.0 * m * math.sin((f - MELT) * 3.1)
            sz = 20 + 12 * m
            A(f'  <text x="{700+jx:.1f}" y="{y-22+jy:.1f}" text-anchor="middle" '
              f'font-family="{CJK}" font-size="{sz:.1f}px" font-weight="700" '
              f'fill="{BURN}" opacity="{0.55+0.45*m:.2f}">走火入魔</text>')

    track(120, "吸星大法", "吸进来，化不掉", TOP,
          "症状：平时相安无事，一到真要干活就发作。只能靠吸新的来压。", True)
    track(340, "北冥神功", "吸进来，化得掉", BOT,
          "产出：一张只有你有的图，加一份「还缺什么」清单。", False)
    A('  <line x1="40" y1="252" x2="920" y2="252" stroke="#d8d4cf" stroke-width="1.5" stroke-dasharray="6 5"/>')
    fop = max(0.0, min(1.0, (f - 50) / 8))
    if fop > 0:
        A(f'  <text x="480" y="516" class="s" text-anchor="middle" opacity="{fop:.2f}">'
          f'差别不在吸了多少，在化没化掉</text>')
    A('</svg>')
    return "\n".join(L)


def _empty_dir(d):
    """逐个删文件后 rmdir —— 本仓禁用 rm -rf / rmtree。"""
    for p in glob.glob(os.path.join(d, "*")):
        os.remove(p)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    tmp = os.path.join(here, ".frames")
    if os.path.isdir(tmp):
        _empty_dir(tmp)
    else:
        os.makedirs(tmp)

    keep = [f for f in range(TOTAL) if f >= 40 or f % 2 == 0]
    for f in keep:
        svg = os.path.join(tmp, f"f{f:03d}.svg")
        png = os.path.join(tmp, f"f{f:03d}.png")
        with open(svg, "w") as fh:
            fh.write(frame_svg(f))
        subprocess.run([RSVG, "-w", str(OUT_W), svg, "-o", png], check=True)

    frames = [Image.open(p).convert("RGB")
              for p in sorted(glob.glob(os.path.join(tmp, "f*.png")))]
    n = len(frames)
    dur = [70] * n
    for i in range(n - 18, n):       # 发作段放慢，看得清
        dur[i] = 85
    pal = [im.convert("P", palette=Image.ADAPTIVE, colors=32) for im in frames]
    out = os.path.normpath(os.path.join(here, "..", "story.gif"))
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=dur,
                loop=0, optimize=True, disposal=2)

    _empty_dir(tmp)
    os.rmdir(tmp)
    print(f"story.gif  {os.path.getsize(out)/1024/1024:.2f} MB  {n} 帧")


if __name__ == "__main__":
    main()
