"""Debugging utility: logs pyreadstat version and runs create_dummy.main() to debug write failures.

Output is written to debug.log in the same directory.
"""
import sys
log = open(r"C:\Users\NinaIrenHoven\src_github\Nina_div\Syklistforeningen\debug.log", "w")

try:
    import pyreadstat
    log.write(f"pyreadstat version: {pyreadstat.__version__}\n")
    import inspect
    sig = inspect.signature(pyreadstat.write_sav)
    log.write(f"write_sav params: {list(sig.parameters.keys())}\n")
except Exception as e:
    log.write(f"import error: {e}\n")

try:
    sys.path.insert(0, r"C:\Users\NinaIrenHoven\src_github\Nina_div\Syklistforeningen")
    import create_dummy
    create_dummy.main()
    log.write("main() completed successfully\n")
except Exception as e:
    import traceback
    log.write(f"ERROR: {e}\n")
    log.write(traceback.format_exc())

log.close()
