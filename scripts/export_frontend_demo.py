#!/usr/bin/env python3
"""Build the pure-frontend MediSlim film and export MP4/WebM assets."""

from __future__ import annotations

import base64
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]
STATIC_DEMO_DIR = ROOT / "static" / "media" / "demo"
TMP_DIR = ROOT / "output" / "video_demo" / "frontend_tmp"
PWCLI = Path.home() / ".codex" / "skills" / "playwright" / "scripts" / "playwright_cli.sh"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
PORT = 8098
BASE_URL = f"http://127.0.0.1:{PORT}"

SCENES = [
    {
        "id": "imbalance",
        "title": "状态先被看见",
        "headline": "先把身体里的混乱，说清楚。",
        "summary": "她不是想再听一套更激进的承诺，她只是想知道，为什么体重、睡眠和皮肤会一起失控。",
        "narration": "她不是想再听一套更激进的承诺，她只是想知道，为什么体重、睡眠和皮肤，会一起失控。",
        "subtitle": "她不是想再听一套更激进的承诺。\n她只是想知道，为什么体重、睡眠和皮肤会一起失控。",
        "hold": 0.8,
    },
    {
        "id": "scan",
        "title": "AI 评估先行",
        "headline": "先做 AI 评估，再谈哪条方案。",
        "summary": "MediSlim 把体重、睡眠、皮肤和九种体质放到一张图里，先看优先级，再决定入口。",
        "narration": "MediSlim 不先卖货。先做 AI 评估，结合九种体质，把体重、睡眠、皮肤和情绪状态，放到一张图里看。",
        "subtitle": "MediSlim 不先卖货。\n先做 AI 评估，结合九种体质，把状态放到一张图里看。",
        "hold": 0.8,
    },
    {
        "id": "data",
        "title": "图表替代空话",
        "headline": "数据不是装饰，是决定顺序。",
        "summary": "什么时候先减重，什么时候先修睡眠，什么时候要把复购提醒提前，都用趋势图来判断。",
        "narration": "数据不是为了好看，而是为了判断。什么时候先减重，什么时候先修睡眠，什么时候要把复购提醒提前，都用趋势图来决定。",
        "subtitle": "数据不是为了好看，而是为了判断。\n先减重，还是先修睡眠，都用趋势图来决定。",
        "hold": 0.8,
    },
    {
        "id": "plan",
        "title": "进入对应产品",
        "headline": "方案来自评估，不是一刀切。",
        "summary": "如果减重优先，就进入 GLP-1 路径；如果睡眠和皮肤更紧急，就切到更轻的干预方案。",
        "narration": "如果减重优先，就进入 GLP 一路径。如果睡眠和皮肤更紧急，就切到更轻的干预方案。",
        "subtitle": "如果减重优先，就进入 GLP-1 路径。\n如果睡眠和皮肤更紧急，就切到更轻的干预方案。",
        "hold": 0.8,
    },
    {
        "id": "network",
        "title": "前台轻，后链路稳",
        "headline": "前台负责解释，后面交给伙伴接住。",
        "summary": "医生审核、药房履约和配送链路交给合作医院和药房，前台只把用户体验和复购信号做清楚。",
        "narration": "前台负责承接和解释，后面的医生审核、药房履约和物流配送，交给合作医院和药房接住。",
        "subtitle": "前台负责承接和解释。\n医生审核、药房履约和物流配送，交给合作医院和药房接住。",
        "hold": 0.9,
    },
    {
        "id": "outcome",
        "title": "回到稳定节奏",
        "headline": "最后留下来的，是更轻、更稳的日常。",
        "summary": "真正留下来的，不是一次冲动下单，而是一套能继续留在生活里的健康节奏和订阅关系。",
        "narration": "最后留下来的，不是一次冲动下单，而是一套更轻、更稳，能继续留在生活里的健康节奏。",
        "subtitle": "最后留下来的，不是一次冲动下单。\n而是一套更轻、更稳，能继续留在生活里的健康节奏。",
        "hold": 1.0,
    },
]


def ensure_dirs() -> None:
    STATIC_DEMO_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run([FFMPEG, *args], check=True)


def probe_duration(audio_path: Path) -> float:
    output = subprocess.check_output(
        [FFMPEG, "-i", str(audio_path), "-f", "null", "-"],
        stderr=subprocess.STDOUT,
        text=True,
    )
    duration_line = next((line for line in output.splitlines() if "Duration:" in line), "")
    stamp = duration_line.split("Duration:")[-1].split(",")[0].strip() if duration_line else "00:00:03.0"
    hours, minutes, seconds = stamp.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def normalize_voice(input_path: Path, output_path: Path) -> None:
    run_ffmpeg([
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "24000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ])


def make_silence(duration: float, output_path: Path) -> None:
    run_ffmpeg([
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=mono:sample_rate=24000",
        "-t",
        f"{duration:.3f}",
        str(output_path),
    ])


def build_voiceover_assets() -> None:
    concat_parts: list[Path] = []
    current_start = 0.0

    for index, scene in enumerate(SCENES, start=1):
        raw_path = TMP_DIR / f"scene-{index}.aiff"
        wav_path = TMP_DIR / f"scene-{index}.wav"
        subprocess.run(["say", "-v", "Tingting", "-o", str(raw_path), scene["narration"]], check=True)
        normalize_voice(raw_path, wav_path)
        speech_duration = probe_duration(wav_path)
        scene_duration = max(speech_duration + scene["hold"], 4.8)
        scene["speech_duration"] = round(speech_duration, 3)
        scene["duration"] = round(scene_duration, 3)
        scene["start"] = round(current_start, 3)
        scene["end"] = round(current_start + scene_duration, 3)
        current_start += scene_duration

        silence_path = TMP_DIR / f"scene-{index}-silence.wav"
        silence_duration = max(scene_duration - speech_duration, 0.0)
        make_silence(silence_duration, silence_path)
        concat_parts.extend([wav_path, silence_path])

    concat_file = TMP_DIR / "voiceover_concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{part.as_posix()}'" for part in concat_parts),
        encoding="utf-8",
    )

    voiceover_wav = STATIC_DEMO_DIR / "medislim-film-voiceover.wav"
    run_ffmpeg([
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        str(voiceover_wav),
    ])

    manifest = {
        "title": "MediSlim Film",
        "duration": round(current_start, 3),
        "fps": 24,
        "voiceover": "/static/media/demo/medislim-film-voiceover.wav",
        "scenes": [
            {
                "id": scene["id"],
                "title": scene["title"],
                "headline": scene["headline"],
                "summary": scene["summary"],
                "subtitle": scene["subtitle"],
                "start": scene["start"],
                "end": scene["end"],
                "duration": scene["duration"],
            }
            for scene in SCENES
        ],
    }

    manifest_path = STATIC_DEMO_DIR / "medislim-film-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


@contextmanager
def http_server():
    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", str(ROOT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"{BASE_URL}/templates/demo_film.html", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            raise RuntimeError("http server did not start in time")
        yield
    finally:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def run_pwcli(args: list[str], capture_output: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["bash", str(PWCLI), *args]
    return subprocess.run(
        cmd,
        check=check,
        cwd=str(ROOT),
        text=True,
        capture_output=capture_output,
    )


def export_frontend_film() -> None:
    run_pwcli(["close-all"], check=False)

    page_url = f"{BASE_URL}/templates/demo_film.html?autoplay=0"
    run_pwcli(["open", page_url], check=True)
    run_pwcli(
        ["eval", "async () => { await window.MediSlimFilm.ready(); return window.MediSlimFilm.getState(); }", "--raw"],
        capture_output=True,
        check=True,
    )

    export_result = run_pwcli(
        ["eval", "async () => await window.MediSlimFilm.exportBase64()", "--raw"],
        capture_output=True,
        check=True,
    )
    payload = json.loads(export_result.stdout)
    raw_voiceover_webm = TMP_DIR / "medislim-demo-voiceover-raw.webm"
    voiceover_webm = STATIC_DEMO_DIR / "medislim-demo-voiceover.webm"
    raw_voiceover_webm.write_bytes(base64.b64decode(payload["base64"]))

    poster_result = run_pwcli(
        ["eval", "async () => await window.MediSlimFilm.exportPosterBase64()", "--raw"],
        capture_output=True,
        check=True,
    )
    poster_png = STATIC_DEMO_DIR / "medislim-demo-poster.png"
    poster_png.write_bytes(base64.b64decode(json.loads(poster_result.stdout)))

    run_pwcli(["close-all"], check=False)

    voiceover_mp4 = STATIC_DEMO_DIR / "medislim-demo-voiceover.mp4"
    loop_webm = STATIC_DEMO_DIR / "medislim-demo-loop.webm"
    loop_mp4 = STATIC_DEMO_DIR / "medislim-demo-loop.mp4"

    run_ffmpeg([
        "-y",
        "-i",
        str(raw_voiceover_webm),
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        "33",
        "-c:a",
        "libopus",
        "-b:a",
        "96k",
        str(voiceover_webm),
    ])

    run_ffmpeg([
        "-y",
        "-i",
        str(voiceover_webm),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(voiceover_mp4),
    ])

    run_ffmpeg([
        "-y",
        "-i",
        str(voiceover_webm),
        "-an",
        "-c:v",
        "copy",
        str(loop_webm),
    ])
    run_ffmpeg([
        "-y",
        "-i",
        str(voiceover_mp4),
        "-an",
        "-c:v",
        "copy",
        str(loop_mp4),
    ])


def main() -> None:
    if not PWCLI.exists():
        raise SystemExit(f"Playwright CLI wrapper not found: {PWCLI}")

    ensure_dirs()
    build_voiceover_assets()
    with http_server():
        export_frontend_film()

    print(STATIC_DEMO_DIR / "medislim-film-manifest.json")
    print(STATIC_DEMO_DIR / "medislim-film-voiceover.wav")
    print(STATIC_DEMO_DIR / "medislim-demo-loop.mp4")
    print(STATIC_DEMO_DIR / "medislim-demo-loop.webm")
    print(STATIC_DEMO_DIR / "medislim-demo-voiceover.mp4")
    print(STATIC_DEMO_DIR / "medislim-demo-voiceover.webm")
    print(STATIC_DEMO_DIR / "medislim-demo-poster.png")


if __name__ == "__main__":
    main()
