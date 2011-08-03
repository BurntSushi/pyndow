import state
import root

heads = [(0, 0, 1920, 1080)]
heads_wa = heads[:]

def which(fx, fy):
    for i, (x, y, w, h) in enumerate(heads):
        if fx >= x and fx < x + w and fy >= y and fy < y + h:
            return i

def workarea(monitor):
    assert monitor < len(heads)

    return heads_wa[monitor]

def strut_calculate():
    # reset the workareas
    for i, head, in enumerate(heads):
        heads_wa[i] = head

    for client in state.windows.itervalues():
        s = client.strut
        sp = client.strut_partial

        if not client.mapped or not any((s, sp)):
            continue
        for i, head in enumerate(heads):
            x, y, w, h = head

            if sp:
                bottom = sp['bottom_start_x'] != sp['bottom_end_x'] \
                         and (__x_in_rect(sp['bottom_start_x'], head)
                              or __x_in_rect(sp['bottom_end_x'], head))
                top    = sp['top_start_x'] != sp['top_end_x'] \
                         and (__x_in_rect(sp['top_start_x'], head)
                              or __x_in_rect(sp['top_end_x'], head))
                left   = sp['left_start_y'] != sp['left_end_y'] \
                         and (__y_in_rect(sp['left_start_y'], head)
                              or __y_in_rect(sp['left_end_y'], head))
                right  = sp['right_start_y'] != sp['right_end_y'] \
                         and (__y_in_rect(sp['right_start_y'], head)
                              or __y_in_rect(sp['right_end_y'], head))

                if bottom:
                    newh = h - (sp['bottom'] - ((root.height - h) - y))
                    __update_wa_monitor(i, (x, y, w, newh))
                elif top:
                    newh = h - (sp['top'] - y)
                    newy = sp['top']
                    __update_wa_monitor(i, (x, newy, w, newh))
                elif right:
                    neww = w - (sp['right'] - ((root.width - w) - x))
                    __update_wa_monitor(i, (x, y, neww, h))
                elif left:
                    neww = w - (sp['left'] - x)
                    newx = sp['left']
                    __update_wa_monitor(i, (newx, y, neww, h))

    # Now apply these new struts!
    for workspace in state.workspaces.itervalues():
        if workspace.monitor is not None:
            workspace.workarea_changed()

def __update_wa_monitor(moni, (x, y, w, h)):
    assert moni < len(heads_wa)
    wa = heads_wa[moni]
    heads_wa[moni] = (max(x, wa[0]), max(y, wa[1]), 
                      min(w, wa[2]), min(h, wa[3]))

def __x_in_rect(xtest, (x, y, w, h)):
    return xtest >= x and xtest < (x + w)

def __y_in_rect(ytest, (x, y, w, h)):
    return ytest >= y and ytest < (y + h)

