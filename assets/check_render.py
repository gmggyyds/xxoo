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
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
GH = "/opt/homebrew/bin/gh"
PAGE = os.path.join(REPO, "_render_check.html")   # 必须在仓根，相对路径的图才加载得到


def render(md_path, context):
    """走 GitHub 的 /markdown API —— 和线上同一个渲染器，结果才可信。"""
    md = io.open(md_path, encoding="utf-8").read()
    r = subprocess.run([GH, "api", "--method", "POST", "/markdown", "--input", "-"],
                       input=json.dumps({"text": md, "mode": "gfm", "context": context}),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("✗ 渲染失败：" + r.stderr[:300])
    io.open(PAGE, "w", encoding="utf-8").write(
        '<!doctype html><meta charset="utf-8">'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css@5/github-markdown-light.css">'
        '<style>body{margin:0;background:#fff}'
        '.markdown-body{box-sizing:border-box;max-width:1012px;margin:0 auto;padding:32px 16px}</style>'
        f'<article class="markdown-body">{r.stdout}</article>')
    return len(r.stdout)


def shoot(out, height):
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size=1100,{height}", f"--screenshot={out}",
                    "--virtual-time-budget=4000", "file://" + PAGE],
                   capture_output=True)
    return os.path.exists(out)


def main():
    n = render(os.path.join(REPO, "README.md"), "gmggyyds/xxoo")
    print(f"✓ 渲染 {n} 字节 → {PAGE}")

    out = "/tmp/readme_render.png"
    if not shoot(out, 8000):
        raise SystemExit("✗ 截图失败")
    print(f"✓ 截图 {out}")
    print("  🔴 截完必须把图 Read 回来肉眼看 —— 尺寸对不代表视觉对")

    if "--keep" not in sys.argv:
        os.remove(PAGE)
        print("✓ 已清理 _render_check.html")


if __name__ == "__main__":
    main()
