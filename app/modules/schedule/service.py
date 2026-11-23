from fractions import Fraction


def reconcile(routes):
    fleet = {}
    for key, route in routes.items():
        order = route['order']
        counts = dict.fromkeys(('open', 'blocked', 'unknown'), Fraction(0))
        for piece in route['pieces']:
            counts[piece['status']] += Fraction(piece['seconds'])
        total = order['end'] - order['start']
        delta = total - sum(counts.values())
        fleet[key] = dict(seconds={k: str(v) for k, v in counts.items()}, window_s=total,
                          delta_s=str(delta), balanced=delta == 0, requested=route['requested'],
                          order_line=order['line'], windows=route['windows'])
    return {'ships': fleet, 'balanced': all(ship['balanced'] for ship in fleet.values())}
