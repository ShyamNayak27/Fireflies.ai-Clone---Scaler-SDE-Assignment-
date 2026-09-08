/**
 * Generic lower-bound binary search: the index of the last element whose key
 * is <= target (or -1 if every element's key is greater than target).
 *
 * Two call sites in this app need exactly this:
 *  - transcript sync: given the player's current time, find the segment whose
 *    start_ms is the latest one at or before it (segments are sorted by idx /
 *    start_ms, see backend/app/repositories/meetings.py)
 *  - the virtual list: given a scroll offset, find the row whose cumulative
 *    top offset is the latest one at or before it
 *
 * Both are O(log n) instead of the O(n) linear scan a naive
 * `segments.find(s => ms >= s.start_ms && ms < s.end_ms)` would do on every
 * player tick — for a long meeting (an hour at normal talk pace is roughly
 * 600-900 segments) re-scanning from the top dozens of times a second is
 * wasted work that a sorted array doesn't need.
 */
export function lowerBoundIndex<T>(items: readonly T[], target: number, key: (item: T) => number): number {
  let lo = 0;
  let hi = items.length - 1;
  let result = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >>> 1;
    if (key(items[mid]) <= target) {
      result = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return result;
}
