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
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, time as clock_time


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
        mouse_moved = 5
        left_mouse_button = 0
        event = self.core_graphics.CGEventCreateMouseEvent(
            None, mouse_moved, point, left_mouse_button
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
    angle = step * (math.pi / 2)

    if screen.width <= 0 or screen.height <= 0:
        return CGPoint(
            origin.x + (math.cos(angle) * distance),
            origin.y + (math.sin(angle) * distance),
        )

    center_x = screen.x + (screen.width / 2)
    center_y = screen.y + (screen.height / 2)

    margin = 8
    return CGPoint(
        clamp(
            center_x + (math.cos(angle) * distance),
            screen.x + margin,
            screen.x + screen.width - margin,
        ),
        clamp(
            center_y + (math.sin(angle) * distance),
            screen.y + margin,
            screen.y + screen.height - margin,
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Moover moves the macOS cursor every few minutes without clicking."
    )
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
        default=3,
        help="Number of cursor moves to make every interval. Default: 3.",
    )
    parser.add_argument(
        "--move-delay",
        type=float,
        default=0.6,
        help="Seconds to wait between moves in the same interval. Default: 0.6.",
    )
    parser.add_argument(
        "--work-start",
        default="09:00",
        help="Earliest local time to run, in HH:MM format. Default: 09:00.",
    )
    parser.add_argument(
        "--work-end",
        default="17:30",
        help="Latest local time to run, in HH:MM format. Default: 17:30.",
    )
    parser.add_argument(
        "--ignore-schedule",
        action="store_true",
        help="Run regardless of the configured work hours.",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run one movement batch and exit. Useful for checking macOS permissions.",
    )
    return parser.parse_args()


def parse_clock_time(value: str) -> clock_time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"Invalid time {value!r}. Use HH:MM, for example 09:00."
        ) from error


def seconds_until_today(target: clock_time) -> int:
    now = datetime.now()
    target_datetime = now.replace(
        hour=target.hour,
        minute=target.minute,
        second=0,
        microsecond=0,
    )
    return max(0, int((target_datetime - now).total_seconds()))


def is_inside_work_window(start: clock_time, end: clock_time) -> bool:
    now = datetime.now().time()
    return start <= now < end


def should_stop_for_schedule(args: argparse.Namespace) -> bool:
    return not args.ignore_schedule and not is_inside_work_window(
        args.work_start_time, args.work_end_time
    )


def main() -> int:
    args = parse_args()
    args.work_start_time = parse_clock_time(args.work_start)
    args.work_end_time = parse_clock_time(args.work_end)
    if args.work_start_time >= args.work_end_time:
        print("Error: --work-start must be earlier than --work-end.", file=sys.stderr)
        return 1

    if should_stop_for_schedule(args):
        print(
            f"Outside work hours ({args.work_start}-{args.work_end}). "
            "Moover will not run.",
            flush=True,
        )
        return 0

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
        f"distance {args.distance}px, work hours {args.work_start}-{args.work_end}. "
        "Press Ctrl+C to stop.",
        flush=True,
    )

    step = 0
    while running:
        if should_stop_for_schedule(args):
            print(f"Reached {args.work_end}. Moover stopping.", flush=True)
            break

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
                time.sleep(args.move_delay)

        if args.run_once:
            break

        seconds_to_sleep = args.interval
        if not args.ignore_schedule:
            seconds_to_sleep = min(seconds_to_sleep, seconds_until_today(args.work_end_time))

        for _ in range(seconds_to_sleep):
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
