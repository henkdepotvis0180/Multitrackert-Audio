"use strict";
const $ = (id) => document.getElementById(id);
let current = null,
  timer = null,
  busy = false;
let initialOptions = true;
let installation = null;
let adLibraryLoaded = false;
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
function renderInstallation() {
  if (!installation) return;
  const platform = $("install-os").value;
  const gpu = $("install-device");
  gpu.querySelector('[value="cuda"]').disabled = platform === "mac";
  if (platform === "mac") gpu.value = "cpu";
  $("app-version").textContent =
    `Je draait versie ${installation.version}. ${installation.update_note}`;
  $("footer-version").textContent = `versie ${installation.version}`;
  $("install-os").parentElement.parentElement.hidden = installation.packaged;
  $("installation-checks").replaceChildren();
  for (const check of installation.checks) {
    const needsCuda =
      check.id === "audio_runtime" &&
      gpu.value === "cuda" &&
      !installation.cuda_available;
    const installed = check.installed && !needsCuda;
    const item = document.createElement("div");
    item.className = "install-item";
    const title = document.createElement("strong");
    title.textContent = `${installed ? "✓" : "○"} ${check.name}`;
    const state = document.createElement("p");
    state.className = installed ? "hint" : "warning";
    state.textContent = installed
      ? "Aanwezig — niet opnieuw nodig."
      : check.required
        ? "Ontbreekt — nodig voor de basis."
        : "Nog nodig voor deze optionele functie.";
    const detail = document.createElement("p");
    detail.className = "hint";
    detail.textContent =
      check.detail +
      (needsCuda
        ? " NVIDIA/CUDA is nog niet beschikbaar. Controleer ook de GPU en driver; CPU blijft mogelijk."
        : "");
    let command = check[platform] || check.posix;
    if (installation.packaged) command = 'Installeer de volledige Windows-installer opnieuw als dit onderdeel ontbreekt. Je projectbestanden blijven buiten de installatiemap bewaard.';
    if (gpu.value === "cuda" && command.includes("/whl/cpu")) {
      command = command
        .replace("/whl/cpu", "/whl/cu128")
        .replace("-m pip install ", "-m pip install --force-reinstall ");
    }
    const code = document.createElement("pre");
    code.textContent = command;
    item.append(title, state, detail);
    if (installed) {
      const more = document.createElement("details"),
        summary = document.createElement("summary");
      summary.textContent = "Toon installatiecommando";
      more.append(summary, code);
      item.append(more);
    } else item.append(code);
    $("installation-checks").append(item);
  }
}
$("install-os").value = /Win/i.test(navigator.userAgent)
  ? "windows"
  : /Mac/i.test(navigator.userAgent)
    ? "mac"
    : "posix";
$("install-os").onchange = renderInstallation;
$("install-device").onchange = renderInstallation;
async function system() {
  try {
    const s = await api("/api/system");
    $("quit-app").hidden = !s.desktop;
    installation = s.installation;
    renderInstallation();
    if (
      initialOptions &&
      installation?.checks.some((c) => c.required && !c.installed)
    ) {
      $("installation-details").open = true;
    }
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
    $("music").disabled = !s.music_ready || busy;
    $("ad-text").disabled = !s.ad_text_ready || busy;
    $("ad-text-status").textContent = s.ad_text_ready
      ? "Lokaal tekstmodel gereed. Aanwijzingen worden getoond bij de fragmenten; tekst verwijdert geen audio."
      : "Optioneel tekstmodel ontbreekt: python scripts/download_ad_text_model.py. Geluidsvergelijking met de reclamebibliotheek werkt ook zonder dit model.";
    if (initialOptions) {
      $("music").checked = s.music_ready;
      $("separate").checked = s.separation_ready;
      initialOptions = false;
    }
    $("music-status").textContent = s.music_ready
      ? "Muziekmodel gereed. Zang kan samen met vergaderstemmen in de stemmix blijven."
      : "Achtergrond/rest wordt altijd bewaard. Voor echte muziekscheiding: installeer PyTorch/torchaudio en voer python scripts/download_music_model.py uit (README).";
    $("file-info").textContent =
      `Maximaal ${(s.max_bytes / 1024 ** 3).toFixed(1)} GB en ${s.max_minutes} minuten. Mono of stereo.`;
  } catch (e) {
    error(e);
  }
}
$("upload-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const file = $("file").files[0];
  const referenceFile = $("reference").files[0];
  const referenceOffset = $("reference-offset").value;
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
    `/api/jobs?speakers=${$("speakers").value}&separate=${$("separate").checked}&device=${$("device").value}&music=${$("music").checked}&known_ads=${$("known-ads").checked}&ad_text=${$("ad-text").checked}&ad_phrases=${encodeURIComponent($("ad-phrases").value)}&reference=${!!referenceFile}${referenceOffset ? "&reference_offset=" + encodeURIComponent(referenceOffset) : ""}`,
  );
  xhr.setRequestHeader("X-Multitrack", "local");
  xhr.setRequestHeader("Content-Type", "video/mp4");
  xhr.setRequestHeader("X-Filename", encodeURIComponent(file.name));
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
      if (referenceFile) uploadReference(referenceFile);
      else poll();
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
function uploadReference(file) {
  $("phase").textContent = "Radio-referentie lokaal ontvangen";
  $("progress").value = 0;
  const xhr = new XMLHttpRequest();
  xhr.open("POST", `/api/jobs/${current}/reference`);
  xhr.setRequestHeader("X-Multitrack", "local");
  xhr.setRequestHeader("Content-Type", "application/octet-stream");
  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) $("progress").value = e.loaded / e.total;
  };
  xhr.onload = () => {
    if (xhr.status >= 400) {
      try {
        error(new Error(JSON.parse(xhr.responseText).detail));
      } catch {
        error(new Error("Referentie-upload mislukt."));
      }
    }
    poll();
  };
  xhr.onerror = () => {
    error(new Error("Referentie-upload onderbroken."));
    poll();
  };
  xhr.send(file);
}
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
  $("fragment-preview").pause();
  $("fragment-preview").removeAttribute("src");
  const data = await api(`/api/jobs/${id}/timeline`);
  $("download").href = `/api/jobs/${id}/download`;
  const storage = await api(`/api/jobs/${id}/storage`);
  $("output-path").textContent = `Lokale uitvoer: ${storage.output_dir} · ZIP: ${storage.zip}`;
  $("summary").textContent =
    `${s.speakers.length} sprekers · ${data.segments.length} fragmenten · ${seconds(data.media.duration)} totaal. ${s.unseparated_overlap_count} overlapregio’s bevatten nog de oorspronkelijke mix.`;
  $("summary").className = s.unseparated_overlap_count ? "warning" : "";
  $("mix-mode").value = data.mix?.mode || "remove_radio";
  for (const option of $("mix-mode").options) {
    option.disabled = !!data.processing?.radio && ["remove_music", "remove_vocals"].includes(option.value);
  }
  $("mix-button").disabled = false;
  $("mix-note").textContent = data.mix
    ? "Nieuwe mix gereed. Gebruik cleaned.wav als één audiobestand onder video.mp4, of importeer timeline.xml voor de losse tracks. removed.wav laat horen wat is weggelaten. Speel de mix niet dubbel met de losse tracks af."
    : "Markeer een radiospreker of losse radio-/reclamefragmenten. Radiostemmen apart zetten werkt ook zonder muziekscheiding. Je kunt de selectie aanpassen zonder opnieuw te analyseren.";
  $("processing-note").textContent = data.processing?.radio
    ? `Radiovermindering met lokale referentie toegepast. ${data.processing.radio.matches ? data.processing.radio.matches.length + " bekende reclamefragmenten gevonden. " : ""}Luister cleaned.wav en de verwijderde radio na: resten of spraaklekkage blijven mogelijk. Achtergrond/rest en eventuele muziek blijven als losse tracks beschikbaar.`
    : data.processing?.music
      ? "Muziek is apart gezet; zang en vergaderstemmen kunnen samen in de stemmix blijven. Dit is geen gegarandeerde verwijdering van een radiozanger."
      : "Achtergrond/rest bewaart geluid buiten de sprekertracks. Muziek onder spraak kan nog in die sprekertracks zitten. Voor scheiding: gebruik de optie “Muziek apart zetten”.";
  if (data.processing?.ad_detection && !data.processing.ad_detection.applied) {
    $("processing-note").textContent += " Geen sterke match met de reclamebibliotheek; de audio is daarvoor ongewijzigd gebleven.";
  }
  if (data.processing?.voice_group_overflow) {
    $("processing-note").textContent += " " + data.processing.voice_group_overflow.note;
  }
  if (data.processing?.ad_text) {
    $("processing-note").textContent += ` ${data.processing.ad_text.candidates.length} tekstvensters met mogelijke reclame. ${data.processing.ad_text.note}`;
  }
  $("video").src = `/api/jobs/${id}/media/input.mp4`;
  $("ad-matches").replaceChildren();
  for (const match of (data.processing?.ad_detection?.matches || [])) {
    const jump = document.createElement("button");
    jump.className = "secondary";
    jump.textContent = `Geluidsmatch: ${match.name} · ${seconds(match.start)}–${seconds(match.end)}`;
    jump.onclick = () => { $("video").currentTime = match.start; $("video").play().catch(error); };
    $("ad-matches").append(jump);
  }
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
    const selectLabel = document.createElement("label");
    selectLabel.className = "check";
    const select = document.createElement("input");
    select.type = "checkbox";
    select.className = "radio-speaker";
    select.dataset.speaker = speaker;
    select.checked = (data.mix?.excluded_speakers || []).includes(speaker);
    selectLabel.append(
      select,
      document.createTextNode(
        "Hele spreker is radio/reclame/zang — apart zetten",
      ),
    );
    div.append(label, canvas, audio, selectLabel);
    $("tracks").append(div);
  }
  for (const track of [...(data.tracks || []), ...(data.mix_tracks || [])].filter(
    (t) => !t.id.startsWith("speaker_"),
  )) {
    const div = document.createElement("div");
    div.className = "track";
    const label = document.createElement("strong");
    label.textContent = track.name;
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "none";
    audio.src = `/api/jobs/${id}/media/${track.file}`;
    div.append(label, audio);
    if (track.id === "radio_voices") {
      const download = document.createElement("a");
      download.href = audio.src;
      download.download = "radio_voices.wav";
      download.textContent = "Download radiostemmen en reclame";
      div.append(download);
    }
    $("tracks").append(div);
  }
  if (data.processing?.radio || data.mix) {
    const div = document.createElement("div");
    div.className = "track";
    const label = document.createElement("strong");
    label.textContent =
      "Gekozen volledige mix — cleaned.wav (niet dubbel met losse tracks afspelen)";
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "none";
    audio.src = `/api/jobs/${id}/media/cleaned.wav`;
    div.append(label, audio);
    $("tracks").append(div);
    const link = document.createElement("a");
    link.href = audio.src;
    link.download = "cleaned.wav";
    link.className = "button";
    link.textContent = "Download deze mix voor Premiere";
    div.append(link);
    if (data.mix) {
      const removed = document.createElement("audio");
      removed.controls = true;
      removed.preload = "none";
      removed.src = `/api/jobs/${id}/media/removed.wav`;
      const note = document.createElement("p");
      note.textContent = "Controle: dit is weggelaten (removed.wav)";
      div.append(note, removed);
    }
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
    const preview = document.createElement("button");
    preview.textContent = "▶ Stemfragment";
    preview.className = "secondary";
    preview.onclick = () => {
      $("video").pause();
      const audio = $("fragment-preview");
      audio.src = `/api/jobs/${id}/media/speaker_${String(x.speaker).padStart(2, "0")}.wav`;
      audio.currentTime = x.start;
      audio.ontimeupdate = () => { if (audio.currentTime >= x.end) audio.pause(); };
      audio.play().catch(error);
    };
    td.append(preview);
    tr.append(td);
    const selection = document.createElement("td");
    const label = document.createElement("label");
    const check = document.createElement("input");
    check.type = "checkbox";
    check.className = "radio-fragment";
    check.dataset.fragment = x.fragment;
    check.checked = (data.mix?.excluded_fragments || []).includes(x.fragment);
    label.append(check, document.createTextNode("Radio / reclame"));
    selection.append(label);
    const textClues = (data.processing?.ad_text?.candidates || []).filter(
      (c) => c.start < x.end && c.end > x.start,
    );
    if (textClues.length) {
      const clue = document.createElement("small");
      const labels = [...new Set(textClues.flatMap((c) => c.matches.map((m) => m.label)))];
      clue.textContent = ` Mogelijke reclame in omgeving: ${labels.join(', ')}. Beluister en bevestig zelf.`;
      clue.title = textClues.map((c) => c.text).join('\n');
      selection.append(clue);
    }
    const overlap = (data.overlaps || []).some(
      (o) => o.start < x.end && o.end > x.start && o.method === "mixed",
    );
    if (overlap) {
      const note = document.createElement("small");
      note.textContent = " Gemengde overlap: ook gesprek kan meekomen.";
      selection.append(note);
    }
    tr.append(selection);
    $("segments").append(tr);
  }
  $("result").hidden = false;
}
$("mix-button").onclick = async () => {
  try {
    $("error").textContent = "";
    const excluded = Array.from(
      document.querySelectorAll(".radio-speaker:checked"),
    ).map((x) => Number(x.dataset.speaker));
    await api(`/api/jobs/${current}/mix`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: $("mix-mode").value,
        excluded_speakers: excluded,
        excluded_fragments: Array.from(
          document.querySelectorAll(".radio-fragment:checked"),
        ).map((x) => Number(x.dataset.fragment)),
      }),
    });
    $("mix-button").disabled = true;
    $("result").hidden = true;
    busy = true;
    $("start").disabled = true;
    clearTimeout(timer);
    poll();
  } catch (e) {
    error(e);
    $("mix-button").disabled = false;
  }
};
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
    label.textContent = `${j.project?.name || j.id.slice(0, 8)} · ${j.project?.created_at ? new Date(j.project.created_at*1000).toLocaleString('nl-NL') + ' · ' : ''}${j.phase || j.state}`;
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
    const folder = document.createElement('button'); folder.className = 'secondary'; folder.textContent = 'Map';
    folder.onclick = async () => { try { await api(`/api/jobs/${j.id}/open-folder`, {method:'POST'}); } catch(e) { error(e); } };
    row.append(folder);
    $("history").append(row);
  }
}
system();
async function adLibrary() {
  const entries = await api('/api/ad-library');
  $("ad-library").replaceChildren();
  for (const entry of entries) {
    const row = document.createElement('div');
    row.className = 'row';
    const name = document.createElement('span');
    name.textContent = `${entry.name} · ${seconds(entry.duration)}`;
    const remove = document.createElement('button');
    remove.className = 'secondary';
    remove.textContent = 'Voorbeeld verwijderen';
    remove.onclick = async () => {
      try { await api(`/api/ad-library/${entry.id}`, {method:'DELETE'}); await adLibrary(); }
      catch(e) { error(e); }
    };
    row.append(name, remove);
    $("ad-library").append(row);
  }
  $("ad-library-status").textContent = `${entries.length} lokale reclamevoorbeelden. Worden niet online gedeeld.`;
  $("known-ads").disabled = entries.length === 0;
  if (!adLibraryLoaded) $("known-ads").checked = entries.length > 0;
  if (!entries.length) $("known-ads").checked = false;
  adLibraryLoaded = true;
}
$("ad-add").onclick = async () => {
  const file = $("ad-file").files[0];
  if (!file) { error(new Error('Kies eerst een reclamevoorbeeld.')); return; }
  $("ad-add").disabled = true;
  try {
    await api('/api/ad-library', {method:'POST', headers:{'Content-Type':'application/octet-stream', 'X-Filename':encodeURIComponent(file.name)}, body:file});
    $("ad-file").value = '';
    await adLibrary();
    $("known-ads").checked = true;
  } catch(e) { error(e); }
  finally { $("ad-add").disabled = false; }
};
adLibrary().catch(error);
history().catch(error);
api('/api/storage').then(s => { $("storage-path").textContent = `Projecten worden bewaard in: ${s.projects_dir}`; }).catch(error);
$("open-storage").onclick = async () => { try { await api('/api/storage/open', {method:'POST'}); } catch(e) { error(e); } };
$("open-output").onclick = async () => { try { await api(`/api/jobs/${current}/open-folder`, {method:'POST'}); } catch(e) { error(e); } };
$("quit-app").onclick = async () => {
  if (!confirm(busy ? 'De app afsluiten? De lopende verwerking stopt. Bewaarde projecten blijven staan.' : 'De lokale app afsluiten? Je projecten blijven bewaard.')) return;
  try { await api('/api/app/quit', {method:'POST'}); clearTimeout(timer); $("system").textContent = 'App afgesloten. Je projecten blijven lokaal bewaard. Start Multitrackert Audio opnieuw via het Startmenu.'; }
  catch(e) { error(e); }
};
