"""Orbit command entry: GUI, login supervisor and explicit registration."""
import sys

def main():
    command=sys.argv.pop(1) if len(sys.argv)>1 else 'gui'
    if command=='gui':
        from ui.app import App
        App().run()
    elif command=='supervise':
        from core.supervisor import main as supervise
        supervise()
    elif command=='register':
        from core.register import main as register
        register()
    else:raise SystemExit('Usage: orbit.py [gui|supervise|register] [options]')

if __name__=='__main__':main()
