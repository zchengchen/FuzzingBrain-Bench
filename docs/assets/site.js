// Shared site helpers. Loaded by pages that render bugs.json.

async function loadBugs() {
  const res = await fetch('bugs.json', { cache: 'no-cache' });
  if (!res.ok) throw new Error('Failed to load bugs.json: ' + res.status);
  return await res.json();
}

function badge(status) {
  return `<span class="badge ${status}">${status}</span>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// The challenges are SEALED: the public catalogue exposes only the neutral
// alias, the project, the language, and the sanitizer — never the bug's title,
// class, or location. renderTable reflects exactly that surface.
function renderTable(bugs, target) {
  const rows = bugs.map(b => `
    <tr data-sanitizer="${escapeHtml(b.sanitizer || '')}" data-language="${escapeHtml(b.language || '')}" data-project="${b.project.toLowerCase()}" data-id="${escapeHtml(b.id)}">
      <td class="id"><code>${escapeHtml(b.id)}</code></td>
      <td class="project">${escapeHtml(b.project)}</td>
      <td class="language">${escapeHtml(b.language || '')}</td>
      <td class="sanitizer"><code>${escapeHtml(b.sanitizer || '')}</code></td>
    </tr>
  `).join('');
  target.innerHTML = `
    <table class="bugs">
      <thead>
        <tr>
          <th>Challenge</th>
          <th>Project</th>
          <th>Language</th>
          <th>Sanitizer</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function attachFilters(allBugs, countEl) {
  const search = document.getElementById('search');
  const sanitizerSel = document.getElementById('f-sanitizer') || document.getElementById('f-class');

  function apply() {
    const q = (search.value || '').trim().toLowerCase();
    const san = sanitizerSel ? sanitizerSel.value : '';
    let shown = 0;
    document.querySelectorAll('table.bugs tbody tr').forEach(tr => {
      const matchSan = !san || tr.dataset.sanitizer === san;
      const text = (tr.dataset.id + ' ' + tr.dataset.project + ' ' + tr.dataset.language).toLowerCase();
      const matchQ = !q || text.includes(q);
      const ok = matchSan && matchQ;
      tr.style.display = ok ? '' : 'none';
      if (ok) shown++;
    });
    countEl.textContent = `Showing ${shown} of ${allBugs.length}`;
  }

  // Populate the sanitizer filter from data.
  if (sanitizerSel) {
    Array.from(new Set(allBugs.map(b => b.sanitizer).filter(Boolean))).sort().forEach(s => {
      const opt = document.createElement('option');
      opt.value = s; opt.textContent = s;
      sanitizerSel.appendChild(opt);
    });
    sanitizerSel.addEventListener('change', apply);
  }
  if (search) search.addEventListener('input', apply);
  apply();
}
