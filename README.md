# python-projects
🐍 Python Learning Projects (1–8)

This repository contains a collection of Python projects built progressively to learn file handling, regex, FastAPI, PostgreSQL, OOPs, CLI tools, and multithreading.
Each project builds on the previous one and introduces new concepts.

📌 Projects
Project 1 – PDF Text Extractor

Reads a PDF and extracts text content.

Saves extracted text to output.txt.

Project 2 – Folder-wise PDF Extractor

Reads all PDFs from sub-folders.

Extracts text and writes to output.txt in each sub-folder.

Handles missing folders/files gracefully.

Project 3 – Configurable Extractor

Supports a config file (config.json) to define extraction rules.

Reads PDFs and applies settings from config.

Writes extracted text accordingly.

Project 4 – Regex-based Extractor

Reads regex pattern from config.json.

Extracts only the matching parts of PDF text.

Handles missing/invalid config files.

Project 5 – PDF to PostgreSQL (FastAPI)

FastAPI backend that ingests questions from PDFs.

Stores in PostgreSQL with fields:

Subject, Chapter, Question Text, Answer Options, Source File, Page Range.

Handles errors: missing files, invalid config, etc.

Project 6 – CLI Chapter Loader

CLI tool to query DB.

Loads and prints all questions from a given chapter.

Handles empty input or no results found.

Project 7 – RSS Feed Loader (Multithreading)

Reads an RSS XML file.

Extracts links and fetches content from each.

Saves content to output.txt.

Uses multithreading for faster parallel downloads.

Project 8 – Question Types with OOPs

Extends Project 5 with inheritance & polymorphism:

Subjective Questions (long answers)

Objective True/False

Objective Multiple Choice (MCQs)

FastAPI API to store different question types.

🛠️ Tech Stack

Python 3.11

FastAPI + Uvicorn

PostgreSQL + SQLAlchemy

PyMuPDF (PDF parsing)

Regex

Requests + Multithreading

Pydantic

📂 Repository Structure
python-projects/
│── Project1/
│   ├── app/
│   └── README.md
│── Project2/
│── Project3/
│── Project4/
│── Project5/
│── Project6/
│── Project7/
│── Project8/
│── requirements.txt
│── README.md   ← master overview (this file)

🚀 How to Run

Clone the repo:

git clone https://github.com/<your-username>/python-projects.git
cd python-projects


Create virtual env & install dependencies:

python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt


Run specific projects:

Project 5/8 FastAPI:

uvicorn app.main:app --reload --port 8000


Project 6 CLI:

python app/cli_load_chapter.py --chapter "Water"


Project 7 RSS Loader:

python app/rss_loader.py rss_feed.xml

🎯 Learning Goals

📄 PDF Parsing & Regex

📂 File System Automation

⚙️ Config-driven Processing

🛢️ Database Integration (Postgres + SQLAlchemy)

🚀 FastAPI for APIs

🖥️ CLI Development

🧵 Multithreading in Python

🏛️ OOPs with Inheritance & Polymorphism

⚡ These projects represent a step-by-step Python learning journey, progressing from basic scripts → config-driven tools → APIs → CLI → multithreaded applications → advanced OOPs with FastAPI.