import { describe, expect, it } from 'vitest';
import { colorFor, hexToRgba, indexClass, legendItems, minuteBreaks, minutesClass, NULL_COLOR, PALETTE } from './colors';

describe('minute classes', () => {
  it('derives breaks from the threshold', () => {
    expect(minuteBreaks(15)).toEqual([5, 10, 15, 30]);
  });

  it('classifies minutes, with breaks belonging to the better class', () => {
    expect(minutesClass(0, 15)).toBe(0);
    expect(minutesClass(5, 15)).toBe(0);
    expect(minutesClass(5.1, 15)).toBe(1);
    expect(minutesClass(15, 15)).toBe(2); // exactly 15 min is still "within 15 minutes"
    expect(minutesClass(15.01, 15)).toBe(3);
    expect(minutesClass(45, 15)).toBe(4);
    expect(minutesClass(null, 15)).toBe(-1);
  });
});

describe('index classes', () => {
  it('maps 1 to the best class and 0 to the worst', () => {
    expect(indexClass(1)).toBe(0);
    expect(indexClass(0.85)).toBe(0);
    expect(indexClass(0.5)).toBe(2);
    expect(indexClass(0)).toBe(4);
    expect(indexClass(1.2)).toBe(0); // clamped
    expect(indexClass(null)).toBe(-1);
  });
});

describe('colorFor', () => {
  it('returns palette colours and grey for null', () => {
    expect(colorFor(3, 'minutes', 15, 255)).toEqual(hexToRgba(PALETTE[0] ?? '', 255));
    expect(colorFor(60, 'minutes', 15, 255)).toEqual(hexToRgba(PALETTE[4] ?? '', 255));
    expect(colorFor(null, 'minutes', 15, 200).slice(0, 3)).toEqual(hexToRgba(NULL_COLOR).slice(0, 3));
  });

  it('parses hex colours', () => {
    expect(hexToRgba('#ff8000', 10)).toEqual([255, 128, 0, 10]);
  });
});

describe('legendItems', () => {
  it('lists 5 classes plus "no data" and shows the threshold as a class edge', () => {
    const items = legendItems('minutes', 15);
    expect(items).toHaveLength(6);
    expect(items[2]?.range).toEqual([10, 15]);
    expect(items[4]?.range).toEqual([30, null]);
    expect(items[5]?.range).toBeNull();
  });

  it('covers [0, 1] for the index', () => {
    const items = legendItems('index', 15);
    expect(items[0]?.range).toEqual([0.8, 1]);
    expect(items[4]?.range).toEqual([0, 0.2]);
  });
});
