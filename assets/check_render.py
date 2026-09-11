#!/usr/bin/env python3
"""在推之前，用 GitHub 自己的渲染器把 README 渲出来、截图、量布局。

    python3 assets/check_render.py            # 渲染 + 整页截图 + 量布局
    python3 assets/check_render.py --keep     # 保留 _render_check.html 便于手动看

为什么要有这个：README 的毛病肉眼在 markdown 源码里看不出来，只有渲染了才现形。
本仓已经这样抓到过三个：
  1. 右浮动 <img align="right"> 后面直接跟 markdown 表格 → 表格被整个推到图下方，中间空一大片
  2. 徽章每行写一个 → 渲染成竖排（要用一个 <p> 包起来才横排）
  3. 正文里裸写 URL → GFM 自动链接把后面的中文一起吃进链接（中文逗号不算终止符）

🔴 两条踩过的坑，别再走：
  - **ego-browser 的 screenshot 在这台机器上是坏的**（CdpRequestTimeoutError: Page.captureScreenshot）。
    一度以为是「带 CSS 动画的页面才超时」，把动画全停掉之后照样超时，那个归因是错的。
    改用 headless Chrome，一次就成。
  - 渲染页必须放在**仓根目录**，否则 ./banner.png 这类相对路径的图加载不出来，
    量出来的布局全是错的。
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
GH = "/opt/homebrew/bin/gh"
PAGE = os.path.join(REPO, "_render_check.html")
# 🔴 设小了页面会被静默截断，而「找最后有内容的行」会把截图边界
#    当成页面结尾——你以为裁到了结尾，其实裁的是中段。实撞过两次。
WINDOW_H = 20000   # 必须在仓根，相对路径的图才加载得到


def render(md_path, context, page=PAGE):
    """走 GitHub 的 /markdown API —— 和线上同一个渲染器，结果才可信。"""
    md = io.open(md_path, encoding="utf-8").read()
    r = subprocess.run([GH, "api", "--method", "POST", "/markdown", "--input", "-"],
                       input=json.dumps({"text": md, "mode": "gfm", "context": context}),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("✗ 渲染失败：" + r.stderr[:300])
    io.open(page, "w", encoding="utf-8").write(
        '<!doctype html><meta charset="utf-8">'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css@5/github-markdown-light.css">'
        '<style>body{margin:0;background:#fff}'
        '.markdown-body{box-sizing:border-box;max-width:1012px;margin:0 auto;padding:32px 16px}</style>'
        f'<article class="markdown-body">{r.stdout}</article>')
    return len(r.stdout)


def shoot(out, height, page=PAGE):
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size=1100,{height}", f"--screenshot={out}",
                    "--virtual-time-budget=4000", "file://" + page],
                   capture_output=True)
    return os.path.exists(out)


def check_assets(repo, md_path):
    """README 里引用的本地图，一张张确认真的存在 —— 缺一张首屏就是碎图。"""
    md = io.open(md_path, encoding="utf-8").read()
    refs = set(re.findall(r'src="\./([^"]+)"', md)) | set(re.findall(r'\]\(\./([^)]+)\)', md))
    missing = [r for r in sorted(refs) if not os.path.exists(os.path.join(repo, r))]
    for r in sorted(refs):
        ok = os.path.exists(os.path.join(repo, r))
        print(f"  {'✓' if ok else '✗'} {r}")
    return missing


BADGE_LINE = re.compile(r'^!\[[^\]]*\]\(https://img\.shields\.io/[^)]+\)\s*$')


def check_badges(md_path):
    """连续多行裸写 ![](shields.io) 会渲染成竖排 —— 必须包进一个 <p>。
    这个毛病在 markdown 源码里完全看不出来，只有渲染了才现形。"""
    lines = io.open(md_path, encoding="utf-8").read().split("\n")
    runs, i = [], 0
    while i < len(lines):
        if BADGE_LINE.match(lines[i]):
            j = i
            while j < len(lines) and BADGE_LINE.match(lines[j]):
                j += 1
            if j - i >= 2:
                runs.append((i + 1, j - i))
            i = j
        else:
            i += 1
    return runs


def main():
    # 用法：check_render.py [仓目录] [owner/repo]
    repo = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else REPO
    ctx = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "gmggyyds/xxoo"
    md_path = os.path.join(repo, "README.md")
    page = os.path.join(repo, "_render_check.html")   # 必须在仓根，相对路径的图才加载得到

    print(f"── {os.path.basename(repo)} ──")
    print("引用的本地图：")
    missing = check_assets(repo, md_path)
    if missing:
        print(f"  🔴 缺 {len(missing)} 张：{missing} —— 推上去就是碎图")

    runs = check_badges(md_path)
    if runs:
        for ln, cnt in runs:
            print(f"  🔴 第 {ln} 行起 {cnt} 个徽章是裸写的 → 会渲染成竖排，要包进一个 <p>")
    else:
        print("  ✓ 徽章写法")

    n = render(md_path, ctx, page)
    print(f"✓ 渲染 {n} 字节")

    out = f"/tmp/render_{os.path.basename(repo)}.png"
    if not shoot(out, WINDOW_H, page):
        raise SystemExit("✗ 截图失败")
    print(f"✓ 截图 {out}")
    print("  🔴 截完必须把图 Read 回来肉眼看 —— 尺寸对不代表视觉对")

    if "--keep" not in sys.argv:
        os.remove(page)


if __name__ == "__main__":
    main()
