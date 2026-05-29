# Moover

![Moover grazing](assets/moover-grazing.gif)

Maintains local session activity.

Moover does not click, type, open apps, or change windows.

Moover skips movement while the macOS session is locked and resumes after unlock.

## Run It

If macOS says the files are from an unidentified developer, run this once from the folder:

```sh
./trust_moover.command
```

This clears the downloaded-file quarantine flag for this local Moover folder.

From this folder:

```sh
python3 moover.py
```

Or double-click:

```text
start_moover.command
```

Stop it with `Ctrl+C` in the terminal window.

## Run It Without Terminal Open

Double-click:

```text
install_moover.command
```

This installs a macOS LaunchAgent that starts Moover in the background.

The installer copies Moover to:

```text
~/Library/Application Support/Moover/moover.py
```

That keeps the background runner out of the macOS-protected Documents folder.

The LaunchAgent is generated during install, so it uses the current Mac user's home folder automatically.

To stop and remove the background runner, double-click:

```text
uninstall_moover.command
```

This removes the installed LaunchAgent, the copied background script, and Moover log files. It does not delete this source folder.

Logs are written to:

```text
/tmp/moover.log
/tmp/moover.err
```

## Check It Once

To run one movement batch and exit:

```sh
python3 moover.py --run-once
```

## Customize

Move every 4 minutes, which is the default:

```sh
python3 moover.py --interval 240
```

Move every minute:

```sh
python3 moover.py --interval 60
```

Move continuously for 1 minute every interval, which is the default:

```sh
python3 moover.py --duration 60
```

Use smoother or lighter movement updates:

```sh
python3 moover.py --step-delay 0.03
```

Use a wider circular path:

```sh
python3 moover.py --distance 140
```

Run even if the session appears locked:

```sh
python3 moover.py --ignore-lock-state
```

## macOS Permissions

If macOS blocks cursor movement, open:

```text
System Settings -> Privacy & Security -> Accessibility
```

Then allow the terminal app you are using, such as Terminal, iTerm, or Codex.
