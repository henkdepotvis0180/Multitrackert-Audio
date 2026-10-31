#!/usr/bin/env bash
# Build only the local formats/codecs this application needs, without GPL/nonfree code.
set -euo pipefail
build_target="${1:-windows}"
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
build_root="${2:-$repo_root/build/windows-media}"
mkdir -p "$build_root/bin" "$build_root/source"
archive="$build_root/source/ffmpeg-n7.1.1.tar.gz"
if [ ! -f "$archive" ]; then
  curl --fail --location --retry 2 https://github.com/FFmpeg/FFmpeg/archive/refs/tags/n7.1.1.tar.gz -o "$archive"
fi
echo 'f117507dc501f2a6c11f9241d8d0c3213846cfad91764361af37befd6b6c523d  '"$archive" | sha256sum --check --status
if [ ! -d "$build_root/FFmpeg-n7.1.1" ]; then tar -xzf "$archive" -C "$build_root"; fi
cd "$build_root/FFmpeg-n7.1.1"
cross_options=()
if [ "$build_target" = windows ]; then
  cross_options=(--target-os=mingw32 --arch=x86_64 --cross-prefix=x86_64-w64-mingw32- --enable-cross-compile --extra-ldflags=-static)
fi
./configure "${cross_options[@]}" --disable-autodetect --disable-everything \
  --disable-doc --disable-debug --disable-ffplay --disable-network --disable-x86asm \
  --disable-gpl --disable-nonfree --enable-small \
  --enable-avcodec --enable-avformat --enable-avfilter --enable-avdevice --enable-swscale --enable-swresample \
  --enable-ffmpeg --enable-ffprobe --enable-protocol=file,pipe \
  --enable-demuxer=mov,matroska,wav,mp3,aac,flac,ogg \
  --enable-muxer=mp4,mov,wav,mp3,flac \
  --enable-decoder=wrapped_avframe,rawvideo,mpeg4,h264,hevc,vp9,aac,aac_fixed,mp3,mp3float,flac,pcm_f32le,pcm_f64le,pcm_s16le,pcm_s24le,pcm_s32le,opus,vorbis,alac,ac3,eac3,wmav2 \
  --enable-encoder=pcm_f32le,pcm_s16le,aac,mpeg4 \
  --enable-parser=aac,aac_latm,mpegaudio,h264,hevc,opus,vorbis,flac,mpeg4video,ac3 \
  --enable-bsf=aac_adtstoasc,h264_mp4toannexb,hevc_mp4toannexb,extract_extradata \
  --enable-filter=aresample,apad,atrim,anull,aformat,asetpts,adelay,concat,volume,color,sine,format,scale,null,anullsink,nullsink \
  --enable-indev=lavfi
make -j2
suffix=''
if [ "$build_target" = windows ]; then suffix='.exe'; fi
cp "ffmpeg$suffix" "ffprobe$suffix" "$build_root/bin/"
cp COPYING.LGPLv2.1 "$build_root/source/"
cp "$repo_root/windows/build_ffmpeg.sh" "$build_root/source/"
cp ffbuild/config.mak "$build_root/source/config-$build_target.mak"
# Source archive + exact configuration travel with the binary release.
cd "$build_root"
tar -czf FFmpeg-Corresponding-Source.tar.gz source
