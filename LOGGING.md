# Comprehensive Guide to Logging in FastAPI

This guide explains how the logging system works in this project. It is designed to help you understand the "Why" and "How" of capturing application events.

## 1. The Big Picture: The Corporate Mailroom Analogy

Imagine your application is a big office building. Things happen constantly (errors, warnings, info). Logging is the system that captures these events and decides where they go.

### The 4 Main Components

1.  **Loggers (The Employees)**
    *   **Role:** These are the entry points. When you write `logger.info("User logged in")`, you are talking to a Logger.
    *   **In your code:** `social_media_app`, `uvicorn`.

2.  **Handlers (The Mailboxes)**
    *   **Role:** Once a Logger receives a message, it needs to send it somewhere. A Handler decides *where* that is (Screen? File? Email?).
    *   **In your code:**
        *   `default`: Prints colorful logs to the **terminal**.
        *   `rotating_file`: Writes logs to a **file** (`social_media_app.log`).

3.  **Formatters (The Translators)**
    *   **Role:** Before a Handler outputs the message, the Formatter decides what it looks like.
    *   **In your code:**
        *   `console`: Simple text for humans (`%(message)s`).
        *   `file`: Structured JSON for machines (`{"message": "..."}`).

4.  **Filters (The Security Guards)**
    *   **Role:** They inspect the log message and can modify it or block it entirely.
    *   **In your code:**
        *   `correlation_id`: Adds a unique ID to track requests.
        *   `email_obfuscation`: Hides sensitive email addresses (e.g., `j***@gmail.com`).

---

## 2. Log Levels (The Priority System)

Log levels act as a filter: **"Only show me messages that are THIS important or higher."**

| Level | Value | Meaning | Example |
| :--- | :--- | :--- | :--- |
| **DEBUG** | 10 | Detailed info for developers. | "Variable x = 5", "Loop 1 of 10" |
| **INFO** | 20 | Confirmation that things work. | "Server started", "User logged in" |
| **WARNING** | 30 | Unexpected but handled issue. | "Disk space low", "Login failed" |
| **ERROR** | 40 | Function failed due to a problem. | "DB connection failed", "File missing" |
| **CRITICAL** | 50 | Serious error, app might crash. | "Out of memory", "System crash" |

### How We Use Levels
*   **Development:** We use **DEBUG** to see everything.
*   **Production:** We use **INFO** to reduce noise and save space.

---

## 3. Understanding `logging_conf.py`

This file configures the entire system using a dictionary (`dictConfig`).

### The Flow of a Log Message
When you run `logger.info("User john@example.com joined")`:

1.  **Logger (`social_media_app`)** receives the message.
2.  It checks the **Level**. If `DEBUG` or higher, it proceeds.
3.  It passes the message to **Handlers**: `default` (Console) and `rotating_file` (File).

**Path A: The Console (`default` handler)**
1.  **Filter (`email_obfuscation`)**: Changes `john@example.com` to `jo**@example.com`.
2.  **Filter (`correlation_id`)**: Adds request ID (e.g., `req-123`).
3.  **Formatter (`console`)**: Formats as text.
4.  **Output**: `req-123 social_media_app:10 - User jo**@example.com joined`

**Path B: The File (`rotating_file` handler)**
1.  **Filter (`correlation_id`)**: Adds request ID.
2.  **Formatter (`file`)**: Formats as JSON.
3.  **Output**: `{"time": "...", "message": "User jo**@example.com joined", ...}` written to file.

---

## 4. Uvicorn Logging

We explicitly configure the `"uvicorn"` logger to **take control** of the server's logs.

**Why?**
1.  **Hijack Output:** Force Uvicorn logs to go through our Handlers (File & Console).
2.  **Apply Rules:** Add `correlation_id` to Uvicorn logs so we can match server requests with app logic.
3.  **Consistency:** Make all logs look the same.

---

## 5. Best Practices

*   **Use the right level:** Don't use `ERROR` for simple warnings.
*   **Don't log sensitive data:** Passwords, API keys, or full credit card numbers. (Our `email_obfuscation` filter helps with this!)
*   **Use structured logging (JSON):** Easier to search and analyze later using tools like Splunk or ELK Stack.
*   **Context is King:** Always include IDs (User ID, Order ID, Request ID) to make debugging easier.
