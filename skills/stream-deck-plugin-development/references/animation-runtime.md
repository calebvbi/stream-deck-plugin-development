# Animation Runtime

Stream Deck receives snapshots, not an animation primitive. Treat SVG, GIF, PNG,
and artwork layers as content formats; verify which component generates frames,
which clock schedules them, and which SDK call delivers them.

## Runtime checklist

1. Prefer cached content plus numeric transforms over prebuilt frame caches. Resolve
   artwork and reusable SVG fragments outside the frame loop; for carousels, retain a
   small stable layer set and update positions, opacity, scale, or rotation at runtime.
2. Give every transition a finite frame/time budget and exactly one owner per action
   ID. Starts are idempotent. New semantic input cancels or supersedes the old owner.
3. Register periodic motion only when the active renderer has a pixel-changing track.
   Semantic status alone is not proof that a key or dial consumes the current tick.
4. Cap device writes. Deduplicate identical bytes, coalesce pending work to the newest
   frame, and drop disposable motion frames while an earlier write remains in flight.
   Resolution of `setImage` or `setFeedback` proves host acceptance, not physical LCD
   application.
5. Cancel work on semantic-state change, motion-preference change, `onWillDisappear`,
   profile/page removal, action replacement, and plugin disposal. Tests must assert
   that cancelled owners produce zero late writes.
6. Do not busy-poll with `setImmediate` between frame deadlines. Use one shared clock
   or deadline-based timers appropriate to Node.js; `requestAnimationFrame` is not
   available by default in the plugin runtime.
7. Make idle quiescence observable. With no active track there must be no render loop,
   SDK write, allocation loop, orphan timer, or periodic retry after a rejected render.
   Fail motion closed, then let a later successful semantic delivery reactivate it.
8. Test Full, Reduced, and Off modes; overlapping transitions; slow/rejected host
   writes; backpressure; appearance/disappearance; terminal one-shot expiry; long soak;
   write counts; CPU; and bounded memory.

## Useful and misleading reference patterns

- Useful: cached nearby artwork in a retained layer ring; runtime transforms update a
  few stable layers instead of rebuilding or precomputing every frame.
- Useful: a 10 Hz ceiling, byte-level image deduplication, and in-flight motion-frame
  dropping when that cadence matches the product's approved motion budget.
- Corrective: keep a renderer-capability table and byte-identity test in agreement so
  a future pixel-changing track cannot be added without updating scheduler eligibility.
- Avoid: a tight `setImmediate` loop that repeatedly checks elapsed time before a frame
  is due.
- Avoid: one timer field on a singleton action class. Several visible instances share
  that singleton, so lifecycle state must be keyed by `action.id`.

## Ownership skeleton

```typescript
type MotionOwner = {
    active: boolean;
    inFlight: boolean;
    timer?: NodeJS.Timeout;
};

const owners = new Map<string, MotionOwner>();

function cancelMotion(actionId: string): void {
    const owner = owners.get(actionId);
    if (!owner) return;
    owner.active = false;
    if (owner.timer) clearTimeout(owner.timer);
    owners.delete(actionId);
}
```

Before every delayed write, verify that the action ID still maps to the same owner.
This prevents a departed action's timer from repainting a replacement that reused its
context or coordinate.
