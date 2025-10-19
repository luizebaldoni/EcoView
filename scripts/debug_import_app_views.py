import importlib
import traceback

try:
    m = importlib.import_module('app.views')
    names = [n for n in dir(m) if not n.startswith('_')]
    print('OK - app.views imported. Public names:')
    print('\n'.join(names))
except Exception:
    traceback.print_exc()

