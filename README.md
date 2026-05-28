# Moover

![Moover grazing](assets/moover-grazing.gif)

Maintains local session activity.

Moover does not click, type, open apps, or change windows.

## Run It

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

To stop and remove the background runner, double-click:

```text
uninstall_moover.command
```

Logs are written to:

```text
/tmp/moover.log
/tmp/moover.err
```

## Check It Once

To run one 3-move batch and exit:

```sh
python3 moover.py --run-once --ignore-schedule
```

## Customize

Move every 3 minutes, which is the default:

```sh
python3 moover.py --interval 180
```

Move every minute:

```sh
python3 moover.py --interval 60
```

Move 5 times every interval:

```sh
python3 moover.py --moves 5
```

Move farther each time:

```sh
python3 moover.py --distance 140
```

Adjust the active window:

```sh
python3 moover.py --work-start 09:30 --work-end 17:00
```

## macOS Permissions

If macOS blocks cursor movement, open:

```text
System Settings -> Privacy & Security -> Accessibility
```

Then allow the terminal app you are using, such as Terminal, iTerm, or Codex.
