import React from 'react';

function inlineMarkdown(text) {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('*') && part.endsWith('*')) return <em key={i}>{part.slice(1, -1)}</em>;
    return part;
  });
}

function splitCells(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim());
}

export default function MarkdownReport({ text = '' }) {
  const lines = String(text).replace(/\r\n/g, '\n').split('\n');
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) { i++; continue; }
    if (/^---+$/.test(line) || /^\*\*\*+$/.test(line)) {
      blocks.push(<hr key={`hr-${i}`} />);
      i++;
      continue;
    }
    if (line.startsWith('|') && i + 1 < lines.length && /^\|?[\s:\-|]+\|?$/.test(lines[i + 1].trim())) {
      const headers = splitCells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(splitCells(lines[i]));
        i++;
      }
      blocks.push(
        <div className="markdown-table-wrap" key={`table-${i}`}>
          <table className="markdown-report-table">
            <thead><tr>{headers.map((cell, j) => <th key={j}>{inlineMarkdown(cell)}</th>)}</tr></thead>
            <tbody>{rows.map((row, r) => <tr key={r}>{headers.map((_, c) => <td key={c}>{inlineMarkdown(row[c] || '')}</td>)}</tr>)}</tbody>
          </table>
        </div>
      );
      continue;
    }
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const content = inlineMarkdown(heading[2]);
      blocks.push(React.createElement(`h${level + 1}`, { key: `h-${i}` }, content));
      i++;
      continue;
    }
    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ''));
        i++;
      }
      blocks.push(<ul key={`ul-${i}`}>{items.map((item, j) => <li key={j}>{inlineMarkdown(item)}</li>)}</ul>);
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i++;
      }
      blocks.push(<ol key={`ol-${i}`}>{items.map((item, j) => <li key={j}>{inlineMarkdown(item)}</li>)}</ol>);
      continue;
    }
    const paragraph = [line];
    i++;
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|---+$|[-*]\s+|\d+\.\s+|\|)/.test(lines[i].trim())) {
      paragraph.push(lines[i].trim());
      i++;
    }
    blocks.push(<p key={`p-${i}`}>{inlineMarkdown(paragraph.join(' '))}</p>);
  }
  return <div className="markdown-report">{blocks}</div>;
}
