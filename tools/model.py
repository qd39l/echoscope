"""Independent, scalar Rule 30R reference (bit i's left neighbor is i-1)."""

MASK = (1 << 32) - 1
INITIAL = (0, 1 << 15, 0, (1 << 15) | (1 << 16))


def rule30(word):
    # Truth-table lookup intentionally differs from the RTL Boolean network.
    result = 0
    for i in range(32):
        neighborhood = (((word >> ((i - 1) % 32)) & 1) << 2
                        | ((word >> i) & 1) << 1
                        | ((word >> ((i + 1) % 32)) & 1))
        result |= ((30 >> neighborhood) & 1) << i
    return result


def step(state, reverse=False):
    result = []
    for past, now in (state[:2], state[2:]):
        result.extend((rule30(past) ^ now, past) if reverse else (now, rule30(now) ^ past))
    return tuple(result)


def kick(state, cell):
    return (*state[:3], state[3] ^ (1 << cell))


def clone(state):
    return (*state[:2], *state[:2])
