import subprocess, os, signal
try:
    out=subprocess.check_output(['lsof','-ti',':8000']).decode().strip().splitlines()
    for pid in out:
        if pid.strip():
            print('Killing',pid); os.kill(int(pid),signal.SIGTERM)
except Exception as e: print('No server to stop or lsof unavailable:',e)
