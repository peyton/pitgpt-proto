import { describe, expect, it } from "vitest";
import { generateSchedule } from "./randomize";

describe("generateSchedule", () => {
  it("uses block_length_days instead of week count", () => {
    const schedule = generateSchedule(6, 14, 123);

    expect(schedule).toHaveLength(3);
    expect(schedule.map((item) => [item.start_day, item.end_day])).toEqual([
      [1, 14],
      [15, 28],
      [29, 42],
    ]);
  });

  it("balances each complete pair", () => {
    const schedule = generateSchedule(6, 7, 123);

    for (let pairIndex = 0; pairIndex < 3; pairIndex++) {
      const pair = schedule.filter((item) => item.pair_index === pairIndex);
      expect(new Set(pair.map((item) => item.condition))).toEqual(new Set(["A", "B"]));
    }
  });
});
