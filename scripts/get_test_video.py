"""
scripts/get_test_video.py
--------------------------
Downloads a free, royalty-free outdoor/surveillance test video for Phase 1
development and places it at data/videos/test_video.mp4.

Usage:
    .venv\\Scripts\\python.exe scripts/get_test_video.py          # Windows
    python scripts/get_test_video.py                              # if venv active

If automatic download fails, see the MANUAL OPTIONS section printed at the end.
"""

from __future__ import annotations

import os
import sys
import urllib.request

OUTPUT_PATH = "data/videos/test_video.mp4"

# Short, freely available outdoor pedestrian/vehicle clips
# (Creative Commons / public domain — no sign-in required)
CANDIDATE_URLS = [
    # VIRAT dataset sample — outdoor surveillance footage (public)
    "https://viratdata.org/video/VIRAT_S_000200_01_000226_000268.mp4",
    # Sample CCTV clip from the MOT challenge dataset mirrors
    "https://motchallenge.net/sequenceVideos/MOT16-01-raw.webm",
    # Fallback: a well-known public MP4 test file (Big Buck Bunny — not surveillance
    # but useful to verify the pipeline works end-to-end)
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
]


def _progress(block_num: int, block_size: int, total_size: int) -> None:
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(downloaded / total_size * 100, 100)
        mb = downloaded / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        print(f"\r  {pct:.1f}%  ({mb:.1f} / {total_mb:.1f} MB)    ", end="", flush=True)
    else:
        mb = downloaded / (1024 * 1024)
        print(f"\r  {mb:.1f} MB downloaded...    ", end="", flush=True)


def try_download(url: str, output: str) -> bool:
    """Attempt to download url to output. Returns True on success."""
    print(f"  URL: {url}")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp, open(output, "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            block = 8192
            downloaded = 0
            block_num = 0
            while True:
                chunk = resp.read(block)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                block_num += 1
                _progress(block_num, block, total)
        print()
        return True
    except Exception as exc:
        print(f"\n  Failed: {exc}")
        if os.path.exists(output):
            os.remove(output)
        return False


def try_yt_dlp(output: str) -> bool:
    """Try yt-dlp with a suitable outdoor scene."""
    import subprocess

    YT_URL = "https://www.youtube.com/watch?v=MNn9qKG2UFI"
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yt_dlp",
                "-f",
                "bestvideo[ext=mp4][height<=480]+bestaudio/best[ext=mp4][height<=480]",
                "--merge-output-format",
                "mp4",
                "-o",
                output,
                YT_URL,
            ],
            capture_output=True,
            timeout=120,
        )
        return result.returncode == 0 and os.path.exists(output)
    except Exception:
        return False


def main() -> None:
    os.makedirs("data/videos", exist_ok=True)

    if os.path.exists(OUTPUT_PATH):
        size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
        print(f"Test video already exists: {OUTPUT_PATH} ({size_mb:.1f} MB)")
        print("Delete it and re-run to replace.")
        return

    print("=" * 60)
    print("  IBVAP - Test Video Downloader")
    print("=" * 60)
    print(f"  Target: {OUTPUT_PATH}\n")

    # 1. Try yt-dlp (best option)
    print("[1] Trying yt-dlp...")
    if try_yt_dlp(OUTPUT_PATH):
        print(f"Downloaded via yt-dlp -> {OUTPUT_PATH}")
        _done()
        return
    print("  yt-dlp unavailable (run: pip install yt-dlp)")

    # 2. Try direct download candidates
    for i, url in enumerate(CANDIDATE_URLS, start=2):
        print(f"\n[{i}] Trying direct download...")
        if try_download(url, OUTPUT_PATH):
            size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
            print(f"Downloaded -> {OUTPUT_PATH} ({size_mb:.1f} MB)")
            _done()
            return

    # All failed — print manual instructions
    print("\n" + "=" * 60)
    print("  All automatic downloads failed.")
    print("=" * 60)
    print("""
MANUAL OPTIONS (choose one):

1. Install yt-dlp and re-run:
   .venv\\Scripts\\pip.exe install yt-dlp
   .venv\\Scripts\\python.exe scripts/get_test_video.py

2. Download a free outdoor clip manually:
   - https://www.pexels.com/search/videos/street/
     (click Download, choose 720p)
   - https://pixabay.com/videos/search/street-traffic/
   - https://www.videvo.net/ (search "street")

   Then save the file as:
     data\\videos\\test_video.mp4

3. Use your own CCTV / dashcam / surveillance footage:
   Copy any .mp4 to: data\\videos\\test_video.mp4

4. Use a webcam instead (real-time):
   Edit configs/phase1_default.yaml:
     camera:
       source: 0    # 0 = default webcam
""")
    sys.exit(1)


def _done() -> None:
    print("\nReady. Run the edge node with:")
    print("  .venv\\Scripts\\python.exe -m apps.edge.main --config configs/phase1_default.yaml")


if __name__ == "__main__":
    main()
