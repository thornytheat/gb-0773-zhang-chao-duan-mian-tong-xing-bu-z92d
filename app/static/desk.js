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
