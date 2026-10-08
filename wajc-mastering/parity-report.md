# WAJC Mastering Parity Report

The Adobe Audition mastering chain (Tube-modeled Compressor, then Match Loudness) has been rebuilt as a Python script that calls FFmpeg ([`wajc-mastering.py`](wajc-mastering.py)). This report compares the script's output with Audition's on the same source episode.

| | |
|---|---|
| Date | 8 October 2026 |
| Test file | `09_25_2026 STTA.mp3` (50:34.46) |
| Script | `wajc-mastering.py` |
| FFmpeg | 7.1 (gyan.dev build, via imageio-ffmpeg) |

## Summary

- Integrated loudness: Audition **−18.3 LUFS**, script **−18.0 LUFS**. Both are within the 0.5 LU tolerance of the −18 LUFS target.
- Compression: the gain curve is the same within 0.3 dB in every loudness band. The script compresses loud passages about 0.3 dB less.
- Over the whole episode, measured in 3 s short-term windows, the script is a median of 0.2 dB louder than Audition. 90% of windows fall between 0.0 and +0.4 dB.
- True peak: Audition −2.0 dBTP, script −1.6 dBTP. Both are under the −1.5 dBTP ceiling.
- Null test: with the script's output kept as uncompressed WAV, the residual against Audition's MP3 is −42.7 dBFS RMS (24.2 dB under the program). Re-encoding Audition's own MP3 once leaves −42.9 dBFS, so the residual is about the size of one MP3 encode's noise. The null can't show any processing difference smaller than that.
- Biggest open difference: the MP3 export settings. Audition exported 192 kb/s CBR; the script uses LAME VBR `-q:a 2` (about 98 kb/s on this mono file).

## Test material

Both masters were made from the same unmastered export. All three files have identical lengths, sample rates and encoder start offsets, so they line up sample for sample with no time shift (verified below). The files are in `test-files/`, which is excluded from git.

| File | Role | Length | Format | Encoder |
|---|---|--:|---|---|
| `09_25_2026 STTA.mp3` | Unmastered source (Audition export) | 50:34.46 | 44.1 kHz mono, 192 kb/s CBR | LAME 3.100 |
| `09_25_2026 STTA CLUFPL Adobe Audition.mp3` | Audition master | 50:34.46 | 44.1 kHz mono, 192 kb/s CBR | LAME 3.100 |
| `09_25_2026 STTA CLUFPL Python FFmpeg.mp3` | Script master | 50:34.46 | 44.1 kHz mono, VBR ≈ 98 kb/s | LAME (libmp3lame), `-q:a 2` |

## Signal chain mapping

Each Audition setting and how the script reproduces it. Both effects run on the whole file. Channels are linked; the test file is mono, and the podcast's stitched episodes are stereo.

| Audition effect | Parameter | Audition value | FFmpeg implementation | Fidelity |
|---|---|---|---|---|
| Tube-modeled Compressor | Threshold | −15 dB | `acompressor threshold=0.17783` (linear) | Same |
| | Ratio | 4:1 | `ratio=4` | Same |
| | Attack | 1 ms | `attack=1` | Same |
| | Release | 150 ms | `release=150` | Same |
| | Output Gain | 0 dB | `volume=0dB` | Same |
| | Tube modelling | Built in | None. `acompressor` is a clean VCA-style compressor: RMS detector, hard knee (`knee=1`). | Approx. |
| Match Loudness | Match To | ITU-R BS.1770-3 | Measured with `ebur128` (BS.1770 / EBU R128 gating) | Same |
| | Target Loudness | −18 LUFS | Static gain = −18 − measured loudness | Same |
| | Tolerance | 0.5 LU | The MP3 output is re-measured and redone (up to 3 tries) until within ±0.5 LU | Same |
| | Max True Peak | −1.5 dBTP | `alimiter limit=0.8414` at 4× oversampling (176.4 kHz), then resampled to 44.1 kHz | Approx. |
| | Look-Ahead | 12 ms | `attack=12` (alimiter's attack is its look-ahead window), `latency=1` compensates the delay | Same |
| | Release | 200 ms | `release=200` | Same |

### Processing order

1. Run the compressor and measure the integrated loudness of its output. On this file that was −22.9 LUFS, so the first gain was +4.9 dB.
2. Compressor, then gain, then oversampled limiter, then encode to MP3.
3. Measure the MP3's integrated loudness and true peak. If loudness is outside ±0.5 LU, adjust the gain by the miss. If true peak is above −1.5 dBTP, lower the limiter ceiling by the overshoot plus 0.1 dB. Then redo step 2.

The peak correction in step 3 exists because of MP3 encoding. Before encoding, the limiter's output measured −1.4 dBTP. After LAME it was −1.0 dBTP, about 0.4 dB of encoder overshoot. The second pass lowered the ceiling, and the final file measured −1.6 dBTP.

### Filter graph used (first pass on the test file)

```
acompressor=threshold=0.17783:ratio=4:attack=1:release=150:knee=1,
volume=0dB,
volume=4.90dB,
aresample=176400,
alimiter=limit=0.8414:attack=12:release=200:level=disabled:latency=1,
aresample=44100
→ libmp3lame -q:a 2
```

## Loudness and dynamics

Whole-file measurements. Loudness, loudness range (LRA) and true peak come from FFmpeg's `ebur128` filter. Sample peak, RMS and crest factor come from `astats`.

| File | Integrated (LUFS) | LRA (LU) | True peak (dBTP) | Sample peak (dBFS) | RMS (dBFS) | Crest factor |
|---|--:|--:|--:|--:|--:|--:|
| Source | −20.4 | 5.2 | +0.2 | 0.0 | −20.9 | 11.06 (20.9 dB) |
| Audition | −18.3 | 3.5 | −2.0 | −2.1 | −18.5 | 6.55 (16.3 dB) |
| Script | −18.0 | 3.6 | −1.6 | −1.7 | −18.3 | 6.78 (16.6 dB) |

The source is already at a 0 dBFS sample peak and +0.2 dBTP, so it was clipping or nearly clipping before mastering. Both masters bring the LRA from 5.2 LU down to 3.5–3.6 LU and cut the crest factor by about 4.5 dB. Audition landed 0.3 LU under target. That is within its tolerance, and it suggests Match Loudness reads loudness before limiting and doesn't correct for what the limiter takes off. The script re-measures after encoding, so it lands closer to −18.0.

## Gain applied over time

To compare the compressor behaviour directly, short-term loudness (3 s window, every 100 ms) was measured for all three files. For each window, the gain each master applied is master short-term loudness minus source short-term loudness. Windows below −45 LUFS in the source (silence) and the first 3 s were excluded, which left 30,308 of 30,344 windows.

| Gain applied (dB) | Median | 5th percentile | 95th percentile |
|---|--:|--:|--:|
| Audition | +2.4 | +1.3 | +3.9 |
| Script | +2.6 | +1.5 | +4.0 |
| Script − Audition | +0.2 | 0.0 | +0.4 |

Mean absolute difference between the two masters: 0.25 dB.

Median gain applied, grouped by the source's short-term loudness:

| Source loudness (LUFS) | Windows | Audition (dB) | Script (dB) |
|---|--:|--:|--:|
| −35 to −30 | 29 | 3.6 | 3.8 |
| −30 to −25 | 1,209 | 4.3 | 4.3 |
| −25 to −20 | 20,683 | 2.6 | 2.8 |
| −20 to −15 | 8,386 | 1.7 | 2.0 |

Quieter passages get more gain and louder passages less, which is the compressor at work. The two curves have the same shape, and the script gives the loudest band 0.3 dB more, so it reduces gain slightly less on loud passages.

## Null tests

Audition's master was polarity-inverted and summed with the script's master. Whatever is left is the difference between them. Residual levels are whole-file RMS. Null depth is the program RMS (Audition master, −18.5 dBFS) minus the residual RMS.

### Alignment

A 60 s excerpt (from 5:00) was nulled at different sample offsets. Offset 0 is clearly the deepest, so the files are already sample-aligned and no delay compensation is needed.

| Offset (samples) | 0 | ±1 | ±2 | ±5 | ±50 | ±576 / ±1105 |
|---|--:|--:|--:|--:|--:|--:|
| Residual RMS (dBFS) | **−39.9** | −31.4 | −26.7 | −23.6 | −16.0 | −15.8 / −16.2 |

### Results

| Comparison | Residual RMS (dBFS) | Null depth (dB) | What is left |
|---|--:|--:|---|
| Script MP3 vs Audition MP3 | −39.8 | 21.3 | Processing difference plus two independent MP3 encodes |
| Same, script level −0.2 dB | −40.2 | 21.7 | Removing the median level offset barely changes it |
| Script WAV vs Audition MP3 | −42.7 | 24.2 | Processing difference plus one MP3 encode (Audition's) |
| Reference: Audition MP3 vs itself re-encoded | −42.9 | 24.4 | One MP3 encode's noise only, no processing difference |

The MP3-vs-MP3 residual (−39.8) is about the sum of two encodes' noise (−42.9 dB twice ≈ −39.9 dBFS). Removing the script's encode brings it to −42.7, essentially the one-encode reference. So at these levels the null shows codec noise, and any difference between Audition's and FFmpeg's processing is quieter than that. A deeper null would need Audition's master exported as WAV, compared against the script's WAV output.

Limitation: the one-encode reference was made by re-encoding Audition's MP3 with FFmpeg's LAME at `-q:a 2`, not Audition's 192 kb/s CBR setting, and from audio that was already MP3. Treat it as an estimate of encode noise, not an exact floor.

## Known differences

- **Tube modelling.** Audition's Tube-modeled Compressor adds harmonic colouration and has its own detector and knee behaviour. FFmpeg has no equivalent. The script uses a clean RMS-detecting, hard-knee compressor with the same threshold, ratio and time constants. On this material the measured gain curve differs by at most 0.3 dB per loudness band.
- **True-peak limiting.** Audition's limiter is a true-peak limiter. The script imitates one by running FFmpeg's sample-peak `alimiter` at 4× oversampling, then checks the true peak of the final MP3 and tightens the ceiling if needed. Audition ended at −2.0 dBTP and the script at −1.6 dBTP.
- **Loudness accuracy.** Audition landed at −18.3 LUFS. The script re-measures its output and landed at −18.0. Both are within ±0.5 LU.
- **MP3 export.** Audition: 192 kb/s CBR. Script: LAME VBR `-q:a 2`, about 98 kb/s on mono speech. The file is 37 MB against 73 MB. If 192 kb/s CBR is a delivery requirement (for example for Libsyn), the script can be changed to `-b:a 192k`.
- **Source is lossy.** The unmastered input is itself a 192 kb/s MP3, so both masters are second-generation encodes. That affects both versions equally and cancels in the null.

## Questions for the Audition chain's author

1. Is 192 kb/s CBR MP3 the intended delivery format, or was it the export preset's default?
2. Do the Tube-modeled Compressor's other settings differ from defaults (for example input gain, tube drive, or detection mode)? Only threshold, ratio, attack, release and output gain were provided.
3. Is anything else in the chain or at export: dither, sample-rate conversion, a high-pass filter, or effects on individual clips before the mastering rack?
4. Could one master be exported from Audition as a 32-bit float WAV? That would allow a null test with no MP3 noise on either side.

## How to reproduce

From the repo root, with the virtual environment set up as in the [main README](../README.md#setup):

```
# Master one file (writes "<name> CLUFPL Python FFmpeg.mp3" next to it)
python wajc-mastering/wajc-mastering.py "wajc-mastering/test-files/09_25_2026 STTA.mp3"

# Stitch episodes with intro, outro and music; mastering is on by default
cd breaking-stereotypes-stitch
python breaking-stereotypes-stitch.py
python breaking-stereotypes-stitch.py --no-wajc-mastering
```

Mastering this 50-minute file took about 64 s. The null-test residuals are saved in `test-files/` as `09_25_2026 STTA Null Test.mp3` (MP3 vs MP3) and `09_25_2026 STTA Null Test (script as WAV).mp3`, for listening.

All measurements were made with FFmpeg 7.1: `ebur128` (BS.1770 / R128, true peak via 4× oversampling) and `astats`. Short-term gain was compared in 3 s windows every 100 ms. The null sum used `amix` with `normalize=0`.
