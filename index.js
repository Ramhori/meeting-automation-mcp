#!/usr/bin/env node
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const serverPath = join(__dirname, 'server.py');

const python = spawn('python', [serverPath], {
  stdio: 'inherit'
});

python.on('close', (code) => {
  process.exit(code);
});
