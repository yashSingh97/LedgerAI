import subprocess
import sys

def generate_requirements():
    """
    Generate requirements.txt from the current Python environment.
    Works on Windows 11 and other platforms.
    """
    try:
        print("Generating requirements.txt from current environment...")
        
        # Run pip freeze command and capture output
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Write the output to requirements.txt
        with open("requirements.txt", "w", encoding="utf-8") as f:
            f.write(result.stdout)
        
        print("✓ Successfully created requirements.txt")
        print(f"✓ Location: {os.path.abspath('requirements.txt')}")
        
        # Display the contents
        print("\nContents:")
        print("-" * 50)
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Error running pip freeze: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import os
    generate_requirements()