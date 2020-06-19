
def caret_mover(fs):
    cur_row = 1

    def inner_func(count=1, with_white_space=False):
        nonlocal cur_row, fs
        for i in range(count):
            fs.write('{}\x0c'.format('\x1d' * 8 + ' ' if with_white_space else ''))
            cur_row += 1
        return cur_row

    return inner_func
