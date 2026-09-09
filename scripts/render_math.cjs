// Render EPUB equations with MathJax 3.2.2; no reader JavaScript is required.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const lib = path.join(root, '.tools', 'mathjax', 'node_modules', 'mathjax-full', 'js');
const {mathjax} = require(path.join(lib, 'mathjax.js'));
const {TeX} = require(path.join(lib, 'input', 'tex.js'));
const {SVG} = require(path.join(lib, 'output', 'svg.js'));
const {liteAdaptor} = require(path.join(lib, 'adaptors', 'liteAdaptor.js'));
const {RegisterHTMLHandler} = require(path.join(lib, 'handlers', 'html.js'));
const {AllPackages} = require(path.join(lib, 'input', 'tex', 'AllPackages.js'));
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const tex = new TeX({packages: AllPackages, formatError: (_, error) => { throw error; }});
const svg = new SVG({fontCache: 'local'});
const document = mathjax.document('', {InputJax: tex, OutputJax: svg});
const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const directory = process.argv[3];
fs.mkdirSync(directory, {recursive: true});
const dimensions = {};
for (const item of manifest) {
  const container = document.convert(item.tex, {display: item.display, em: 16, ex: 8, containerWidth: 720});
  const element = adaptor.firstChild(container);
  let xml = adaptor.outerHTML(element);
  if (xml.includes('data-mjx-error')) throw new Error(`Invalid math: ${item.tex}`);
  const width = parseFloat(adaptor.getAttribute(element, 'width')) / 2;
  const height = parseFloat(adaptor.getAttribute(element, 'height')) / 2;
  const alignment = /vertical-align:\s*([-\d.]+)ex/.exec(adaptor.getAttribute(element, 'style') || '');
  dimensions[item.id] = {width, height, baseline: alignment ? Number(alignment[1]) / 2 : 0};
  // Absolute intrinsic dimensions also work in readers that ignore CSS em units.
  xml = xml.replace(/width="[^"]+"/, `width="${width * 16}px"`)
           .replace(/height="[^"]+"/, `height="${height * 16}px"`);
  const escaped = item.tex.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  xml = xml.replace(/(<svg\b[^>]*>)/, `$1<title>${escaped}</title>`);
  fs.writeFileSync(path.join(directory, `${item.id}.svg`), xml, 'utf8');
}
fs.writeFileSync(path.join(directory, 'dimensions.json'), JSON.stringify(dimensions), 'utf8');
console.log(`Rendered ${manifest.length} unique EPUB formulas.`);
