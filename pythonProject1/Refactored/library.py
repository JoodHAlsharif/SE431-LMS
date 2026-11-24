import sqlite3
# import os  # Used for temporary database path checking
from datetime import datetime, timedelta
# Figure 3.9
DB = "library.db"

# Named Constants
MAX_BORROW_LIMIT = 3
LOAN_PERIOD_DAYS = 14


def setup():
    db = sqlite3.connect(DB)
    c = db.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS members(
            id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS books(
            id INTEGER PRIMARY KEY,
            title TEXT,
            author TEXT,
            available INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS loans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id TEXT,
            book_id INTEGER,
            borrow_date TEXT,
            due_date TEXT,
            returned INTEGER
        )
    """)

    db.commit()

    c.execute(
        "INSERT OR IGNORE INTO members VALUES ('S1','Ali','ACTIVE')"
    )

    c.execute(
        "INSERT OR IGNORE INTO members VALUES ('S2','Sara','ACTIVE')"
    )

    c.execute(
        "INSERT OR IGNORE INTO books VALUES (1,'Clean Code','Robert Martin',1)"
    )

    c.execute(
        "INSERT OR IGNORE INTO books VALUES (2,'Refactoring','Martin Fowler',1)"
    )

    c.execute(
        "INSERT OR IGNORE INTO books VALUES (3,'Design Patterns','Gamma et al.',1)"
    )

    # Temporary test book - disabled after testing
    # c.execute(
    #     "INSERT OR IGNORE INTO books VALUES (4,'Test Book','Test Author',1)"
    # )

    db.commit()
    return db


def search_books(db, text):
    c = db.cursor()

    c.execute(
        """SELECT id,title,author,available
           FROM books
           WHERE title LIKE ? OR author LIKE ?""",
        ("%" + text + "%", "%" + text + "%")
    )

    rows = c.fetchall()

    for row in rows:
        print(row[0], row[1], "-", row[2],
              "Available:", bool(row[3]))

    return rows

# screen shot 1
def validate_member(c, member_id):
    c.execute(
        "SELECT id,status FROM members WHERE id=?",
        (member_id,)
    )

    member = c.fetchone()

    if not member:
        print("Member not found")
        return False

    if member[1] != "ACTIVE":
        print("Member is not active")
        return False

    return True

# screen shot 2
def validate_book(c, book_id):
    c.execute(
        "SELECT available FROM books WHERE id=?",
        (book_id,)
    )

    book = c.fetchone()

    if not book:
        print("Book not found")
        return False

    if book[0] == 0:
        print("Book is unavailable")
        return False

    return True


# screen shot 3
def check_borrowing_limit(c, member_id):
    c.execute(
        """SELECT COUNT(*) FROM loans
           WHERE member_id=? AND returned=0""",
        (member_id,)
    )

# Figure 3.9
    if c.fetchone()[0] >= MAX_BORROW_LIMIT:
        print("Borrowing limit reached")
        return False

    return True

# screen shot 4
def record_loan(db, c, member_id, book_id):

    today = datetime.now()
    due = today + timedelta(days=LOAN_PERIOD_DAYS)

    c.execute(
        """INSERT INTO loans
           (member_id,book_id,borrow_date,due_date,returned)
           VALUES(?,?,?,?,0)""",
        (
            member_id,
            book_id,
            today.isoformat(),
            due.isoformat()
        )
    )
    c.execute(
        "UPDATE books SET available=0 WHERE id=?",
        (book_id,)
    )
    db.commit()
    print("Book borrowed. Due:", due.date())
    return True


#After Refactoring  Figure 3.2: Refactored borrow() Function
def borrow(db, member_id, book_id):
    c = db.cursor()

    if not validate_member(c, member_id):
        return False

    if not validate_book(c, book_id):
        return False

    if not check_borrowing_limit(c, member_id):
        return False

    return record_loan(db, c, member_id, book_id)

# Figure 3.7 (a)
def calculate_fine(today, due):
    late = (today - due).days
    return late if late > 0 else 0


def return_book(db, member_id, book_id):
    c = db.cursor()
    c.execute(
        """SELECT id,due_date FROM loans
           WHERE member_id=? AND book_id=? AND returned=0""",
        (member_id, book_id)
    )

    loan = c.fetchone()
    if not loan:
        print("Active loan not found")
        return False

# Figure 3.7 (b)
    loan_id = loan[0]
    due = datetime.fromisoformat(loan[1])
    today = datetime.now()

    fine = calculate_fine(today, due)

    c.execute(
        "UPDATE loans SET returned=1 WHERE id=?",
        (loan_id,)
    )

    c.execute(
        "UPDATE books SET available=1 WHERE id=?",
        (book_id,)
    )

    db.commit()

    print("Book returned")

    if fine:
        print("Fine:", fine)

    return True


def main():
    db = setup()

    while True:
        print("\nLIBRARY")
        print("1 Search")
        print("2 Borrow")
        print("3 Return")
        print("4 Exit")

        choice = input("Choice: ")

        if choice == "1":
            text = input("Search: ")
            search_books(db, text)

        elif choice == "2":
            member = input("Member ID: ")
            book = int(input("Book ID: "))
            borrow(db, member, book)

        elif choice == "3":
            member = input("Member ID: ")
            book = int(input("Book ID: "))
            return_book(db, member, book)

        elif choice == "4":
            db.close()
            break

        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()

    # Temporary database check - disabled after testing
    #
    # print("Database path:", os.path.abspath(DB))
    #
    # db = sqlite3.connect(DB)
    # c = db.cursor()
    #
    # c.execute("""
    #     SELECT member_id, book_id, returned
    #     FROM loans
    # """)
    #
    # print("Loan records:", c.fetchall())
    #
    # db.close()

    # Temporary test for calculate_fine()
    #test_due = datetime(2026, 11, 10)
    #test_today = datetime(2026, 11, 16)
    #print("Late return fine:", calculate_fine(test_today, test_due))
