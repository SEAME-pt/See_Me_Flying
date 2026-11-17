#!/usr/bin/env python3
"""
A melody through ROS: notes become vertical-speed setpoints on
/fc/setpoint_velocity, fc_bridge (rc_override) turns them into the throttle
stick, INAV into motor speed, and motor speed is pitch. Armed, props off,
SA on. Run by sing.sh, which handles the bridge, the radio steps and the mic.

    sing.py calibrate --tmp DIR        throttle steps, for the pitch map
    sing.py play SONG --map PITCH.json --tmp DIR
    sing.py play SONG --map PITCH.json --dry-run    (no ROS needed)

It publishes idle (throttle 1000) from start to finish, so fc_bridge never
times out and centres the throttle (1500). It waits for DIR/go before the
sequence, writes DIR/done after it, and goes back to idle until stopped.
Times in DIR/steps.json and DIR/events.json are wall clock (the mic
recording on the host uses the same clock).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtttl  # noqa: E402

MAX_SPEED_Z = 0.3       # fc_bridge's max_speed_z: full throttle stick
IDLE = 1000             # throttle stick
MAX_THROTTLE = 1450     # never above, whatever the map says
CALIBRATION = [1050, 1100, 1150, 1200, 1250, 1300, 1350, 1400]
CALIBRATION_STEP_S = 2.0
RATE_HZ = 50.0


def z_for(throttle):
    """The setpoint fc_bridge maps to this throttle stick (1500 + 500 z / max)."""
    return (throttle - 1500) / 500.0 * MAX_SPEED_Z


def pitch_map(path):
    """(hz, throttle) points rising in pitch; steps whose pitch doesn't rise are dropped."""
    with open(path) as f:
        rows = json.load(f)
    points = []
    for r in sorted(rows, key=lambda r: r['value']):
        if not points or r['fundamental_hz'] > points[-1][0]:
            points.append((r['fundamental_hz'], r['value']))
    if len(points) < 2:
        sys.exit(f'{path}: fewer than two usable steps')
    return points


def throttle_for(hz, points):
    for (f0, v0), (f1, v1) in zip(points, points[1:]):
        if f0 <= hz <= f1:
            return round(v0 + (v1 - v0) * (hz - f0) / (f1 - f0))
    return None


def song_plan(args):
    """[(label, throttle, seconds)] for the song, shifted into the map."""
    with open(args.song) as f:
        notes = rtttl.parse(f.read())
    if args.part == 'first':
        notes = rtttl.first_phrase(notes)
    points = pitch_map(args.map)
    midis = [n.midi + args.nudge for n in notes if n.midi is not None]
    shifts = [args.octave] if args.octave is not None else range(2, -5, -1)
    hz = lambda m: 440.0 * 2 ** ((m - 69) / 12)  # noqa: E731
    k = next((k for k in shifts if all(throttle_for(hz(m + 12 * k), points) for m in midis)),
             None)
    if k is None:
        sys.exit(f'No octave shift fits the melody into {points[0][0]}-{points[-1][0]} Hz '
                 '(try --octave or --nudge, or calibrate wider)')
    plan = []
    for n in notes:
        if n.midi is None:
            plan.append(('pause', IDLE, n.seconds))
        else:
            m = n.midi + args.nudge + 12 * k
            plan.append((rtttl.name(m), min(throttle_for(hz(m), points), MAX_THROTTLE),
                         n.seconds))
    print(f'Octave shift {k:+d}, nudge {args.nudge:+d}, {len(plan)} notes, '
          f'{sum(s for _, _, s in plan):.1f} s')
    for label, throttle, seconds in plan:
        print(f'   {label:>5}  throttle {throttle}  {seconds:.2f} s')
    return plan


def calibration_plan():
    return [(f'step {t}', t, CALIBRATION_STEP_S) for t in CALIBRATION]


def perform(plan, tmp):
    import rclpy
    from geometry_msgs.msg import TwistStamped

    rclpy.init()
    node = rclpy.create_node('motor_music')
    pub = node.create_publisher(TwistStamped, '/fc/setpoint_velocity', 10)

    def send(throttle):
        msg = TwistStamped()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.z = z_for(throttle)
        pub.publish(msg)

    def hold(throttle, until):
        while time.time() < until:
            send(throttle)
            time.sleep(min(1.0 / RATE_HZ, max(until - time.time(), 0.0)))

    go, done = os.path.join(tmp, 'go'), os.path.join(tmp, 'done')
    try:
        while not os.path.exists(go):
            hold(IDLE, time.time() + 0.1)
        steps = []
        t = time.time() + 0.5
        hold(IDLE, t)
        for label, throttle, seconds in plan:
            steps.append({'label': label, 'value': throttle, 'start_epoch': round(t, 3),
                          'end_epoch': round(t + seconds, 3)})
            hold(throttle, t + seconds)   # hard change: straight to the note
            t += seconds
        with open(os.path.join(tmp, 'steps.json'), 'w') as f:
            json.dump(steps, f, indent=1)
            f.write('\n')
        open(done, 'w').close()
        while True:
            hold(IDLE, time.time() + 1.0)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('mode', choices=['calibrate', 'play'])
    p.add_argument('song', nargs='?')
    p.add_argument('--tmp', help='folder for go/done and the step times')
    p.add_argument('--map', help='pitch.json from a calibration')
    p.add_argument('--part', choices=['first', 'all'], default='first')
    p.add_argument('--octave', type=int, help='octave shift (default: highest that fits)')
    p.add_argument('--nudge', type=int, default=0, help='shift by semitones')
    p.add_argument('--dry-run', action='store_true', help='print the notes, publish nothing')
    args = p.parse_args()
    if args.mode == 'play' and not (args.song and args.map):
        p.error('play needs a song and --map')
    plan = calibration_plan() if args.mode == 'calibrate' else song_plan(args)
    if args.dry_run:
        return
    if not args.tmp:
        p.error('--tmp is needed to perform')
    perform(plan, args.tmp)


if __name__ == '__main__':
    main()
