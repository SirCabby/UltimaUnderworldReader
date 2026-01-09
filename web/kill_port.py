#!/usr/bin/env python3
"""
Kill any process using the specified port.
Works on both Windows and Unix-like systems.
"""
import sys
import subprocess
import os

def kill_port(port):
    """Kill any process using the specified port."""
    if os.name == 'nt':  # Windows
        try:
            # Find process using the port using netstat
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                check=False
            )
            
            pids_found = set()
            for line in result.stdout.split('\n'):
                # Look for lines with LISTENING state and matching port
                if 'LISTENING' in line.upper() and f':{port}' in line:
                    # Extract PID (last column in netstat -ano output)
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        # Validate PID is numeric
                        if pid.isdigit():
                            pids_found.add(pid)
            
            # Kill all found processes
            killed_any = False
            for pid in pids_found:
                kill_result = subprocess.run(
                    ['taskkill', '/F', '/PID', pid],
                    capture_output=True,
                    check=False
                )
                if kill_result.returncode == 0:
                    print(f"Killed process {pid} using port {port}")
                    killed_any = True
            
            return killed_any
        except Exception as e:
            print(f"Error killing process on Windows: {e}", file=sys.stderr)
            return False
    else:  # Unix-like (Linux, macOS)
        try:
            # Find process using the port
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                # Kill all processes using the port
                kill_result = subprocess.run(
                    ['kill', '-9'] + pids,
                    capture_output=True,
                    check=False
                )
                if kill_result.returncode == 0:
                    print(f"Killed processes {', '.join(pids)} using port {port}")
                    return True
        except FileNotFoundError:
            # lsof not available, try fuser as alternative
            try:
                result = subprocess.run(
                    ['fuser', '-k', f'{port}/tcp'],
                    capture_output=True,
                    check=False
                )
                if result.returncode == 0:
                    print(f"Killed process using port {port}")
                    return True
            except FileNotFoundError:
                pass
        except Exception as e:
            print(f"Error killing process on Unix: {e}", file=sys.stderr)
            return False
    
    return False

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>", file=sys.stderr)
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
    except ValueError:
        print(f"Error: Invalid port number: {sys.argv[1]}", file=sys.stderr)
        sys.exit(1)
    
    killed = kill_port(port)
    if not killed:
        print(f"No process found using port {port}")
    # Always exit with 0 to allow Makefile to continue
    sys.exit(0)
