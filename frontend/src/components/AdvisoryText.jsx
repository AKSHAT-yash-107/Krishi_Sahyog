
import React from "react";

function InlineText({ text }) {
  const parts = String(text)
    .replace(/<br\s*\/?>/gi, "\n")
    .split(/(\*\*.*?\*\*)/g);

  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return <strong key={index}>{part.slice(2, -2)}</strong>;
        }

        return part.split("\n").map((line, i) => (
          <React.Fragment key={`${index}-${i}`}>
            {i > 0 && <br />}
            {line.replace(/^[_*]+|[_*]+$/g, "")}
          </React.Fragment>
        ));
      })}
    </>
  );
}

export default function AdvisoryText({ text }) {
  if (!text) return null;

  const lines = String(text)
    .replace(/\r/g, "")
    .split("\n")
    .map(line => line.trim())
    .filter(Boolean);

  const blocks = [];
  let bullets = [];
  let tableRows = [];

  const flushBullets = () => {
    if (!bullets.length) return;

    blocks.push(
      <ul className="advisory-list" key={`list-${blocks.length}`}>
        {bullets.map((item, i) => (
          <li key={i}><InlineText text={item} /></li>
        ))}
      </ul>
    );
    bullets = [];
  };

  const flushTable = () => {
    if (!tableRows.length) return;

    const rows = tableRows
      .filter(row => !row.every(cell => /^[-:\s]+$/.test(cell)))
      .map(row => row.filter((_, i) => i < 3));

    if (rows.length) {
      const [header, ...body] = rows;

      blocks.push(
        <div className="advisory-table-wrap" key={`table-${blocks.length}`}>
          <table className="advisory-table">
            <thead>
              <tr>
                {header.map((cell, i) => (
                  <th key={i}><InlineText text={cell} /></th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((row, i) => (
                <tr key={i}>
                  {header.map((_, j) => (
                    <td key={j}>
                      <InlineText text={row[j] || "—"} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    tableRows = [];
  };

  for (const line of lines) {
    // Markdown table rows
    if (line.startsWith("|") && line.endsWith("|")) {
      flushBullets();

      const cells = line
        .slice(1, -1)
        .split("|")
        .map(cell => cell.trim());

      // Ignore markdown separator rows
      if (cells.every(cell => /^[-:\s]+$/.test(cell))) continue;

      tableRows.push(cells);
      continue;
    }

    flushTable();

    // Markdown headings
    const heading = line.match(/^\*\*(.+?)\*\*:?\s*$/);

    if (heading) {
      flushBullets();

      blocks.push(
        <h4 className="advisory-heading" key={`heading-${blocks.length}`}>
          {heading[1]}
        </h4>
      );
      continue;
    }

    // Bullet points
    if (/^[-•]\s+/.test(line)) {
      bullets.push(line.replace(/^[-•]\s+/, ""));
      continue;
    }

    flushBullets();

    // Opening weather summary
    if (blocks.length === 0) {
      blocks.push(
        <div className="advisory-summary" key="summary">
          <InlineText text={line} />
        </div>
      );
    } else {
      blocks.push(
        <p className="advisory-paragraph" key={`para-${blocks.length}`}>
          <InlineText text={line} />
        </p>
      );
    }
  }

  flushBullets();
  flushTable();

  return <div className="advisory-formatted">{blocks}</div>;
}
