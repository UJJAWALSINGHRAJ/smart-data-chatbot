# Smart Data Chatbot

AI-powered business analytics chatbot using Python, SQL, Streamlit, and real e-commerce data.

## Overview

Smart Data Chatbot is an AI-style business analytics assistant built using Python, Streamlit, SQLite, and the Olist e-commerce dataset. It allows users to ask both general and business-related questions and returns related answers, SQL-backed insights, charts, and summaries.

## Features

- Premium Streamlit UI
- General chat support
- Business data question support
- SQL-backed answers from real e-commerce dataset
- KPI cards
- Charts and insight summaries
- Multi-question input support
- Free smart matching without API key

## Tech Stack

- Python
- Streamlit
- SQLite
- SQL
- Pandas

## Dataset

This project uses the Olist Brazilian E-Commerce dataset.

Main tables used:
- orders
- customers
- payments
- reviews
- order_items
- products
- sellers

## Example Questions

- hello
- how are you
- what is sql
- explain this project
- how many orders do we have
- total revenue
- which city has highest orders
- payment method
- reviews summary
- monthly trend
- total orders and total revenue

## Project Structure

```bash
smart-data-chatbot/
│── app.py
│── db_loader.py
│── db_query.py
│── requirements.txt
│── data/
│── .gitignore