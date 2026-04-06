#!/usr/bin/env python3
"""Generate a cinematic MediSlim demo video for the homepage."""

from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static" / "media" / "demo"
OUTPUT_DIR = ROOT / "output" / "video_demo"
TMP_DIR = OUTPUT_DIR / "tmp"

WIDTH = 1280
HEIGHT = 720
FPS = 24

BG = (247, 239, 228)
TEXT = (26, 56, 49)
MUTED = (93, 116, 109)
BRAND = (16, 143, 111)
BRAND_DARK = (13, 94, 75)
ACCENT = (245, 123, 66)
WHITE = (255, 255, 255)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


@dataclass
class Scene:
    title: str
    body: str
    narration: str
    key: str
    duration: float = 0.0


SCENES: List[Scene] = [
    Scene(
        title="她不是想变得更狠，她只是想把生活重新过顺。",
        body="体重、睡眠和皮肤状态一起失控，连照镜子和出门都开始变得费劲。",
        narration="她不是想变得更狠，她只是想把生活重新过顺。体重、睡眠和皮肤状态一起失控，连照镜子和出门都开始变得费劲。",
        key="emotion",
    ),
    Scene(
        title="先问身体状态，再判断适合哪条路。",
        body="MediSlim 先做 AI 评估和九种体质辨识，再决定先减重、助眠、皮肤还是男性健康。",
        narration="MediSlim 先做 AI 评估和九种体质辨识，再判断该进入哪一条方案。",
        key="assessment",
    ),
    Scene(
        title="不是一刀切，而是进入对应产品方案。",
        body="评估后直接进入适合的方案入口，价格、履约方式和后续复购节奏都一并看清。",
        narration="如果适合，就进入对应的减重、助眠或皮肤管理产品方案。",
        key="products",
    ),
    Scene(
        title="前台轻，医院和药房把后面的事接住。",
        body="医生审核、药房履约和配送链路一起接上，产品方和订阅提醒持续跟进。",
        narration="后续由合作医院完成审核，合作药房完成履约和配送。",
        key="fulfillment",
    ),
    Scene(
        title="不是更激进，而是终于回到自己的节奏。",
        body="体重更稳，睡得更沉，状态更轻一点，用户愿意把这套服务继续留在生活里。",
        narration="最后留下来的，不只是一次订单，而是更稳的身体状态和复购关系。",
        key="outcome",
    ),
]

PRODUCT_ASSETS = [
    ("glp1", "GLP-1 科学减重", 399),
    ("sleep", "助眠调理", 199),
    ("skin", "皮肤管理", 299),
]

PARTNER_ASSETS = [
    ("jd-health", "京东健康"),
    ("wedoctor", "微医"),
    ("dashenlin", "大参林"),
    ("yifeng", "益丰"),
]


def ensure_dirs() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def load_font(size: int, serif: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 0) if serif else ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
        ("/System/Library/Fonts/Supplemental/Times New Roman.ttf", None),
    ]
    for path, index in candidates:
        if Path(path).exists():
            try:
                if index is None:
                    return ImageFont.truetype(path, size=size)
                return ImageFont.truetype(path, size=size, index=index)
            except Exception:
                continue
    return ImageFont.load_default()


FONT_BODY = load_font(28)
FONT_SMALL = load_font(20)
FONT_TINY = load_font(16)
FONT_LABEL = load_font(18)
FONT_HEAD = load_font(62, serif=True)
FONT_SCENE = load_font(24)
FONT_METRIC = load_font(40)


def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    words = list(text)
    lines: List[str] = []
    current = ""
    for ch in words:
        trial = current + ch
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return "\n".join(lines)


def draw_gradient(base: Image.Image, top: Tuple[int, int, int], bottom: Tuple[int, int, int]) -> None:
    arr = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    top_np = np.array(top, dtype=np.float32)
    bottom_np = np.array(bottom, dtype=np.float32)
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        arr[y, :, :] = (top_np * (1 - t) + bottom_np * t).astype(np.uint8)
    overlay = Image.fromarray(arr)
    base.paste(overlay)


def apply_texture(base: Image.Image) -> None:
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    draw.ellipse((80, -40, 560, 440), fill=(15, 143, 111, 38))
    draw.ellipse((WIDTH - 420, 120, WIDTH + 80, 620), fill=(245, 123, 66, 48))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    base.alpha_composite(glow)


def draw_title_block(base: Image.Image, scene: Scene) -> None:
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle((72, 68, 236, 104), radius=18, fill=(232, 246, 240, 255))
    draw.text((92, 76), "MediSlim Story", fill=BRAND_DARK, font=FONT_SCENE)
    title = wrap_text(draw, scene.title, FONT_HEAD, 560)
    draw.multiline_text((72, 144), title, fill=TEXT, font=FONT_HEAD, spacing=6)
    body = wrap_text(draw, scene.body, FONT_BODY, 540)
    draw.multiline_text((74, 330), body, fill=MUTED, font=FONT_BODY, spacing=8)


def draw_progress(base: Image.Image, index: int) -> None:
    draw = ImageDraw.Draw(base)
    start_x = 72
    y = HEIGHT - 72
    for idx in range(len(SCENES)):
        color = (200, 210, 206, 255)
        if idx == index:
            color = (*BRAND, 255)
        draw.rounded_rectangle((start_x + idx * 116, y, start_x + idx * 116 + 86, y + 6), radius=6, fill=color)


def sips_png(src: Path, dst: Path) -> Path:
    if dst.exists():
        return dst
    subprocess.run(
        ["sips", "-s", "format", "png", str(src), "--out", str(dst)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return dst


def load_png_asset(src: Path, size: Tuple[int, int]) -> Image.Image:
    png = TMP_DIR / f"{src.stem}-{size[0]}x{size[1]}.png"
    sips_png(src, png)
    image = Image.open(png).convert("RGBA")
    image.thumbnail(size, Image.LANCZOS)
    return image


def draw_emotion_scene(base: Image.Image, progress: float) -> None:
    panel = Image.new("RGBA", (420, 560), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle((52, 30, 380, 520), radius=42, fill=(27, 58, 50, 230))
    draw.ellipse((110, 74, 310, 274), fill=(243, 212, 189, 255))
    draw.rounded_rectangle((138, 248, 282, 454), radius=72, fill=(244, 226, 214, 255))
    draw.rounded_rectangle((102, 258, 148, 414), radius=24, fill=(244, 226, 214, 235))
    draw.rounded_rectangle((272, 258, 318, 414), radius=24, fill=(244, 226, 214, 235))
    draw.rounded_rectangle((152, 280, 268, 498), radius=36, fill=(239, 171, 138, 255))
    draw.rounded_rectangle((154, 300, 266, 340), radius=18, fill=(255, 255, 255, 28))
    panel = panel.filter(ImageFilter.GaussianBlur(0.2))

    x = int(780 + 12 * math.sin(progress * math.pi))
    y = 92
    base.alpha_composite(panel, (x, y))

    draw = ImageDraw.Draw(base)
    chips = ["睡不好", "总在反弹", "没力气"]
    for idx, label in enumerate(chips):
        yy = 150 + idx * 118 + int(10 * math.sin(progress * math.pi + idx))
        ww = 180 if idx != 1 else 204
        draw.rounded_rectangle((930, yy, 930 + ww, yy + 62), radius=22, fill=(255, 255, 255, 232))
        draw.text((954, yy + 18), label, fill=TEXT, font=FONT_BODY)


def draw_assessment_scene(base: Image.Image, progress: float) -> None:
    phone = Image.new("RGBA", (360, 560), (0, 0, 0, 0))
    draw = ImageDraw.Draw(phone)
    draw.rounded_rectangle((0, 0, 360, 560), radius=42, fill=(21, 34, 31, 250))
    draw.rounded_rectangle((132, 22, 228, 34), radius=8, fill=(255, 255, 255, 70))
    draw.rounded_rectangle((28, 74, 332, 214), radius=28, fill=(255, 255, 255, 22))
    draw.text((52, 104), "AI 评估中", fill=WHITE, font=FONT_METRIC)
    draw.text((54, 154), "BMI / 睡眠 / 皮肤状态 / 体质偏向", fill=(225, 232, 228), font=FONT_SMALL)

    for idx, label in enumerate(["气郁倾向", "湿热偏高", "建议先做轻评估"]):
        yy = 260 + idx * 82
        fill = (255, 255, 255, int(36 + 18 * idx))
        draw.rounded_rectangle((28, yy, 332, yy + 60), radius=22, fill=fill)
        draw.text((52, yy + 18), label, fill=WHITE, font=FONT_LABEL)

    bar_width = 220 + int(80 * ease(progress))
    draw.rounded_rectangle((54, 494, 306, 510), radius=8, fill=(255, 255, 255, 40))
    draw.rounded_rectangle((54, 494, 54 + min(bar_width, 252), 510), radius=8, fill=(245, 123, 66, 255))
    base.alpha_composite(phone, (808, 86))


def draw_products_scene(base: Image.Image, progress: float) -> None:
    slots = [(740, 90, 264, 216), (1020, 150, 220, 180), (860, 360, 250, 188)]
    for idx, (product_id, name, price) in enumerate(PRODUCT_ASSETS):
        x, y, w, h = slots[idx]
        shift = int((1 - ease(progress)) * 28)
        card = Image.new("RGBA", (w, h), (255, 255, 255, 235))
        draw = ImageDraw.Draw(card)
        draw.rounded_rectangle((0, 0, w, h), radius=28, fill=(255, 255, 255, 235))
        draw.rounded_rectangle((16, 16, w - 16, int(h * 0.58)), radius=22, fill=(249, 242, 235))
        img = load_png_asset(ROOT / "static" / "media" / "products" / f"{product_id}.svg", (w - 36, int(h * 0.58) - 20))
        ix = (w - img.width) // 2
        iy = 24 + max(0, (int(h * 0.58) - img.height - 8) // 2)
        card.alpha_composite(img, (ix, iy))
        draw.text((20, int(h * 0.63)), name, fill=TEXT, font=FONT_LABEL)
        draw.text((20, int(h * 0.79)), f"¥{price} 起", fill=BRAND_DARK, font=FONT_BODY)
        base.alpha_composite(card, (x, y + shift))


def draw_fulfillment_scene(base: Image.Image, progress: float) -> None:
    draw = ImageDraw.Draw(base)
    card = Image.new("RGBA", (430, 520), (255, 255, 255, 224))
    cdraw = ImageDraw.Draw(card)
    cdraw.rounded_rectangle((0, 0, 430, 520), radius=34, fill=(255, 255, 255, 224))

    for idx, (partner_id, name) in enumerate(PARTNER_ASSETS):
        col = idx % 2
        row = idx // 2
        x = 24 + col * 200
        y = 30 + row * 116
        cdraw.rounded_rectangle((x, y, x + 180, y + 86), radius=20, fill=(249, 243, 236))
        logo = load_png_asset(ROOT / "static" / "media" / "partners" / f"{partner_id}.svg", (126, 42))
        lx = x + (180 - logo.width) // 2
        ly = y + 12
        card.alpha_composite(logo, (lx, ly))
        cdraw.text((x + 24, y + 56), name, fill=MUTED, font=FONT_TINY)

    timeline_labels = ["AI 评估", "医生审核", "药房发货", "订阅跟踪"]
    for idx, label in enumerate(timeline_labels):
        yy = 298 + idx * 50
        cx = 42
        cdraw.ellipse((cx, yy + 6, cx + 14, yy + 20), fill=(*BRAND, 255))
        cdraw.rounded_rectangle((70, yy, 376, yy + 30), radius=12, fill=(240, 247, 244))
        cdraw.text((94, yy + 5), label, fill=TEXT, font=FONT_LABEL)
    base.alpha_composite(card, (770, 98))


def draw_outcome_scene(base: Image.Image, progress: float) -> None:
    panel = Image.new("RGBA", (430, 520), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle((0, 0, 430, 520), radius=36, fill=(255, 251, 246, 236))
    draw.rounded_rectangle((28, 36, 402, 188), radius=28, fill=(255, 255, 255, 220))
    quote = "“我不是被推着走，\n而是终于又能照顾自己了。”"
    draw.multiline_text((56, 72), quote, fill=TEXT, font=FONT_BODY, spacing=10)

    metrics = [("5", "核心品类"), ("9", "体质辨识"), ("1", "统一前台")]
    for idx, (value, label) in enumerate(metrics):
        x = 28 + idx * 132
        draw.rounded_rectangle((x, 232, x + 112, 360), radius=24, fill=(245, 249, 246))
        draw.text((x + 32, 256), value, fill=BRAND_DARK, font=FONT_METRIC)
        draw.text((x + 18, 316), label, fill=MUTED, font=FONT_TINY)

    draw.rounded_rectangle((140, 388, 288, 500), radius=56, fill=(239, 190, 160))
    draw.ellipse((110, 312, 320, 500), fill=(238, 222, 206))
    draw.rounded_rectangle((162, 404, 266, 492), radius=38, fill=(255, 250, 246))
    base.alpha_composite(panel, (760, 94))


SCENE_DRAWERS = {
    "emotion": draw_emotion_scene,
    "assessment": draw_assessment_scene,
    "products": draw_products_scene,
    "fulfillment": draw_fulfillment_scene,
    "outcome": draw_outcome_scene,
}


def build_frame(scene: Scene, scene_index: int, progress: float) -> np.ndarray:
    base = Image.new("RGBA", (WIDTH, HEIGHT), (*BG, 255))
    top_color = (255, 249, 242)
    bottom_color = (242, 233, 223)
    if scene.key == "emotion":
        top_color, bottom_color = (255, 248, 241), (231, 220, 212)
    elif scene.key == "assessment":
        top_color, bottom_color = (250, 247, 242), (233, 242, 239)
    elif scene.key == "products":
        top_color, bottom_color = (255, 251, 246), (244, 234, 226)
    elif scene.key == "fulfillment":
        top_color, bottom_color = (246, 250, 247), (233, 242, 237)
    elif scene.key == "outcome":
        top_color, bottom_color = (255, 250, 244), (239, 235, 228)
    draw_gradient(base, top_color, bottom_color)
    apply_texture(base)
    draw_title_block(base, scene)
    SCENE_DRAWERS[scene.key](base, progress)
    draw_progress(base, scene_index)
    return np.array(base.convert("RGB"))


def run_ffmpeg(args: List[str]) -> None:
    subprocess.run([FFMPEG, *args], check=True)


def probe_duration(audio_path: Path) -> float:
    duration_out = subprocess.check_output(
        [FFMPEG, "-i", str(audio_path), "-f", "null", "-"],
        stderr=subprocess.STDOUT,
        text=True,
    )
    duration_line = next((line for line in duration_out.splitlines() if "Duration:" in line), "")
    stamp = duration_line.split("Duration:")[-1].split(",")[0].strip() if duration_line else "00:00:03.0"
    h, m, s = stamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def make_silence(duration: float, output_path: Path) -> None:
    run_ffmpeg(
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=mono:sample_rate=22050",
            "-t",
            f"{duration:.3f}",
            str(output_path),
        ]
    )


def normalize_voice(input_path: Path, output_path: Path) -> None:
    run_ffmpeg(
        [
            "-y",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            "22050",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    )


def generate_narration() -> Tuple[Path, float]:
    voice = "Tingting"
    scene_audio: List[Path] = []
    total = 0.0
    for idx, scene in enumerate(SCENES):
        raw_audio_path = TMP_DIR / f"scene-{idx + 1}.aiff"
        audio_path = TMP_DIR / f"scene-{idx + 1}.wav"
        subprocess.run(["say", "-v", voice, "-o", str(raw_audio_path), scene.narration], check=True)
        normalize_voice(raw_audio_path, audio_path)
        clip_duration = probe_duration(audio_path)
        scene.duration = max(clip_duration + 1.3, 4.0)
        total += scene.duration
        scene_audio.append(audio_path)
        silence_path = TMP_DIR / f"silence-{idx + 1}.wav"
        make_silence(scene.duration - clip_duration, silence_path)

    concat_inputs: List[Path] = []
    for idx, audio_path in enumerate(scene_audio):
        concat_inputs.append(audio_path)
        concat_inputs.append(TMP_DIR / f"silence-{idx + 1}.wav")

    concat_file = TMP_DIR / "audio_concat.txt"
    concat_file.write_text("\n".join(f"file '{path.as_posix()}'" for path in concat_inputs), encoding="utf-8")
    full_audio = OUTPUT_DIR / "medislim-story-voiceover.wav"
    run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(full_audio)])
    return full_audio, total


def render_video(video_path: Path, total_duration: float, with_audio: bool = False, audio_path: Path | None = None) -> None:
    writer = imageio_ffmpeg.write_frames(
        str(video_path),
        size=(WIDTH, HEIGHT),
        fps=FPS,
        codec="libx264",
        pix_fmt_in="rgb24",
        output_params=["-crf", "18", "-movflags", "+faststart"],
    )
    writer.send(None)
    elapsed = 0.0
    for scene_index, scene in enumerate(SCENES):
        frame_count = max(1, int(scene.duration * FPS))
        for frame_idx in range(frame_count):
            progress = frame_idx / max(1, frame_count - 1)
            frame = build_frame(scene, scene_index, progress)
            writer.send(frame)
        elapsed += scene.duration
    writer.close()

    if with_audio and audio_path is not None:
        temp_muxed = video_path.with_name(video_path.stem + "-muxed.mp4")
        run_ffmpeg(
            [
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-shortest",
                str(temp_muxed),
            ]
        )
        temp_muxed.replace(video_path)


def render_webm(source_mp4: Path, output_webm: Path) -> None:
    run_ffmpeg(
        [
            "-y",
            "-i",
            str(source_mp4),
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            "0",
            "-crf",
            "30",
            "-an",
            str(output_webm),
        ]
    )


def render_poster(output_png: Path) -> None:
    frame = build_frame(SCENES[2], 2, 0.72)
    Image.fromarray(frame).save(output_png)


def main() -> None:
    ensure_dirs()
    audio_path, total_duration = generate_narration()
    loop_mp4 = STATIC_DIR / "medislim-demo-loop.mp4"
    voice_mp4 = STATIC_DIR / "medislim-demo-voiceover.mp4"
    loop_webm = STATIC_DIR / "medislim-demo-loop.webm"
    poster = STATIC_DIR / "medislim-demo-poster.png"

    render_video(loop_mp4, total_duration, with_audio=False)
    render_video(voice_mp4, total_duration, with_audio=True, audio_path=audio_path)
    render_webm(loop_mp4, loop_webm)
    render_poster(poster)

    print(loop_mp4)
    print(loop_webm)
    print(voice_mp4)
    print(poster)


if __name__ == "__main__":
    main()
