import argparse
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

# WAJC mastering, replicating the Adobe Audition chain.
# Step 1, Tube-modeled Compressor:
masterThreshold = -15  # dB
masterRatio = 4  # 4:1
masterAttack = 1  # ms
masterRelease = 150  # ms
masterOutputGain = 0  # dB
# Step 2, Match Loudness (ITU-R BS.1770-3) with a true-peak limiter:
masterLoudness = -18  # LUFS
masterTolerance = 0.5  # LU
masterTruePeak = -1.5  # dBTP
masterLookAhead = 12  # ms
masterLimiterRelease = 200  # ms

# Added to the input's name when no output is given.
MASTERED_SUFFIX = " CLUFPL Python FFmpeg"

MP3_CODEC = ["-c:a", "libmp3lame", "-q:a", "2"]


def measureLoudness(path, filters=None):
    """Integrated loudness (LUFS) and true peak (dBTP) per ITU-R BS.1770, after optional filters."""
    chain = f"{filters},ebur128=peak=true" if filters else "ebur128=peak=true"
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-nostats", "-i", str(path),
         "-af", chain, "-f", "null", "-"],
        capture_output=True, text=True,
    )
    summary = result.stderr.rsplit("Summary:", 1)[-1]
    loudness = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    peak = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    if result.returncode != 0 or not loudness or not peak:
        raise ValueError(f"Could not measure loudness of {path}")
    return float(loudness.group(1)), float(peak.group(1))


def compressorFilter():
    """Tube-modeled Compressor step. Both channels share one gain, so the stereo image holds."""
    threshold = 10 ** (masterThreshold / 20)
    return (
        f"acompressor=threshold={threshold:.5f}:ratio={masterRatio}"
        f":attack={masterAttack}:release={masterRelease}:knee=1,"
        f"volume={masterOutputGain}dB"
    )


def loudnessFilter(gain, ceiling):
    """Match Loudness step: gain to the target, then a look-ahead limiter on true peaks at ceiling dB.

    The limiter runs at 4x the sample rate so it catches peaks that fall between samples.
    """
    limit = 10 ** (ceiling / 20)
    return (
        f"volume={gain:.2f}dB,aresample=176400,"
        f"alimiter=limit={limit:.4f}:attack={masterLookAhead}:release={masterLimiterRelease}"
        ":level=disabled:latency=1,"
        "aresample=44100"
    )


def master(source, output, tags=None):
    """WAJC mastering: compress, then match loudness to masterLoudness, and save as MP3.

    tags is the file whose tags (title, artist...) are copied to the output; defaults to source.
    Re-measures the MP3 and redoes it until it is within masterTolerance and under
    masterTruePeak: limiting pulls the loudness down a little, and MP3 encoding pushes
    peaks up a little, so the gain and limiter ceiling are corrected by what was measured.
    """
    compress = compressorFilter()
    loudness, _ = measureLoudness(source, compress)
    gain = masterLoudness - loudness
    ceiling = masterTruePeak
    for _ in range(3):
        subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(source), "-i", str(tags or source),
             "-af", f"{compress},{loudnessFilter(gain, ceiling)}",
             "-map", "0:a", "-map_metadata", "1",
             *MP3_CODEC, str(output)],
            check=True,
        )
        loudness, peak = measureLoudness(output)
        miss = masterLoudness - loudness
        over = peak - masterTruePeak
        if abs(miss) <= masterTolerance and over <= 0:
            break
        gain += miss
        ceiling -= max(over, 0) + 0.1  # small margin so the next try lands under, not on, the limit
    else:
        print(f"Warning: '{Path(output).name}' is {loudness:.1f} LUFS with a true peak of {peak:.1f} dBTP, "
              f"outside the {masterLoudness} LUFS ± {masterTolerance} / {masterTruePeak} dBTP targets.")
    print(f"  mastered: {loudness:.1f} LUFS, true peak {peak:.1f} dBTP")


def main():
    parser = argparse.ArgumentParser(description="Apply WAJC mastering (compressor, then match loudness to -18 LUFS) to an audio file.")
    parser.add_argument("source", help="audio file to master")
    parser.add_argument("output", nargs="?",
                        help=f"MP3 to write (default: the source's name plus '{MASTERED_SUFFIX}', next to it)")
    parser.add_argument("--tags", help="file to copy tags from (default: the source)")
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output) if args.output else source.with_name(f"{source.stem}{MASTERED_SUFFIX}.mp3")
    master(source, output, args.tags)


if __name__ == "__main__":
    main()
