# Recovered Tapico degree-show prototype

Recovered on 2026-09-12 from the Raspberry Pi Zero 2 W application's `/home/june/tapico` directory. The separate original local recovery contains 199 files verified against source SHA256 hashes. It remains unchanged. This public snapshot preserves 83 selected original files byte-for-byte; `SHA256SUMS` records their hashes. This is an application source backup, not a full SD-card image or a tested fresh installation.

## Provenance and attribution

Tapico is Anto's 2024 university degree-show prototype, adapted from [Zerowriter](https://github.com/zerowriter/zerowriter1), including jacobsmith's contributions and Waveshare display drivers. Anto selected the components, designed the mechanical housing and assembly, and adapted the software for the show with ChatGPT and VS Code. The code is not all original Tapico work. Original README, source notices, drivers, and historical setup instructions are preserved inside `tapico/`; their descriptions may differ from the final prototype. Existing June repository files and history are untouched.

The recovered implementation is `tapico/e-Paper/RaspberryPi_JetsonNano/python/examples/zerowriter.py` (source modification date: 2024-06-10). Entry point: `main.py` in the same directory. Code inspection confirms typing, backspace, newline and Ctrl-Backspace; an Escape mock file menu; four information screens after 60 seconds idle, 15 seconds each; Space advances the screensaver, another key returns to writing; Ctrl-M opens Wi-Fi/About/Files/Power Off. These are code observations, not a fresh hardware acceptance test.

## Public-backup exclusions

- Pi `.git` metadata and history: kept only in the original local recovery; the existing June history is preserved by this additive commit.
- Saved writing, autosave, archive and unused text drafts: only the four presentation assets `data/info1.txt` through `data/info4.txt` are included.
- `FSM_Round.png`: the mock file-menu screenshot contains personal-looking journal filenames. Escape's mock image needs this local-only asset restored before use.
- `zwconfig.json`: mutable credential file, excluded even though its recovered values are only `none` placeholders. Python bytecode, macOS metadata and generated build/distribution/egg-info output are also excluded. Python driver source, native driver libraries and fonts remain.

The local recovery's `BACKUP.md` and full manifest are not uploaded because they describe the private recovery, including excluded files. This folder's manifest covers only published original files. The new `.gitignore` and this README are backup metadata, not recovered source.

## Restore preparation

Work from a copy of `tapico/`. Historical platform setup is in `tapico/setup_2.2`; it is preserved as documentation, not a claim that old dependency installation commands still work unchanged. No dependencies were upgraded and no application code was changed for this backup.

From `tapico/e-Paper/RaspberryPi_JetsonNano/python/examples/`, create a local `zwconfig.json` containing `{"username": "none", "password": "none"}`. Restore `FSM_Round.png` from the private original recovery if the original Escape mock menu is needed. Optional original writing/cache can also be restored locally; keep these files private. The preserved examples `.gitignore` excludes `data/*`; presentation assets are intentionally tracked in this snapshot. Credentials and the mock image are ignored by the added root `.gitignore`.

On a configured Pi, the historical entry command is `sudo python3 main.py` from that examples directory. This backup task did not connect to, restart, or alter the Pi. It does not include system packages, OS configuration, or autostart files outside the recovered application directory.

## Verification

From this folder, run `shasum -a 256 -c SHA256SUMS` to verify the 83 original published files. Python sources were syntax-checked without importing or running hardware/network code. No claim of fresh-device runtime testing is made.
