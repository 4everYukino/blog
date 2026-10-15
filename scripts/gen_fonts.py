"""生成 assets/css/fonts.css，并把用到的字体文件复制到 static/fonts/。

字体取自 Fontsource 的 npm 包（需要 npm），版本见 FONTS。
用法：python3 scripts/gen_fonts.py
"""
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 中文字体只认领这些码位，拉丁字母、符号与 emoji 留给字体栈里的其它字体
CJK = [
    (0x2E80, 0x2FDF),    # 部首
    (0x2FF0, 0x2FFF),    # 汉字结构描述符
    (0x3000, 0x303F),    # 中日韩符号与标点
    (0x3040, 0x30FF),    # 平假名、片假名
    (0x3100, 0x312F),    # 注音
    (0x3190, 0x31FF),    # 汉文训读、注音扩展、笔画、片假名扩展
    (0x3200, 0x33FF),    # 带圈字符、兼容字符
    (0x3400, 0x4DBF),    # 扩展 A
    (0x4E00, 0x9FFF),    # 基本汉字
    (0xF900, 0xFAFF),    # 兼容汉字
    (0xFE10, 0xFE1F),    # 竖排标点
    (0xFE30, 0xFE4F),    # 兼容标点
    (0xFF00, 0xFFEF),    # 全角、半角字符
    (0x20000, 0x3FFFF),  # 扩展 B 及以后
]


@dataclass
class Font:
    package: str
    version: str
    css: list[str]  # 包内要用的 CSS，文件名决定可变轴与正斜体
    family: str
    slug: str  # static/fonts/ 下的目录名
    only: list[tuple[int, int]] | None = None  # 只保留这些码位


FONTS = [
    # opsz 版带光学尺寸轴：正文与大标题自动用不同字形
    Font("@fontsource-variable/source-serif-4", "5.3.0", ["opsz.css", "opsz-italic.css"],
         "Source Serif 4", "source-serif-4"),
    Font("@fontsource-variable/noto-serif-sc", "5.3.0", ["wght.css"],
         "Noto Serif SC CJK", "noto-serif-sc", only=CJK),
    Font("@fontsource-variable/cascadia-code", "5.3.0", ["wght.css", "wght-italic.css"],
         "Cascadia Code", "cascadia-code"),
]


def parse_ranges(s):
    ranges = []
    for r in s.split(","):
        a, _, b = r.strip()[2:].partition("-")
        ranges.append((int(a, 16), int(b or a, 16)))
    return ranges


def clip(ranges, allowed):
    """取交集并合并相邻区间。"""
    hits = sorted(
        (max(a, x), min(b, y))
        for a, b in ranges
        for x, y in allowed
        if max(a, x) <= min(b, y)
    )
    merged = []
    for a, b in hits:
        if merged and a <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def format_ranges(ranges):
    return ",".join(f"U+{a:x}" if a == b else f"U+{a:x}-{b:x}" for a, b in ranges)


def fetch(font, tmp):
    """npm pack 下载并解压，返回包目录。"""
    out = subprocess.run(
        ["npm", "pack", "--json", f"{font.package}@{font.version}"],
        cwd=tmp, check=True, capture_output=True, text=True,
    ).stdout
    with tarfile.open(tmp / json.loads(out)[0]["filename"]) as tar:
        tar.extractall(tmp / font.slug, filter="data")
    return tmp / font.slug / "package"


def font_faces(font, pkg):
    """改写包内的 @font-face 并复制所需字体文件，逐条返回 CSS。"""
    dst = ROOT / "static/fonts" / font.slug
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    shutil.copy2(pkg / "LICENSE", dst)

    for css in font.css:
        for body in re.findall(r"@font-face \{(.*?)\}", (pkg / css).read_text(), re.S):
            face = dict(re.findall(r"([\w-]+): ([^;]+);", body))
            if font.only:
                ranges = clip(parse_ranges(face["unicode-range"]), font.only)
                if not ranges:
                    continue
                face["unicode-range"] = format_ranges(ranges)
            file = re.search(r"url\(\./files/([^)]+)\)", face["src"]).group(1)
            shutil.copy2(pkg / "files" / file, dst)
            face["font-family"] = f"'{font.family}'"
            face["src"] = face["src"].replace("./files/", f"../fonts/{font.slug}/")
            yield "@font-face {\n" + "".join(f"  {k}: {v};\n" for k, v in face.items()) + "}\n"


def main():
    header = ["/* 由 scripts/gen_fonts.py 生成，请勿手改。字体均为 SIL Open Font License 1.1。"]
    header += [f" * {f.family}: {f.package}@{f.version}" for f in FONTS]
    blocks = ["\n".join(header) + "\n */\n"]
    with tempfile.TemporaryDirectory() as tmp:
        for font in FONTS:
            blocks += font_faces(font, fetch(font, Path(tmp)))
    (ROOT / "assets/css/fonts.css").write_text("\n".join(blocks))


if __name__ == "__main__":
    main()
