import json
import os

from sympy import Integer, GoldenRatio, atan, sqrt, pi, latex

from generate_sources.decisions import iter_decisions, Decider
from generate_sources.utils import call, serialize_value


golden_ratio = GoldenRatio
radian = 180 / pi

root_path = 'src'


def get_file(path, expression, metadata):
    def write_content(file):
        use_path = os.path.relpath('_fillygon.scad', os.path.dirname(path))

        print('use <{}>'.format(use_path), file=file)
        print('render() {};'.format(serialize_value(expression)), file=file)

    return path, write_content, dict(metadata, path=path)


def decide_file(decider: Decider):
    reversed_edges = []
    side_repetitions = 1

    regular = decider.get_boolean()

    if regular:
        if decider.get_boolean():
            num_sides = decider.get_item(range(3, 12 + 1))

            if num_sides <= 6:
                side_repetitions = decider.get(1, 2)
        else:
            # n-gons with reversed sides.
            num_sides, *reversed_edges = decider.get(
                (3, True),
                (4, True),
                (4, True, True),
                (4, True, False, True),
                (5, True),
                (5, True, True),
                (5, True, False, True))

            reversed_edges += (False,) * (num_sides - len(reversed_edges))

        directions = [
            Integer(360) / num_sides * i
            for i in range(num_sides)
            for _ in range(side_repetitions)]

        angles = [180 - b + a for a, b in zip(directions, directions[1:])]

        name = '{}-Gon'.format(num_sides)
        polygon_name = '{}-gon'.format(num_sides)

        if side_repetitions > 1:
            polygon_name += '-double'

        if reversed_edges:
            polygon_name += '-reversed-{}'.format(''.join('.r'[i] for i in reversed_edges))
    else:
        if decider.get_boolean():
            # Rhombi
            acute_angle = decider.get(
                2 * atan(1 / sqrt(2)) * radian,
                2 * atan(1 / golden_ratio) * radian,
                2 * atan(1 / golden_ratio ** 2) * radian,
                2 * atan(1 / sqrt(3)) * radian,
                2 * atan(1 / sqrt(15)) * radian)

            degrees_rounded = round(float(acute_angle))
            name = 'Rhombus ({})'.format(degrees_rounded)
            polygon_name = 'rhombus-{}'.format(degrees_rounded)

            angles = [acute_angle, 180 - acute_angle, acute_angle]
        elif decider.get_boolean():
            # Flat hexagons
            opposite_angle = decider.get(
                2 * atan(golden_ratio) * radian,
                90,
                2 * atan(sqrt(2)) * radian,
                2 * atan(1 / golden_ratio) * radian,
                2 * atan(1 / sqrt(2)) * radian)

            other_angle = 180 - opposite_angle / 2

            degrees_rounded = round(float(opposite_angle))
            name = '6-Gon {}'.format(degrees_rounded)
            polygon_name = '6-gon-flat-{}'.format(degrees_rounded)

            angles = [
                other_angle,
                opposite_angle,
                other_angle,
                other_angle,
                opposite_angle]
        else:
            name, polygon_name, *angles = decider.get(
                ('Rectangle', 'rectangle', 180, 90, 90, 180, 90),
                ('Triamond', 'triamond', 60, 120, 120, 60))

    filled = decider.get_boolean()
    filled_corners = decider.get_boolean()
    gap = decider.get(.2, .25, .4)

    if filled_corners:
        min_convex_angle = 90
        min_concave_angle = 180

        if filled:
            variant_name = 'filled-corners'
        else:
            variant_name = 'corners'
    else:
        if filled:
            variant_name = 'filled'
        else:
            variant_name = 'normal'

        min_convex_angle = 38
        min_concave_angle = 38

    angles.append((len(angles) - 1) * 180 - sum(angles))

    path = os.path.join(
        'variants',
        '{}mm'.format(gap),
        polygon_name,
        variant_name + '.scad')

    arguments = dict(
        angles=angles[:-1],
        reversed_edges=reversed_edges,
        filled=filled,
        filled_corners=filled_corners,
        min_convex_angle=min_convex_angle,
        min_concave_angle=min_concave_angle,
        gap=gap)

    metadata = dict(
        name=name,
        regular=regular,
        side_repetitions=side_repetitions,
        angles_formulae=list(map(lambda s: latex(s, inv_trig_style="full"), angles)),
        angles_values=list(map(float, angles)),
        reversed_edges=reversed_edges,
        filled=filled,
        filled_corners=filled_corners,
        min_convex_angle=min_convex_angle,
        min_concave_angle=min_concave_angle,
        gap=gap)

    return get_file(path, call('fillygon', **arguments), metadata)


def get_files():
    """
    Return a dict from filenames to file contents represented as a function
    taking a file object which writes the file's content to the file object.
    """
    files = {}
    metadata_entries = []

    def add_file(path, write_content_fn):
        full_path = os.path.join(root_path, path)

        assert full_path not in files

        files[full_path] = write_content_fn

    for path, write_content_fn, metadata in iter_decisions(decide_file):
        add_file(path, write_content_fn)
        metadata_entries.append(metadata)

    def write_metadata(file):
        json.dump(metadata_entries, file, indent=4, sort_keys=True)

    add_file('variants.json', write_metadata)

    return files
