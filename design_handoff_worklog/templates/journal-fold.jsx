/* ── JournalFoldView ──
   마크다운 헤더(# / ## / ###) 기준으로 일지를 섹션으로 나눠 접기/펼치기.
   메일 본문 등 긴 텍스트를 헤더 아래 묻어두고, 헤더만 펼쳐서 빠르게 스캔하기 위함. */

function parseSections(text) {
  const lines = (text || '').split('\n');
  const sections = [];
  let cur = { header: null, level: 0, body: [] };
  for (const line of lines) {
    const m = line.match(/^(#{1,6})\s+(.*)$/);
    if (m) {
      if (cur.header !== null || cur.body.length) sections.push({ ...cur, body: cur.body.join('\n') });
      cur = { header: line, level: m[1].length, body: [] };
    } else {
      cur.body.push(line);
    }
  }
  if (cur.header !== null || cur.body.length) sections.push({ ...cur, body: cur.body.join('\n') });
  return sections;
}

function joinSections(sections) {
  const out = [];
  for (const s of sections) {
    if (s.header !== null) out.push(s.header);
    if (s.body.length > 0) out.push(...s.body.split('\n'));
  }
  return out.join('\n');
}

function JournalFoldView({ text, onChange, dateKey }) {
  const sections = React.useMemo(() => parseSections(text), [text]);

  /* 접힘 상태 — 날짜별로 localStorage 저장 */
  const stateKey = `worklog.journal.fold.${dateKey}`;
  const [folded, setFolded] = React.useState(() => {
    try {
      const arr = JSON.parse(localStorage.getItem(stateKey) || 'null');
      if (Array.isArray(arr)) return new Set(arr);
    } catch (e) {}
    /* 기본: body가 6줄 이상이면 자동 접기 */
    const def = new Set();
    sections.forEach((s, i) => {
      if (s.header !== null && (s.body.split('\n').length > 6 || s.body.length > 300)) def.add(i);
    });
    return def;
  });
  React.useEffect(() => {
    localStorage.setItem(stateKey, JSON.stringify([...folded]));
  }, [folded, stateKey]);

  function toggle(idx) {
    setFolded((prev) => {
      const n = new Set(prev);
      n.has(idx) ? n.delete(idx) : n.add(idx);
      return n;
    });
  }

  function updateBody(idx, newBody) {
    const next = sections.map((s, i) => i === idx ? { ...s, body: newBody } : s);
    onChange(joinSections(next));
  }

  function updateHeader(idx, newHeader) {
    const next = sections.map((s, i) => i === idx ? { ...s, header: newHeader } : s);
    onChange(joinSections(next));
  }

  function addHeaderAfter(idx) {
    /* idx 섹션 뒤에 새 빈 헤더 섹션 삽입 */
    const next = [...sections];
    next.splice(idx + 1, 0, { header: '## 새 섹션', level: 2, body: '' });
    onChange(joinSections(next));
  }

  function deleteSection(idx) {
    if (!confirm('이 섹션을 삭제할까요?')) return;
    const next = sections.filter((_, i) => i !== idx);
    onChange(joinSections(next));
  }

  function expandAll() { setFolded(new Set()); }
  function foldAll() {
    const all = new Set();
    sections.forEach((s, i) => { if (s.header !== null) all.add(i); });
    setFolded(all);
  }

  const hasHeaders = sections.some((s) => s.header !== null);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6, overflow: 'auto', paddingRight: 4 }}>
      {/* 헤더 없을 때 안내 */}
      {!hasHeaders &&
        <div style={{ fontSize: 11, color: 'var(--text-3)', background: 'var(--surface-2)', borderRadius: 4, padding: '8px 10px', lineHeight: 1.6 }}>
          💡 <strong>접을 섹션이 없어요.</strong> 본문에 <code style={{ fontFamily: 'var(--mono)', background: 'var(--surface)', padding: '0 4px', borderRadius: 2 }}>## 헤더</code> 또는 <code style={{ fontFamily: 'var(--mono)', background: 'var(--surface)', padding: '0 4px', borderRadius: 2 }}># 헤더</code>를 추가하면 그 줄 단위로 접기·펼치기가 가능해져요.
        </div>
      }

      {/* 일괄 토글 */}
      {hasHeaders &&
        <div style={{ display: 'flex', gap: 6, fontSize: 11, color: 'var(--text-3)' }}>
          <button className="btn btn-sm" onClick={foldAll}>▶ 모두 접기</button>
          <button className="btn btn-sm" onClick={expandAll}>▼ 모두 펼치기</button>
          <span style={{ alignSelf: 'center', marginLeft: 6, color: 'var(--text-4)' }}>
            섹션 {sections.filter((s) => s.header !== null).length}개 · 접힘 {folded.size}개
          </span>
        </div>
      }

      {sections.map((s, i) => {
        const isPreamble = s.header === null;
        const isFolded = folded.has(i);
        const bodyLines = s.body ? s.body.split('\n').length : 0;
        const bodyChars = s.body.length;
        const headerText = s.header ? s.header.replace(/^#{1,6}\s+/, '') : '(상단)';
        const indentPx = isPreamble ? 0 : (s.level - 1) * 12;

        return (
          <div key={i} style={{ marginLeft: indentPx, background: 'var(--surface)' }}>
            {/* 헤더 줄 — 항상 편집 가능, 좌측 chevron만 fold 토글 */}
            {!isPreamble &&
              <div style={{
                display: 'flex', alignItems: 'center', gap: 4,
                borderTop: i > 0 ? '1px solid var(--border)' : 'none',
                background: isFolded ? 'var(--surface-2)' : 'transparent',
                padding: '2px 0'
              }}>
                <button
                  onClick={() => toggle(i)}
                  title={isFolded ? '펼치기' : '접기'}
                  style={{
                    background: 'transparent', border: 'none', cursor: 'pointer',
                    color: 'var(--text-3)', fontSize: 11, width: 22, padding: '4px 0',
                    flexShrink: 0, lineHeight: 1
                  }}>{isFolded ? '▶' : '▼'}</button>
                <input
                  value={s.header}
                  onChange={(e) => updateHeader(i, e.target.value)}
                  spellCheck={false}
                  style={{
                    flex: 1, border: 'none', outline: 'none',
                    padding: '4px 4px', fontFamily: 'var(--mono)', fontSize: 13,
                    color: 'var(--text)', background: 'transparent', fontWeight: 600
                  }}
                  title="헤더 — 자유롭게 편집 가능" />
                {isFolded && bodyLines > 0 &&
                  <span style={{ fontSize: 10, color: 'var(--text-4)', background: 'var(--bg)', padding: '1px 8px', borderRadius: 99, marginRight: 4 }}>
                    +{bodyLines}줄 / {bodyChars}자
                  </span>
                }
                <button
                  onClick={() => addHeaderAfter(i)}
                  className="icon-btn"
                  title="아래에 새 섹션"
                  style={{ fontSize: 10, padding: '1px 6px', marginRight: 2 }}>+</button>
                <button
                  onClick={() => deleteSection(i)}
                  className="icon-btn"
                  title="섹션 삭제"
                  style={{ fontSize: 10, padding: '1px 6px', color: 'var(--red)', borderColor: 'transparent', marginRight: 4 }}>✕</button>
              </div>
            }
            {/* 본문 — 접혔을 때 숨김, 그 외에는 항상 편집 가능 */}
            {!isFolded &&
              <textarea
                value={s.body}
                onChange={(e) => updateBody(i, e.target.value)}
                placeholder={isPreamble ? '(헤더 위 본문)' : '내용...'}
                rows={Math.max(2, Math.min(24, bodyLines + 1))}
                spellCheck={false}
                style={{
                  width: '100%', border: 'none', outline: 'none',
                  padding: isPreamble ? '4px 4px 8px' : '2px 4px 8px 26px',
                  fontFamily: 'var(--mono)', fontSize: 13,
                  color: 'var(--text)', background: 'transparent', resize: 'vertical',
                  lineHeight: 1.8, minHeight: isPreamble ? 40 : 48,
                  display: 'block'
                }} />
            }
          </div>
        );
      })}

      {sections.length === 0 &&
        <div style={{ fontSize: 12, color: 'var(--text-4)', padding: 12, textAlign: 'center' }}>(내용 없음)</div>
      }
    </div>
  );
}

window.JournalFoldView = JournalFoldView;
