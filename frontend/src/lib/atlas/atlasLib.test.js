import { parseTokenList, normalizeStep } from './normalizeStep';
import { aggregateHostFlows, hostFromUrl } from './aggregateSankey';

describe('parseTokenList', () => {
  test('parses JSON array string', () => {
    expect(parseTokenList('["a","b"]')).toEqual(['a', 'b']);
  });

  test('parses python-ish single-quoted list', () => {
    expect(parseTokenList("['foo', 'bar']")).toEqual(['foo', 'bar']);
  });

  test('splits comma list', () => {
    expect(parseTokenList('x, y, z')).toEqual(['x', 'y', 'z']);
  });
});

describe('normalizeStep', () => {
  test('maps storage-like row', () => {
    const r = normalizeStep({
      number: '3',
      url: 'https://ex.com/p',
      src: 'https://a.com',
      status_code: '200',
      timestamp: '2024-01-01T00:00:00Z',
      text_length: '10',
      text: 'hello world',
      error: '',
      words: '["w"]',
      tags: '',
      hrases: '',
    });
    expect(r._n).toBe(3);
    expect(r.status_num).toBe(200);
    expect(r.words).toEqual(['w']);
    expect(Number.isFinite(r._ts)).toBe(true);
  });
});

describe('aggregateHostFlows', () => {
  test('aggregates transitions', () => {
    const steps = [
      { url: 'https://b.com/x', src: 'https://a.com/' },
      { url: 'https://b.com/y', src: 'https://a.com/' },
      { url: 'https://c.com/', src: '' },
    ];
    const { nodes, links } = aggregateHostFlows(steps, { maxNodes: 20 });
    expect(nodes.length).toBeGreaterThan(0);
    expect(links.length).toBeGreaterThan(0);
    const sum = links.reduce((s, l) => s + l.value, 0);
    expect(sum).toBe(3);
  });
});

describe('hostFromUrl', () => {
  test('extracts hostname', () => {
    expect(hostFromUrl('https://Example.COM/path')).toBe('example.com');
  });
});
