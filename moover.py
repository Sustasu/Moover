#!/usr/bin/env python3
"""
Move the macOS cursor at a fixed interval without clicking.

This uses CoreGraphics directly through ctypes, so it does not need any
third-party Python packages.
"""

from __future__ import annotations

import argparse
import ctypes
import math
import random
import signal
import subprocess
import sys
import time
from dataclasses import dataclass


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


@dataclass(frozen=True)
class Screen:
    x: float
    y: float
    width: int
    height: int


class MacCursor:
    def __init__(self) -> None:
        self.core_graphics = ctypes.CDLL(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
        )

        self.core_graphics.CGMainDisplayID.restype = ctypes.c_uint32
        self.core_graphics.CGDisplayPixelsWide.argtypes = [ctypes.c_uint32]
        self.core_graphics.CGDisplayPixelsWide.restype = ctypes.c_size_t
        self.core_graphics.CGDisplayPixelsHigh.argtypes = [ctypes.c_uint32]
        self.core_graphics.CGDisplayPixelsHigh.restype = ctypes.c_size_t

        self.core_graphics.CGEventCreate.argtypes = [ctypes.c_void_p]
        self.core_graphics.CGEventCreate.restype = ctypes.c_void_p
        self.core_graphics.CGEventGetLocation.argtypes = [ctypes.c_void_p]
        self.core_graphics.CGEventGetLocation.restype = CGPoint
        self.core_graphics.CFRelease.argtypes = [ctypes.c_void_p]

        self.core_graphics.CGWarpMouseCursorPosition.argtypes = [CGPoint]
        self.core_graphics.CGWarpMouseCursorPosition.restype = ctypes.c_int
        self.core_graphics.CGEventCreateMouseEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            CGPoint,
            ctypes.c_uint32,
        ]
        self.core_graphics.CGEventCreateMouseEvent.restype = ctypes.c_void_p
        self.core_graphics.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]

    def screen(self) -> Screen:
        display_id = self.core_graphics.CGMainDisplayID()
        return Screen(
            x=0,
            y=0,
            width=int(self.core_graphics.CGDisplayPixelsWide(display_id)),
            height=int(self.core_graphics.CGDisplayPixelsHigh(display_id)),
        )

    def position(self) -> CGPoint:
        event = self.core_graphics.CGEventCreate(None)
        if not event:
            raise RuntimeError("Could not read the current cursor position.")

        try:
            return self.core_graphics.CGEventGetLocation(event)
        finally:
            self.core_graphics.CFRelease(event)

    def move_to(self, point: CGPoint) -> None:
        result = self.core_graphics.CGWarpMouseCursorPosition(point)
        if result == 0:
            return

        # Some macOS environments refuse direct cursor warping but still allow
        # posting a normal mouse-moved event.
        event = self.core_graphics.CGEventCreateMouseEvent(
            None, self.MOUSE_MOVED, point, 0
        )
        if not event:
            raise RuntimeError(
                "Could not create a mouse movement event. Check Accessibility "
                "permission for your terminal app."
            )

        try:
            hid_event_tap = 0
            self.core_graphics.CGEventPost(hid_event_tap, event)
        finally:
            self.core_graphics.CFRelease(event)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def next_position(origin: CGPoint, screen: Screen, distance: int, step: int) -> CGPoint:
    angle = (step * (math.pi / 2)) + random.uniform(-0.45, 0.45)
    move_distance = random.uniform(distance * 0.55, distance * 1.35)

    if screen.width <= 0 or screen.height <= 0:
        return CGPoint(
            origin.x + (math.cos(angle) * move_distance),
            origin.y + (math.sin(angle) * move_distance),
        )

    center_x = screen.x + (screen.width / 2)
    center_y = screen.y + (screen.height / 2)

    margin = 8
    return CGPoint(
        clamp(
            center_x + (math.cos(angle) * move_distance),
            screen.x + margin,
            screen.x + screen.width - margin,
        ),
        clamp(
            center_y + (math.sin(angle) * move_distance),
            screen.y + margin,
            screen.y + screen.height - margin,
        ),
    )


def is_screen_locked() -> bool:
    try:
        result = subprocess.run(
            ["/usr/sbin/ioreg", "-n", "Root", "-d1"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False

    return (
        '"CGSSessionScreenIsLocked" = Yes' in result.stdout
        or '"IOConsoleLocked" = Yes' in result.stdout
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Maintains local session activity.")
    parser.add_argument(
        "--interval",
        type=int,
        default=180,
        help="Seconds between cursor moves. Default: 180 seconds, or 3 minutes.",
    )
    parser.add_argument(
        "--distance",
        type=int,
        default=80,
        help="Pixels to move each time. Default: 80.",
    )
    parser.add_argument(
        "--moves",
        type=int,
        default=10,
        help="Number of cursor moves to make every interval. Default: 10.",
    )
    parser.add_argument(
        "--min-move-delay",
        type=float,
        default=0.6,
        help="Minimum seconds between moves in the same interval. Default: 0.6.",
    )
    parser.add_argument(
        "--max-move-delay",
        type=float,
        default=2.4,
        help="Maximum seconds between moves in the same interval. Default: 2.4.",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run one movement batch and exit. Useful for checking macOS permissions.",
    )
    parser.add_argument(
        "--ignore-lock-state",
        action="store_true",
        help="Run even when the macOS session appears locked.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.min_move_delay < 0 or args.max_move_delay < 0:
        print("Error: move delays must be zero or greater.", file=sys.stderr)
        return 1
    if args.min_move_delay > args.max_move_delay:
        print("Error: --min-move-delay must be no greater than --max-move-delay.", file=sys.stderr)
        return 1

    cursor = MacCursor()
    screen = cursor.screen()
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    print(
        f"Moover running: {args.moves} moves every {args.interval}s, "
        f"distance {args.distance}px. "
        "Press Ctrl+C to stop.",
        flush=True,
    )

    step = 0
    while running:
        if not args.ignore_lock_state and is_screen_locked():
            print("Session locked. Moover waiting.", flush=True)
            for _ in range(args.interval):
                if not running:
                    break
                time.sleep(1)
            continue

        for move_number in range(1, args.moves + 1):
            if not running:
                break

            current = cursor.position()
            target = next_position(current, screen, args.distance, step)
            cursor.move_to(target)
            print(
                f"Move {move_number}/{args.moves}: "
                f"({target.x:.0f}, {target.y:.0f})",
                flush=True,
            )
            step += 1

            if move_number < args.moves:
                time.sleep(random.uniform(args.min_move_delay, args.max_move_delay))

        if args.run_once:
            break

        for _ in range(args.interval):
            if not running:
                break
            time.sleep(1)

    print("Moover stopped.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nMoover stopped.", flush=True)
        raise SystemExit(0)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
