import threading
import pandas as pd
from collections import namedtuple

import config
from user import User

Link = namedtuple("Link", ["user", "bad_user", "link_status", "link_data"])

def parse_row(row, bad_logins, bad_devices, users, bad_users):
    login = row["login"]

    if login == "-":
        return

    if login in bad_logins or row["device_id"] in bad_devices:
        if login not in bad_users:
            bad_users[login] = User(login)

        bad_users[login].parse_event(row)
    else:
        if login not in users:
            users[login] = User(login)
        
        users[login].parse_event(row)

def find_links(users, new_bad_users, old_bad_users):
    # Неочевидно, зачем здесь разделение на new_bad_users и old_bad_users.
    # При втором и след запусках не нужно рассматривать тех пользователей, о компрометации которых мы УЖЕ знаем,
    # по этой причине следует передавать bad_users в каждом запуске.
    # С другой стороны, нет смысла прогонять через функцию is_linked пользователей из bad_users,
    # так как это уже сделано в первом запуске. Похоже на костыль, но идея в оптимизации времени.
    linked_users = {}

    for uid, user in users.items():
        if uid in old_bad_users or uid in new_bad_users:
            continue

        for bad_user in new_bad_users.values():
            link_status, link_data = user.is_linked(bad_user)
            if link_status != User.NOT_LINKED:
                linked_users[user.uid] = Link(user, bad_user, link_status, link_data)

    return linked_users


def main():
    data = pd.read_excel(config.filename)
    users = {}
    bad_users = {}

    threads = []
    for _, row in data.iterrows():
        new_thread = threading.Thread(target=parse_row,
                             args=(row, config.bad_logins, config.bad_devices, users, bad_users))
        threads.append(new_thread)
        new_thread.start()

        if len(threads) >= config.max_threads:
            for t in threads:
                t.join()
            threads = []

    for t in threads:
        t.join()

    
    linked_users = find_links(users, bad_users, bad_users)
    new_links = find_links(users, linked_users, bad_users)
    while new_links:
        linked_users.update(new_links)
        new_links = find_links(users, new_links, dict(bad_users, **linked_users))
    
    print("Скомпрометированные пользователи:")
    [print(f"{i}. {bad_user}") for i, bad_user in enumerate(bad_users, 1)]
    print("\nСвязанные с ними пользователи:")
    [print(f"{i}. {user.user.uid}\nСвязан с: {user.bad_user.uid}\n" + \
           f"Тип связи: {user.link_status}\nПересечение: {user.link_data}\n")
        for i, user in enumerate(linked_users.values(), 1)]


if __name__ == "__main__":
    main()
