# WAJC mastering

Masters an audio file the way the WAJC Adobe Audition chain does: a compressor, then match loudness to −18 LUFS with a true-peak limiter. The [breaking-stereotypes-stitch](../breaking-stereotypes-stitch/) script runs it on every stitched episode, and it also works on its own on any audio file.

## Setup

Follow the [setup in the main README](../README.md#setup), then install this script's packages:

```
pip install -r wajc-mastering/requirements.txt
```

## Running

With the virtual environment active:

```
python wajc-mastering/wajc-mastering.py "some file.mp3"
python wajc-mastering/wajc-mastering.py "some file.wav" "mastered.mp3" --tags "file to copy tags from.mp3"
```

With no output given, it writes `<name> CLUFPL Python FFmpeg.mp3` next to the source. Tags (title, artist and so on) are copied from the source unless `--tags` names another file. It prints the final loudness and true peak, for example:

```
  mastered: -18.0 LUFS, true peak -1.6 dBTP
```

It masters whatever file it's given. If the result misses the loudness or peak targets (for example with silent input), it prints a warning and still writes the file.

## What it does

It applies the same two effects as the WAJC Adobe Audition chain, in this order, to both channels. The settings are at the top of `wajc-mastering.py`:

| Audition effect | Setting | Script setting | ffmpeg equivalent |
|---|---|---|---|
| Tube-modeled Compressor | Threshold −15 dB | `masterThreshold` | `acompressor` |
| | Ratio 4:1 | `masterRatio` | |
| | Attack 1 ms | `masterAttack` | |
| | Release 150 ms | `masterRelease` | |
| | Output Gain 0 dB | `masterOutputGain` | |
| Match Loudness (ITU-R BS.1770-3) | Target −18 LUFS | `masterLoudness` | measured with `ebur128`, then `volume` |
| | Tolerance 0.5 LU | `masterTolerance` | |
| | Max True Peak −1.5 dBTP | `masterTruePeak` | `alimiter` |
| | Look-Ahead 12 ms | `masterLookAhead` | |
| | Release 200 ms | `masterLimiterRelease` | |

How it works:

1. The compressor is applied and the result is measured to find its loudness.
2. The gain needed to reach −18 LUFS is applied, then the limiter keeps peaks under −1.5 dBTP. The limiter runs at 4× the sample rate, so it also catches peaks that fall between samples ("true peaks").
3. The result is saved as MP3 (LAME variable bitrate, `-q:a 2`) and measured. If it's more than 0.5 LU off target (limiting can pull it down a little), or its true peak is above −1.5 dBTP (converting to MP3 can push peaks up by about 0.4 dB), the gain and the limiter's ceiling are corrected by what was measured and it's redone, up to 3 tries.

Differences from Audition:

- **Tube character:** Audition's Tube-modeled Compressor adds a tube-style colour. ffmpeg's compressor has the same settings but sounds clean, with no colour.
- **Slightly less compression on loud passages:** about 0.3 dB, too small to hear. See the comparison below.
- **MP3 settings:** Audition exported 192 kb/s constant bitrate. This script uses variable bitrate, about 98 kb/s on mono speech, so files are about half the size.

## Compared with Audition

The full comparison, with the effect-by-effect mapping, gain curves, null tests and open questions, is in [parity-report.md](parity-report.md). In short:

Tested on `09_25_2026 STTA.mp3` (50:34, mono), mastered by the script and by Audition with the same settings:

| | Loudness (LUFS) | Loudness range (LU) | True peak (dBTP) | Crest factor |
|---|---|---|---|---|
| Original | −20.4 | 5.2 | +0.2 | 11.06 |
| Audition | −18.3 | 3.5 | −2.0 | 6.55 |
| Script | −18.0 | 3.6 | −1.6 | 6.78 |

Through the episode, the script's version is a median 0.2 dB louder than Audition's (within 0.4 dB 95% of the time). Both compress the same way: quiet passages get about 4.3 dB of gain from both; the loudest passages get 1.7 dB from Audition and 2.0 dB from the script. Mastering the 50-minute file takes about a minute.

**Null test** (Audition's version inverted and mixed with the script's): what's left is 21.3 dB quieter than the audio. That's about what two separate MP3 conversions leave behind on their own (converting Audition's MP3 to MP3 again and nulling it leaves −42.9 dB, about −39.9 dB for two conversions, against −39.8 dB measured), so almost all of the difference comes from MP3 conversion rather than the mastering.

With the script's master saved as uncompressed WAV instead of MP3, so only Audition's MP3 conversion remains, what's left is −42.7 dB (24.2 dB below the audio). That's the same as one MP3 conversion leaves on its own (−42.9 dB), so any difference in the mastering itself is smaller than Audition's MP3 conversion noise.

## Test files

The comparison files live in `test-files/`, which is excluded from git:

| File | What it is |
|---|---|
| `09_25_2026 STTA.mp3` | Unmastered source, exported from Audition |
| `09_25_2026 STTA CLUFPL Adobe Audition.mp3` | Audition's master |
| `09_25_2026 STTA CLUFPL Python FFmpeg.mp3` | This script's master |
| `09_25_2026 STTA Null Test.mp3` | What's left when the two MP3 masters cancel each other |
| `09_25_2026 STTA Null Test (script as WAV).mp3` | The same, with the script's master kept as WAV |
