// Ambil CSRF dari cookie
export function getCSRF() {
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? m[1] : '';
}

export async function postJSON(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRF()},
    body: JSON.stringify(data),
    credentials: 'same-origin'
  });
  const json = await res.json().catch(() => ({ ok: false, errors: [{message: 'Respon bukan JSON'}] }));
  if (!res.ok) throw json;
  return json;
}