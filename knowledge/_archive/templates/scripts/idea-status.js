const STATUS_ORDER = ["init", "active", "finished"];

const STATUS_LABELS = {
  init: "Init",
  active: "Active",
  finished: "Finished",
};

const STATUS_COLORS = {
  init: "#64748b",
  active: "#2563eb",
  finished: "#16a34a",
};

const filePath = input?.file?.path ?? dv.current()?.file?.path;
const file = filePath ? app.vault.getAbstractFileByPath(filePath) : null;

if (!file || !("path" in file)) {
  dv.paragraph("idea-status: файл не найден");
  return;
}

const cache = app.metadataCache.getFileCache(file) ?? {};
const frontmatter = cache.frontmatter ?? {};
const currentStatus = String(frontmatter.status ?? "init").trim().toLowerCase();
const content = await app.vault.cachedRead(file);
const taskMatches = [...content.matchAll(/^- \[( |x)\] /gm)];
const totalTasks = taskMatches.length;
const doneTasks = taskMatches.filter(([, mark]) => mark === "x").length;

function nowStamp() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
  ].join("-") + " " + [pad(now.getHours()), pad(now.getMinutes())].join(":");
}

function inferStatus() {
  if (totalTasks > 0 && doneTasks === totalTasks) {
    return "finished";
  }

  if (doneTasks > 0 || /status:\s*active/i.test(content)) {
    return "active";
  }

  return "init";
}

async function updateIdeaStatus(nextStatus) {
  await app.fileManager.processFrontMatter(file, (fm) => {
    fm.status = nextStatus;
    fm.updated = nowStamp();
  });

  new Notice(`Idea status -> ${nextStatus}`);
}

const suggestedStatus = inferStatus();
const wrapper = dv.el("div", "", { cls: "idea-status-view" });
wrapper.style.border = "1px solid var(--background-modifier-border)";
wrapper.style.borderRadius = "12px";
wrapper.style.padding = "12px";
wrapper.style.marginTop = "8px";

const header = wrapper.createDiv({ cls: "idea-status-header" });
header.style.display = "flex";
header.style.gap = "8px";
header.style.alignItems = "center";
header.style.flexWrap = "wrap";

const statusBadge = header.createEl("span", {
  text: `Status: ${STATUS_LABELS[currentStatus] ?? currentStatus}`,
});
statusBadge.style.display = "inline-flex";
statusBadge.style.alignItems = "center";
statusBadge.style.padding = "4px 10px";
statusBadge.style.borderRadius = "999px";
statusBadge.style.fontWeight = "600";
statusBadge.style.background = STATUS_COLORS[currentStatus] ?? "#64748b";
statusBadge.style.color = "#ffffff";

const taskBadge = header.createEl("span", {
  text: totalTasks > 0 ? `Tasks: ${doneTasks}/${totalTasks}` : "Tasks: none",
});
taskBadge.style.color = "var(--text-muted)";

if (frontmatter.updated) {
  const updatedBadge = header.createEl("span", {
    text: `Updated: ${frontmatter.updated}`,
  });
  updatedBadge.style.color = "var(--text-muted)";
}

const buttons = wrapper.createDiv({ cls: "idea-status-buttons" });
buttons.style.display = "flex";
buttons.style.flexWrap = "wrap";
buttons.style.gap = "8px";
buttons.style.marginTop = "12px";

for (const status of STATUS_ORDER) {
  const button = buttons.createEl("button", {
    text: STATUS_LABELS[status],
  });

  button.style.padding = "6px 10px";
  button.style.borderRadius = "8px";
  button.style.border = "1px solid var(--background-modifier-border)";
  button.style.cursor = "pointer";
  button.style.background =
    status === currentStatus ? "var(--interactive-accent)" : "var(--background-secondary)";
  button.style.color = status === currentStatus ? "var(--text-on-accent)" : "var(--text-normal)";

  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await updateIdeaStatus(status);
    } finally {
      button.disabled = false;
    }
  });
}

if (suggestedStatus !== currentStatus) {
  const hint = wrapper.createDiv({
    text: `Рекомендуемый статус по чекбоксам: ${STATUS_LABELS[suggestedStatus] ?? suggestedStatus}`,
  });
  hint.style.marginTop = "12px";
  hint.style.color = "var(--text-muted)";

  const applySuggested = wrapper.createEl("button", {
    text: "Применить рекомендуемый",
  });
  applySuggested.style.marginTop = "8px";
  applySuggested.style.padding = "6px 10px";
  applySuggested.style.borderRadius = "8px";
  applySuggested.style.border = "1px solid var(--background-modifier-border)";
  applySuggested.style.cursor = "pointer";

  applySuggested.addEventListener("click", async () => {
    applySuggested.disabled = true;
    try {
      await updateIdeaStatus(suggestedStatus);
    } finally {
      applySuggested.disabled = false;
    }
  });
}
