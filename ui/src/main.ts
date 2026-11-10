interface LinkResponse {
  code: string;
}

interface ErrorResponse {
  detail?: string;
}

const form = document.getElementById("shorten-form") as HTMLFormElement;
const input = document.getElementById("url-input") as HTMLInputElement;
const submitBtn = form.querySelector("button") as HTMLButtonElement;
const errorEl = document.getElementById("error") as HTMLParagraphElement;
const resultEl = document.getElementById("result") as HTMLDivElement;
const shortLink = document.getElementById("short-url") as HTMLAnchorElement;
const copyBtn = document.getElementById("copy-btn") as HTMLButtonElement;

function showError(message: string): void {
  errorEl.textContent = message;
  errorEl.hidden = false;
  resultEl.hidden = true;
}

function hideError(): void {
  errorEl.hidden = true;
}

function setLoading(on: boolean): void {
  submitBtn.disabled = on;
  submitBtn.textContent = on ? "Working…" : "Shorten";
}

async function shorten(rawUrl: string): Promise<void> {
  hideError();

  const value = rawUrl.trim();
  if (!value) {
    showError("Please enter a URL.");
    return;
  }

  // The input has type="url" but browsers accept some junk. Mirror the
  // server's rule so the user gets instant feedback.
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    showError("That does not look like a URL.");
    return;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    showError("URL must start with http:// or https://");
    return;
  }

  setLoading(true);
  try {
    const resp = await fetch("/links", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ url: parsed.toString() }),
    });

    if (!resp.ok) {
      const body = (await resp.json().catch(() => ({}))) as ErrorResponse;
      throw new Error(body.detail ?? `HTTP ${resp.status}`);
    }

    const { code } = (await resp.json()) as LinkResponse;
    const shortUrl = `${window.location.origin}/${code}`;

    shortLink.href = shortUrl;
    shortLink.textContent = shortUrl;
    resultEl.hidden = false;
    copyBtn.textContent = "Copy";
    input.value = "";
    input.focus();
  } catch (err) {
    showError(err instanceof Error ? err.message : "Request failed.");
  } finally {
    setLoading(false);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  void shorten(input.value);
});

copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(shortLink.href);
    copyBtn.textContent = "Copied";
    window.setTimeout(() => {
      copyBtn.textContent = "Copy";
    }, 1500);
  } catch {
    showError("Could not copy — select the link manually.");
  }
});