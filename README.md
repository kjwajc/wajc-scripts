# WAJC audio scripts

Python scripts for WAJC audio production. They use ffmpeg for the audio work and run on Windows, macOS and Linux.

| Script | What it does |
|---|---|
| [breaking-stereotypes-stitch](breaking-stereotypes-stitch/) | Builds Breaking Stereotypes episodes: intro + show + outro with background music, then masters them. |
| [wajc-mastering](wajc-mastering/) | WAJC mastering (compressor, then match loudness to −18 LUFS), rebuilt from the Adobe Audition chain. Works on any audio file. |

Each script has its own folder, with a README and a `requirements.txt`.

## Setup

### 1. Install Python

Python 3.10 or newer. Version in use: Python 3.14.8.

- **Windows:** download the installer from [python.org/downloads](https://www.python.org/downloads/). On the first screen, tick **"Add python.exe to PATH"**, then click Install Now.
- **macOS:** download the installer from [python.org/downloads](https://www.python.org/downloads/), or run `brew install python`.
- **Linux:** use your package manager, for example `sudo apt install python3 python3-venv python3-pip`.

Check it worked by opening a new terminal and running:

```
python --version
```

On macOS and Linux the command may be `python3` instead of `python`. Use whichever one works in all the commands below.

### 2. Create a virtual environment

This keeps the scripts' packages separate from the rest of your computer. From the repo's root folder:

```
python -m venv .venv
```

Then activate it:

- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **macOS / Linux:** `source .venv/bin/activate`

Activate it again each time you open a new terminal. One environment at the root serves all the scripts.

### 3. Install the packages, including ffmpeg

Install the requirements for each script you'll use, for example:

```
pip install -r breaking-stereotypes-stitch/requirements.txt
pip install -r wajc-mastering/requirements.txt
```

This installs `imageio-ffmpeg`, which includes a ready-made ffmpeg for your operating system. The scripts find it on their own, so ffmpeg doesn't need to be on your PATH. To use a different ffmpeg, set the `IMAGEIO_FFMPEG_EXE` environment variable to the full path of that ffmpeg program.

## Audio files

Audio is never committed. `.gitignore` excludes the audio folders inside each script's folder and all common audio file types, so recordings stay on your computer. See each script's README for the folders it expects.
