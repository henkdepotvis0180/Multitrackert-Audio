"use strict";
const $ = (id) => document.getElementById(id);
let current = null,
  timer = null,
  busy = false;
const headers = { "X-Multitrack": "local" };
const terminal = new Set(["done", "error", "cancelled", "interrupted"]);
function seconds(n) {
  return `${Math.floor(n / 60)}:${(n % 60).toFixed(1).padStart(4, "0")}`;
}
async function api(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { ...headers, ...options.headers },
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "Aanvraag mislukt");
  }
  return response.json();
}
function error(e) {
  $("error").textContent = e.message;
}
async function system() {
  try {
    const s = await api("/api/system");
    $("system").textContent =
      `CPU: ${s.cpu_threads} threads · ${s.inference_threads} modelthreads · ${s.ram_available_gb} GB RAM vrij · Herkenning: CPU · Scheiding: ${s.separation_device === "cuda" ? s.gpu + " (CUDA)" : "CPU"} · Modellen: ${s.models_ready ? "gereed" : "ontbreken"}`;
    if (!s.models_ready)
      $("system").append(
        document.createTextNode(
          " — voer eerst python scripts/download_models.py uit.",
        ),
      );
    if (!s.ffmpeg)
      $("system").append(
        document.createTextNode(" — FFmpeg of ffprobe ontbreekt."),
      );
    $("start").disabled = !s.models_ready || !s.ffmpeg || busy;
    $("separate").disabled = !s.separation_ready || busy;
    $("file-info").textContent =
      `Maximaal ${(s.max_bytes / 1024 ** 3).toFixed(1)} GB en ${s.max_minutes} minuten. Mono of stereo.`;
  } catch (e) {
    error(e);
  }
}
$("upload-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const file = $("file").files[0];
  if (!file) return;
  clearTimeout(timer);
  $("error").textContent = "";
  $("result").hidden = true;
  $("progress-section").hidden = false;
  $("phase").textContent = "Upload naar je lokale server";
  $("progress").value = 0;
  $("cancel").hidden = true;
  $("eta").textContent = "";
  busy = true;
  $("start").disabled = true;
  const xhr = new XMLHttpRequest();
  xhr.open(
    "POST",
    `/api/jobs?speakers=${$("speakers").value}&separate=${$("separate").checked}&device=${$("device").value}`,
  );
  xhr.setRequestHeader("X-Multitrack", "local");
  xhr.setRequestHeader("Content-Type", "video/mp4");
  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      $("progress").value = e.loaded / e.total;
      $("progress-text").textContent =
        `${Math.round((e.loaded / e.total) * 100)}% lokaal ontvangen`;
    }
  };
  xhr.onload = () => {
    try {
      const data = JSON.parse(xhr.responseText);
      if (xhr.status >= 400) throw new Error(data.detail);
      current = data.id;
      localStorage.setItem("multitrack-job", current);
      poll();
    } catch (e) {
      busy = false;
      error(e);
      system();
    }
  };
  xhr.onerror = () => {
    busy = false;
    error(new Error("Verbinding met lokale server verloren."));
    system();
  };
  xhr.send(file);
});
async function poll() {
  try {
    const s = await api(`/api/jobs/${current}`);
    $("progress-section").hidden = false;
    $("phase").textContent = s.phase || s.state;
    if (typeof s.fraction === "number") $("progress").value = s.fraction;
    else $("progress").removeAttribute("value");
    $("progress-text").textContent =
      `${s.message || ""}${s.elapsed_seconds ? " · " + seconds(s.elapsed_seconds + (terminal.has(s.state) ? 0 : Math.max(0, Date.now() / 1000 - (s.updated_at || Date.now() / 1000)))) + " verstreken" : ""}`;
    $("eta").textContent = s.phase_eta_seconds
      ? `Geschat nog ${seconds(s.phase_eta_seconds)} voor deze fase; volgende fases komen daarna. Dit is een schatting.`
      : "Resterende tijd wordt per fase geschat zodra voldoende voortgang is gemeten.";
    $("cancel").hidden = terminal.has(s.state);
    $("cancel").disabled = false;
    busy = !terminal.has(s.state);
    $("start").disabled = busy;
    if (s.state === "done") {
      $("eta").textContent = "Klaar — je ZIP staat lokaal gereed.";
      await showResult(current, s);
    } else if (terminal.has(s.state)) error(new Error(s.message));
    else timer = setTimeout(poll, 1000);
    if (!busy) {
      await system();
      await history();
    }
  } catch (e) {
    error(e);
    timer = setTimeout(poll, 4000);
  }
}
$("cancel").onclick = async () => {
  try {
    const s = await api(`/api/jobs/${current}/cancel`, { method: "POST" });
    $("cancel").disabled = true;
    $("eta").textContent = s.message;
  } catch (e) {
    error(e);
  }
};
async function showResult(id, s) {
  const data = await api(`/api/jobs/${id}/timeline`);
  $("result").hidden = false;
  $("download").href = `/api/jobs/${id}/download`;
  $("summary").textContent =
    `${s.speakers.length} sprekers · ${data.segments.length} fragmenten · ${seconds(data.media.duration)} totaal. ${s.unseparated_overlap_count} overlapregio’s bevatten nog de oorspronkelijke mix.`;
  $("summary").className = s.unseparated_overlap_count ? "warning" : "";
  $("video").src = `/api/jobs/${id}/media/input.mp4`;
  $("tracks").replaceChildren();
  $("segments").replaceChildren();
  for (const speaker of s.speakers) {
    const div = document.createElement("div");
    div.className = "track";
    const label = document.createElement("strong");
    label.textContent = `Spreker ${speaker}`;
    const canvas = document.createElement("canvas");
    canvas.width = 1600;
    canvas.height = 56;
    canvas.setAttribute("aria-label", `Spreekmomenten van spreker ${speaker}`);
    const context = canvas.getContext("2d");
    context.fillStyle = ["#82e3b8", "#8ab4f8", "#f2cd86", "#dda5ed"][
      (speaker - 1) % 4
    ];
    data.segments
      .filter((x) => x.speaker === speaker)
      .forEach((x) => {
        context.fillRect(
          (x.start / data.media.duration) * 1600,
          8,
          Math.max(2, ((x.end - x.start) / data.media.duration) * 1600),
          40,
        );
      });
    canvas.onclick = (e) => {
      $("video").currentTime =
        (e.offsetX / canvas.clientWidth) * data.media.duration;
      $("video").play().catch(error);
    };
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "none";
    audio.src = `/api/jobs/${id}/media/speaker_${String(speaker).padStart(2, "0")}.wav`;
    div.append(label, canvas, audio);
    $("tracks").append(div);
  }
  for (const x of data.segments) {
    const tr = document.createElement("tr");
    for (const value of [
      x.fragment,
      `Spreker ${x.speaker}`,
      seconds(x.start),
      seconds(x.end),
    ]) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.append(td);
    }
    const td = document.createElement("td"),
      button = document.createElement("button");
    button.textContent = "▶ Origineel";
    button.className = "secondary";
    button.onclick = () => {
      $("video").currentTime = x.start;
      $("video").play().catch(error);
    };
    td.append(button);
    tr.append(td);
    $("segments").append(tr);
  }
}
async function history() {
  const list = await api("/api/jobs");
  $("history").replaceChildren();
  if (!list.length) $("history").textContent = "Nog geen opdrachten.";
  const active = list.find((j) => !terminal.has(j.state));
  if (active && !busy) {
    current = active.id;
    poll();
  }
  for (const j of list) {
    const row = document.createElement("div");
    row.className = "history-row";
    const label = document.createElement("span");
    label.textContent = `${j.id.slice(0, 8)} · ${j.phase || j.state}`;
    const open = document.createElement("button");
    open.textContent = "Open";
    open.className = "secondary";
    open.onclick = () => {
      if (busy && current !== j.id) return;
      clearTimeout(timer);
      current = j.id;
      $("error").textContent = "";
      $("result").hidden = true;
      poll();
    };
    const del = document.createElement("button");
    del.textContent = "Verwijder";
    del.className = "secondary";
    del.disabled = !terminal.has(j.state);
    del.onclick = async () => {
      if (
        !confirm(
          "Deze opdracht en alle bijbehorende lokale bestanden verwijderen?",
        )
      )
        return;
      try {
        await api(`/api/jobs/${j.id}`, { method: "DELETE" });
        if (current === j.id) {
          clearTimeout(timer);
          current = null;
          $("result").hidden = true;
          $("progress-section").hidden = true;
        }
        await history();
      } catch (e) {
        error(e);
      }
    };
    row.append(label, open, del);
    $("history").append(row);
  }
}
system();
history().catch(error);
