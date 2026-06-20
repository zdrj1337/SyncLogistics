# Inventory Tracker

A small warehouse-style stock management web app. Add products, track quantities,
move stock in and out, and get a visual alert when an item runs low. Built as a
portfolio project, inspired by warehouse operations (picking, stock handling) I did
during a logistics internship.

## Features

- **Add products** with name, SKU, quantity, storage location, and a low-stock threshold
- **Search** the inventory by name or SKU
- **Stock in / stock out** with one click, with a guard that prevents quantities going below zero
- **Low-stock alerts** — items at or below their threshold are highlighted with a `LOW` badge
- **Activity log** — every stock movement is recorded and shown as a recent-activity feed
- **Delete** products you no longer track

## Tech stack

- **Backend:** Python, [Flask](https://flask.palletsprojects.com/) — a small JSON REST API
- **Database:** SQLite (via Python's built-in `sqlite3`, no setup required)
- **Frontend:** plain HTML, CSS, and JavaScript (no framework), talking to the API with `fetch()`

The frontend and backend are decoupled: the server exposes a JSON API and the page
fetches from it, rather than the server rendering data into HTML. This keeps the
structure close to how real web apps are built.

## Running it locally

You need Python 3.10+ installed.

```bash
# 1. (optional but recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate

# 2. install the one dependency
pip install -r requirements.txt

# 3. run
python app.py
```

Then open **http://127.0.0.1:5000** in your browser. The database file
(`inventory.db`) is created automatically on first run.

## Project structure

```
inventory-tracker/
├── app.py              # Flask app: routes + API + database access
├── requirements.txt    # Python dependencies (just Flask)
├── templates/
│   └── index.html      # the single page
└── static/
    ├── style.css       # styling
    └── app.js          # frontend logic (fetch + DOM rendering)
```

## API reference

| Method   | Endpoint                       | Description                                  |
|----------|--------------------------------|----------------------------------------------|
| `GET`    | `/api/products`                | List products. `?q=` filters by name or SKU. |
| `POST`   | `/api/products`                | Add a product.                               |
| `POST`   | `/api/products/<id>/adjust`    | Change stock by `{ "delta": ±n }`.           |
| `DELETE` | `/api/products/<id>`           | Delete a product.                            |
| `GET`    | `/api/movements`               | List the most recent stock movements.        |

## Possible next steps

Ideas I would add with more time:

- User accounts and login
- Editing an existing product (currently you delete and re-add)
- Export the inventory to CSV
- Pagination once the product list gets long
- Rewrite the frontend in React to learn a component-based framework

## Author

Built by **Florin-Traian Zadorojneac** — Automation & Applied Informatics student, Galați.
