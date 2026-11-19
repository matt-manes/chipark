from backend.scripts import populate_parks, populate_tickets, populate_users


def main() -> None:
    populate_parks.main()
    populate_users.main()
    populate_tickets.main()


if __name__ == "__main__":
    main()
