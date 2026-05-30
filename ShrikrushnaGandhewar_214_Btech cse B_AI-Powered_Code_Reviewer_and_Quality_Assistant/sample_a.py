if not self.employees:

    options = {key: func for key, _, func in items}
    menu_text = "\n".join(
        ["\n========== Employee Management =========="]
        + [f"{key}. {desc}" for key, desc, _ in items]
    )
    while True:
        print(menu_text)
        choice = input("Enter Choice: ").strip()
        if choice == "10":
            print("Exiting System")
            break
        action = options.get(choice)
        if action is None:
            print("Invalid Choice")
            continue
        action()


