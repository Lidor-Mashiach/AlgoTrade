# 🖥️ CLI (Presentation Layer)

> Everything the user sees from launch onward. Despite the name **CLI**, the requirements
> (hover, zoomable/fullscreen charts, login screens, warm colors) describe a **graphical UI**.
> Default in this template: **Streamlit + Plotly** — swap freely (decision point).

---

## 🧭 Contents

1. [Why Streamlit + Plotly](#-why-streamlit--plotly)
2. [Folder structure](#-folder-structure)
3. [Screens](#-screens)
4. [Auth flow](#-auth-flow)
5. [Charts](#-charts)
6. [UX rules](#-ux-rules)
7. [Talking to the backend](#-talking-to-the-backend)

---

## 🤔 Why Streamlit + Plotly

| Requirement | How it's met |
|-------------|--------------|
| hover tooltips | native in Plotly |
| zoom / pan / drag | native in Plotly |
| fullscreen (YouTube-style) | Plotly modebar expand |
| warm, themed colors & headers | Streamlit theming / CSS |
| popups *from below* (not dropping from top) | toast / modal components |
| back navigation | screen-stack in session state |
| English-only, custom toolbar | sidebar nav |

> A literal terminal cannot do hover/zoom/fullscreen — hence the web-app choice. If a true
> CLI is mandated, this folder would instead host a `rich`/`textual` app and charts become
> ASCII/sparklines. Flagged as an open decision in the main README.

---

## 📂 Folder structure

```
cli/
├── README.md
├── app.py                 ← entry point + screen router
├── screens/
│   ├── guest_home.py      ← market overview (no auth): up/down %, green/red, FX
│   ├── auth.py            ← login / register (cross-link to each other)
│   ├── user_home.py       ← welcome {first} {last}, live clock HH:mm:ss DD/MM/YYYY
│   ├── prediction.py      ← index × horizon picker, forecast, profit estimator, chart
│   └── settings.py        ← change name / password
├── widgets/
│   └── charts.py          ← Plotly candle chart + highlighted forecast band
└── assets/                ← logo, css, icons
```

---

## 🪟 Screens

### 👤 Guest home (pre-login)
- Indices vs. previous close: **green = up**, **red = down**, with the %.
- Optional FX (USD / EUR / ILS) with same up/down coloring.
- Buttons: **Login** / **Register**. No other access.

### 🔐 Auth
- Login and Register **cross-link** (registered user on Register → sent to Login, and vice-versa).
- On success → back to home, now in **personalized** mode.

### 🏠 User home (post-login)
- `Welcome {first name} {last name}`.
- Live clock: `HH:mm:ss DD/MM/YYYY`.
- Navigation to Prediction and Settings.

### 🔮 Prediction
- Pick **index** + **horizon** → instant forecast: range `[low, high]`, confidence, and
  **Long / Short / Stay-out**.
- 💰 **Profit estimator:** enter an amount (₪/$/€) → expected profit range from the forecast bounds.
- 📈 Chart of the index up to last close, with the **forecast band highlighted to the right**;
  fully **dynamic** across index, horizon, and updated forecasts.

### ⚙️ Settings
- Change name, change password (hashing handled by the backend).

---

## 🔁 Auth flow

```
guest_home ──Login──▶ auth(login) ──ok──▶ user_home
guest_home ──Register▶ auth(register) ──ok──▶ user_home
auth(login) ⇄ auth(register)   (cross redirect if wrong screen)
```

---

## 📈 Charts

- Candlestick (or line) per `(index, horizon)`, built in `widgets/charts.py` with **Plotly**.
- Zoom, pan, fullscreen out of the box.
- Forecast band drawn as a shaded region immediately after the last real candle, recolored as
  the forecast updates.

---

## ✨ UX rules

- 🌈 Warm, light palette; clear header / sub-header hierarchy; pleasant chart colors.
- 🖱️ Tasteful **hover**; popups appear **from below** (toasts/modals), never dropping from top.
- ⬅️ Every screen allows **back** navigation.
- 🌐 No connectivity → friendly *"Internet connection required"* popup, **no crash**.
- 🇬🇧 **English only**, simple and obvious controls.

---

## 🔌 Talking to the backend

The CLI imports **only** `backend.api` — never data sources, models, or the DB directly.

```python
from backend import api
snap = api.market_snapshot()
res  = api.predict(index="SPY", horizon="weekly", amount=1000, currency="USD")
```
