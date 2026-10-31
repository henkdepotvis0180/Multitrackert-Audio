import argparse
import shutil


def main():
    parser = argparse.ArgumentParser(description="Multitrackert lokale server")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("Installeer FFmpeg en ffprobe en voeg deze toe aan PATH. Zie README.")
    import uvicorn

    uvicorn.run("multitrack.app:app", host="127.0.0.1", port=args.port, workers=1)


if __name__ == "__main__":
    main()
