const sample = document.querySelector('#sample');
sample.addEventListener('change', () => document.querySelector('input[name=run]')?.remove());
document.querySelector('#print-book').addEventListener('click', () => window.print());
const rerun = document.querySelector('#rerun');
rerun?.addEventListener('click', async () => {
  const feedback = document.querySelector('#feedback');
  rerun.disabled = true;
  feedback.textContent = '复算中…';
  try {
    const res = await fetch(`/api/journal/${rerun.dataset.run}/rerun`, {method:'POST'});
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || '复算失败');
    feedback.textContent = data.reused ? '复算一致，沿用原簿' : '新簿已归档';
  } catch (error) {
    feedback.textContent = `${error.message}，请重试。`;
  } finally { rerun.disabled = false; }
});

const roundtripPanel = document.querySelector('.roundtrip-panel');
if (roundtripPanel) {
  const body = document.querySelector('#roundtrip-body');
  const unloadInput = document.querySelector('#unloading-input');
  const note = () => document.querySelector('#roundtrip-feedback');

  const fmtTime = (stamp) => {
    if (!/^\d+$/.test(String(stamp))) return stamp;
    return new Date(Number(stamp) * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z');
  };

  const gaugeLines = (leg) => leg.evidence.map((ev) =>
    `${ev.section}:${ev.lines.length ? ev.lines.join('/') : '—'}`).join(' · ');

  const render = (pairing) => {
    if (!pairing.feasible) {
      const reason = pairing.reason === 'NO_OUTBOUND_WINDOW'
        ? '船期内无去程可行潮窗。' : '卸货后没有可行回程潮窗，往返不予确认。';
      body.innerHTML = `<p class="no-window">${reason}</p><p id="roundtrip-feedback" class="feedback" role="status"></p>`;
      return;
    }
    const rows = Object.entries(pairing.plans).map(([name, plan]) => `
      <tr class="plan-row" data-plan="${name}">
        <td>${name === 'early' ? '早走腾位' : '晚走留余'}</td>
        <td><b>${fmtTime(plan.outbound.departure)}</b></td>
        <td>${fmtTime(plan.unload_ready)}</td>
        <td><b>${fmtTime(plan.return_leg.departure)}</b></td>
        <td>${plan.buffer_s}</td>
        <td class="gauge-lines"><span class="leg-lines">去 ${gaugeLines(plan.outbound)}</span>
          <span class="leg-lines">回 ${gaugeLines(plan.return_leg)}</span></td>
        <td><button type="button" class="confirm-btn" data-plan="${name}">确认往返</button></td>
      </tr>`).join('');
    body.innerHTML = `<table class="roundtrip-table"><thead><tr><th>安排</th><th>去程出发</th><th>卸货就绪</th>
      <th>回程出发</th><th>回程富余 s</th><th>潮尺（去 / 回）</th><th></th></tr></thead><tbody>${rows}</tbody></table>
      <p class="hint">去程到港后须留足 ${pairing.unloading_s} s 卸货；回程出发落在其后的最早可行潮窗。卸货时长一变即按新时长重算。</p>
      <p id="roundtrip-feedback" class="feedback" role="status"></p>`;
  };

  const buildPayload = (extra) => {
    const payload = {unloading_s: Number(unloadInput.value), ...extra};
    if (roundtripPanel.dataset.run) payload.run = roundtripPanel.dataset.run;
    else payload.sample = roundtripPanel.dataset.sample;
    return payload;
  };

  const recalc = async () => {
    note().textContent = '重算中…';
    try {
      const query = new URLSearchParams(buildPayload({}));
      const res = await fetch(`/api/roundtrip/${encodeURIComponent(roundtripPanel.dataset.vessel)}?${query}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || '重算失败');
      render(data.pairing);
    } catch (error) {
      note().textContent = `${error.message}，请重试。`;
    }
  };

  let timer;
  unloadInput.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(recalc, 350);
  });

  body.addEventListener('click', async (event) => {
    const button = event.target.closest('.confirm-btn');
    if (!button) return;
    button.disabled = true;
    note().textContent = '提交确认…';
    try {
      const res = await fetch(`/api/roundtrip/${encodeURIComponent(roundtripPanel.dataset.vessel)}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(buildPayload({plan: button.dataset.plan})),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || '确认失败');
      note.textContent = data.reused ? '同一安排已留档，未重复建档。' : '往返安排已确认并留档。';
      if (!data.reused) window.setTimeout(() => window.location.reload(), 600);
    } catch (error) {
      note.textContent = `${error.message}，请重试。`;
      button.disabled = false;
    }
  });
}
