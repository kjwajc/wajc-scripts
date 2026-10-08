# Breaking Stereotypes stitch

Builds episodes of the Breaking Stereotypes podcast. For each show, the script picks a random matched intro/outro pair (both recorded by the same host), joins intro + show + outro, lays background music underneath, masters the result with [wajc-mastering](../wajc-mastering/), and saves it to `./Stitched-Files`. The output file name records which pair was used, for example:

```
01.05.2025 Breaking Stereotypes - Intro-Outro 2 (LJ) CLUFPL Python FFmpeg.mp3
```

## Setup

Follow the [setup in the main README](../README.md#setup), then install this script's packages:

```
pip install -r breaking-stereotypes-stitch/requirements.txt
```

Mastering is done by [`wajc-mastering.py`](../wajc-mastering/), which must stay in its folder next to this one (`../wajc-mastering/`).

## Folder layout it expects

The audio sits in this script's folder. It's excluded from git, so copy it in on each computer.

```
breaking-stereotypes-stitch/
├── breaking-stereotypes-stitch.py
├── Breaking Stereotypes/
│   ├── Intros-Outros/
│   │   ├── background-music.m4a
│   │   └── Original Intro-Outro Recordings/
│   │       ├── Br St Intro - 1 (AW) - 011426.mp3
│   │       ├── Br St Outro - 1 (AW) - 011426.mp3
│   │       ├── Br St Intro - 2 (LJ).mp3
│   │       └── ...
│   └── Original BS's for editting/
│       └── 2025/
│           ├── 01.05.2025 Breaking Stereotypes.mp3
│           └── ...
└── Stitched-Files/          (created by the script)
```

- **Intros and outros** are named `Br St Intro - <number> (<initials>)` and `Br St Outro - <number> (<initials>)`. An intro and outro with the same number and initials form a pair. If a recording has dated versions (`- MMDDYY` on the end), the most recent one is used instead of the undated one.
- **Shows** must start with a date, `MM.DD.YYYY`. Other files in the folder are ignored. If the year in a file name doesn't match its year folder (for example `04.06.2015` inside `2025`), the script uses the folder's year and prints a warning.

## Running

Run the script from inside this folder, with the virtual environment active. It looks for audio relative to where it's run from.

```
cd breaking-stereotypes-stitch
python breaking-stereotypes-stitch.py
```

It prints which intro/outro pair each show got and the mastered loudness, and writes the files to `./Stitched-Files`. An existing file with the same name is overwritten.

Mastering is on by default, and mastered files end in ` CLUFPL Python FFmpeg.mp3`. To skip mastering for one run:

```
python breaking-stereotypes-stitch.py --no-wajc-mastering
```

Unmastered files don't have ` CLUFPL` in the name, so the two versions don't overwrite each other.

## Configuration

Settings are at the top of the script:

| Setting | Default | What it does |
|---|---|---|
| `filePath` | `"./Breaking Stereotypes"` | Folder containing the layout above. |
| `outputPath` | `"./Stitched-Files"` | Where stitched shows are saved. |
| `runAll` | `False` | `True` stitches every dated show. `False` stitches one show. |
| `singleFile` | `None` | The show to stitch when `runAll` is `False`. `None` means the oldest show. To pick one, give its path, for example `"./Breaking Stereotypes/Original BS's for editting/2025/03.02.2025 Breaking Stereotypes.mp3"`. |
| `musicVolume` | `-18` | Background music level in dB. More negative is quieter. Try steps of 2–3 dB. |
| `musicDuck` | `6` | The most the music drops while someone speaks, in dB. Smaller lets more music through under the voice; larger pushes it further back. |
| `musicFadeOut` | `5` | Seconds the music takes to fade out at the end. |
| `musicStart` | `28` | Where in the music track the first play starts, in seconds. Later loops play the whole track from the beginning. |
| `wajcMastering` | `True` | Masters each stitched file with `wajc-mastering.py`. `False` turns mastering off by default; `--wajc-mastering` then turns it on for one run. |

## Background music

`background-music.m4a` plays under the whole file (intro, show and outro). The first play starts 28 seconds into the track (`musicStart`), so it runs for 1:39. If the stitched file is longer than that, the whole track (2:07) then loops from the beginning for as long as needed. The music fades out over the last few seconds.

The voice always takes priority over the music, in three steps:

1. **Levelling.** The music gets much louder partway through (around 13 dB louder from about 0:55 to 1:50). The script evens this out first (ffmpeg's `dynaudnorm` filter), so the loud section stays close to the level of the rest.
2. **Background level.** The levelled music is turned down by `musicVolume`.
3. **Ducking.** Whenever someone speaks, the music drops further, by no more than `musicDuck` dB, then rises back during pauses (ffmpeg's `sidechaincompress` filter).

In testing on a 3-minute show with the default settings, the music dropped about 4 dB while someone was speaking, and the voice was on average about 16 dB louder than the music. The music comes up to its background level during pauses.

- **To hear more music under the voice:** lower `musicDuck`.
- **To make the music louder or quieter everywhere, pauses included:** change `musicVolume`.

## Mastering

After stitching, the script saves the mix as a temporary uncompressed WAV and runs `../wajc-mastering/wajc-mastering.py` on it, copying the show's tags to the result. Using WAV in between means the audio is only converted to MP3 once. See the [wajc-mastering README](../wajc-mastering/README.md) for what the mastering does and how it compares with Adobe Audition.

## Output format

Shows and intros/outros don't all share the same format (some are mono, some stereo, at different bitrates), so the script converts everything to 44.1 kHz stereo and applies a limiter to stop the mix from clipping. Mastered files are saved as described in the mastering README. Unmastered files are saved as variable-bitrate MP3 (about 190 kb/s at most). The show's tags (title, artist and so on) are copied to the output.
