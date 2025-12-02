import os
import sqlite3
from datetime import date, datetime

import tkinter as tk
from tkinter import ttk, messagebox

from tkcalendar import DateEntry
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# ==========================================================
#        MS TRADERS – CORPORATE SILVER BILLING SUITE
# ==========================================================

DB_NAME = "ms_traders_billing.db"

# --------- UI COLORS (Silver Corporate) ----------
BG = "#ECEFF1"        # App background
CARD = "#FFFFFF"      # Panels
BORDER = "#CFD8DC"    # Borders
TEXT = "#263238"      # Main text
MUTED = "#607D8B"     # Sub text
ACCENT = "#1565C0"    # Primary blue
ACCENT_SOFT = "#90CAF9"
GOLD = "#FFC107"
GREEN = "#2E7D32"
RED = "#C62828"

# ==========================================================
#               DATABASE SETUP
# ==========================================================

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

# items / entries table (simple row-wise storage)
cur.execute("""
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    customer_id INTEGER,
    vehicle TEXT,
    branch TEXT,
    type TEXT,
    qty REAL,
    rate REAL,
    labour REAL,
    advance REAL,
    pre REAL,
    total REAL,
    note TEXT
)
""")

# try to add customer_id column if old DB exists (safe no-op on new DB)
try:
    cur.execute("ALTER TABLE entries ADD COLUMN customer_id INTEGER")
    conn.commit()
except sqlite3.OperationalError:
    pass

# customers table
cur.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    mobile TEXT,
    address TEXT
)
""")

conn.commit()

# ==========================================================
#                 TK ROOT + STYLE
# ==========================================================

root = tk.Tk()
root.title("MS TRADERS – Saad Usamni")
root.geometry("1350x780")
root.configure(bg=BG)

style = ttk.Style()
style.theme_use("clam")

style.configure(
    "Treeview",
    background="white",
    fieldbackground="white",
    foreground=TEXT,
    rowheight=26,
    bordercolor=BORDER,
    borderwidth=1,
)
style.configure(
    "Treeview.Heading",
    background=ACCENT,
    foreground="white",
    font=("Segoe UI", 10, "bold")
)
style.map(
    "Treeview",
    background=[("selected", ACCENT)],
    foreground=[("selected", "white")]
)

style.configure(
    "Primary.TButton",
    font=("Segoe UI", 9, "bold"),
    padding=6
)
style.configure(
    "Secondary.TButton",
    font=("Segoe UI", 9),
    padding=5
)

# ==========================================================
#            HELPERS & UTILITIES
# ==========================================================

def entry(parent, var=None, width=20):
    return tk.Entry(
        parent,
        textvariable=var,
        bg="white",
        fg=TEXT,
        insertbackground=TEXT,
        relief="flat",
        bd=1,
        width=width,
        highlightthickness=1,
        highlightcolor=ACCENT,
        highlightbackground=BORDER
    )


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def ensure_invoice_folder():
    if not os.path.exists("invoices"):
        os.makedirs("invoices")


# ==========================================================
#                VARIABLES
# ==========================================================

# customer
v_customer_id = tk.StringVar(value="-")
v_customer_name = tk.StringVar()
v_customer_mobile = tk.StringVar()
v_customer_address = tk.StringVar()

# header / bill info
v_date = tk.StringVar(value=str(date.today()))
v_vehicle = tk.StringVar()
v_branch = tk.StringVar()
v_type = tk.StringVar()

# line item
v_qty = tk.StringVar()
v_rate = tk.StringVar()
v_labour = tk.StringVar()
v_advance = tk.StringVar(value="0")
v_note = tk.StringVar()
v_calc_mode = tk.StringVar(value="Rate × Qty + Labour × Qty")

# totals / search / reports
grand_total = tk.StringVar(value="0.00")

search_date = tk.StringVar()
search_vehicle = tk.StringVar()
search_branch = tk.StringVar()

report_date = tk.StringVar(value=str(date.today()))

# customer panel globals
customer_panel = None
cust_tree = None
cust_total_qty = tk.StringVar(value="0.00")
cust_total_amt = tk.StringVar(value="0.00")
cust_bill_count = tk.StringVar(value="0")


# ==========================================================
#        CUSTOMER FUNCTIONS
# ==========================================================

def load_customers():
    cur.execute("SELECT id, name, mobile, address FROM customers ORDER BY name")
    return cur.fetchall()


def save_customer():
    name = v_customer_name.get().strip()
    mobile = v_customer_mobile.get().strip()
    address = v_customer_address.get().strip()

    if not name:
        messagebox.showerror("Customer", "Customer name is required.")
        return

    # try to find existing
    cur.execute(
        "SELECT id FROM customers WHERE name = ? AND mobile = ?",
        (name, mobile)
    )
    row = cur.fetchone()
    if row:
        cid = row[0]
    else:
        cur.execute(
            "INSERT INTO customers (name, mobile, address) VALUES (?,?,?)",
            (name, mobile, address)
        )
        conn.commit()
        cid = cur.lastrowid

    v_customer_id.set(str(cid))
    messagebox.showinfo("Customer", f"Customer saved / selected.\nID: {cid}")
    open_customer_panel()  # auto open / refresh panel


def choose_customer_popup():
    win = tk.Toplevel(root)
    win.title("Select Customer")
    win.geometry("600x400")
    win.configure(bg=BG)

    cols = ("ID", "Name", "Mobile", "Address")
    tv = ttk.Treeview(win, columns=cols, show="headings")
    for c in cols:
        tv.heading(c, text=c)
        tv.column(c, width=120)
    tv.pack(fill="both", expand=True, padx=10, pady=10)

    for cid, name, mobile, address in load_customers():
        tv.insert("", tk.END, values=(cid, name, mobile, address))

    def on_select(event=None):
        sel = tv.selection()
        if not sel:
            return
        vals = tv.item(sel[0], "values")
        v_customer_id.set(str(vals[0]))
        v_customer_name.set(vals[1])
        v_customer_mobile.set(vals[2])
        v_customer_address.set(vals[3])
        win.destroy()
        open_customer_panel()  # auto open / refresh panel

    tv.bind("<Double-1>", on_select)

    ttk.Button(
        win, text="Select", style="Primary.TButton",
        command=on_select
    ).pack(pady=5)


# ==========================================================
#        ENTRY / BILLING FUNCTIONS
# ==========================================================

def calculate_pre_total(rate, qty, labour, mode):
    if mode == "Rate × Qty + Labour × Qty":
        return (rate * qty) + (labour * qty)
    elif mode == "Rate × Qty Only":
        return rate * qty
    elif mode == "Labour × Qty Only":
        return labour * qty
    else:
        return (rate * qty) + (labour * qty)


def add_item():
    # 1) If no customer ID, either attach to existing (by name+mobile) or allow "no customer"
    cid = None

    name = v_customer_name.get().strip()
    mobile = v_customer_mobile.get().strip()
    address = v_customer_address.get().strip()

    # Case A: ID is already set (from Save/Select or Choose Existing)
    if v_customer_id.get().isdigit():
        cid = int(v_customer_id.get())

    # Case B: No ID, but name/mobile present → try to lookup or create
    elif name:
        cur.execute(
            "SELECT id FROM customers WHERE name = ? AND mobile = ?",
            (name, mobile)
        )
        row = cur.fetchone()
        if row:
            cid = row[0]
        else:
            # create a new customer record silently
            cur.execute(
                "INSERT INTO customers (name, mobile, address) VALUES (?,?,?)",
                (name, mobile, address)
            )
            conn.commit()
            cid = cur.lastrowid
        v_customer_id.set(str(cid))  # sync UI label

    # Case C: no customer at all → ask user if they really want to continue
    else:
        if not messagebox.askyesno(
            "No Customer",
            "No customer selected.\nDo you want to continue without saving customer?"
        ):
            return
        cid = None  # allow anonymous bill

    # 2) Now do the line-item validation & math
    qty = safe_float(v_qty.get())
    rate = safe_float(v_rate.get())
    labour = safe_float(v_labour.get())
    advance = safe_float(v_advance.get())

    if qty <= 0 or rate <= 0:
        messagebox.showerror("Input Error", "Quantity and Rate must be greater than 0.")
        return

    pre = calculate_pre_total(rate, qty, labour, v_calc_mode.get())
    total = pre - advance

    # 3) Add to MAIN TABLE UI
    tree.insert(
        "",
        tk.END,
        values=(
            v_date.get(),
            v_customer_name.get(),
            v_vehicle.get(),
            v_branch.get(),
            v_type.get(),
            qty,
            rate,
            labour,
            advance,
            round(pre, 2),
            round(total, 2),
            v_note.get()
        )
    )

    # 4) Save to DB with proper customer_id (cid)
    cur.execute("""
        INSERT INTO entries (
            date, customer_id, vehicle, branch, type,
            qty, rate, labour, advance, pre, total, note
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        v_date.get(), cid, v_vehicle.get(), v_branch.get(), v_type.get(),
        qty, rate, labour, advance, pre, total, v_note.get()
    ))
    conn.commit()

    # 5) Clear line fields
    v_qty.set("")
    v_rate.set("")
    v_labour.set("")
    v_advance.set("0")
    v_note.set("")

    # 6) Refresh customer panel if open
    if cid is not None:
        refresh_customer_panel()

def reload_tree_from_records(records):
    """Clear the main Treeview and load the given records."""
    tree.delete(*tree.get_children())
    for r in records:
        # r: (date, customer_name, vehicle, branch, type, qty, rate, labour, advance, pre, total, note)
        tree.insert("", tk.END, values=r)


def load_all_entries():
    """Load all bills from DB into the main dashboard Treeview."""
    cur.execute("""
        SELECT e.date,
               COALESCE(c.name, ''),
               e.vehicle,
               e.branch,
               e.type,
               e.qty,
               e.rate,
               e.labour,
               e.advance,
               e.pre,
               e.total,
               e.note
        FROM entries e
        LEFT JOIN customers c ON e.customer_id = c.id
        ORDER BY e.date DESC, e.id DESC
    """)
    records = cur.fetchall()
    reload_tree_from_records(records)



def calculate_selected_total(tree_widget=None):
    if tree_widget is None:
        tree_widget = tree

    selected = tree_widget.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select at least one row.")
        return None

    total_sum = 0.0
    for item in selected:
        vals = tree_widget.item(item, "values")
        total_sum += safe_float(vals[10])

    grand_total.set(f"{total_sum:,.2f}")
    return total_sum


# ==========================================================
#           SEARCH & REPORT FUNCTIONS
# ==========================================================

def search_entries():
    q = """
        SELECT e.date,
               COALESCE(c.name, ''),
               e.vehicle,
               e.branch,
               e.type,
               e.qty,
               e.rate,
               e.labour,
               e.advance,
               e.pre,
               e.total,
               e.note
        FROM entries e
        LEFT JOIN customers c ON e.customer_id = c.id
        WHERE 1=1
    """
    params = []

    d = search_date.get().strip()
    v = search_vehicle.get().strip()
    b = search_branch.get().strip()

    if d:
        q += " AND e.date = ?"
        params.append(d)
    if v:
        q += " AND e.vehicle LIKE ?"
        params.append(f"%{v}%")
    if b:
        q += " AND e.branch LIKE ?"
        params.append(f"%{b}%")

    q += " ORDER BY e.date DESC, e.id DESC"
    cur.execute(q, params)
    records = cur.fetchall()
    reload_tree_from_records(records)


def show_all_entries():
    search_date.set("")
    search_vehicle.set("")
    search_branch.set("")
    load_all_entries()


def daily_report():
    d = report_date.get().strip()
    if not d:
        messagebox.showerror("Report", "Please enter a valid date (YYYY-MM-DD).")
        return

    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(qty),0), COALESCE(SUM(total),0)
        FROM entries
        WHERE date = ?
    """, (d,))
    count, qty_sum, amt_sum = cur.fetchone()

    messagebox.showinfo(
        "Daily Report",
        f"Date: {d}\n"
        f"Total Bills: {count}\n"
        f"Total Qty: {qty_sum:.2f} Kg\n"
        f"Total Amount: ₹ {amt_sum:,.2f}"
    )


def monthly_report():
    d = report_date.get().strip()
    if len(d) < 7:
        messagebox.showerror("Report", "Use format YYYY-MM-DD.")
        return
    ym = d[:7]
    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(qty),0), COALESCE(SUM(total),0)
        FROM entries
        WHERE substr(date,1,7) = ?
    """, (ym,))
    count, qty_sum, amt_sum = cur.fetchone()

    messagebox.showinfo(
        "Monthly Report",
        f"Month: {ym}\n"
        f"Total Bills: {count}\n"
        f"Total Qty: {qty_sum:.2f} Kg\n"
        f"Total Amount: ₹ {amt_sum:,.2f}"
    )


# ==========================================================
#                   DELETE ENTRY FEATURE
# ==========================================================

def delete_entries(tree_widget=None):
    if tree_widget is None:
        tree_widget = tree  # default main dashboard

    selected = tree_widget.selection()
    if not selected:
        messagebox.showwarning("Delete", "⚠ Please select at least one row to delete.")
        return

    if not messagebox.askyesno("Confirm Delete",
        "Are you sure you want to permanently delete selected records?"):
        return

    deleted_count = 0

    for item in selected:
        vals = tree_widget.item(item, "values")

        d, cust, veh, br, t, qty, rate, labour, adv, pre, total, note = vals

        cur.execute("""
            DELETE FROM entries WHERE 
                date=? AND vehicle=? AND branch=? AND type=?
                AND qty=? AND rate=? AND labour=? AND advance=? AND pre=? AND total=? AND note=?
        """, (d, veh, br, t, qty, rate, labour, adv, pre, total, note))

        tree_widget.delete(item)
        deleted_count +=1

    conn.commit()

    load_all_entries()       # Refresh main dashboard
    refresh_customer_panel() # Refresh customer panel if open

    messagebox.showinfo("Deleted", f"🗑 Removed {deleted_count} record(s).")


# ==========================================================
#           INVOICE (C2 – THIN GOLD HEADER)
# ==========================================================

def open_invoice_folder():
    ensure_invoice_folder()
    os.startfile("invoices")
def generate_invoice(tree_widget=None):
    if tree_widget is None:
        tree_widget = tree

    selected = tree_widget.selection()
    if not selected:
        messagebox.showwarning("Invoice", "⚠ Select at least one row.")
        return

    invoice_total = 0.0
    selected_rows = []
    for item in selected:
        vals = tree_widget.item(item, "values")
        if len(vals) == 12:  # main table
            row = [vals[5], vals[6], vals[7], vals[8], vals[9], vals[10], vals[11]]
        else:                # customer panel
            row = [vals[4], vals[5], vals[6], vals[7], vals[8], vals[9], vals[10]]

        selected_rows.append(row)
        invoice_total += float(row[5])

    ensure_invoice_folder()
    invoice_no = datetime.now().strftime("MS%Y%m%d%H%M%S")
    filename = f"invoices/{invoice_no}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)
    w, h = A4

    # ===== HEADER (SPACING FIXED) =====
    try:
        c.drawImage("logo.jpeg", 30, h-95, width=140, height=80, preserveAspectRatio=True)
    except:
        pass

    # Company Title ↓ moved slightly higher
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(w/2, h-65, "A.B ENTERPRISES")

    c.setFont("Helvetica", 12)
    c.drawCentredString(w/2, h-88, "Cattle Feed Supplies")

    # Golden strip ↓ lowered for breathing space
    c.setFillColor(colors.HexColor(GOLD))
    c.rect(0, h-105, w, 5, fill=1)

    # Phone & Address moved down safely
    y_info = h-130
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.black)
    c.drawString(30, y_info, "Ph 95948473 / 9172319000 / 9076313413")

    c.setFont("Helvetica", 9)
    c.drawString(30, y_info-15, "Gala No.34-C , Rashid compound, Survey No.4 , C.T.S No.161,")
    c.drawString(30, y_info-30, "Saki Naka , Mumbai-400072")

    # Invoice No (right side)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawRightString(w-20, h-65, f"Invoice No : {invoice_no}")

    # ===== CUSTOMER BLOCK LEFT =====
    y = h-180
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Customer:")
    c.setFont("Helvetica", 10)
    c.drawString(120, y, v_customer_name.get())
    y -= 15
    c.drawString(120, y, f"Mobile: {v_customer_mobile.get()}")
    y -= 15
    c.drawString(120, y, f"Address: {v_customer_address.get()}")

    # ===== BILL DETAILS RIGHT =====
    y2 = h-180
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w-220, y2, "Bill Details")
    c.setFont("Helvetica", 10)
    c.drawString(w-220, y2-15, f"Date: {v_date.get()}")
    c.drawString(w-220, y2-30, f"Vehicle: {v_vehicle.get()}")
    c.drawString(w-220, y2-45, f"Branch: {v_branch.get()}")
    c.drawString(w-220, y2-60, f"Type: {v_type.get()}")

    # ===== TABLE =====
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    styles = getSampleStyleSheet()

    data = [["Qty", "Rate", "Labour", "Advance", "PreTotal", "Total", "Note"]]
    for row in selected_rows:
        row[-1] = Paragraph(str(row[-1]), styles["Normal"])
        data.append(row)

    table = Table(data, colWidths=[60, 60, 60, 60, 75, 75, 170])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2E86C1")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.7, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))

    TABLE_Y = h-320
    table.wrapOn(c, 0, 0)
    table.drawOn(c, 40, TABLE_Y)

    # ===== GRAND TOTAL =====
    c.setFont("Helvetica-Bold", 12)
    c.rect(w-230, TABLE_Y-50, 180, 28, stroke=1, fill=0)
    c.drawString(w-220, TABLE_Y-42, "Grand Total : ₹")
    c.drawRightString(w-60, TABLE_Y-42, f"{invoice_total:,.2f}")

    # ===== FOOTER (AUTO POSITION NEAR TABLE) =====
    FOOTER_Y = TABLE_Y - 70   # adjust to 60/90 based on layout

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.red)
    c.drawCentredString(w/2, FOOTER_Y, "This is a computer generated invoice – no signature required.")

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawCentredString(w/2, FOOTER_Y-15, "Thank you for your business!")

    c.save()
    os.startfile(filename)
    messagebox.showinfo("Invoice Ready", f"Saved Invoice:\n{filename}")

  

    # # =====================================================
    # #               CUSTOMER & BILL INFO
    # # =====================================================

    #    # =====================================================
    # #              CUSTOMER + BILL DETAILS CLEAN LAYOUT
    # # =====================================================

    # # LEFT BLOCK — CUSTOMER INFO
    # y = h - 170  # lowered to avoid overlap
    # c.setFont("Helvetica-Bold", 10)
    # c.drawString(40, y, "Customer:")
    # c.setFont("Helvetica", 10)
    # c.drawString(120, y, v_customer_name.get())
    # y -= 15
    # c.drawString(120, y, f"Mobile: {v_customer_mobile.get()}")
    # y -= 15
    # c.drawString(120, y, f"Address: {v_customer_address.get()}")

    # # RIGHT BLOCK — BILL INFO (aligned with customer)
    # y_right = h - 170
    # c.setFont("Helvetica-Bold", 10)
    # c.drawString(w - 220, y_right, "Bill Details")
    # y_right -= 15
    # c.setFont("Helvetica", 10)
    # c.drawString(w - 220, y_right, f"Date: {v_date.get()}")
    # y_right -= 15
    # c.drawString(w - 220, y_right, f"Vehicle: {v_vehicle.get()}")
    # y_right -= 15
    # c.drawString(w - 220, y_right, f"Branch: {v_branch.get()}")
    # y_right -= 15
    # c.drawString(w - 220, y_right, f"Type: {v_type.get()}")

    # # ---------------- TABLE POSITION FIX ----------------

    # table_top_y = h - 250  # perfect balanced height
    # table.wrapOn(c, w - 80, h)
    # table.drawOn(c, 40, table_top_y)  # moved UP precisely




# ==========================================================
#           CUSTOMER PANEL (AUTO OPEN)
# ==========================================================

def load_customer_entries(cid, tree_widget):
    tree_widget.delete(*tree_widget.get_children())

    cur.execute("""
        SELECT date, vehicle, branch, type,
               qty, rate, labour, advance, pre, total, note
        FROM entries
        WHERE customer_id = ?
        ORDER BY date DESC, id DESC
    """, (cid,))
    records = cur.fetchall()

    total_qty = 0.0
    total_amt = 0.0
    count = 0

    for r in records:
        # r: (date, vehicle, branch, type, qty, rate, labour, advance, pre, total, note)
        vals = (
            r[0],   # date
            r[1],   # vehicle
            r[2],   # branch
            r[3],   # type
            r[4],   # qty
            r[5],   # rate
            r[6],   # labour
            r[7],   # advance
            r[8],   # pre
            r[9],   # total
            r[10],  # note
        )
        tree_widget.insert("", tk.END, values=vals)

        total_qty += safe_float(r[4])
        total_amt += safe_float(r[9])
        count += 1

    cust_total_qty.set(f"{total_qty:.2f}")
    cust_total_amt.set(f"{total_amt:,.2f}")
    cust_bill_count.set(str(count))


def refresh_customer_panel():
    global customer_panel, cust_tree
    if customer_panel is None or not customer_panel.winfo_exists():
        return
    if not v_customer_id.get().isdigit():
        return
    load_customer_entries(int(v_customer_id.get()), cust_tree)

def open_customer_panel():
    global customer_panel, cust_tree

    if not v_customer_id.get().isdigit():
        return

    if customer_panel is not None and customer_panel.winfo_exists():
        customer_panel.lift()
    else:
        customer_panel = tk.Toplevel(root)
        customer_panel.title("Customer Overview")
        customer_panel.geometry("900x500")
        customer_panel.configure(bg=BG)

        # Header
        tk.Label(
            customer_panel,
            text="Customer Overview",
            bg=BG,
            fg=ACCENT,
            font=("Segoe UI", 14, "bold")
        ).pack(pady=8)

        # --------- CUSTOMER INFO BLOCK ----------
        info_frame = tk.Frame(
            customer_panel,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=10,
            pady=8
        )
        info_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(info_frame, text="Name:", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(info_frame, textvariable=v_customer_name, bg=CARD, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w", padx=4)

        tk.Label(info_frame, text="Mobile:", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w")
        tk.Label(info_frame, textvariable=v_customer_mobile, bg=CARD, fg=TEXT,
                 font=("Segoe UI", 10)).grid(row=0, column=3, sticky="w", padx=4)

        tk.Label(info_frame, text="Address:", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=(4, 0))
        tk.Label(
            info_frame,
            textvariable=v_customer_address,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 10),
            wraplength=400,
            justify="left"
        ).grid(row=1, column=1, columnspan=3, sticky="w", padx=4, pady=(4, 0))

        # --------- SUMMARY BLOCK ----------
        summary_frame = tk.Frame(
            customer_panel,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=10,
            pady=8
        )
        summary_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(summary_frame, text="Total Bills:", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(summary_frame, textvariable=cust_bill_count, bg=CARD, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).grid(row=1, column=0, sticky="w")

        tk.Label(summary_frame, text="Total Quantity (Kg):", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=20)
        tk.Label(summary_frame, textvariable=cust_total_qty, bg=CARD, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).grid(row=1, column=1, sticky="w", padx=20)

        tk.Label(summary_frame, text="Total Amount (₹):", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=20)
        tk.Label(summary_frame, textvariable=cust_total_amt, bg=CARD, fg=GREEN,
                 font=("Segoe UI", 11, "bold")).grid(row=1, column=2, sticky="w", padx=20)

        # --------- CUSTOMER ENTRIES TABLE ----------
        table_frame = tk.Frame(customer_panel, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cust_cols = (
            "Date", "Vehicle", "Branch", "Type",
            "Qty", "Rate", "Labour", "Advance", "PreTotal", "Total", "Note"
        )

        cust_tree_local = ttk.Treeview(
            table_frame,
            columns=cust_cols,
            show="headings",
            selectmode="extended"   # allow multi-select with Ctrl/Shift
        )

        # Ensure focus so Ctrl / Shift multi-selection works properly
        cust_tree_local.bind("<Button-1>", lambda e: cust_tree_local.focus_set())

        for col in cust_cols:
            cust_tree_local.heading(col, text=col)

            width = 90
            if col in ("Vehicle", "Branch", "Type", "Note"):
                width = 120

            cust_tree_local.column(col, width=width, anchor="center")

        cust_tree_local.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=cust_tree_local.yview)
        cust_tree_local.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        # --------- BOTTOM BUTTONS ----------
        cp_bottom = tk.Frame(customer_panel, bg=BG, pady=10)
        cp_bottom.pack(fill="x")

        ttk.Button(
            cp_bottom,
            text="Calculate Total (Selected)",
            style="Secondary.TButton",
            command=lambda: calculate_selected_total(cust_tree_local)
        ).pack(side="left", padx=5)

        ttk.Button(
            cp_bottom,
            text="Generate Invoice",
            style="Primary.TButton",
            command=lambda: generate_invoice(cust_tree_local)
        ).pack(side="left", padx=5)

        ttk.Button(
    cp_bottom,
    text="Delete Selected",
    style="Secondary.TButton",
    command=lambda: delete_entries(cust_tree_local)
).pack(side="left", padx=5)

        ttk.Button(
            cp_bottom,
            text="Open Invoice Folder",
            style="Secondary.TButton",
            command=open_invoice_folder
        ).pack(side="left", padx=5)

        ttk.Button(
            cp_bottom,
            text="Refresh Panel",
            style="Secondary.TButton",
            command=refresh_customer_panel
        ).pack(side="right", padx=5)

        # store reference globally so refresh_customer_panel can use it
        cust_tree = cust_tree_local

    # finally, load data for this customer into the panel
    load_customer_entries(int(v_customer_id.get()), cust_tree)



# ==========================================================
#                    UI LAYOUT
# ==========================================================

# ---- TITLE ----
title = tk.Label(
    root,
    text="MS TRADERS – Corporate Silver Billing Suite",
    bg=BG,
    fg=ACCENT,
    font=("Segoe UI", 18, "bold")
)
title.pack(pady=10)

# ---- CUSTOMER + BILL INFO BAR (P2 Layout) ----
top_frame = tk.Frame(root, bg=CARD, bd=0,
                     highlightbackground=BORDER, highlightthickness=1,
                     padx=12, pady=10)
top_frame.pack(fill="x", padx=15)

tk.Label(top_frame, text="Customer ID:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
lbl_id = tk.Label(top_frame, textvariable=v_customer_id, bg=CARD, fg=TEXT,
                  width=6, anchor="w", font=("Segoe UI", 10, "bold"))
lbl_id.grid(row=0, column=1, padx=(2, 12))

tk.Label(top_frame, text="Name:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w")
entry(top_frame, v_customer_name, 18).grid(row=0, column=3, padx=4)

tk.Label(top_frame, text="Mobile:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky="w")
entry(top_frame, v_customer_mobile, 14).grid(row=0, column=5, padx=4)

tk.Label(top_frame, text="Address:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=0, column=6, sticky="w")
entry(top_frame, v_customer_address, 25).grid(row=0, column=7, padx=4)

tk.Label(top_frame, text="Date:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=0, column=8, sticky="w")
date_picker = DateEntry(
    top_frame,
    textvariable=v_date,
    date_pattern="yyyy-mm-dd",
    background=ACCENT,
    foreground="white",
    borderwidth=0,
    width=12
)
date_picker.grid(row=0, column=9, padx=4)

# second row: vehicle, branch, type + customer buttons
tk.Label(top_frame, text="Vehicle:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=(6, 0))
entry(top_frame, v_vehicle, 14).grid(row=1, column=1, padx=4, pady=(6, 0))

tk.Label(top_frame, text="Branch:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=1, column=2, sticky="w", pady=(6, 0))
entry(top_frame, v_branch, 18).grid(row=1, column=3, padx=4, pady=(6, 0))

tk.Label(top_frame, text="Type:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=1, column=4, sticky="w", pady=(6, 0))
entry(top_frame, v_type, 14).grid(row=1, column=5, padx=4, pady=(6, 0))

ttk.Button(
    top_frame,
    text="Save/Select Customer",
    style="Primary.TButton",
    command=save_customer
).grid(row=1, column=7, padx=6, pady=(6, 0), sticky="e")

ttk.Button(
    top_frame,
    text="Choose Existing",
    style="Secondary.TButton",
    command=choose_customer_popup
).grid(row=1, column=8, padx=4, pady=(6, 0), sticky="w")

# ---- LINE ITEM FRAME ----
item_frame = tk.Frame(root, bg=CARD, bd=0,
                      highlightbackground=BORDER, highlightthickness=1,
                      padx=12, pady=8)
item_frame.pack(fill="x", padx=15, pady=8)


def ilabel(txt, c):
    tk.Label(item_frame, text=txt, bg=CARD, fg=MUTED,
             font=("Segoe UI", 9, "bold")).grid(row=0, column=c, sticky="w")


ilabel("Quantity (Kg)", 0)
entry(item_frame, v_qty, 10).grid(row=1, column=0, padx=4)

ilabel("Rate", 1)
entry(item_frame, v_rate, 10).grid(row=1, column=1, padx=4)

ilabel("Labour / Kg", 2)
entry(item_frame, v_labour, 10).grid(row=1, column=2, padx=4)

ilabel("Advance", 3)
entry(item_frame, v_advance, 10).grid(row=1, column=3, padx=4)

ilabel("Calc Mode", 4)
calc_combo = ttk.Combobox(
    item_frame,
    textvariable=v_calc_mode,
    values=[
        "Rate × Qty + Labour × Qty",
        "Rate × Qty Only",
        "Labour × Qty Only"
    ],
    state="readonly",
    width=25
)
calc_combo.grid(row=1, column=4, padx=4)

ilabel("Note", 5)
entry(item_frame, v_note, 25).grid(row=1, column=5, padx=4)

ttk.Button(
    item_frame,
    text="Add Line",
    style="Primary.TButton",
    command=add_item
).grid(row=1, column=6, padx=10)

# ---- SEARCH / FILTER FRAME ----
search_frame = tk.Frame(root, bg=CARD, bd=0,
                        highlightbackground=BORDER, highlightthickness=1,
                        padx=12, pady=8)
search_frame.pack(fill="x", padx=15, pady=4)

tk.Label(search_frame, text="Filter Date:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
entry(search_frame, search_date, 12).grid(row=0, column=1, padx=4)

tk.Label(search_frame, text="Vehicle:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w")
entry(search_frame, search_vehicle, 12).grid(row=0, column=3, padx=4)

tk.Label(search_frame, text="Branch:", bg=CARD, fg=MUTED,
         font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky="w")
entry(search_frame, search_branch, 12).grid(row=0, column=5, padx=4)

ttk.Button(
    search_frame,
    text="Search",
    style="Secondary.TButton",
    command=search_entries
).grid(row=0, column=6, padx=6)

ttk.Button(
    search_frame,
    text="Show All",
    style="Secondary.TButton",
    command=show_all_entries
).grid(row=0, column=7, padx=4)

# ---- TREEVIEW (ITEM LIST) ----
tree_frame = tk.Frame(root, bg=BG)
tree_frame.pack(fill="both", expand=True, padx=15, pady=6)

columns = (
    "Date", "Customer", "Vehicle", "Branch", "Type",
    "Qty", "Rate", "Labour", "Advance", "PreTotal", "Total", "Note"
)

tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")

# 👇 IMPORTANT: give focus to tree so Ctrl/Shift selection works
tree.bind("<Button-1>", lambda e: tree.focus_set())

for col in columns:
    tree.heading(col, text=col)
    width = 100
    if col in ("Date", "Qty", "Rate", "Labour", "Advance", "PreTotal", "Total"):
        width = 90
    if col in ("Customer", "Note", "Branch"):
        width = 140
    tree.column(col, width=width, anchor="center")
tree.pack(side="left", fill="both", expand=True)

scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")

# ---- BOTTOM BAR ----
bottom = tk.Frame(root, bg=BG)
bottom.pack(fill="x", padx=15, pady=10)

ttk.Button(
    bottom,
    text="Calculate Total (Selected)",
    style="Secondary.TButton",
    command=lambda: calculate_selected_total(tree)
).pack(side="left", padx=4)

tk.Label(
    bottom,
    text="Grand Total: ₹",
    bg=BG,
    fg=TEXT,
    font=("Segoe UI", 10, "bold")
).pack(side="left")

tk.Label(
    bottom,
    textvariable=grand_total,
    bg=BG,
    fg=GREEN,
    font=("Segoe UI", 13, "bold")
).pack(side="left", padx=4)

ttk.Button(
    bottom,
    text="Generate Invoice",
    style="Primary.TButton",
    command=lambda: generate_invoice(tree)
).pack(side="left", padx=12)
ttk.Button(
    bottom,
    text="Delete Selected",
    style="Secondary.TButton",
    command=lambda: delete_entries(tree)
).pack(side="left", padx=6)


ttk.Button(
    bottom,
    text="Open Invoices Folder",
    style="Secondary.TButton",
    command=open_invoice_folder
).pack(side="left", padx=4)

# reports block
report_frame = tk.Frame(bottom, bg=BG)
report_frame.pack(side="right", padx=4)

tk.Label(
    report_frame,
    text="Report Date:",
    bg=BG,
    fg=MUTED,
    font=("Segoe UI", 8, "bold")
).grid(row=0, column=0, padx=4)

entry(report_frame, report_date, 10).grid(row=0, column=1, padx=2)

ttk.Button(
    report_frame,
    text="Daily",
    style="Secondary.TButton",
    command=daily_report
).grid(row=0, column=2, padx=2)

ttk.Button(
    report_frame,
    text="Monthly",
    style="Secondary.TButton",
    command=monthly_report
).grid(row=0, column=3, padx=2)

# ==========================================================
#      INITIAL LOAD & MAINLOOP
# ==========================================================

load_all_entries()
root.mainloop()  