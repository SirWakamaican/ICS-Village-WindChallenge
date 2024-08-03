import os

def run_script(script_path):
    try:
        exec(open(script_path).read(), globals())
    except Exception as e:
        print(f"Error running script: {e}")

def display_menu(script_files):
    print("Select a script to run:")
    for idx, script in enumerate(script_files, start=1):
        print(f"{idx}. {script}")

def main():
    script_dir = "/app/scripts"
    script_files = [file for file in os.listdir(script_dir) if file.endswith(".py")]

    if not script_files:
        print("No Python scripts found in the specified directory.")
        return

    while True:
        display_menu(script_files)

        try:
            choice = int(input("Enter the script number (0 to exit): "))
        except ValueError:
            print("Invalid input. Please enter a valid number.")
            continue

        if choice == 0:
            print("Exiting the script.")
            break
        elif 0 < choice <= len(script_files):
            selected_script = script_files[choice - 1]
            script_path = os.path.join(script_dir, selected_script)
            run_script(script_path)
        else:
            print("Invalid choice. Please enter a valid script number.")

if __name__ == "__main__":
    main()

