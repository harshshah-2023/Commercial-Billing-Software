Commercial Billing Software – Desktop Application

A modern, fully offline Billing & Customer Management System designed for small and medium businesses.
Built using Python, Tkinter, SQLite, and ReportLab, this app delivers a fast, clean, and professional billing workflow.

🧾 Key Features
💼 Billing & Line-Item Management

Add unlimited billing entries

Multiple calculation modes:

Rate × Qty

Labour × Qty

Combined Mode

Automatically computes:

PreTotal

Total

Supports multi-row invoice generation

Professional PDF invoices with:

Logo (excluded from repo)

Signature (excluded from repo)

Corporate silver-grey theme

👤 Customer Management

Add/update customers automatically

Auto-detect existing customers

Customer Overview Panel:

All past bills

Total quantity purchased

Total billing value

Total number of invoices

Generate invoice from customer history

🔍 Search & Reporting

Search by:

Date

Vehicle Number

Branch

Reports:

Daily Summary

Monthly Summary

Multi-select delete

📄 Invoice Highlights

Premium layout with gold header

Auto-aligned data table

Company branding (Logo + Signature placeholders)

Modern clean typography

“System Generated – No Signature Needed” footer

Supports multiple selected rows in a single invoice

🖥️ Tech Stack
Component	Technology
UI	Tkinter (Silver-grey corporate theme)
Database	SQLite
PDF Generator	ReportLab
Packaging	PyInstaller
Distribution	Inno Setup Installer
⚙️ Installation (Developers)
1️⃣ Clone the Repository
git clone https://github.com/harshshah-2023/Commercial-Billing-Software.git
cd Commercial-Billing-Software/src

2️⃣ Create Virtual Environment
python -m venv venv


Activate it (Windows):

venv\Scripts\activate

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Run the App
python main.py

🛠️ Build EXE (Standalone)
Install PyInstaller
pip install pyinstaller

Build Command
pyinstaller --noconsole --onefile --icon=logo.ico main.py


Your EXE will be generated here:

src/dist/main.exe

📦 Deployment (Client Version)

Prepare your deployment folder:

Billing_Install/
 ├ main.exe
 ├ ms_traders_billing.db
 ├ invoices/
 ├ logo.jpeg     ← (Not included in repo)
 ├ sign.jpeg     ← (Not included in repo)


Use Inno Setup to create a single-click installer for clients.

📁 Project Structure
Commercial-Billing-Software/
 └── src/
     ├── main.py
     ├── requirements.txt
     ├── main.spec
     ├── logo.jpeg       // Not included
     ├── sign.jpeg       // Not included
     ├── invoices/
     ├── build/
     └── dist/

📜 License (MIT)

This project is licensed under the MIT License:

✔ Free personal & commercial use
✔ Modification allowed
✔ Sharing allowed with attribution
✘ Author not liable for damages

Developed with care by Harsh Shah
