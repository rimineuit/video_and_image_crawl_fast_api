# get_transcripts.py
import subprocess
import sys
import json
from pathlib import Path
import tempfile

def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)

def vtt_to_text(vtt_path: Path) -> str:
    """Chuyển file VTT thành transcript text"""
    print(f"Processing VTT file: {vtt_path}")
    lines = []
    with open(vtt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("WEBVTT") or "-->" in line:  # bỏ metadata & timestamp
                continue
            lines.append(line)
    return " ".join(lines)

def download_transcript(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = str(Path(tmpdir) / "sub.%(ext)s")

        # thử phụ đề thường
        cmd = [sys.executable, "-m", "yt_dlp", "--skip-download",
               "--write-sub", "--sub-lang", "vie-VN", "--sub-format", "vtt",
               "-o", outtmpl, url]
        try:
            run(cmd)
        except subprocess.CalledProcessError:
            # fallback auto-sub
            cmd = [sys.executable, "-m", "yt_dlp", "--skip-download",
                   "--write-auto-sub", "--sub-lang", "vie-VN", "--sub-format", "vtt",
                   "-o", outtmpl, url]
            try:
                run(cmd)
            except subprocess.CalledProcessError:
                return ""

        # In toàn bộ nội dung (đệ quy) trong tmpdir
        def debug_tree(root):
            root = Path(root)
            print(f"[DEBUG] Listing under: {root.resolve()}")
            for p in sorted(root.rglob("*")):
                kind = "(dir)" if p.is_dir() else f"({p.stat().st_size} bytes)"
                print(" -", p.relative_to(root), kind)

        debug_tree(tmpdir)

        # Tìm file .vtt thật sự trong tmpdir
        vtt_files = sorted(Path(tmpdir).rglob("*.vtt"))  # dùng rglob để quét cả thư mục con
        print("[DEBUG] .vtt candidates:", [str(p) for p in vtt_files])

        if not vtt_files:
            print("[DEBUG] No .vtt found")
            return ""

        print("[DEBUG] Using:", vtt_files[0])
        return vtt_to_text(vtt_files[0])
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_transcripts.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    transcript = download_transcript(url)
    print("Result:\n")
    print(json.dumps({"transcripts": transcript}, ensure_ascii=False))
