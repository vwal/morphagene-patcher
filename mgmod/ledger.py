"""Refuse overlapping flash, physical RAM, option keys and gestures."""
MOD_BASE = 0x2002A000
SETTINGS_BASE = 0x2002A0F0

def overlaps(a, b):
    return a[0] <= b[1] and b[0] <= a[1]

def check(modules):
    problems, seen, names = [], {}, []
    for module in modules:
        if module.name in names:
            problems.append(f'duplicate module {module.name}')
        for need in module.requires:
            if need not in names:
                problems.append(f'{module.name} requires {need} earlier in the remix')
        names.append(module.name)
        memory = list(module.ram)
        for first, last in module.mod_bytes:
            if not 0 <= first <= last < 240:
                problems.append(f'{module.name}: MOD offsets must be in 0..239')
            memory.append((MOD_BASE + first, MOD_BASE + last))
        for offset in module.settings:
            if not 0 <= offset < 16:
                problems.append(f'{module.name}: setting offset must be in 0..15')
            memory.append((SETTINGS_BASE + offset, SETTINGS_BASE + offset))
        claims = {'flash site': list(module.sites()), 'RAM': memory}
        replacements = {}
        for kind, ranges in claims.items():
            for first, last in ranges:
                if first > last:
                    problems.append(f'{module.name}: inverted {kind} range')
                if kind == 'RAM' and not (0x200243C8 <= first <= last < 0x2002B800):
                    problems.append(f'{module.name}: RAM claim outside the initialized mod arena')
                for other, previous in seen.get(kind, []):
                    if (kind == 'flash site' and first == previous[0] and last <= previous[1]
                            and module.replaces_hooks.get(first) == other):
                        replacements[first] = other
                        continue
                    if overlaps((first, last), previous):
                        problems.append(f'{module.name} and {other} both claim {kind} {first:#x}..{last:#x}')
                seen.setdefault(kind, []).append((module.name, (first, last)))
        if replacements != module.replaces_hooks:
            problems.append(f'{module.name}: declared replacement does not match an earlier hook')
        for kind, values in (('options.txt key', module.options_keys), ('gesture', module.gestures)):
            for value in values:
                for other, previous in seen.get(kind, []):
                    if value == previous:
                        problems.append(f'{module.name} and {other} both claim {kind} {value!r}')
                seen.setdefault(kind, []).append((module.name, value))
    if problems:
        raise ValueError('ledger:\n  ' + '\n  '.join(problems))
    return seen
