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

Auto add / update customers

Automatically detects existing customers

Customer Overview Panel shows:

All past bills

Total quantity purchased

Total billing amount

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

Supports multi-select delete

📄 Invoice Highlights

Premium layout with gold header

Auto-aligned table

Logo + Signature placeholders

Clean, modern typography

“System Generated – No Signature Needed” footer

Multi-row invoice support

🖥️ Tech Stack
Component	Technology
UI	Tkinter (Silver-Grey Theme)
Database	SQLite
PDF Generator	ReportLab
Packaging	PyInstaller
Installer	Inno Setup
⚙️ Installation (Developers)
1️⃣ Clone the Repository
git clone https://github.com/harshshah-2023/Commercial-Billing-Software.git
cd Commercial-Billing-Software/src

2️⃣ Create Virtual Environment
python -m venv venv


Activate (Windows):

venv\Scripts\activate

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Run the Application
python main.py

🛠️ Build EXE (Standalone)

Install PyInstaller:

pip install pyinstaller


Build Command:

pyinstaller --noconsole --onefile --icon=logo.ico main.py


EXE will be generated here:

src/dist/main.exe

📦 Deployment (Client Release)

Prepare deployment folder:

Billing_Install/
 ├ main.exe
 ├ ms_traders_billing.db
 ├ invoices/
 ├ logo.jpeg      ← Not included in repo
 ├ sign.jpeg      ← Not included in repo


Use Inno Setup to build a Windows Installer (.exe).

📁 Project Structure
Commercial-Billing-Software/
 └── src/
     ├── main.py
     ├── requirements.txt
     ├── main.spec
     ├── logo.jpeg    // Not included
     ├── sign.jpeg    // Not included
     ├── invoices/
     ├── build/
     └── dist/

📜 License — No License (All Rights Reserved)

This project is released WITHOUT a license, meaning:

❌ Not allowed:

No commercial use

No personal use

No modification

No redistribution

No derivative works

✔ Allowed:

Only viewing the source code on GitHub

By default, ALL RIGHTS RESERVED.

This fully protects your work and prevents misuse, copying, reselling, or repackaging by anyone.

👨‍💻 Developed With Care

Harsh Shah

Offline, optimized for business workflows, and production-ready for real clients.
