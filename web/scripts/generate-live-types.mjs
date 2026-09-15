import { readFile, writeFile } from 'node:fs/promises';
import { compile } from 'json-schema-to-typescript';

const schemas = JSON.parse(await readFile(new URL('../src/live/generated/schemas.json', import.meta.url), 'utf8'));
const output = new URL('../src/live/generated/contracts.ts', import.meta.url);
const parts = await Promise.all(Object.entries(schemas).map(async ([name, schema]) => {
  const source = await compile(schema, name, { bannerComment: '', additionalProperties: false, format: true });
  return `export namespace ${name}Contract {\n${source}\n}\nexport type ${name} = ${name}Contract.${name};\n`;
}));
const generated = '// Generated from flytrap/live/contracts.py JSON Schemas. Do not edit.\n' + parts.join('\n');
if (process.argv.includes('--check')) {
  if (await readFile(output, 'utf8') !== generated) {
    throw new Error('Live TypeScript contracts are stale; run node scripts/generate-live-types.mjs.');
  }
} else {
  await writeFile(output, generated);
}
