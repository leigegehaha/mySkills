const fs = require('fs');
const crypto = require('crypto');
const zlib = require('zlib');

const width = 512;
const height = 512;

const signature = Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);

function crc32(buf) {
  const table = new Int32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[i] = c;
  }
  let crc = -1;
  for (let i = 0; i < buf.length; i++) {
    crc = table[(crc ^ buf[i]) & 0xFF] ^ (crc >>> 8);
  }
  return Buffer.from([(crc ^ -1) >>> 24, (crc ^ -1) >>> 16, (crc ^ -1) >>> 8, (crc ^ -1) & 0xFF]);
}

function createChunk(type, data) {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const typeBuf = Buffer.from(type);
  const crc = crc32(Buffer.concat([typeBuf, data]));
  return Buffer.concat([length, typeBuf, data, crc]);
}

const ihdrData = Buffer.alloc(13);
ihdrData.writeUInt32BE(width, 0);
ihdrData.writeUInt32BE(height, 4);
ihdrData.writeUInt8(8, 8);
ihdrData.writeUInt8(2, 9);
ihdrData.writeUInt8(0, 10);
ihdrData.writeUInt8(0, 11);
ihdrData.writeUInt8(0, 12);
const ihdr = createChunk('IHDR', ihdrData);

let rawData = Buffer.alloc(0);
for (let y = 0; y < height; y++) {
  const row = Buffer.alloc(1 + width * 3);
  row[0] = 0;
  for (let x = 0; x < width; x++) {
    row[1 + x * 3] = 255;
    row[1 + x * 3 + 1] = 100;
    row[1 + x * 3 + 2] = 100;
  }
  rawData = Buffer.concat([rawData, row]);
}
const compressed = zlib.deflateSync(rawData);
const idat = createChunk('IDAT', compressed);
const iend = createChunk('IEND', Buffer.alloc(0));

const png = Buffer.concat([signature, ihdr, idat, iend]);
fs.writeFileSync('test-image.png', png);
console.log('测试图片已创建: test-image.png (512x512 红色)');
