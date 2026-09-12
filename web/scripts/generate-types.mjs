import { readFile, writeFile } from 'node:fs/promises';
import { compile } from 'json-schema-to-typescript';

const schemas = JSON.parse(await readFile(new URL('../src/generated/schemas.json', import.meta.url), 'utf8'));
const output = new URL('../src/generated/contracts.ts', import.meta.url);
const banner = '// Generated from flytrap/contracts.py JSON Schemas. Do not edit.\n';
// Each schema is self-contained; namespaces avoid collisions among shared definitions.
const parts = await Promise.all(Object.entries(schemas).map(async ([name, schema]) => {
  const source = await compile(schema, name, { bannerComment: '', additionalProperties: false, format: true });
  return `export namespace ${name}Contract {\n${source}\n}\nexport type ${name} = ${name}Contract.${name};\n`;
}));
const generated = banner + parts.join('\n');
if (process.argv.includes('--check')) {
  if (await readFile(output, 'utf8') !== generated) {
    throw new Error('Generated TypeScript contracts are stale; run npm run generate:types.');
  }
} else {
  await writeFile(output, generated);
}
