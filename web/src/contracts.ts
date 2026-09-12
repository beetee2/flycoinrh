import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import schemas from './generated/schemas.json';
import type { Capabilities } from './generated/contracts';

export type ContractName = keyof typeof schemas;
const ajv = new Ajv2020({ allErrors: true, strict: true, strictNumbers: true });
addFormats(ajv);
const validators = Object.fromEntries(
  Object.entries(schemas).map(([name, schema]) => [name, ajv.compile(schema)]),
);

export function validateContract(name: ContractName, value: unknown): boolean {
  return validators[name](value) as boolean;
}

export function parseCapabilities(value: unknown): Capabilities {
  if (!validateContract('Capabilities', value)) {
    throw new Error('The service returned an invalid capabilities response.');
  }
  return value as Capabilities;
}
