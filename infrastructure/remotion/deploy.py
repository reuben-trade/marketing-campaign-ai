#!/usr/bin/env python3
"""
Remotion Lambda Deployment Script

This script deploys the Remotion Lambda function to AWS for cloud video rendering.
It handles:
1. Creating/updating the Lambda function
2. Setting up required IAM roles and policies
3. Configuring S3 buckets for input/output
4. Setting up the Lambda serve URL

Prerequisites:
- AWS CLI configured with appropriate credentials
- Node.js 18+ installed
- Remotion dependencies installed in remotion/ directory

Usage:
    python infrastructure/remotion/deploy.py --region us-east-1 --memory 3009
    python infrastructure/remotion/deploy.py --check  # Check deployment status
    python infrastructure/remotion/deploy.py --cleanup  # Remove deployment
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Default configuration
DEFAULT_REGION = "us-east-1"
DEFAULT_MEMORY_SIZE = 3009  # Remotion recommends 3009 MB
DEFAULT_TIMEOUT = 900  # 15 minutes (max Lambda timeout)
DEFAULT_DISK_SIZE = 2048  # 2GB ephemeral storage
LAMBDA_FUNCTION_PREFIX = "remotion-render"


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_remotion_dir() -> Path:
    """Get the remotion project directory."""
    return get_project_root() / "remotion"


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except FileNotFoundError as e:
        return False, f"Command not found: {e}"


def check_prerequisites() -> list[str]:
    """Check if all prerequisites are met."""
    errors = []

    # Check AWS CLI
    success, _ = run_command(["aws", "--version"])
    if not success:
        errors.append("AWS CLI is not installed or not in PATH")

    # Check Node.js
    success, output = run_command(["node", "--version"])
    if not success:
        errors.append("Node.js is not installed or not in PATH")
    else:
        # Check version >= 18
        version = output.strip().lstrip("v")
        major = int(version.split(".")[0])
        if major < 18:
            errors.append(f"Node.js 18+ required, found {version}")

    # Check npx
    success, _ = run_command(["npx", "--version"])
    if not success:
        errors.append("npx is not installed or not in PATH")

    # Check remotion directory
    remotion_dir = get_remotion_dir()
    if not remotion_dir.exists():
        errors.append(f"Remotion directory not found: {remotion_dir}")
    elif not (remotion_dir / "package.json").exists():
        errors.append("package.json not found in remotion directory")

    # Check AWS credentials
    success, _ = run_command(["aws", "sts", "get-caller-identity"])
    if not success:
        errors.append("AWS credentials not configured or invalid")

    return errors


def install_remotion_lambda_deps() -> bool:
    """Install Remotion Lambda dependencies."""
    remotion_dir = get_remotion_dir()
    print("Installing Remotion Lambda dependencies...")

    # Check if @remotion/lambda is already installed
    package_json = remotion_dir / "package.json"
    with open(package_json) as f:
        pkg = json.load(f)

    deps = pkg.get("dependencies", {})
    if "@remotion/lambda" not in deps:
        print("Adding @remotion/lambda to dependencies...")
        success, output = run_command(
            ["npm", "install", "@remotion/lambda", "--save"],
            cwd=remotion_dir,
        )
        if not success:
            print(f"Failed to install @remotion/lambda: {output}")
            return False

    return True


def deploy_lambda(
    region: str,
    memory_size: int = DEFAULT_MEMORY_SIZE,
    timeout: int = DEFAULT_TIMEOUT,
    disk_size: int = DEFAULT_DISK_SIZE,
) -> dict:
    """Deploy the Remotion Lambda function."""
    remotion_dir = get_remotion_dir()

    print(f"Deploying Remotion Lambda to {region}...")
    print(f"  Memory: {memory_size} MB")
    print(f"  Timeout: {timeout} seconds")
    print(f"  Disk: {disk_size} MB")

    # Use Remotion's built-in Lambda deployment
    cmd = [
        "npx",
        "remotion",
        "lambda",
        "functions",
        "deploy",
        "--region",
        region,
        "--memory",
        str(memory_size),
        "--timeout",
        str(timeout),
        "--disk",
        str(disk_size),
        "--yes",  # Skip confirmation prompts
    ]

    success, output = run_command(cmd, cwd=remotion_dir)
    if not success:
        print(f"Deployment failed: {output}")
        return {"success": False, "error": output}

    print(output)
    return {"success": True, "output": output}


def deploy_sites(region: str) -> dict:
    """Deploy the Remotion bundle to S3 (site)."""
    remotion_dir = get_remotion_dir()

    print(f"Deploying Remotion site (bundle) to {region}...")

    cmd = [
        "npx",
        "remotion",
        "lambda",
        "sites",
        "create",
        "--region",
        region,
        "--site-name",
        f"marketing-campaign-ai-{region}",
        "--yes",
    ]

    success, output = run_command(cmd, cwd=remotion_dir)
    if not success:
        print(f"Site deployment failed: {output}")
        return {"success": False, "error": output}

    # Parse the site URL from output
    site_url = None
    for line in output.split("\n"):
        if "https://" in line and ".s3." in line:
            site_url = line.strip()
            break

    print(output)
    return {"success": True, "output": output, "site_url": site_url}


def get_function_info(region: str) -> dict | None:
    """Get information about deployed Lambda function."""
    remotion_dir = get_remotion_dir()

    cmd = [
        "npx",
        "remotion",
        "lambda",
        "functions",
        "ls",
        "--region",
        region,
    ]

    success, output = run_command(cmd, cwd=remotion_dir)
    if not success:
        return None

    # Parse function info from output
    functions = []
    for line in output.split("\n"):
        if LAMBDA_FUNCTION_PREFIX in line:
            functions.append(line.strip())

    if not functions:
        return None

    return {
        "functions": functions,
        "region": region,
    }


def get_sites_info(region: str) -> dict | None:
    """Get information about deployed Remotion sites."""
    remotion_dir = get_remotion_dir()

    cmd = [
        "npx",
        "remotion",
        "lambda",
        "sites",
        "ls",
        "--region",
        region,
    ]

    success, output = run_command(cmd, cwd=remotion_dir)
    if not success:
        return None

    return {"sites": output.strip(), "region": region}


def cleanup(region: str) -> bool:
    """Remove Remotion Lambda deployment."""
    remotion_dir = get_remotion_dir()

    print(f"Cleaning up Remotion Lambda in {region}...")

    # Remove functions
    cmd = [
        "npx",
        "remotion",
        "lambda",
        "functions",
        "rmall",
        "--region",
        region,
        "--yes",
    ]

    success, output = run_command(cmd, cwd=remotion_dir)
    if not success:
        print(f"Warning: Could not remove functions: {output}")

    # Remove sites
    cmd = [
        "npx",
        "remotion",
        "lambda",
        "sites",
        "rmall",
        "--region",
        region,
        "--yes",
    ]

    success, output = run_command(cmd, cwd=remotion_dir)
    if not success:
        print(f"Warning: Could not remove sites: {output}")

    print("Cleanup complete.")
    return True


def generate_env_config(region: str, function_name: str, site_name: str) -> str:
    """Generate environment variable configuration."""
    return f"""
# Remotion Lambda Configuration
# Add these to your .env file

REMOTION_AWS_REGION={region}
REMOTION_FUNCTION_NAME={function_name}
REMOTION_SITE_NAME={site_name}
"""


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Remotion Lambda for cloud video rendering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_REGION,
        help=f"AWS region for deployment (default: {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--memory",
        type=int,
        default=DEFAULT_MEMORY_SIZE,
        help=f"Lambda memory in MB (default: {DEFAULT_MEMORY_SIZE})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Lambda timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--disk",
        type=int,
        default=DEFAULT_DISK_SIZE,
        help=f"Lambda disk size in MB (default: {DEFAULT_DISK_SIZE})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check deployment status only",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove Remotion Lambda deployment",
    )

    args = parser.parse_args()

    # Check prerequisites
    print("Checking prerequisites...")
    errors = check_prerequisites()
    if errors:
        print("\nPrerequisite check failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("All prerequisites met.\n")

    if args.check:
        # Check status only
        func_info = get_function_info(args.region)
        if func_info:
            print(f"Lambda functions in {args.region}:")
            for func in func_info["functions"]:
                print(f"  - {func}")
        else:
            print(f"No Lambda functions found in {args.region}")

        sites_info = get_sites_info(args.region)
        if sites_info:
            print(f"\nSites in {args.region}:")
            print(sites_info["sites"])

        return

    if args.cleanup:
        cleanup(args.region)
        return

    # Install dependencies if needed
    if not install_remotion_lambda_deps():
        print("Failed to install dependencies")
        sys.exit(1)

    # Deploy Lambda function
    print("\n" + "=" * 60)
    result = deploy_lambda(
        region=args.region,
        memory_size=args.memory,
        timeout=args.timeout,
        disk_size=args.disk,
    )
    if not result["success"]:
        sys.exit(1)

    # Deploy site (Remotion bundle)
    print("\n" + "=" * 60)
    site_result = deploy_sites(args.region)
    if not site_result["success"]:
        print("Warning: Site deployment failed. You may need to deploy manually.")

    # Show configuration
    print("\n" + "=" * 60)
    print("Deployment complete!")
    print("\nNext steps:")
    print("1. Add the following to your .env file:")
    print(f"   REMOTION_AWS_REGION={args.region}")
    print("   REMOTION_FUNCTION_NAME=<function-name-from-output>")
    print("   REMOTION_SITE_NAME=<site-name-from-output>")
    print("\n2. The backend will automatically use Lambda when REMOTION_AWS_REGION is set.")
    print("\nFor more information, see: docs/remotion-setup.md")


if __name__ == "__main__":
    main()
