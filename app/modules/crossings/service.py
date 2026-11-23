from fractions import Fraction

from .interpolate import interpolate


def find_crossings(normalized, vessels):
    sections = normalized['sections']
    return {key: {'order': vessel, 'sections': {
        name: {**section, 'bands': interpolate(section['points'], section['gap_s'], Fraction(vessel['threshold_m']))}
        for name, section in sections.items()}} for key, vessel in vessels.items()}
