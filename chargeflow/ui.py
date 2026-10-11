"""Design system and custom HTML components for the ChargeFlow dashboard.

Presentation only: everything here receives numbers computed by scheduler.py.

Art direction: Swiss editorial layout on warm paper, ink typography, one cobalt
accent. Colour carries meaning only:
- cobalt     the ChargeFlow plan being viewed, and grid power
- graphite   uncontrolled plug-in-and-charge, always
- gray       the other ChargeFlow variant when shown as a comparison
- amber      the sanctioned-load threshold, and nothing else
- vermilion  a violation: over the limit, or a rickshaw left short
- yellow     solar,  teal  second-life storage
"""
import hashlib
import json
import math
from html import escape

PAPER = "#F4F2EC"
PAPER_2 = "#ECE9E2"
INK = "#171A20"
INK_2 = "#4A4F57"
INK_3 = "#6B7078"
RULE = "#D6D2C7"
GRID = "#E4E0D7"
COBALT = "#2457D6"
GRAPHITE = "#2B2F36"
GRAY = "#8E9198"
AMBER = "#C98200"
AMBER_TEXT = "#8A5A00"
VERMILION = "#C8412A"
SOLAR = "#E8B730"
STORAGE = "#2A8C82"
SANS = "Inter, 'Helvetica Neue', Arial, sans-serif"
DISPLAY = "'Inter Tight', Inter, 'Helvetica Neue', Arial, sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, Menlo, Consolas, monospace"


# ---------------------------------------------------------------- motion runtime
# Tweens numbers and CSS properties from the values this tab last displayed to the
# new ones; injects SVG (Streamlit's sanitiser strips <svg> from st.html); runs once
# per mounted block, so unrelated reruns never replay anything. It also records the
# reduced-motion preference in a cookie so the server can turn chart transitions off.
RUNTIME = """
window.CF = window.CF || (function () {
  const prev = {}, blocks = {};
  const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
  const setPref = () => { document.cookie = 'cf_rm=' + (mq.matches ? 1 : 0) + '; path=/; SameSite=Lax; max-age=31536000'; };
  setPref(); mq.addEventListener && mq.addEventListener('change', setPref);
  const ease = t => 1 - Math.pow(1 - t, 3);
  const fmt = (v, d) => v.toLocaleString('en-IN', {minimumFractionDigits: d, maximumFractionDigits: d});
  function num(el) {
    const key = el.dataset.num, to = parseFloat(el.dataset.to), d = +(el.dataset.dec || 0);
    const from = prev[key]; prev[key] = to;
    if (mq.matches || from === undefined || Math.abs(from - to) < 1e-9) return;
    const t0 = performance.now(), dur = 260;
    el.textContent = fmt(from, d);
    (function step(now) {
      const p = Math.min(1, Math.max(0, (now - t0) / dur));
      el.textContent = fmt(from + (to - from) * ease(p), d);
      if (p < 1) requestAnimationFrame(step); else el.textContent = fmt(to, d);
    })(t0);
  }
  function prop(el) {
    const key = el.dataset.anim, name = el.dataset.prop, to = el.dataset.to;
    const from = prev[key]; prev[key] = to;
    if (mq.matches || from === undefined || from === to) return;
    const saved = el.style.transition;
    el.style.transition = 'none';
    el.style.setProperty(name, from);
    el.getBoundingClientRect();
    el.style.transition = saved;
    requestAnimationFrame(() => el.style.setProperty(name, to));
  }
  function sync() {
    for (const id in blocks) {
      const b = blocks[id], root = document.getElementById(id);
      if (!root || root.dataset.cfDone || root.dataset.cfv !== b.version) continue;
      root.dataset.cfDone = '1';
      for (const sel in b.inject) {
        const el = root.querySelector(sel);
        if (el) el.innerHTML = b.inject[sel];
      }
      root.querySelectorAll('[data-num]').forEach(num);
      root.querySelectorAll('[data-anim]').forEach(prop);
    }
  }
  let queued = false;
  new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; sync(); });
  }).observe(document.body, {childList: true, subtree: true});
  return {block(id, version, inject) { blocks[id] = {version, inject: inject || {}}; sync(); }};
})();
"""


def _block(block_id, markup, inject=None):
    inject = inject or {}
    version = hashlib.md5((markup + json.dumps(inject)).encode()).hexdigest()[:12]
    markup = markup.replace(f'id="{block_id}"', f'id="{block_id}" data-cfv="{version}"', 1)
    payload = json.dumps(inject).replace("<", "\\u003c")
    return f'{markup}<script>{RUNTIME}window.CF.block({json.dumps(block_id)}, "{version}", {payload});</script>'


def num(key, value, decimals=0):
    """A number that tweens from its previously displayed value."""
    return (f'<span class="tn" data-num="{escape(key)}" data-to="{value:.{decimals}f}" '
            f'data-dec="{decimals}">{value:,.{decimals}f}</span>')


def anim(key, prop, value, extra=""):
    """Inline style + data attributes for a CSS property that tweens on change."""
    return f'style="{prop}:{value};{extra}" data-anim="{escape(key)}" data-prop="{prop}" data-to="{value}"'


def fmt_min(m):
    h, m = divmod(int(m), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


# ---------------------------------------------------------------- stylesheet
CSS = """
:root {
  --paper:#F4F2EC; --paper-2:#ECE9E2; --paper-3:#E3DFD6; --surface:#FFFFFF;
  --ink:#171A20; --ink-2:#4A4F57; --ink-3:#6B7078; --rule:#D6D2C7; --rule-soft:#E4E0D7;
  --cobalt:#2457D6; --cobalt-ink:#173C9E; --cobalt-wash:#E3E9F8;
  --amber:#C98200; --amber-text:#8A5A00; --vermilion:#C8412A; --vermilion-wash:#F6E1DB;
  --solar:#E8B730; --storage:#2A8C82;
  --sans: Inter, "Helvetica Neue", Arial, sans-serif;
  --display: "Inter Tight", Inter, "Helvetica Neue", Arial, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
  --r1:2px; --r2:4px; --r3:8px;
  --ease: cubic-bezier(.2,0,0,1); --ease-out: cubic-bezier(.16,1,.3,1);
  --gutter: 48px;
}

/* ---------- canvas and type */
.stApp { background: var(--paper); }
.stApp, .stApp p, .stApp label { font-feature-settings: "cv11", "ss01"; }
.tn, .tab { font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
[data-testid="stHeader"] { background: transparent; height: 0; min-height: 0; overflow: visible; }
[data-testid="stDecoration"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"],
[data-testid="stToolbarActions"], [data-testid="stStatusWidget"] { display: none !important; }
[data-testid="stExpandSidebarButton"] {
  position: fixed !important; top: 14px; left: 10px; z-index: 1000; width: 36px; height: 36px;
  border-radius: var(--r2); display: inline-flex !important; align-items: center; justify-content: center;
  background: var(--paper) !important; box-shadow: 0 0 0 1px var(--rule);
  transition: background-color .15s var(--ease);
}
[data-testid="stExpandSidebarButton"]:hover { background: var(--paper-2) !important; }
[data-testid="stMainBlockContainer"] { padding: 0 var(--gutter) 96px; max-width: 1640px; }
.stApp button:focus-visible, .stApp input:focus-visible, .stApp [role="tab"]:focus-visible,
.stApp [role="radio"]:focus-visible, .stApp a:focus-visible {
  outline: 2px solid var(--cobalt) !important; outline-offset: 2px;
}

/* ---------- masthead */
.st-key-masthead {
  margin: 0 calc(-1 * var(--gutter)); width: calc(100% + 2 * var(--gutter)) !important; max-width: none !important;
  padding: 18px var(--gutter) 14px; box-sizing: border-box; border-bottom: 1px solid var(--ink);
}
.stApp:has([data-testid="stExpandSidebarButton"]) .st-key-masthead { padding-left: calc(var(--gutter) + 36px); }
.st-key-masthead > [data-testid="stElementContainer"]:first-child { flex: 1 1 auto !important; min-width: 140px; }
.st-key-masthead > [data-testid="stElementContainer"]:not(:first-child) { flex: none !important; }
.cf-mast { display: flex; align-items: baseline; gap: 18px; white-space: nowrap; overflow: hidden; }
.cf-word { font: 600 22px/28px var(--display); letter-spacing: -.02em; color: var(--ink); }
.cf-word i { font-style: normal; color: var(--cobalt); }
.cf-mast-cap { font: 400 11px/16px var(--mono); letter-spacing: .04em; text-transform: uppercase; color: var(--ink-3);
  overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.st-key-masthead .stButton button, .st-key-masthead .stDownloadButton button {
  border: none; background: transparent; box-shadow: none; min-height: 32px; padding: 4px 10px; color: var(--ink-2);
  border-radius: var(--r2); transition: color .15s var(--ease), background-color .15s var(--ease);
}
.st-key-masthead .stButton button p, .st-key-masthead .stDownloadButton button p { font: 500 13px/18px var(--sans); }
.st-key-masthead .stButton button:hover, .st-key-masthead .stDownloadButton button:hover {
  background: rgba(23,26,32,.05); color: var(--ink);
}
.st-key-masthead [data-testid="stIconMaterial"] { font-size: 18px; }
.stButton button:active, .stDownloadButton button:active, [data-testid="stButtonGroup"] button:active { transform: translateY(1px); }

/* ---------- section heads */
.cf-sec { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
.cf-sec .n { font: 500 12px/16px var(--mono); color: var(--cobalt); letter-spacing: .02em; }
.cf-sec h2 {
  font: 600 13px/18px var(--sans) !important; letter-spacing: .08em; text-transform: uppercase; margin: 0 !important;
  padding: 0 !important; color: var(--ink);
}
.cf-sec .note { font: 400 13px/18px var(--sans); color: var(--ink-3); }
.cf-sec.ruled { border-top: 1px solid var(--ink); padding-top: 14px; }
.st-key-outcome { padding-top: 34px; }
.st-key-outhead [data-testid="stHorizontalBlock"] { flex-wrap: wrap; row-gap: 14px; }
.st-key-outhead [data-testid="stColumn"]:first-child { flex: 1 1 380px !important; }
.st-key-outhead [data-testid="stColumn"]:last-child { flex: 0 1 auto !important; width: auto !important; max-width: 100%; }
.st-key-figs [data-testid="stHorizontalBlock"] { flex-wrap: wrap; column-gap: 72px; row-gap: 36px; }
.st-key-figs [data-testid="stColumn"] { flex: 1 1 400px !important; min-width: min(100%, 340px); }
.st-key-sec2, .st-key-sec3 { margin-top: 60px; }
.st-key-outcome [data-testid="stWidgetLabel"] p { font: 400 11px/16px var(--mono); letter-spacing: .04em; text-transform: uppercase; color: var(--ink-3); }

/* ---------- scenario control: hairline segmented, ink when selected */
[data-variant="segmented_control"] {
  background: transparent; color: var(--ink-2); border-color: var(--rule); min-height: 36px;
  transition: background-color .18s var(--ease), color .18s var(--ease), border-color .18s var(--ease);
}
[data-variant="segmented_control"] p { font: 500 13px/18px var(--sans); }
[data-variant="segmented_control"]:hover { background: rgba(23,26,32,.04); color: var(--ink); border-color: var(--rule); }
[data-variant="segmented_control"][data-selected="true"] {
  background: var(--ink) !important; color: var(--paper) !important; border-color: var(--ink) !important;
}
/* compare toggles: square check-style chips */
[data-variant="pills"] {
  background: transparent; color: var(--ink-2); border: 1px solid var(--rule); border-radius: var(--r1) !important;
  min-height: 30px !important; padding: 3px 12px 3px 10px !important;
  transition: background-color .18s var(--ease), color .18s var(--ease), border-color .18s var(--ease);
}
[data-variant="pills"] p { font: 500 12.5px/18px var(--sans); }
[data-variant="pills"]::before {
  content: ""; width: 9px; height: 9px; margin-right: 8px; border: 1px solid var(--ink-3); border-radius: 1px;
  transition: background-color .18s var(--ease), border-color .18s var(--ease); flex: none;
}
[data-variant="pills"]:hover { border-color: var(--ink-3); color: var(--ink); background: transparent; }
[data-variant="pills"][data-selected="true"] { color: var(--ink) !important; border-color: var(--ink) !important; background: transparent !important; }
[data-variant="pills"][data-selected="true"]::before { background: var(--ink); border-color: var(--ink); }

/* ---------- outcome: headline figures */
.cf-out { font-family: var(--sans); color: var(--ink); padding-top: 26px; }
.cf-lab { font: 400 11px/16px var(--mono); letter-spacing: .05em; text-transform: uppercase; color: var(--ink-3); margin: 0; }
.cf-fig { font: 500 104px/0.92 var(--display); letter-spacing: -.045em; margin: 14px 0 0; white-space: nowrap; }
.cf-fig small { font-size: .4em; letter-spacing: -.02em; color: var(--ink-3); margin-left: .08em; }
.cf-state { margin: 18px 0 0; padding-left: 19px; text-indent: -19px; font: 500 17px/24px var(--sans); max-width: 62ch; }
.cf-state::before { content: ""; display: inline-block; width: 9px; height: 9px; margin-right: 10px; vertical-align: 1px; background: var(--cobalt); }
.cf-state.bad::before { background: var(--vermilion); }
.cf-state span { font-weight: 400; color: var(--ink-2); }
.cf-bars { position: relative; display: flex; align-items: flex-end; gap: 4px; height: 56px; margin-top: 30px;
  border-bottom: 1px solid var(--ink); max-width: 560px; }
.cf-bars i { flex: 1 1 0; min-width: 2px; background: var(--cobalt); transition: height .45s var(--ease-out); }
.cf-bars i.short { background: var(--vermilion); }
.cf-bars .tgt { position: absolute; left: 0; right: 0; border-top: 1px dashed var(--ink-3); }
.cf-bars .tgt span { position: absolute; right: 0; top: -17px; font: 400 10.5px/14px var(--mono); color: var(--ink-3); background: var(--paper); padding-left: 6px; }
.cf-bars-cap { display: flex; justify-content: space-between; max-width: 560px; margin-top: 6px;
  font: 400 10.5px/14px var(--mono); color: var(--ink-3); letter-spacing: .03em; }

/* ruler gauge */
.cf-ruler { position: relative; height: 76px; margin-top: 30px; }
.cf-ruler .base { position: absolute; left: 0; right: 0; top: 38px; border-top: 1px solid var(--ink); }
.cf-ruler .tick { position: absolute; top: 38px; width: 1px; height: 6px; background: var(--ink); }
.cf-ruler .tick.major { height: 10px; }
.cf-ruler .tl { position: absolute; top: 52px; transform: translateX(-50%); font: 400 10.5px/14px var(--mono); color: var(--ink-3); }
.cf-ruler .bar { position: absolute; left: 0; top: 26px; height: 12px; background: var(--cobalt); transition: width .5s var(--ease-out); }
.cf-ruler .over { position: absolute; top: 26px; height: 12px; background: var(--vermilion); transition: width .5s var(--ease-out), left .5s var(--ease-out); }
.cf-ruler .lim { position: absolute; top: 6px; height: 48px; width: 2px; margin-left: -1px; background: var(--amber); transition: left .5s var(--ease-out); }
.cf-ruler .lim span, .cf-ruler .unc span {
  position: absolute; top: -2px; left: 8px; white-space: nowrap; font: 500 10.5px/14px var(--mono); letter-spacing: .03em;
}
.cf-ruler .lim span { color: var(--amber-text); }
.cf-ruler .lim.flip span, .cf-ruler .unc.flip span { left: auto; right: 8px; }
.cf-ruler .unc { position: absolute; top: 12px; height: 26px; width: 0; transition: left .5s var(--ease-out); }
.cf-ruler .unc::after { content: ""; position: absolute; left: -5px; bottom: 0; border: 5px solid transparent; border-top: 7px solid var(--ink); border-bottom: 0; }
.cf-ruler .unc span { color: var(--ink-2); top: -12px; }

/* data strip */
.cf-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(176px, 1fr)); margin-top: 40px;
  border-top: 1px solid var(--rule); font-family: var(--sans); }
.cf-strip > div { padding: 14px 20px 4px 0; margin-right: 20px; border-right: 1px solid var(--rule); min-width: 0; }
.cf-strip > div:last-child { border-right: none; }
.cf-strip .cf-lab { min-height: 32px; }
.cf-strip b { display: block; font: 500 24px/30px var(--display); letter-spacing: -.01em; margin-top: 8px; font-variant-numeric: tabular-nums; }
.cf-strip b small { font: 500 13px var(--sans); color: var(--ink-3); margin-left: 3px; letter-spacing: 0; }
.cf-strip em { display: block; font: 400 12px/16px var(--sans); font-style: normal; color: var(--ink-3); margin-top: 2px; }
.cf-strip b.bad { color: var(--vermilion); }

/* ---------- analysis surfaces and view tabs */
.st-key-ws { background: var(--surface); border: 1px solid var(--rule); border-radius: var(--r3); padding: 6px 32px 30px; margin-top: 18px; }
.st-key-sup { margin-top: 18px; }
.stApp [role="tablist"] { gap: 28px; box-shadow: inset 0 -1px 0 var(--rule); }
.stApp [data-testid="stTab"] { height: 46px; padding: 0 2px; margin: 0; color: var(--ink-3); background: transparent;
  transition: color .18s var(--ease); }
.stApp [data-testid="stTab"] p { font: 500 14px/20px var(--sans) !important; color: inherit; }
.stApp [data-testid="stTab"] code { background: none; padding: 0; margin-right: 8px; font: 400 11px var(--mono); color: var(--ink-3); }
.stApp [data-testid="stTab"]:hover { color: var(--ink); background: transparent; }
.stApp [data-testid="stTab"][aria-selected="true"] { color: var(--ink); }
.stApp [data-testid="stTab"][aria-selected="true"] code { color: var(--cobalt); }
.stApp [data-testid="stTab"][aria-selected="true"] > div[data-rac] { background: var(--cobalt) !important; height: 2px !important; border-radius: 0 !important; }
.stApp [role="tabpanel"] { padding-top: 22px; }
/* views fade up when opened (closed views aren't rendered, so this runs on open only) */
@keyframes cf-view { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.stApp [role="tabpanel"] > div > [data-testid="stVerticalBlock"] > * { animation: cf-view .32s var(--ease-out) both; }
.cf-vh { display: flex; flex-direction: column; gap: 3px; }
.cf-vh b { font: 600 18px/24px var(--display); letter-spacing: -.01em; color: var(--ink); }
.cf-vh span { font: 400 13px/18px var(--sans); color: var(--ink-3); }
.cf-note { font: 400 12.5px/18px var(--sans); color: var(--ink-3); margin: 0; }
.cf-note b { font-weight: 500; color: var(--ink-2); }
[data-testid="stExpander"] details { border: none; border-top: 1px solid var(--rule); border-radius: 0; background: transparent; }
[data-testid="stExpander"] summary { padding-left: 0; }
[data-testid="stExpander"] summary p { font: 500 13px var(--sans); color: var(--ink-2); }
[data-testid="stExpander"] summary:hover p { color: var(--cobalt); }

/* ---------- sidebar: subordinate instrument panel */
[data-testid="stSidebar"] { box-shadow: inset -1px 0 0 var(--rule); }
[data-testid="stSidebar"][aria-expanded="true"] { min-width: 292px !important; max-width: 292px !important; }
[data-testid="stSidebarUserContent"] { padding: 2px 22px 48px; }
.cf-side { font: 600 13px/18px var(--sans); letter-spacing: .08em; text-transform: uppercase; color: var(--ink);
  padding-bottom: 12px; border-bottom: 1px solid var(--ink); }
.cf-side span { display: block; font: 400 12px/17px var(--sans); letter-spacing: 0; text-transform: none; color: var(--ink-3); margin-top: 4px; }
.cf-grp { display: flex; gap: 10px; align-items: baseline; margin: 22px 0 2px; font: 500 11px/16px var(--mono);
  letter-spacing: .06em; text-transform: uppercase; color: var(--ink-2); }
.cf-grp span { color: var(--cobalt); }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font: 400 13px/18px var(--sans); color: var(--ink-2); }
[data-testid="stSliderThumbValue"] p { font: 500 11.5px/16px var(--mono) !important; color: var(--ink) !important; }
[data-testid="stSliderTickBarMin"] p, [data-testid="stSliderTickBarMax"] p, [data-testid="stSliderTickBar"] p {
  font: 400 10.5px var(--mono) !important; color: var(--ink-3) !important; }
[data-testid="stSlider"] [role="group"] > div > div[style*="left"]:not([data-testid]) {
  transition: box-shadow .18s var(--ease), scale .18s var(--ease);
}
[data-testid="stSlider"] [role="group"] > div > div[style*="left"]:not([data-testid]):hover { box-shadow: 0 0 0 6px rgba(36,87,214,.12); }
[data-testid="stSlider"] [role="group"] > div > div[style*="left"]:not([data-testid]):active { scale: 1.12; }
[data-testid="stSlider"] [role="group"] > div > div[style*="left"]:has(input:focus-visible) {
  box-shadow: 0 0 0 3px var(--paper-2), 0 0 0 5px var(--cobalt);
}
[data-testid="stNumberInput"] input { font-family: var(--mono); font-size: 13px; }
[data-testid="stSidebar"] [data-variant="segmented_control"] { min-height: 32px; padding: 0 11px; }
[data-testid="stSidebar"] [data-variant="segmented_control"] p { font-size: 12.5px; }

/* ---------- charging schedule */
.cf-tl { font-family: var(--sans); color: var(--ink); }
.cf-key { display: flex; flex-wrap: wrap; gap: 8px 22px; font: 400 12.5px/18px var(--sans); color: var(--ink-2); margin-bottom: 6px; }
.cf-key span { display: inline-flex; align-items: center; gap: 8px; }
.cf-key i { display: inline-block; width: 18px; height: 8px; }
.cf-tlh, .cf-tlr { display: grid; grid-template-columns: 132px minmax(0, 1fr) 150px; column-gap: 24px; align-items: center; }
.cf-tlh { padding: 16px 0 8px; border-bottom: 1px solid var(--ink); font: 400 10.5px/14px var(--mono); letter-spacing: .04em;
  text-transform: uppercase; color: var(--ink-3); }
.cf-axis { position: relative; height: 14px; text-transform: none; font-variant-numeric: tabular-nums; }
.cf-axis span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
.cf-axis span:first-child { transform: none; } .cf-axis span:last-child { transform: translateX(-100%); }
.cf-tlr { padding: 9px 0; border-bottom: 1px solid var(--rule-soft); transition: background-color .15s var(--ease); }
.cf-tlr:hover { background: #FAF9F6; }
.cf-tlr .nm b { display: block; font: 500 13.5px/18px var(--sans); }
.cf-tlr .nm span { display: block; font: 400 11px/15px var(--mono); color: var(--ink-3); font-variant-numeric: tabular-nums; }
.cf-track { position: relative; height: 20px;
  background-image: repeating-linear-gradient(to right, var(--rule-soft) 0, var(--rule-soft) 1px, transparent 1px, transparent 20%); }
.cf-win { position: absolute; top: 6px; height: 8px; background: var(--paper-3); }
.cf-seg { position: absolute; top: 6px; height: 8px; background: var(--cobalt); transform-origin: left center;
  animation: cf-seg .3s var(--ease-out) both; }
.cf-seg.float { background: #E6A795; }
@keyframes cf-seg { from { opacity: 0; transform: scaleX(.85); } to { opacity: 1; transform: none; } }
.cf-out2 { display: grid; grid-template-columns: 1fr 44px; align-items: center; column-gap: 12px; }
.cf-prog { position: relative; height: 4px; background: var(--paper-3); }
.cf-prog i { position: absolute; left: 0; top: 0; bottom: 0; background: var(--ink); transition: width .5s var(--ease-out); }
.cf-prog i.short { background: var(--vermilion); }
.cf-prog u { position: absolute; top: -4px; height: 12px; width: 1px; background: var(--ink-3); }
.cf-pct { font: 500 13px/18px var(--mono); text-align: right; font-variant-numeric: tabular-nums; }
.cf-pct.short { color: var(--vermilion); }

/* ---------- energy schematic and facts */
.cf-flow { font-family: var(--sans); }
.cf-flow-svg { min-height: 160px; }
.cf-flow-svg svg { display: block; width: 100%; height: auto; overflow: visible; }
.cf-flow .e { fill: none; transition: stroke-width .45s var(--ease-out); }
.cf-flow .off { fill: none; stroke: var(--rule); stroke-width: 1; stroke-dasharray: 3 4; }
.cf-flow .bx { fill: var(--surface); stroke: var(--rule); }
.cf-flow .lb { font: 500 10px var(--mono); letter-spacing: .06em; fill: var(--ink-3); }
.cf-flow .vl { font: 500 17px var(--display); fill: var(--ink); font-variant-numeric: tabular-nums; }
.cf-flow .sb { font: 400 11px var(--sans); fill: var(--ink-3); }
.cf-flow .el { font: 500 11px var(--mono); fill: var(--ink); font-variant-numeric: tabular-nums; }
.cf-flow .el.z { fill: var(--ink-3); }
.cf-flow-list { display: none; }
.cf-facts { font-family: var(--sans); }
.cf-row { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; padding: 10px 0;
  border-bottom: 1px solid var(--rule-soft); font-size: 13.5px; line-height: 19px; }
.cf-row:first-of-type { border-top: 1px solid var(--ink); }
.cf-row span { color: var(--ink-2); display: inline-flex; align-items: center; gap: 9px; }
.cf-row span i { width: 8px; height: 8px; flex: none; }
.cf-row b { font: 500 14px/19px var(--mono); color: var(--ink); text-align: right; font-variant-numeric: tabular-nums; }
.cf-row b em { font: 400 12px var(--sans); font-style: normal; color: var(--ink-3); }

/* ---------- entrance (first render of a session only; added by styles()) */
@keyframes cf-enter { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

/* ---------- responsive */
@media (max-width: 1280px) { .stApp { --gutter: 32px; } .cf-fig { font-size: 88px; } }
@media (max-width: 900px) {
  .stApp { --gutter: 20px; }
  .st-key-ws { padding: 4px 18px 22px; }
  .cf-tlh, .cf-tlr { grid-template-columns: 96px minmax(0, 1fr) 96px; column-gap: 14px; }
  .cf-out2 { grid-template-columns: 1fr; } .cf-prog { display: none; }
}
@media (max-width: 640px) {
  .stApp { --gutter: 16px; }
  .cf-mast-cap { display: none; }
  .st-key-masthead { flex-wrap: wrap !important; row-gap: 2px; padding-bottom: 8px; }
  .st-key-masthead > [data-testid="stElementContainer"]:first-child { flex-basis: 100% !important; }
  .st-key-masthead .stButton button, .st-key-masthead .stDownloadButton button { padding: 4px 8px; }
  .st-key-masthead > [data-testid="stElementContainer"]:nth-child(2) .stButton button { padding-left: 0; }
  .cf-fig { font-size: 72px; }
  .cf-strip > div { border-right: none; margin-right: 0; border-bottom: 1px solid var(--rule-soft); padding-bottom: 12px; }
  .stApp [role="tablist"] { gap: 18px; overflow-x: auto; }
  .stApp [data-testid="stTab"] code { display: none; }
  .st-key-outcome [role="radiogroup"] { flex-wrap: wrap; gap: 6px; }
  [data-testid="stButtonGroup"], [data-testid="stButtonGroup"] > div { max-width: 100%; flex-wrap: wrap; gap: 6px; }
  .st-key-outcome [data-variant="segmented_control"] { border-radius: var(--r2) !important; border-width: 1px !important; }
  .cf-tlh, .cf-tlr { grid-template-columns: 56px minmax(0, 1fr) 46px; column-gap: 10px; }
  .cf-tlr .nm span { display: none; }
  .cf-axis span:nth-child(even) { display: none; }
  .cf-flow-svg { display: none; } .cf-flow-list { display: block; }
}
@media (prefers-reduced-motion: reduce) {
  .stApp *, .stApp *::before, .stApp *::after {
    animation-duration: .001ms !important; animation-iteration-count: 1 !important; transition-duration: .001ms !important;
  }
}
"""


def styles(first_run):
    """The stylesheet as one <style> element (st.html keeps only one per call). On a
    session's first render it also carries a short staggered entrance."""
    css = CSS
    if first_run:
        css += "\n".join(f".st-key-{k} {{ animation: cf-enter .5s var(--ease-out) {i * 80}ms both; }}"
                         for i, k in enumerate(("masthead", "outcome", "sec2", "sec3")))
    return f"<style>{css}</style>"


# ---------------------------------------------------------------- page parts
def masthead(caption):
    return (f'<div class="cf-mast"><span class="cf-word">Charge<i>Flow</i></span>'
            f'<span class="cf-mast-cap">{escape(caption)}</span></div>')


def side_head():
    return '<div class="cf-side">Parameters<span>Every change re-plans the night.</span></div>'


def group(number, title):
    return f'<div class="cf-grp"><span>{number}</span>{escape(title)}</div>'


def section(number, title, note=None, ruled=False):
    n = f'<span class="note">{note}</span>' if note else ""
    return (f'<div class="cf-sec{" ruled" if ruled else ""}"><span class="n">{number}</span>'
            f'<h2>{escape(title)}</h2>{n}</div>')


def view_head(title, sub=None):
    s = f"<span>{sub}</span>" if sub else ""
    return f'<div class="cf-vh"><b>{escape(title)}</b>{s}</div>'


def readiness(ready, total, target_pct, socs, short_names):
    """socs: list of (name, departure %, ready)."""
    ok = ready == total
    if ok:
        state = f'Every rickshaw ready. <span>All {total} reach {target_pct}% before they leave.</span>'
    else:
        short = total - ready
        listed = ", ".join(short_names[:4]) + (" and more" if len(short_names) > 4 else "")
        state = (f'{short} short of {target_pct}%. <span>{escape(listed)} '
                 f'{"leaves" if short == 1 else "leave"} undercharged.</span>')
    bars = "".join(f'<i class="{"" if r else "short"}" title="{escape(n)}: {p:.0f}% at departure" '
                   f'{anim("rb_" + n, "height", f"{p:.1f}%")}></i>' for n, p, r in socs)
    first, last = socs[0][0], socs[-1][0]
    markup = f"""
<div class="cf-out" id="cf-ready" role="group" aria-label="Fleet readiness: {ready} of {total} ready">
  <p class="cf-lab">Fleet readiness at departure</p>
  <p class="cf-fig">{num('ready', ready)}<small>/{total}</small></p>
  <p class="cf-state {'' if ok else 'bad'}">{state}</p>
  <div class="cf-bars" role="img" aria-label="Charge at departure per rickshaw against the {target_pct}% target">
    {bars}<div class="tgt" style="bottom:{target_pct}%"><span>{target_pct}%</span></div>
  </div>
  <div class="cf-bars-cap"><span>{escape(first)}</span><span>charge at departure, per rickshaw</span><span>{escape(last)}</span></div>
</div>"""
    return _block("cf-ready", markup)


def _ticks(scale_max):
    step = 1 if scale_max <= 12 else 2 if scale_max <= 24 else 5
    major = step * 2
    vals = [i * step for i in range(int(scale_max // step) + 1)]
    return vals, major


def demand(peak, peak_time, limit, unc_peak, over_min, trips, trips_on, compare_note):
    ok = over_min == 0 and trips == 0
    scale = math.ceil(max(limit, peak, unc_peak or 0) * 1.12)
    pos = lambda v: f"{min(v, scale) / scale * 100:.2f}%"
    vals, major = _ticks(scale)
    def tick_label(v):
        edge = "transform:none" if v == 0 else "transform:translateX(-100%)" if v >= scale - 1e-9 else ""
        return f'<span class="tl" style="left:{pos(v)};{edge}">{v}</span>'
    ticks = "".join(
        f'<i class="tick{" major" if v % major == 0 else ""}" style="left:{pos(v)}"></i>'
        + (tick_label(v) if v % major == 0 else "") for v in vals)
    within = min(peak, limit)
    over_w = max(peak - limit, 0)
    # Labels sit to the right of their marker unless that would collide with the other
    # marker's label or run off the end of the scale.
    lim_left = limit / scale > 0.72
    unc, unc_left = "", False
    if unc_peak is not None:
        unc_left = unc_peak / scale > 0.72
        if unc_peak >= limit:
            lim_left = True    # marker to the right of the limit: limit label goes left
        else:
            unc_left = True    # marker to the left of the limit: its label goes left
        label = "uncontrolled" if unc_peak >= peak else "ChargeFlow + solar"
        # close to the limit marker: lift this label a row higher so the two never overlap
        lift = ' style="top:-34px"' if abs(unc_peak - limit) / scale < 0.3 else ""
        unc = (f'<div class="unc{" flip" if unc_left else ""}" {anim("g_unc", "left", pos(unc_peak))}>'
               f'<span{lift}>{label} {unc_peak:.1f}</span></div>')
    lim_flip = " flip" if lim_left else ""
    if ok:
        state = f'Within the sanctioned load all night. <span>{compare_note}</span>'
    elif over_min:
        state = (f'Over the sanctioned load for {fmt_min(over_min)}. '
                 f'<span>Peak exceeds {limit:.1f} kW by {peak - limit:.1f} kW.</span>')
    else:
        state = f'Supply cut out {trips} time{"s" if trips != 1 else ""}. <span>{compare_note}</span>'
    trip = (f'<span>Supply cut-outs: {trips}</span>' if trips_on else "")
    markup = f"""
<div class="cf-out" id="cf-demand" role="group" aria-label="Peak grid demand {peak:.1f} kW against {limit:.1f} kW sanctioned">
  <p class="cf-lab">Peak grid demand · {escape(peak_time)}</p>
  <p class="cf-fig">{num('peak', peak, 1)}<small>kW</small></p>
  <p class="cf-state {'' if ok else 'bad'}">{state}</p>
  <div class="cf-ruler" role="img" aria-label="Scale from 0 to {scale} kW">
    <div class="bar" {anim("g_bar", "width", pos(within))}></div>
    <div class="over" style="left:{pos(limit)};width:{over_w / scale * 100:.2f}%" data-anim="g_over" data-prop="width" data-to="{over_w / scale * 100:.2f}%"></div>
    <div class="base"></div>{ticks}
    <div class="lim{lim_flip}" {anim("g_lim", "left", pos(limit))}><span>sanctioned {limit:.1f}</span></div>
    {unc}
  </div>
  <div class="cf-bars-cap" style="max-width:none;justify-content:flex-start;gap:18px;margin-top:-10px"><span>kW drawn from the grid</span>{trip}</div>
</div>"""
    return _block("cf-demand", markup)


def strip(items):
    """items: (label, value_html, note_html, bad)."""
    cells = "".join(f'<div><p class="cf-lab">{escape(l)}</p><b{" class=bad" if bad else ""}>{v}</b>'
                    f'<em>{n}</em></div>' for l, v, n, bad in items)
    return _block("cf-strip", f'<div class="cf-strip" id="cf-strip">{cells}</div>')


# ---------------------------------------------------------------- schedule
def timeline(rows, color, target_pct, tick_labels):
    """rows: dicts with name, sub, window (l, w), window_title, segments [(l, w, kind, title)],
    soc_leave, ready, aria."""
    key = (f'<div class="cf-key"><span><i style="background:{color}"></i>Charger on</span>'
           f'<span><i style="background:var(--paper-3)"></i>Plugged in, waiting</span>'
           f'<span><i style="background:#E6A795"></i>Full, charger still drawing</span>'
           f'<span><i style="background:var(--ink);height:3px"></i>Charge at departure · mark at {target_pct}%</span></div>')
    n = len(tick_labels) - 1
    axis = "".join(f'<span style="left:{i / n * 100:.2f}%">{t}</span>' for i, t in enumerate(tick_labels))
    head = f'<div class="cf-tlh"><div>Rickshaw</div><div class="cf-axis">{axis}</div><div>At departure</div></div>'
    body = []
    for r in rows:
        segs = "".join(f'<i class="cf-seg {"float" if k == "float" else ""}" style="left:{l:.3f}%;width:{w:.3f}%;'
                       f'{"background:" + color if k == "charge" else ""}" title="{escape(t)}"></i>'
                       for l, w, k, t in r["segments"])
        wl, ww = r["window"]
        st = "" if r["ready"] else "short"
        body.append(
            f'<div class="cf-tlr" role="row" aria-label="{escape(r["aria"])}">'
            f'<div class="nm"><b>{escape(r["name"])}</b><span>{escape(r["sub"])}</span></div>'
            f'<div class="cf-track"><i class="cf-win" style="left:{wl:.3f}%;width:{ww:.3f}%" '
            f'title="{escape(r["window_title"])}"></i>{segs}</div>'
            f'<div class="cf-out2"><div class="cf-prog"><i class="{st}" {anim("tl_" + r["name"], "width", f"{r["soc_leave"]:.1f}%")}></i>'
            f'<u style="left:{target_pct}%"></u></div>'
            f'<span class="cf-pct {st}">{num("tp_" + r["name"], r["soc_leave"])}%</span></div></div>')
    return _block("cf-tl", f'<div class="cf-tl" id="cf-tl" role="table">{key}{head}{"".join(body)}</div>')


# ---------------------------------------------------------------- energy schematic
def flow(f, period_label):
    """Schematic of the simulated energy flows (kWh) for one period.
    f keys: solar, direct, to_pack, unused, from_pack, grid, demand, ev, rooms, *_sub labels."""
    edges = [  # key, path, colour, label anchor
        ("unused", "M170,36 L590,36", SOLAR, (380, 36)),
        ("direct", "M170,70 C 250,70 250,104 330,104", SOLAR, (250, 87)),
        ("to_pack", "M64,88 L64,124", SOLAR, (64, 106)),
        ("from_pack", "M170,156 L330,156", STORAGE, (250, 156)),
        ("grid", "M170,256 C 250,256 250,212 330,212", COBALT, (250, 234)),
        ("ev", "M330,134 C 460,134 460,128 590,128", GRAPHITE, (460, 131)),
        ("rooms", "M330,190 C 460,190 460,232 590,232", GRAY, (460, 211)),
    ]
    peak = max([f[k] for k, *_ in edges] + [1e-9])
    defs = "".join(
        f'<marker id="ah{i}" viewBox="0 0 10 10" refX="8" refY="5" markerUnits="userSpaceOnUse" '
        f'markerWidth="11" markerHeight="11" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
        for i, c in enumerate((SOLAR, STORAGE, COBALT, GRAPHITE, GRAY)))
    mk = {SOLAR: 0, STORAGE: 1, COBALT: 2, GRAPHITE: 3, GRAY: 4}
    paths, labels = [], []
    for key, d, c, (lx, ly) in edges:
        v = f[key]
        if v < 0.05:
            paths.append(f'<path class="off" d="{d}"/>')
            txt, cls = "0", "el z"
        else:
            w = 1.5 + 9 * v / peak
            paths.append(f'<path class="e" d="{d}" stroke="{c}" marker-end="url(#ah{mk[c]})" '
                         f'{anim("fw_" + key, "stroke-width", f"{w:.2f}px")}/>')
            txt, cls = f"{v:.1f}", "el"
        tw = 7 * len(txt) + 12
        labels.append(f'<rect x="{lx - tw / 2:.1f}" y="{ly - 9}" width="{tw:.1f}" height="18" rx="2" fill="{PAPER}"/>'
                      f'<text class="{cls}" x="{lx}" y="{ly + 4}" text-anchor="middle">{txt}</text>')

    def box(x, y, w, h, label, value, sub, accent):
        return (f'<rect class="bx" x="{x}" y="{y}" width="{w}" height="{h}" rx="3"/>'
                f'<rect x="{x}" y="{y}" width="3" height="{h}" fill="{accent}"/>'
                f'<text class="lb" x="{x + 14}" y="{y + 18}">{escape(label)}</text>'
                f'<text class="vl" x="{x + 14}" y="{y + 40}">{value}</text>'
                f'<text class="sb" x="{x + 14}" y="{y + h - 9}">{escape(sub)}</text>')

    k = lambda v: f"{v:.1f} kWh"
    nodes = (box(0, 20, 170, 68, "SOLAR PV", k(f["solar"]), f["solar_sub"], SOLAR)
             + box(0, 124, 170, 68, "SECOND-LIFE PACK", f"{f['to_pack']:.1f} in · {f['from_pack']:.1f} out", "kWh",
                   STORAGE)
             + box(0, 224, 170, 68, "GRID", k(f["grid"]), f["grid_sub"], COBALT)
             + box(590, 96, 170, 68, "RICKSHAW CHARGERS", k(f["ev"]), f["fleet_sub"], GRAPHITE)
             + box(590, 200, 170, 68, "ROOMS", k(f["rooms"]), "lights, fans", GRAY)
             + box(590, 4, 170, 64, "UNUSED SOLAR", k(f["unused"]), "pack already full", RULE))
    bus = (f'<line x1="330" y1="86" x2="330" y2="232" stroke="{INK}" stroke-width="3"/>'
           f'<text class="lb" x="342" y="78">BUILDING</text>'
           f'<text class="vl" x="342" y="258" style="font-size:15px">{k(f["demand"])}</text>'
           f'<text class="sb" x="342" y="274">consumed</text>')
    aria = (f"Energy flow, {period_label}: solar {f['solar']:.1f} kWh ({f['direct']:.1f} used directly, "
            f"{f['to_pack']:.1f} into the pack, {f['unused']:.1f} unused); pack {f['from_pack']:.1f} kWh and grid "
            f"{f['grid']:.1f} kWh to the building; chargers {f['ev']:.1f} kWh, rooms {f['rooms']:.1f} kWh.")
    rows = [("Solar generated", f["solar"], SOLAR), ("Solar used directly", f["direct"], SOLAR),
            ("Solar into pack", f["to_pack"], SOLAR), ("Unused solar", f["unused"], RULE),
            ("Pack to building", f["from_pack"], STORAGE), ("Grid to building", f["grid"], COBALT),
            ("Rickshaw chargers", f["ev"], GRAPHITE), ("Rooms", f["rooms"], GRAY)]
    fallback = "".join(f'<div class="cf-row"><span><i style="background:{c}"></i>{escape(t)}</span>'
                       f'<b>{v:.1f} kWh</b></div>' for t, v, c in rows)
    svg = (f'<svg viewBox="0 0 760 300" aria-hidden="true"><defs>{defs}</defs>{bus}{"".join(paths)}'
           f'{nodes}{"".join(labels)}</svg>')
    return _block("cf-flow", f'<div class="cf-flow" id="cf-flow"><div class="cf-flow-svg" role="img" '
                             f'aria-label="{escape(aria)}"></div><div class="cf-flow-list">{fallback}</div></div>',
                  inject={".cf-flow-svg": svg})


def facts(rows):
    """rows: (label, value_html, colour or None)."""
    body = "".join(f'<div class="cf-row"><span>{f"<i style=background:{c}></i>" if c else ""}{escape(l)}</span>'
                   f'<b>{v}</b></div>' for l, v, c in rows)
    return _block("cf-facts", f'<div class="cf-facts" id="cf-facts">{body}</div>')
