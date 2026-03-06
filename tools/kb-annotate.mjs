#!/usr/bin/env node
/**
 * KB Annotation Tool
 *
 * Overlays SVG annotations (rectangles, circles, arrows) onto screenshots
 * for Knowledge Base documentation. Uses sharp for high-quality compositing.
 *
 * Usage:
 *   node tools/kb-annotate.mjs <input.png> <output.png> [annotations...]
 *
 * Annotation format:
 *   rect:x,y,w,h          — Rectangle highlight
 *   circle:cx,cy,r        — Circle highlight
 *   arrow:x1,y1,x2,y2    — Arrow from (x1,y1) to (x2,y2)
 *
 * Example:
 *   node tools/kb-annotate.mjs \
 *     screenshots/contacts-list.png \
 *     annotated/contacts-add-btn.png \
 *     rect:1200,80,180,40 \
 *     circle:1290,100,24 \
 *     arrow:1290,140,1290,200
 *
 * Config (via JSON file):
 *   node tools/kb-annotate.mjs --config=annotations.json
 *
 *   annotations.json format:
 *   {
 *     "input": "screenshots/contacts-list.png",
 *     "output": "annotated/contacts-add-btn.png",
 *     "annotations": [
 *       { "type": "rect", "x": 1200, "y": 80, "w": 180, "h": 40 },
 *       { "type": "circle", "cx": 1290, "cy": 100, "r": 24 },
 *       { "type": "arrow", "x1": 1290, "y1": 140, "x2": 1290, "y2": 200 }
 *     ]
 *   }
 */

import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

// ── Theming ─────────────────────────────────────────────────

const ACCENT = '#FF4500';
const STROKE_WIDTH = 3;
const ARROW_HEAD_SIZE = 12;
const RECT_RADIUS = 6;
const FILL_OPACITY = 0.08;

// ── SVG Generators ──────────────────────────────────────────

function svgRect(x, y, w, h) {
    return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${RECT_RADIUS}" ry="${RECT_RADIUS}" fill="${ACCENT}" fill-opacity="${FILL_OPACITY}" stroke="${ACCENT}" stroke-width="${STROKE_WIDTH}" />`;
}

function svgCircle(cx, cy, r) {
    return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${ACCENT}" stroke-width="${STROKE_WIDTH}" />`;
}

function svgArrow(x1, y1, x2, y2) {
    // Calculate arrowhead
    const angle = Math.atan2(y2 - y1, x2 - x1);
    const ha1x = x2 - ARROW_HEAD_SIZE * Math.cos(angle - Math.PI / 6);
    const ha1y = y2 - ARROW_HEAD_SIZE * Math.sin(angle - Math.PI / 6);
    const ha2x = x2 - ARROW_HEAD_SIZE * Math.cos(angle + Math.PI / 6);
    const ha2y = y2 - ARROW_HEAD_SIZE * Math.sin(angle + Math.PI / 6);

    return `
        <line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${ACCENT}" stroke-width="${STROKE_WIDTH}" stroke-linecap="round" />
        <polygon points="${x2},${y2} ${ha1x},${ha1y} ${ha2x},${ha2y}" fill="${ACCENT}" />
    `;
}

// ── Parse CLI annotations ───────────────────────────────────

function parseAnnotation(str) {
    const [type, coords] = str.split(':');
    const nums = coords.split(',').map(Number);

    switch (type) {
        case 'rect':
            return { type: 'rect', x: nums[0], y: nums[1], w: nums[2], h: nums[3] };
        case 'circle':
            return { type: 'circle', cx: nums[0], cy: nums[1], r: nums[2] };
        case 'arrow':
            return { type: 'arrow', x1: nums[0], y1: nums[1], x2: nums[2], y2: nums[3] };
        default:
            console.warn(`Unknown annotation type: ${type}`);
            return null;
    }
}

// ── Render annotations to SVG ───────────────────────────────

function renderSVG(width, height, annotations) {
    const elements = annotations.map(a => {
        switch (a.type) {
            case 'rect': return svgRect(a.x, a.y, a.w, a.h);
            case 'circle': return svgCircle(a.cx, a.cy, a.r);
            case 'arrow': return svgArrow(a.x1, a.y1, a.x2, a.y2);
            default: return '';
        }
    });

    return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
        ${elements.join('\n        ')}
    </svg>`;
}

// ── Main ────────────────────────────────────────────────────

async function main() {
    const args = process.argv.slice(2);

    let inputPath, outputPath, annotations;

    // Config file mode
    const configArg = args.find(a => a.startsWith('--config='));
    if (configArg) {
        const configPath = configArg.split('=')[1];
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        inputPath = path.resolve(ROOT, config.input);
        outputPath = path.resolve(ROOT, config.output);
        annotations = config.annotations;
    } else {
        // CLI mode
        if (args.length < 3) {
            console.log('Usage: kb-annotate.mjs <input.png> <output.png> <annotations...>');
            console.log('  rect:x,y,w,h     — Rectangle highlight');
            console.log('  circle:cx,cy,r   — Circle highlight');
            console.log('  arrow:x1,y1,x2,y2 — Arrow');
            console.log('');
            console.log('Example:');
            console.log('  node tools/kb-annotate.mjs in.png out.png rect:100,50,200,40 circle:200,70,20');
            process.exit(0);
        }

        inputPath = path.resolve(args[0]);
        outputPath = path.resolve(args[1]);
        annotations = args.slice(2).map(parseAnnotation).filter(Boolean);
    }

    if (!fs.existsSync(inputPath)) {
        console.error(`❌ Input file not found: ${inputPath}`);
        process.exit(1);
    }

    // Ensure output directory
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });

    // Get image dimensions
    const metadata = await sharp(inputPath).metadata();
    const { width, height } = metadata;

    console.log(`🖼️  Input:  ${inputPath} (${width}×${height})`);
    console.log(`✏️  Annotations: ${annotations.length}`);

    // Generate SVG overlay
    const svgOverlay = renderSVG(width, height, annotations);

    // Composite
    const result = await sharp(inputPath)
        .composite([{
            input: Buffer.from(svgOverlay),
            top: 0,
            left: 0,
        }])
        .png({ quality: 95 })
        .toFile(outputPath);

    const sizeKB = (fs.statSync(outputPath).size / 1024).toFixed(0);
    console.log(`✅ Output: ${outputPath} (${sizeKB} KB)`);
}

main().catch(err => {
    console.error('❌ Error:', err.message);
    process.exit(1);
});
