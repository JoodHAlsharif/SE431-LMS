import sqlite3
from datetime import datetime, timedelta
# مهم
# We use a separate database to test the maintenance changes
# (*) without affecting the original library database
DB = "library.db"

# These constants make the borrowing rules easier to update.
MAX_BORROW_LIMIT = 3
LOAN_PERIOD_DAYS = 14


def setup():
    db = sqlite3.connect(DB)
    c = db.cursor()

    # The members table remains unchanged (*)
    c.execute("""
        CREATE TABLE IF NOT EXISTS members(
            id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT
        )
    """)

    # MR-01: We replaced the single availability flag with two fields
    # This will allows us to store how many copies exist and how many are available (*)
    c.execute("""
        CREATE TABLE IF NOT EXISTS books(
            id INTEGER PRIMARY KEY,
            title TEXT,
            author TEXT,
            total_copies INTEGER,
            available_copies INTEGER
        )
    """)

    # Now each loan wull  still refers to a book using its book_id <--
    # We track the number of copies **not individual copy IDs**
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

    # MR-01: each book now starts with multiple available copies (*)
    # These numbers are sample data used to test the new feature
    c.execute(
        """INSERT OR IGNORE INTO books
           VALUES (1,'Clean Code','Robert Martin',3,3)"""
    )

    c.execute(
        """INSERT OR IGNORE INTO books
           VALUES (2,'Refactoring','Martin Fowler',2,2)"""
    )

    c.execute(
        """INSERT OR IGNORE INTO books
           VALUES (3,'Design Patterns','Gamma et al.',4,4)"""
    )

    db.commit()
    return db


def search_books(db, text):
    c = db.cursor()

    # We now display the number of copies instead of T or F
    c.execute(
        """SELECT id,title,author,total_copies,available_copies
           FROM books
           WHERE title LIKE ? OR author LIKE ?""",
        ("%" + text + "%", "%" + text + "%")
    )

    rows = c.fetchall()

    for row in rows:
        print(
            row[0], row[1], "-", row[2],
            "Total Copies:", row[3],
            "Available Copies:", row[4]
        )

    return rows


# the Refactoring: We moved member validation out of the borrow() (*)
# to make the borrowing fun short and easier to read
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

# importent **
# MR-01: a book can be borrowed if at least 1 copy is available
def validate_book(c, book_id):
    c.execute(
        "SELECT available_copies FROM books WHERE id=?",
        (book_id,)
    )

    book = c.fetchone()

    if not book:
        print("Book not found")
        return False

    if book[0] <= 0:
        print("Book is unavailable")
        return False

    return True


# Refactoring We separated the borrowing limit
# The original rule of 3 active loans is still the same
def check_borrowing_limit(c, member_id):
    c.execute(
        """SELECT COUNT(*) FROM loans
           WHERE member_id=? AND returned=0""",
        (member_id,)
    )

    if c.fetchone()[0] >= MAX_BORROW_LIMIT:
        print("Borrowing limit reached")
        return False

    return True


# MR-01: now after borrowing only 1 available copy is removed
# We also save the loan info in the same transaction ***
def record_loan(db, c, member_id, book_id):
    today = datetime.now()
    due = today + timedelta(days=LOAN_PERIOD_DAYS)

    c.execute(
        """UPDATE books
           SET available_copies = available_copies - 1
           WHERE id=? AND available_copies > 0""",
        (book_id,)
    )

    # This check prevents copy count becoming negative
    if c.rowcount != 1:
        db.rollback()
        print("Book is unavailable")
        return False

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

    db.commit()

    print("Book borrowed. Due:", due.date())
    return True


# borrow() now calls smaller functions
# This keeps validation separate from recording the loan
def borrow(db, member_id, book_id):
    c = db.cursor()

    if not validate_member(c, member_id):
        return False

    if not validate_book(c, book_id):
        return False

    if not check_borrowing_limit(c, member_id):
        return False

    return record_loan(db, c, member_id, book_id)


# refact: **Fine calculation** is handled in a separate fun
# The original late-return calculation remains unchanged
def calculate_fine(today, due):
    late = (today - due).days
    return late if late > 0 else 0


def return_book(db, member_id, book_id):
    c = db.cursor()

    # Find an active loan before allowing the return
    c.execute(
        """SELECT id,due_date FROM loans
           WHERE member_id=? AND book_id=? AND returned=0""",
        (member_id, book_id)
    )

    loan = c.fetchone()

    if not loan:
        print("Active loan not found")
        return False

    loan_id = loan[0]
    due = datetime.fromisoformat(loan[1])
    today = datetime.now()

    fine = calculate_fine(today, due)

    #  loan as returned
    c.execute(
        "UPDATE loans SET returned=1 WHERE id=?",
        (loan_id,)
    )

    # MR-01: returning a book adds 1 available copy
    # We are making sure that the count does not exceed the total copies
    c.execute(
        """UPDATE books
           SET available_copies = available_copies + 1
           WHERE id=? AND available_copies < total_copies""",
        (book_id,)
    )

    if c.rowcount != 1:
        db.rollback()
        print("Book availability update failed")
        return False

    db.commit()

    print("Book returned")

    if fine:
        print("Fine:", fine)

    return True


def main():
    db = setup()

    # We still kept the original menu and user interactions (*)
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
