from system_pet.windows_geo import floor_y

BOTTOM = 800.0
WIN = [(100, 400, 500)]            # a window whose top edge is at y=400, spanning x=100..500


def test_screen_bottom_when_no_surface():
    assert floor_y(300, 100, [], BOTTOM) == BOTTOM


def test_lands_on_window_below_feet():
    assert floor_y(300, 350, WIN, BOTTOM) == 400


def test_outside_window_span_falls_to_bottom():
    assert floor_y(600, 350, WIN, BOTTOM) == BOTTOM
    assert floor_y(50, 350, WIN, BOTTOM) == BOTTOM


def test_surface_above_feet_is_ignored():
    # feet at 700 are well below the window top: the pet is in front of it, never teleports up
    assert floor_y(300, 700, WIN, BOTTOM) == BOTTOM


def test_small_overlap_snaps_to_surface():
    assert floor_y(300, 405, WIN, BOTTOM) == 400       # feet 5px under the top edge: within tolerance


def test_highest_reachable_surface_wins():
    stack = [(0, 300, 1000), (0, 500, 1000)]
    assert floor_y(300, 100, stack, BOTTOM) == 300
    assert floor_y(300, 400, stack, BOTTOM) == 500
