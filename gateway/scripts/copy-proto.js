const fs = require('fs');
const path = require('path');

const src = path.join(__dirname, '..', 'src', 'proto');
const dst = path.join(__dirname, '..', 'dist', 'proto');

fs.mkdirSync(dst, { recursive: true });
for (const file of fs.readdirSync(src)) {
  if (file.endsWith('.proto')) {
    fs.copyFileSync(path.join(src, file), path.join(dst, file));
  }
}
console.log('Copied .proto files to dist/proto');