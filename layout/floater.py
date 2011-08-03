import xpybutil.ewmh as ewmh

import state

from layout import Layout, tilers

class FloatLayout(Layout): 
    def __init__(self, workspace):
        Layout.__init__(self, workspace)

        self._resizing = None
        self._moving = None

    def workarea_changed(self):
        assert self.workspace.monitor is not None

        wa = self.workspace.workarea
        for client in self.clients():
            x, y = client.frame.parent.geom['x'], client.frame.parent.geom['y']
            if x < wa['x']:
                x += wa['x'] - x
            if y < wa['y']:
                y += wa['y'] - y

            client.configure(x=x, y=y)

    def add(self, client):
        Layout.add(self, client)

        if not client.initial_map:
            self.place(client)

    def place(self, client=None):
        if client is not None:
            client.configure(**self._try_nonoverlapping_xy(client))

    def save(self, client):
        assert client.win.id in self._windows
        assert self.workspace.monitor is not None

        wa = self.workspace.workarea
        geom = client.frame.parent.geom
        self._windows[client.win.id] = {
            'x': geom['x'] - wa['x'], 'y': geom['y'] - wa['y'],
            'width': geom['width'], 'height': geom['height']
        }

    def restore(self, client):
        assert client.win.id in self._windows

        wa = self.workspace.workarea
        geom = self._windows[client.win.id]
        client.frame_full()
        client.frame.configure(x=geom['x'] + wa['x'], y=geom['y'] + wa['y'],
                               width=geom['width'], height=geom['height'])

    def save_all(self):
        for client in self.clients():
            self.save(client)

    def restore_all(self):
        for client in self.clients():
            self.restore(client)

    def _try_nonoverlapping_xy(self, client):
        """
        Retrieves an x,y position such that the given client can be positioned
        without overlapping another window. If no such x,y position exists,
        return 0,0.

        Algorithm:
        - Keep a list of rectangles that represent uncovered space. Initialize 
          it to the entire area.
        - For each of the given rectangles
          - For each rectangle in uncovered space
            - If they intersect, divide the uncovered space into smaller
              rectangles around the covering rectangle, and add the smaller
              rectangles (if any) to your list of uncovered ones.
        - If your list of uncovered space still has any entries, they contain
          all points not covered by the given rectangles.

        Source: http://stackoverflow.com/questions/3859010/efficient-algorithm-to-find-a-point-not-touched-by-a-set-of-rectangles/3859667#3859667

        XXX: It might be a good idea to prematurely return 0,0 if there are
             more than N number of windows in this layout.
        """

        def empty_rect((x, y, w, h)):
            return w <= 0 or h <= 0

        def rect_subtract((r1x1, r1y1, r1w, r1h), (r2x1, r2y1, r2w, r2h)):
            r1x2, r1y2 = r1x1 + r1w, r1y1 + r1h
            r2x2, r2y2 = r2x1 + r2w, r2y1 + r2h
            
            # No intersection, return the free area back
            if r2x1 >= r1x2 or r1x1 >= r2x2 or r2y1 >= r1y2 or r1y1 >= r2y2:
                return [(r1x1, r1y1, r1w, r1h)]

            # "r2 >= r1" => no free rectangles
            if r1x1 >= r2x1 and r1y1 >= r2y1 and r1x2 <= r2x2 and r1y2 <= r2y2:
                return []

            # I think this is "write once, read never" code...
            # All it's doing is subtracting r2 from r1---which could yield
            # up to 4 new rectangles (or no rectangles); hence the filter...
            return filter(lambda rect: not empty_rect(rect),
                          [(r1x1, r1y1, r1w, r2y1 - r1y1),
                           (r1x1, r1y1, r2x1 - r1x1, r1h),
                           (r1x1, r2y2, r1w, r1h - ((r2y1 - r1y1) + r2h)),
                           (r2x2, r1y1, r1w - ((r2x1 - r1x1) + r2w), r1h)])

        def get_empty_rects():
            empty = [(wa['x'], wa['y'], wa['width'], wa['height'])]

            for c in self.clients():
                if c == client:
                    continue

                geom = c.frame.parent.geom
                clientrect = (geom['x'], geom['y'], 
                              geom['width'], geom['height'])
                for i, rect in enumerate(empty[:]):
                    empty.remove(rect)
                    empty += rect_subtract(rect, clientrect)

            return empty

        wa = self.workspace.workarea
        cgeom = client.frame.parent.geom
        rects_fit_client = (lambda (x, y, w, h):
                                w >= cgeom['width'] and h >= cgeom['height'])
        empty = filter(rects_fit_client, get_empty_rects())
        
        if empty:
            empty = sorted(empty, key=lambda (x, y, w, h): (y, x)) # By y then x
            return { 'x': empty[0][0], 'y': empty[0][1] }
        else:
            return { 'x': wa['x'], 'y': wa['y'] }

    def resize_start(self, client, root_x, root_y, event_x, event_y,
                     direction=None):
        # shortcuts
        cont = client.frame.parent
        w = cont.geom['width']
        h = cont.geom['height']
        mr = ewmh.MoveResize

        if direction is None:
            # Left
            if event_x < w / 3:
                # Top
                if event_y < h / 3:
                    direction = mr.SizeTopLeft
                # Bottom
                elif event_y > h * 2 / 3:
                    direction = mr.SizeBottomLeft
                # Middle
                else: # event_y >= h / 3 and event_y <= h * 2 / 3
                    direction = mr.SizeLeft
            # Right
            elif event_x > w * 2 / 3:
                # Top
                if event_y < h / 3:
                    direction = mr.SizeTopRight
                # Bottom
                elif event_y > h * 2 / 3:
                    direction = mr.SizeBottomRight
                # Middle
                else: # event_y >= h / 3 and event_y <= h * 2 / 3
                    direction = mr.SizeRight
            # Middle
            else: # event_x >= w / 3 and event_x <= w * 2 / 3
                # Top
                if event_y < h / 2:
                    direction = mr.SizeTop
                # Bottom
                else: # event_y >= h / 2
                    direction = mr.SizeBottom

            assert direction is not None

        cursor = {
            mr.SizeTop: state.cursors['TopSide'],
            mr.SizeTopRight: state.cursors['TopRightCorner'],
            mr.SizeRight: state.cursors['RightSide'],
            mr.SizeBottomRight: state.cursors['BottomRightCorner'],
            mr.SizeBottom: state.cursors['BottomSide'],
            mr.SizeBottomLeft: state.cursors['BottomLeftCorner'],
            mr.SizeLeft: state.cursors['LeftSide'],
            mr.SizeTopLeft: state.cursors['TopLeftCorner']
        }.setdefault(direction, state.cursors['LeftPtr'])

        self._resizing = {
            'root_x': root_x,
            'root_y': root_y,
            'x': cont.geom['x'],
            'y': cont.geom['y'],
            'w': cont.geom['width'],
            'h': cont.geom['height'],
            'direction': direction
        }

        return { 'grab': True, 'cursor': cursor }

    def resize_drag(self, client, root_x, root_y, event_x, event_y):
        # shortcut
        cont = client.frame.parent
        d = self._resizing['direction']
        mr = ewmh.MoveResize

        xs = (mr.SizeLeft, mr.SizeTopLeft, mr.SizeBottomLeft)
        ys = (mr.SizeTop, mr.SizeTopLeft, mr.SizeTopRight)

        ws = (mr.SizeTopLeft, mr.SizeTopRight, mr.SizeRight,
              mr.SizeBottomRight, mr.SizeBottomLeft, mr.SizeLeft)
        hs = (mr.SizeTopLeft, mr.SizeTop, mr.SizeTopRight,
              mr.SizeBottomRight, mr.SizeBottom, mr.SizeBottomLeft)

        diffx = root_x - self._resizing['root_x']
        diffy = root_y - self._resizing['root_y']

        old_x = cont.geom['x']
        old_y = cont.geom['y']

        new_x = new_y = new_width = new_height = None

        if d in xs:
            new_x = self._resizing['x'] + diffx

        if d in ys:
            new_y = self._resizing['y'] + diffy

        if d in ws:
            if d in xs:
                new_width = self._resizing['w'] - diffx
            else:
                new_width = self._resizing['w'] + diffx

        if d in hs:
            if d in ys:
                new_height = self._resizing['h'] - diffy
            else:
                new_height = self._resizing['h'] + diffy

        w, h = client.frame.validate_size(new_width, new_height)

        # If the width and height didn't change, don't adjust x,y...
        if new_x is not None and w != new_width:
            new_x = self._resizing['x'] + (self._resizing['w'] - w)
        if new_y is not None and h != new_height:
            new_y = self._resizing['y'] + (self._resizing['h'] - h)

        client.frame.configure(x=new_x, y=new_y, width=w, height=h)

    def resize_end(self, client, root_x, root_y):
        self._resizing = None
        client.frame.configure() # ?

    def move_start(self, client, root_x, root_y):
        self._moving = {
            'root_x': root_x,
            'root_y': root_y
        }

        return { 'grab': True, 'cursor': state.cursors['Fleur'] }

    def move_drag(self, client, root_x, root_y):
        cont = client.frame.parent # shortcut

        cont.geom['x'] += root_x - self._moving['root_x']
        cont.geom['y'] += root_y - self._moving['root_y']

        self._moving['root_x'] = root_x
        self._moving['root_y'] = root_y

        client.frame.configure(x=cont.geom['x'], y=cont.geom['y'])

    def move_end(self, client, root_x, root_y):
        self._moving = None

tilers[FloatLayout.__name__] = FloatLayout

