import warnings

from warnings import (_is_internal_frame, _next_external_frame,
    _filters_mutated, showwarning, defaultaction, onceregistry)

wfmu = _filters_mutated

warnings._filters_version = 1

def _filters_mutated():
    warnings._filters_version += 1
    
warnings._filters_mutated = _filters_mutated


def new_warn_explicit(message, category, filename, lineno,
                  module=None, registry=None, module_globals=None, emit_module=None):
    lineno = int(lineno)
    if module is None:
        module = filename or "<unknown>"
        if module[-3:].lower() == ".py":
            module = module[:-3] # XXX What about leading pathname?
    if registry is None:
        registry = {}
    if registry.get('version', 0) != warnings._filters_version:
        registry.clear()
        registry['version'] = warnings._filters_version
    if isinstance(message, Warning):
        text = str(message)
        category = message.__class__
    else:
        text = message
        message = category(message)
    key = (text, category, lineno)
    # Quick test for common case
    if registry.get(key):
        return
    # Search the filters
    for item in warnings.filters:
        if len(item) == 5:
            action, msg, cat, mod, ln = item
            emod = None
            print('Nop')
        else:
            action, msg, cat, mod, ln, emod= item
            # print('oh hey !')
            # print('     ', (msg is None or msg.match(text)))
            # print('     ', issubclass(category, cat))
            # print('     ', (mod is None or mod.match(module)), module)
            # print('     ', (emod is None or emod.match(emit_module)))
            # print('     ', (ln == 0 or lineno == ln))
        if ((msg is None or msg.match(text)) and
            issubclass(category, cat) and
            (mod is None or mod.match(module)) and
            (emod is None or emod.match(emit_module)) and
            (ln == 0 or lineno == ln)):
            break
    else:
        action = defaultaction
    # Early exit actions
    if action == "ignore":
        registry[key] = 1
        return

    # Prime the linecache for formatting, in case the
    # "file" is actually in a zipfile or something.
    import linecache
    linecache.getlines(filename, module_globals)

    if action == "error":
        raise message
    # Other actions
    if action == "once":
        registry[key] = 1
        oncekey = (text, category)
        if onceregistry.get(oncekey):
            return
        onceregistry[oncekey] = 1
    elif action == "always":
        pass
    elif action == "module":
        registry[key] = 1
        altkey = (text, category, 0)
        if registry.get(altkey):
            return
        registry[altkey] = 1
    elif action == "default":
        registry[key] = 1
    else:
        # Unrecognized actions are errors
        raise RuntimeError(
              "Unrecognized action (%r) in warnings.filters:\n %s" %
              (action, item))
    if not callable(showwarning):
        raise TypeError("warnings.showwarning() must be set to a "
                        "function or method")
    # Print message and context
    showwarning(message, category, filename, lineno)


import sys
def _get_stack_frame(stacklevel):
    stacklevel = stacklevel +1
    if stacklevel <= 1 or _is_internal_frame(sys._getframe(1)):
        # If frame is too small to care or if the warning originated in
        # internal code, then do not try to hide any frames.
        frame = sys._getframe(stacklevel)
    else:
        frame = sys._getframe(1)
        # Look for one frame less since the above line starts us off.
        for x in range(stacklevel-1):
            frame = _next_external_frame(frame)
            if frame is None:
                raise ValueError
    return frame
def new_warn(message, category=None, stacklevel=1, emitstacklevel=1):
    """Issue a warning, or maybe ignore it or raise an exception."""
    # Check if message is already a Warning object
    
    ####################
    ### Get category ###
    ####################
    if isinstance(message, Warning):
        category = message.__class__
    # Check category argument
    if category is None:
        category = UserWarning
    if not (isinstance(category, type) and issubclass(category, Warning)):
        raise TypeError("category must be a Warning subclass, "
                        "not '{:s}'".format(type(category).__name__))
    # Get context information
    try:
        frame = _get_stack_frame(stacklevel)
    except ValueError:
        globals = sys.__dict__
        lineno = 1
    else:
        globals = frame.f_globals
        lineno = frame.f_lineno
        
    try:
        eframe = _get_stack_frame(emitstacklevel)
    except ValueError:
        eglobals = sys.__dict__
    else:
        eglobals = eframe.f_globals
    if '__name__' in eglobals:
        emodule = eglobals['__name__']
    else:
        emodule = "<string>"
        
    ####################
    ### Get Filename ###
    ####################
    if '__name__' in globals:
        module = globals['__name__']
    else:
        module = "<string>"
    ####################
    ### Get Filename ###
    ####################
    filename = globals.get('__file__')
    if filename:
        fnl = filename.lower()
        if fnl.endswith(".pyc"):
            filename = filename[:-1]
    else:
        if module == "__main__":
            try:
                filename = sys.argv[0]
            except AttributeError:
                # embedded interpreters don't have sys.argv, see bug #839151
                filename = '__main__'
        if not filename:
            filename = module
    registry = globals.setdefault("__warningregistry__", {})
    new_warn_explicit(message, category, filename, lineno, module, registry,
                  globals, emit_module=emodule)


def newfilterwarnings(action, message="", category=Warning, module="", lineno=0,
                   append=False, emodule=""):
    """Insert an entry into the list of warnings filters (at the front).

    'action' -- one of "error", "ignore", "always", "default", "module",
                or "once"
    'message' -- a regex that the warning message must match
    'category' -- a class that the warning must be a subclass of
    'module' -- a regex that the module name must match
    'lineno' -- an integer line number, 0 matches all warnings
    'append' -- if true, append to the list of filters
    """
    import re
    assert action in ("error", "ignore", "always", "default", "module",
                      "once"), "invalid action: %r" % (action,)
    assert isinstance(message, str), "message must be a string"
    assert isinstance(category, type), "category must be a class"
    assert issubclass(category, Warning), "category must be a Warning subclass"
    assert isinstance(module, str), "module must be a string"
    assert isinstance(lineno, int) and lineno >= 0, \
           "lineno must be an int >= 0"
    item = (action, re.compile(message, re.I), category,
            re.compile(module), lineno, re.compile(emodule))
    if append:
        warnings.filters.append(item)
    else:
        warnings.filters.insert(0, item)
    warnings._filters_mutated()
warnings.warn_explicit = new_warn_explicit
warnings.warn = new_warn
warnings.filterwarnings = newfilterwarnings