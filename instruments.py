# Helper functions for instruments

def init_keithley(rm, address, source_mode, compliance):
    """
    Initialize a Keithley SMU for CW measurements.

    source_mode: 'curr' or 'volt'
    compliance:  compliance value in A or V (already converted)
    """
    k = rm.open_resource(address)

    k.write("*RST; status:preset; *CLS")
    k.write(f"sour:func {source_mode}")

    if source_mode == 'curr':
        k.write("sens:func 'volt'")
        k.write(f"sens:volt:prot:lev {compliance}")
        k.write("sens:volt:range:auto on")
    else:
        k.write("sens:func 'curr'")
        k.write(f"sens:curr:prot:lev {compliance}")
        k.write("sens:curr:range:auto on")

    k.write("form:elem curr")
    k.write("outp on")

    return k
