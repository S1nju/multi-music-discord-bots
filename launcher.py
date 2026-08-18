import subprocess
import os
import sys

def main():
    # Read variables natively injected by Docker (via env_file) into the OS environment
    base_env = os.environ.copy()
    
    processes = []
    
    # Loop over 1 to 8 bots as defined in the .env and docker-compose
    for i in range(1, 10):
        token = base_env.get(f"BOT_TOKEN{i}")
        if token and token.strip() != "":
            print(f"Starting bot {i}...")
            
            # Map the indexed variables to the standard variables main.py expects
            bot_env = base_env.copy()
            bot_env["BOT_TOKEN"] = token
            bot_env["BOT_PREFIX"] = base_env.get(f"BOT_PREFIX{i}", "-")
            bot_env["BOT_CHANNEL_ID"] = base_env.get(f"BOT_CHANNEL_ID{i}", "")
            bot_env["BOT_PLAY_LETTER"] = base_env.get(f"BOT_PLAY_LETTER{i}", "")
            
            # Use subprocess to isolate memory and avoid pure async singleton collisions (like Wavelink Pool)
            p = subprocess.Popen([sys.executable, "main.py"], env=bot_env)
            processes.append(p)
            
    if not processes:
        print("No valid BOT_TOKEN{x} found in .env!")
        return

    print(f"Successfully started {len(processes)} bots. Press CTRL+C to stop all.")
    
    try:
        # Keep the launcher script alive so we can shutdown smoothly
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\nShutting down all bots...")
        for p in processes:
            p.terminate()

if __name__ == "__main__":
    main()
