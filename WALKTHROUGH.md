# Bastion — Beginner Walkthrough (Jupyter + AMD, zero assumed knowledge)

Your private repo (already pushed): **https://github.com/techstroll/bastion-amd-hackathon**

This doc has one job: tell you **exactly where to click**. Do the steps in order.
Total time: ~1–2 hours, most of it waiting for downloads/training.

---

## Part 0 — Words you'll see, in plain language

- **Jupyter Notebook** = a webpage where you run code in little boxes called
  "cells." Click a cell, press the ▶ (Run) button, it executes.
- **Terminal** (inside Jupyter) = a black text window where you type commands
  instead of clicking. We'll use this more than the notebook cells — it's
  just faster for what we're doing.
- **GPU** = the AMD MI300X chip your notebook rents. All the heavy AI work
  runs on it.
- **Model** = the AI brain (e.g. "Llama-3.1-8B"). **LoRA adapter** = a small
  file that customizes that brain for one department (legal/finance) without
  retraining the whole thing.
- **vLLM** = the program that "serves" the model — i.e. turns it into an API
  you can send questions to.
- **Router** = our own small program (already written) that decides which
  model answers each question.
- **Container / Docker** = a box that packages our router so it runs
  identically anywhere — the hackathon requires this.

---

## Part 1 — Get your AMD notebook running

1. Go back to the lablab.ai hackathon page → **Technology & Access** section
   → click **AMD AI Developer Program** if you haven't signed up, then find
   the notebook launcher (the dropdown you screenshotted earlier).
2. In the dropdown, confirm **"ROCm 7.2 + vLLM 0.16.0 + PyTorch 2.9"** is
   selected (it's the one with the checkmark). Do **not** pick the Unsloth one.
3. Click **Request Notebook**. Wait — this can take a few minutes while it
   provisions a GPU for you.
4. Once ready, you'll see a **link/button to open Jupyter** (often labeled
   "Open" or a URL). Click it — a new browser tab opens with the Jupyter
   interface (looks like a file browser).
5. In that Jupyter file browser, look for a menu **File → New → Terminal**
   (or a "Terminal" icon/tile on the launcher screen). Click it. A black
   terminal window opens inside your browser tab. **This is where you'll type
   everything for the rest of Part 1 and Part 2.**

---

## Part 2 — Get the code onto the GPU machine

In the terminal you just opened, type each line below and press Enter.
(You can copy-paste; right-click → Paste usually works in these terminals.)

```bash
git clone https://github.com/techstroll/bastion-amd-hackathon.git
cd bastion-amd-hackathon
ls
```

You should see `PLAN.md`, `router/`, `gpu/`, `dashboard/`, etc. printed out —
that confirms the code arrived.

---

## Part 3 — Install the extra Python packages we need for training

Still in the terminal:

```bash
pip install peft datasets transformers
```

This takes 1–3 minutes. Lines will scroll by — that's normal. Wait until you
get your terminal prompt back (no more scrolling).

**If Llama-3.1-8B fails to download (gated model):**
Meta requires a free Hugging Face account + accepting their license before
you can download Llama models. If you hit an error mentioning "gated repo"
or "401", tell me and I'll swap the base model in the scripts to an
ungated one (Qwen2.5-7B) — one-line change, no need to solve the Meta
approval process under time pressure.

---

## Part 4 — Train the two department "brains" (LoRA adapters)

This teaches the AI to answer like a legal team and like a finance team,
using the sample data already in `gpu/datasets/`. It trains **on this GPU** —
nothing leaves the machine, which is the whole point of our pitch.

```bash
python gpu/finetune_lora.py --tenant legal
```

Wait for it to finish — you'll see training progress lines, then a final
line like `✅ legal-lora saved to ...`. Takes a few minutes.

Then do the same for finance:

```bash
python gpu/finetune_lora.py --tenant finance
```

---

## Part 5 — Turn the AI into an API (start the server)

This is the step that makes the model "listen" for questions.

```bash
bash gpu/serve_multilora.sh
```

You'll see a bunch of log lines. **Wait until you see something like
`Application startup complete`** — that means it's ready. Leave this running
(don't close the terminal). If you want, open a **second terminal**
(File → New → Terminal again) for the next steps so this one keeps running.

To double check it's working, in the **second terminal**, run:

```bash
curl -s localhost:8000/v1/models
```

You should see text mentioning `legal-lora` and `finance-lora`. That means
your one GPU is now serving two custom department models. 🎉

**Optional (only if you have extra time):** also start the big 70B model for
"hard" questions:
```bash
ENABLE_70B=1 bash gpu/serve_multilora.sh
```

**Take a screenshot now** of this command's output — it's your proof slide:
```bash
rocm-smi --showmeminfo vram
```

---

## Part 6 — Start the router (the part judges actually talk to)

Still in the second terminal, inside the `bastion-amd-hackathon` folder:

```bash
pip install fastapi "uvicorn[standard]" httpx
uvicorn router.main:app --host 0.0.0.0 --port 9000
```

Wait for `Application startup complete` again.

### See the dashboard
Jupyter notebooks usually expose a way to preview a running web app. Look for
a **"Ports"** tab/panel in the Jupyter/ADC interface (often on the left
sidebar) — find port **9000**, click it, and it opens the dashboard in a new
tab. If there's no ports panel, ask me and I'll help you find the public URL
for this notebook.

You should see the **Bastion** dashboard — mostly empty/zero right now. That's
expected, we haven't sent any questions yet.

---

## Part 7 — Add your Fireworks key (so the "cheap tier" works)

1. Get your Fireworks API key from the hackathon credits/dashboard (starts
   with `fw_...`).
2. In the terminal (Ctrl+C to stop the router first, or use a third terminal):

```bash
export FIREWORKS_API_KEY=fw_paste_your_key_here
```

3. Restart the router:
```bash
uvicorn router.main:app --host 0.0.0.0 --port 9000
```

---

## Part 8 — Run the demo (this is what you'll record)

Open **another terminal** (keep the server ones running), go into the folder,
and run:

```bash
cd bastion-amd-hackathon
python demo/send_demo_traffic.py --router http://localhost:9000
```

You'll see 8 lines print, one per simulated question. **Switch to your
dashboard browser tab while this runs** — watch the numbers and the table
update live. This is the moment to have your screen recorder already running.

---

## Part 9 — Record the demo video

Simple screen-recording plan (use your OS's built-in recorder — Mac:
Cmd+Shift+5, Windows: Win+G, or QuickTime/OBS):

1. **Start recording.**
2. Show the terminal with the `rocm-smi` screenshot output (or re-run it) —
   say out loud: *"One AMD MI300X GPU, 192 GB, serving our base model plus
   two custom department models at the same time."*
3. Switch to the dashboard tab (empty/zero state).
4. In a terminal, run `python demo/send_demo_traffic.py`.
5. Narrate as it runs / as the dashboard updates:
   - Point at a **public question** → routed to **Fireworks** (external).
   - Point at a **confidential question** → routed to **local LoRA**, egress
     counter **stays at 0** — this is your money shot, say it explicitly:
     *"Sensitive data never leaves the GPU."*
   - Point at the **same question asked to Legal vs Finance** → show the two
     different answer styles — proof one GPU serves two distinct "brains."
   - Point at the **hard question** → routed to the 70B path.
6. End on the dashboard wide shot (cost saved, egress = 0, engine
   distribution chart).
7. **Stop recording.** 2–3 minutes total is plenty.

---

## Part 10 — Package for submission (containerize + push final code)

Back in a terminal (can be on your own laptop, doesn't need the GPU):

```bash
cd /Users/nick/Development/amd_hackathon
docker compose up --build
```

This proves the router runs in a container (the hackathon's requirement).
Ctrl+C to stop it once you've confirmed it starts without errors.

Push any changes (like the Fireworks key setup, if you edited files):

```bash
git add -A
git commit -m "Final demo run"
git push
```

**If your repo needs to be public for judging**, tell me and I'll flip it —
right now it's private under your `techstroll` account.

---

## Part 11 — Submit on lablab.ai

Go back to the hackathon page → find the **Submit** button → fill in:
- Repo URL: `https://github.com/techstroll/bastion-amd-hackathon`
- Demo video: upload/link the recording from Part 9
- Track: **Unicorn Track**
- Description: copy the one-liner from `pitch/PITCH.md`

Full checklist also in `SUBMISSION.md` in the repo.

---

## If something breaks

Tell me the **exact error text** you see and which Part number you were on —
that's enough for me to fix it fast. Common ones I already expect:
- Llama-3.1-8B download fails → gated model, see Part 3 note.
- `curl: command not found` → some notebooks don't have curl; skip that
  check, just trust the "Application startup complete" message.
- Port 9000/8000 not reachable from the dashboard link → notebook networking
  quirk, tell me what the "Ports" panel shows and I'll adjust.
