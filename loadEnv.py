import json
import os
from pathlib import Path

def load_env_from_launch_json(file_path):
    """
    Read a launch.json file and set environment variables from the 'env' property.

    Args:
        file_path (str): Path to the launch.json file
    """
    try:
        # Read the JSON file
        with open(file_path, 'r') as file:
            launch_config = json.load(file)

        # VS Code launch.json typically has a 'configurations' array
        configurations = launch_config.get('configurations', [])

        # Process each configuration
        for config in configurations:
            config_name = config.get('name', 'Unknown')
            env_vars = config.get('env', {})

            if env_vars:
                print(f"Setting environment variables from configuration: {config_name}")

                # Set each environment variable
                for key, value in env_vars.items():
                    os.environ[key] = str(value)
                    print(f"  {key} = {value}")
            else:
                print(f"No environment variables found in configuration: {config_name}")

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file '{file_path}': {e}")
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")

def main():
    # Example usage
    launch_json_path = ".vscode/launch.json"

    # Check if the file exists
    if Path(launch_json_path).exists():
        load_env_from_launch_json(launch_json_path)

        # Verify environment variables were set
        print("\nCurrent environment variables:")
        for key, value in os.environ.items():
            if not key.startswith('_'):  # Skip system variables starting with _
                print(f"{key} = {value}")
    else:
        print(f"launch.json not found at {launch_json_path}")


if __name__ == "__main__":
    main()
