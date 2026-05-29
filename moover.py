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
from typing import Callable


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


@dataclass(frozen=True)
class Screen:
    x: float
    y: float
    width: int
    height: int


class MacCursor:
    MOUSE_MOVED = 5

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


def circular_position(center: CGPoint, screen: Screen, radius: int, angle: float) -> CGPoint:
    wobble = random.uniform(radius * -0.08, radius * 0.08)
    x_radius = max(4, radius + wobble)
    y_radius = max(4, (radius * 0.72) + (wobble * 0.6))

    x = center.x + (math.cos(angle) * x_radius)
    y = center.y + (math.sin(angle) * y_radius)

    if screen.width <= 0 or screen.height <= 0:
        return CGPoint(x, y)

    margin = max(8, radius + 8)
    return CGPoint(
        clamp(x, screen.x + margin, screen.x + screen.width - margin),
        clamp(y, screen.y + margin, screen.y + screen.height - margin),
    )


def run_circular_motion(
    cursor: MacCursor,
    screen: Screen,
    duration: float,
    radius: int,
    step_delay: float,
    keep_running: Callable[[], bool],
) -> int:
    center = cursor.position()
    start = time.monotonic()
    angle = random.uniform(0, math.tau)
    direction = random.choice([-1, 1])
    rotations_per_second = random.uniform(0.42, 0.62)
    moves = 0

    while keep_running():
        elapsed = time.monotonic() - start
        if elapsed >= duration:
            break

        angle += direction * math.tau * rotations_per_second * step_delay
        angle += random.uniform(-0.025, 0.025)
        target = circular_position(center, screen, radius, angle)
        cursor.move_to(target)
        moves += 1
        time.sleep(step_delay)

    return moves


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
        default=240,
        help="Seconds between cursor moves. Default: 240 seconds, or 4 minutes.",
    )
    parser.add_argument(
        "--distance",
        type=int,
        default=80,
        help="Circular movement radius in pixels. Default: 80.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=20,
        help="Seconds to move continuously each interval. Default: 20.",
    )
    parser.add_argument(
        "--step-delay",
        type=float,
        default=0.035,
        help="Seconds between tiny cursor updates. Default: 0.035.",
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
    if args.duration <= 0:
        print("Error: --duration must be greater than zero.", file=sys.stderr)
        return 1
    if args.step_delay <= 0:
        print("Error: --step-delay must be greater than zero.", file=sys.stderr)
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
        f"Moover running: {args.duration:g}s circular movement every "
        f"{args.interval}s, radius {args.distance}px. "
        "Press Ctrl+C to stop.",
        flush=True,
    )

    while running:
        if not args.ignore_lock_state and is_screen_locked():
            print("Session locked. Moover waiting.", flush=True)
            for _ in range(args.interval):
                if not running:
                    break
                time.sleep(1)
            continue

        moves = run_circular_motion(
            cursor=cursor,
            screen=screen,
            duration=args.duration,
            radius=args.distance,
            step_delay=args.step_delay,
            keep_running=lambda: running,
        )
        print(f"Completed circular movement with {moves} updates.", flush=True)

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
