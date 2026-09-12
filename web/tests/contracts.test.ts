import { describe, expect, it } from 'vitest';
import cases from '../../tests/fixtures/contracts/cases.json';
import schemas from '../src/generated/schemas.json';
import { validateContract, type ContractName } from '../src/contracts';

describe('Pydantic JSON Schema parity (shared Python / TypeScript fixtures)', () => {
  it('contains positive and negative cases for every exported contract', () => {
    expect(Object.keys(schemas)).toHaveLength(11);
    for (const name of Object.keys(schemas)) {
      expect(cases.some((item) => item.contract === name && item.valid)).toBe(true);
      expect(cases.some((item) => item.contract === name && !item.valid)).toBe(true);
    }
  });
  it.each(cases)('$contract / $name', (item) => {
    expect(validateContract(item.contract as ContractName, item.payload)).toBe(item.valid);
  });
  it.each([NaN, Infinity, -Infinity])('rejects nonfinite JavaScript numbers %s', (number) => {
    function paths(value: unknown, prefix: (string | number)[] = []): (string | number)[][] {
      if (typeof value === 'number') return [prefix];
      if (value !== null && typeof value === 'object') {
        return Object.entries(value).flatMap(([key, child]) => paths(child, [...prefix, key]));
      }
      return [];
    }
    for (const source of cases.filter((item) => item.valid)) {
      for (const path of paths(source.payload)) {
        const payload = structuredClone(source.payload) as Record<string, unknown>;
        let target = payload;
        for (const key of path.slice(0, -1)) target = target[key] as Record<string, unknown>;
        target[path.at(-1)!] = number;
        expect(validateContract(source.contract as ContractName, payload), `${source.contract}/${path.join('.')}`).toBe(false);
      }
    }
  });
});
