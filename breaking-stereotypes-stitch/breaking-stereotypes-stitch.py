import argparse
import glob
import random
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import date, datetime
from pathlib import Path

import imageio_ffmpeg

# Where the script looks for audio. Kept as a global so the source can change later.
filePath = "./Breaking Stereotypes"

# Where stitched shows are written.
outputPath = "./Stitched-Files"

# True: stitch every dated show. False: stitch only singleFile. --all does the same for one run.
runAll = False

# Show to stitch when runAll is False. None means the oldest dated show.
singleFile = None

# Background music level in dB, applied after the music is levelled out.
# More negative is quieter. The music is also ducked further whenever someone speaks.
musicVolume = -18

# The most the music drops while someone speaks, in dB. Smaller lets more music through.
musicDuck = 6

# Seconds the music takes to fade out at the end of each file.
musicFadeOut = 5

# Where in the music track the first play starts, in seconds. Later loops play the whole track.
musicStart = 28

# True: master each stitched file with wajc-mastering.py. Turn off for one run with --no-wajc-mastering.
wajcMastering = True

SHOWS_FOLDER = "Original BS's for editting"
INTRO_OUTRO_FOLDER = "Intros-Outros/Original Intro-Outro Recordings"
BACKGROUND_MUSIC = "Intros-Outros/background-music.m4a"

# "01.05.2025 Breaking Stereotypes.mp3" -> month, day, year
SHOW_NAME = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})\b")

# "Br St Intro - 1 (AW) - 011426.mp3" -> kind, set number, initials, optional MMDDYY date
INTRO_OUTRO_NAME = re.compile(r"^Br St (Intro|Outro) - (\d+) \((\w+)\)(?: - (\d{6}))?$")

MP3_CODEC = ["-c:a", "libmp3lame", "-q:a", "2"]

# Added to the output name when the file is mastered.
MASTERED_SUFFIX = " CLUFPL Python FFmpeg"

MASTERING_SCRIPT = Path(__file__).resolve().parent.parent / "wajc-mastering" / "wajc-mastering.py"


def showDate(path):
    """Date from a show's file name. If the year disagrees with its year folder, trust the folder."""
    month, day, year = (int(n) for n in SHOW_NAME.match(path.name).groups())
    folder = path.parent.name
    if folder.isdigit() and len(folder) == 4 and int(folder) != year:
        print(f"Warning: '{path.name}' is in folder {folder}; using {folder} as its year.")
        year = int(folder)
    return date(year, month, day)


def getFiles():
    """Return every dated show under filePath's shows folder, oldest first."""
    root = Path(filePath) / SHOWS_FOLDER
    if not root.is_dir():
        raise FileNotFoundError(f"Folder not found: {root.resolve()}")
    shows = [p for p in root.rglob("*.mp3") if SHOW_NAME.match(p.name)]
    return sorted(shows, key=showDate)


def getIntroOutroSets():
    """Return matched intro/outro pairs keyed by label, e.g. {"1 (AW)": (intro, outro)}.

    When a set has dated and undated recordings, the most recent dated one wins.
    """
    folder = Path(filePath) / INTRO_OUTRO_FOLDER
    best = {}  # (kind, label) -> (date sort key, path)
    for p in folder.glob("*.mp3"):
        m = INTRO_OUTRO_NAME.match(p.stem)
        if not m:
            continue
        kind, number, initials, mmddyy = m.groups()
        label = f"{number} ({initials})"
        # YYMMDD sorts by date; undated sorts before any dated version.
        rank = mmddyy[4:] + mmddyy[:4] if mmddyy else ""
        if (kind, label) not in best or rank > best[(kind, label)][0]:
            best[(kind, label)] = (rank, p)

    labels = {label for _, label in best}
    return {
        label: (best[("Intro", label)][1], best[("Outro", label)][1])
        for label in sorted(labels)
        if ("Intro", label) in best and ("Outro", label) in best
    }


def getDuration(path):
    """Length of an audio file in seconds, read from ffmpeg's file info."""
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        capture_output=True, text=True,
    )
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", result.stderr)
    if not m:
        raise ValueError(f"Could not read duration of {path}")
    hours, minutes, seconds = m.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def stitch(show, intro, outro, music, output, codec=MP3_CODEC):
    """Join intro + show + outro, lay looped background music under it, and save (MP3 by default).

    The voice always takes priority: the music is first levelled out (it builds up
    loudly partway through), set to musicVolume, then ducked whenever the voice is
    speaking via sidechain compression.
    """
    parts = [intro, show, outro]
    total = sum(getDuration(p) for p in parts)
    fadeStart = max(0, total - musicFadeOut)

    normalize = "".join(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}];" for i in range(3))
    joined = "[a0][a1][a2]concat=n=3:v=0:a=1,asplit=2[voice][key];"
    # Input 3 is the first play from musicStart; input 4 loops the whole track after it.
    bed = (
        "[3:a]aformat=sample_rates=44100:channel_layouts=stereo[m0];"
        "[4:a]aformat=sample_rates=44100:channel_layouts=stereo[m1];"
        "[m0][m1]concat=n=2:v=0:a=1,"
        "dynaudnorm=f=500:g=31,"  # flatten the music's slow build-up
        f"volume={musicVolume}dB,"
        f"atrim=duration={total:.3f},"
        f"afade=t=out:st={fadeStart:.3f}:d={musicFadeOut}[bed];"
    )
    # mix blends un-ducked music back in, which puts a floor of musicDuck dB under the ducking.
    duckMix = 1 - 10 ** (-musicDuck / 20)
    duck = f"[bed][key]sidechaincompress=threshold=0.015:ratio=8:attack=20:release=800:mix={duckMix:.4f}[ducked];"
    mix = (
        "[voice][ducked]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.97:level=disabled[out]"  # catch any peaks the mix pushes over
    )

    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y"]
    for p in parts:
        command += ["-i", str(p)]
    command += ["-ss", str(musicStart), "-i", str(music)]
    command += ["-stream_loop", "-1", "-i", str(music)]
    command += [
        "-filter_complex", normalize + joined + bed + duck + mix,
        "-map", "[out]",
        "-map_metadata", "1",
        *codec,
        str(output),
    ]
    # Output is captured so a failure's reason can go in the show's error log.
    subprocess.run(command, check=True, capture_output=True, text=True)


def master(stitched, show, output):
    """Run wajc-mastering.py on the stitched audio, copying the show's tags to the output."""
    result = subprocess.run(
        [sys.executable, str(MASTERING_SCRIPT), str(stitched), str(output), "--tags", str(show)],
        check=True, capture_output=True, text=True,
    )
    print(result.stdout, end="")


def existingOutput(show, outDir, mastering):
    """A stitched version of show already in outDir (mastered or not, to match this run), or None."""
    for p in outDir.glob(f"{glob.escape(show.stem)} - Intro-Outro *.mp3"):
        if p.stem.endswith(MASTERED_SUFFIX) == mastering:
            return p
    return None


def writeErrorLog(path, show, step, details, error):
    """Save why a show failed. Call from inside the except block, so the traceback is available."""
    lines = [
        f"Show: {show}",
        f"Time: {datetime.now():%Y-%m-%d %H:%M:%S}",
        *details,
        "",
        f"Failed while {step}: {type(error).__name__}",
    ]
    if isinstance(error, subprocess.CalledProcessError):
        lines.append(f"Exit code {error.returncode}")
        output = "\n".join(s.strip() for s in (error.stdout, error.stderr) if s and s.strip())
        lines += ["", "Output:", output or "(none)"]
    else:
        lines.append(str(error))
    lines += ["", "Traceback:", traceback.format_exc()]
    path.write_text("\n".join(lines), encoding="utf-8")


def clearFolder(folder):
    """Delete everything inside folder. Returns how many items were removed."""
    items = list(folder.iterdir())
    for p in items:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
    return len(items)


def main():
    parser = argparse.ArgumentParser(description="Stitch Breaking Stereotypes shows with an intro, outro and background music.")
    parser.add_argument("--all", action="store_true", help="stitch every dated show (default: only the oldest)")
    parser.add_argument("--clear", action="store_true", help="empty the output folder first, so every show is redone")
    parser.add_argument("--wajc-mastering", action=argparse.BooleanOptionalAction, default=wajcMastering,
                        help="master each stitched file with wajc-mastering.py (on by default)")
    args = parser.parse_args()
    mastering = args.wajc_mastering

    shows = getFiles()
    if runAll or args.all:
        selected = shows
    elif singleFile:
        selected = [Path(singleFile)]
    else:
        selected = shows[:1]

    sets = getIntroOutroSets()
    if not sets:
        raise FileNotFoundError("No matched intro/outro sets found.")

    music = Path(filePath) / BACKGROUND_MUSIC
    if not music.is_file():
        raise FileNotFoundError(f"Background music not found: {music.resolve()}")

    outDir = Path(outputPath)
    outDir.mkdir(parents=True, exist_ok=True)
    if args.clear:
        print(f"Cleared {clearFolder(outDir)} item(s) from {outDir}")

    done, skipped, failed = 0, 0, []
    for show in selected:
        existing = existingOutput(show, outDir, mastering)
        if existing:
            print(f"{show.name}: skipped, already stitched as '{existing.name}'")
            skipped += 1
            continue

        label = random.choice(list(sets))
        intro, outro = sets[label]
        suffix = MASTERED_SUFFIX if mastering else ""
        output = outDir / f"{show.stem} - Intro-Outro {label}{suffix}.mp3"
        errorLog = outDir / f"{show.stem} error.log"
        print(f"{show.name}: intro/outro {label} ({intro.name}, {outro.name}) -> {output}", flush=True)
        step = "stitching"
        try:
            if mastering:
                # Stitch to lossless WAV first so the audio is only encoded to MP3 once.
                with tempfile.TemporaryDirectory() as tempDir:
                    stitched = Path(tempDir) / "stitched.wav"
                    stitch(show, intro, outro, music, stitched, codec=["-c:a", "pcm_f32le"])
                    step = "mastering"
                    master(stitched, show, output)
            else:
                stitch(show, intro, outro, music, output)
        except Exception as error:
            output.unlink(missing_ok=True)  # a half-written file would make the next run skip this show
            details = [f"Intro/outro: {label} ({intro.name}, {outro.name})", f"Output: {output}"]
            writeErrorLog(errorLog, show, step, details, error)
            print(f"  FAILED while {step}; reason saved to '{errorLog.name}'")
            failed.append(show.name)
            continue
        errorLog.unlink(missing_ok=True)  # an earlier failure has now been fixed
        done += 1

    print(f"\nDone: {done} stitched, {skipped} skipped (already stitched), {len(failed)} failed.")
    for name in failed:
        print(f"  failed: {name}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
