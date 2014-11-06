# Detect barlines for each single staff from the horizontal projection of the
# slice of the image containing the staff.
# Next, barlines close to each other on adjacent staves need to be checked
# to see if they are joined, in which case we join the staves into one system.
from ..gpu import *
from .. import bitimage, filter, util

def staff_barlines(page, staff_num):
    img_slice = bitimage.as_hostimage(page.staves.extract_staff(staff_num,
                                                page.barline_filter,
                                                extract_lines=8))
    # The barlines should contain mostly black pixels just in the actual staff,
    # but we need to check above and below the staff for other symbols
    staff_proj = img_slice[page.staff_dist*2:page.staff_dist*6, :].sum(0)
    gap_proj = img_slice.sum(0)

    # Barline must take up at least 90% of the vertical space,
    # and there should be background (few black pixels) around it
    is_barline = staff_proj > page.staff_dist * 4 * 0.8
    is_background = gap_proj < page.staff_dist/2
    near_background_left = is_background.copy()
    near_background_right = is_background.copy()
    for i in range(1, page.staff_dist/2):
        near_background_left[i:] |= is_background[:-i]
    for i in range(1, page.staff_dist/2):
        near_background_right[:-i] |= is_background[i:]
    is_barline &= near_background_left & near_background_right
    labels, num_labels = util.label_1d(is_barline)
    barlines = np.rint(util.center_of_mass_1d(labels)).astype(int)

    # Add a barline at the start and end of the staff if necessary
    if len(barlines):
        staff = page.staves()[staff_num]
        if barlines[0] - staff[0,0] > page.staff_dist*2:
            barlines = np.concatenate([[staff[0,0]], barlines])
        if staff[1,0] - barlines[-1] > page.staff_dist*2:
            barlines = np.concatenate([barlines, [staff[1,0]]])
    return barlines

def get_barlines(page):
    page.barline_filter = page.staves.nostaff()
    page.barlines = [staff_barlines(page, i)
                     for i in xrange(len(page.staves()))]
    del page.barline_filter
    return page.barlines

def show_barlines(page):
    import pylab
    for staff_line, barlines in zip(page.staves(), page.barlines):
        staff_y = np.mean(staff_line[:, 1])
        for barline_x in barlines:
            pylab.plot([barline_x, barline_x],
                       [staff_y - page.staff_dist*2,
                        staff_y + page.staff_dist*2],
                       color='g')
