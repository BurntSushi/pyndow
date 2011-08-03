import state
import focus
import frame

class Layout(object):
    def __init__(self, workspace):
        self._windows = {}
        self._workspace = workspace

    def place(self, client=None):
        assert False, 'subclass responsibility'

    def focused(self, client):
        client.frame.set_state(frame.State.Active)

    def unfocused(self, client):
        client.frame.set_state(frame.State.Inactive)

    def add(self, client):
        assert client.win.id not in self._windows

        self._windows[client.win.id] = {
            'x': None, 'y': None, 'width': None, 'height': None,
        }

    def remove(self, client):
        assert client.win.id in self._windows

        del self._windows[client.win.id]

    def remove_one(self, client):
        assert False, 'subclass responsibility'

    def save(self, client):
        assert client.win.id in self._windows
        assert self.workspace.monitor is not None

        wa = self.workspace.workarea
        geom = client.frame.parent.geom
        self._windows[client.win.id] = {
            'x': geom['x'] - wa['x'], 'y': geom['y'] - wa['y'],
            'width': geom['width'], 'height': geom['height'],
            'frame': client.frame.__class__
        }

    def restore(self, client):
        assert client.win.id in self._windows

        wa = self.workspace.workarea
        conf = self._windows[client.win.id]
        client.frame_switch(conf['frame'])
        client.frame.configure(x=conf['x'] + wa['x'], y=conf['y'] + wa['y'],
                               width=conf['width'], height=conf['height'])

    def save_all(self):
        for client in self.clients():
            self.save(client)

    def restore_all(self):
        for client in self.clients():
            self.restore(client)

    def clients(self):
        for client in focus.get_stack():
            if client.workspace == self.workspace and not client.iconified:
                if client.layout() == self:
                    yield client

    def focus_up(self): pass
    def focus_down(self): pass
    def focus_right(self): pass
    def focus_left(self): pass
    def master_size_increase(self): pass
    def master_size_decrease(self): pass
    def master_increment(self): pass
    def master_decrement(self): pass
    def previous(self): pass
    def next(self): pass
    def move_previous(self): pass
    def move_next(self): pass

    def resize_start(self, client, root_x, root_y, event_x, event_y,
                     direction=None):
        return { 'grab': False }

    def resize_drag(self, client, root_x, root_y, event_x, event_y):
        pass

    def resize_end(self, client, root_x, root_y):
        pass

    def move_start(self, client, root_x, root_y):
        return { 'grab': False }

    def move_drag(self, client, root_x, root_y):
        pass

    def move_end(self, client, root_x, root_y):
        pass

    @property
    def workspace(self):
        return self._workspace

    @workspace.setter
    def workspace(self, newwork):
        if newwork != self._workspace:
            self._workspace = newwork
            return True
        return False

    def __contains__(self, client):
        return client.win.id in self._windows

class TileBox(object):
    def __init__(self, parent):
        self.parent = parent
        self.children = []
        self.proportion = 1.0

        self.x = self.y = 0
        self.w = self.h = 1

    def childs(self):
        for child in self.children:
            if isinstance(child, TileLeaf):
                yield child
            else:
                for c in child.childs():
                    yield c

    def add_child(self, box, before_index=None):
        assert isinstance(box, TileBox)
        assert box not in self.children
        assert before_index is None or before_index <= len(self.children)

        if before_index is not None:
            self.children.insert(before_index, box)
        else:
            self.children.append(box)

        box.parent = self

    def remove_child(self, box):
        assert isinstance(box, TileBox) and box in self.children

        self.children.remove(box)
        box.parent = None

        if self.children:
            add = box.proportion / len(self.children)
            for child in self.children:
                child.proportion += add

    def prune_child(self, box):
        assert len(self.children) >= 2

        self.remove_child(box)

        if len(self.children) == 1:
            child = self.children[0]
            child.proportion = self.proportion
            child.parent = self.parent
            child.parent.replace_child(self, child)

    def replace_child(self, find, replace):
        assert (isinstance(find, TileBox) and isinstance(replace, TileBox)
                and find in self.children)

        self.children[self.children.index(find)] = replace

        find.parent = None
        replace.parent = self

    def moveresize(self, x, y, w, h):
        self._moveresize(x, y, w, h)

    def _moveresize(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    def _depth(self):
        d = 0
        parent = self.parent

        while parent is not None:
            d += 1
            parent = parent.parent

        return d

    def __str__(self):
        ret = '--' * self._depth() + self._string() + '\n'

        if isinstance(self, TileRoot):
            if self.child is not None:
                ret += str(self.child)
        else:
            for child in self.children:
                ret += str(child)

        return ret

class TileRoot(TileBox):
    def __init__(self):
        TileBox.__init__(self, None)
        self.child = None

    def childs(self):
        return self.child.childs()

    def add_child(self, box):
        self.child = box
        self.child.proportion = 1.0

    def remove_child(self):
        self.child = None

    def replace_child(self, find, replace):
        assert (isinstance(find, TileBox) and isinstance(replace, TileBox)
                and find == self.child)

        self.child = replace

    def activate(self):
        state.root_focus()

    def _moveresize(self, x, y, w, h):
        TileBox._moveresize(self, x, y, w, h)

        if self.child is not None:
            self.child.moveresize(x, y, w, h)

    def _find_like_parent(self, cls, no_child_index):
        return None, self

    def select(self, **kwargs):
        return self

    def leaf_direction(self, direction, shallow=False):
        return None

    def proportion_direction(self, *args, **kwargs):
        pass

    def _string(self):
        return 'ROOT: (%d, %d) -- %dx%d' % (self.x, self.y, self.w, self.h)

class TileLeaf(TileBox):
    def __init__(self, parent, client):
        TileBox.__init__(self, parent)
        self.client = client
        self.cyc_ind = 0
        self.hidden = []

    def childs(self):
        yield self

    def add_child(self, box):
        pass

    def remove_child(self, box):
        pass

    def activate(self):
        self.client.focus()

    def select(self, *args, **kwargs):
        return self

    def switch(self, leaf):
        self.client, leaf.client = leaf.client, self.client

    def leaf_direction(self, direction, shallow=False):
        assert direction in ('up', 'right', 'down', 'left')

        boxClass = TileHorizontalBox
        if direction in ('up', 'down'):
            boxClass = TileVerticalBox

        child_exclude = 0 # Exclude first for up/left movement
        child_next = -1 # Move back in list for up/left movement
        if direction in ('down', 'right'):
            child_exclude = -1 # Exclude last for down/right movement
            child_next = 1 # Move forward in list for down/right movement

        parent, child = self.parent, self
        if not shallow:
            parent, child = self._find_like_parent(boxClass, child_exclude)
        elif not isinstance(parent, boxClass):
            parent, child = parent.parent, parent

        if parent.children[child_exclude] != child:
            cs = parent.children
            nexti = cs.index(child) + child_next
            return cs[nexti].select(where=direction, x=self.x,
                                    y=self.y, w=self.w, h=self.h)

        return None

    def proportion_direction(self, direction, prop_change, shallow=False):
        boxClass = TileHorizontalBox
        if direction in ('up', 'down'):
            boxClass = TileVerticalBox

        child_exclude = 0
        if direction in ('down', 'right'):
            child_exclude = -1

        parent, child = self.parent, self
        if not shallow:
            parent, child = self._find_like_parent(boxClass, child_exclude)

        parent.proportion_direction(direction, child, prop_change)

    def split(self, split_type, client, append=False):
        assert split_type in ('horizontal', 'vertical')

        leaf = TileLeaf(None, client)

        boxClass = (TileHorizontalBox if split_type == 'horizontal' 
                    else TileVerticalBox)

        if isinstance(self.parent, boxClass):
            leaf.proportion = 1.0 / len(self.parent.children)

            add_beforei = None if append else self.parent.children.index(self)
            self.parent.add_child(leaf, add_beforei)

            clen = float(len(self.parent.children))
            factor = (clen - 1) / clen
            for child in self.parent.children:
                child.proportion *= factor
        else:
            parent = boxClass(self.parent)
            parent.proportion = self.proportion
            parent.parent.replace_child(self, parent)

            self.proportion = 0.5
            leaf.proportion = 0.5
            
            parent.add_child(leaf)
            parent.add_child(self)

    def _moveresize(self, x, y, w, h):
        TileBox._moveresize(self, x, y, w, h)

        self.client.frame.configure(x=x, y=y, width=w, height=h, 
                                    ignore_hints=True)
        self.client.stack_raise()

    def _find_like_parent(self, cls, no_child_index):
        child = self
        parent = self.parent
        while parent:
            if (isinstance(parent, cls) 
                and parent.children[no_child_index] != child):
                break
            child = parent
            parent = parent.parent

        return parent, child

    def _string(self):
        return 'LEAF: (%d, %d) -- %dx%d -- %s (%s)' % (
               self.x, self.y, self.w, self.h, 
               self.client.win.wmname[0:30], hex(self.client.win.id))

class TileHorizontalBox(TileBox):
    def select(self, where, x, y, w, h):
        assert where in ('up', 'right', 'down', 'left')
        assert self.children

        if where == 'left':
            return self.children[-1].select(where, x, y, w, h)
        elif where == 'right':
            return self.children[0].select(where, x, y, w, h)
        elif where in ('up', 'down'):
            if x is not None and w is not None:
                overlap = []
                for c in self.children:
                    overlap.append(_intoverlap(x, x + w, c.x, c.x + c.w))
                mi = overlap.index(max(overlap))
                
                return self.children[mi].select(where, x, y, w, h)
            else:
                return self.children[0].select(where, x, y, w, h)

    def proportion_direction(self, direction, child, prop_change):
        assert child in self.children

        if direction in ('up', 'down'):
            self.parent.proportion_direction(direction, self, prop_change)
        else:
            newprop = child.proportion + prop_change
            if newprop > 1 or newprop < 0:
                return

            if direction is 'left':
                allonside = self.children[:self.children.index(child)]
            else:
                allonside = self.children[self.children.index(child) + 1:]

            if allonside:
                add_to = -prop_change / len(allonside)
                for c in allonside:
                    c.proportion += add_to
                child.proportion += prop_change

    def _moveresize(self, x, y, w, h):
        TileBox._moveresize(self, x, y, w, h)

        # Since we represent window sizes by proportions, we must consider
        # rounding error. Since we truncate towards 0 with 'int()', we will
        # always have to *add* pixels, if there is any rounding error.
        # When there is rounding error, distribute the pixels across each
        # window.

        # First, calculate the widths of each child based on proportion.
        # We'll be either exactly correct or a few pixels short (rounding error)
        if len(self.children) > 1:
            widths = [int(w * c.proportion) for c in self.children]
        else:
            widths = [w]

        # Now determine how many pixels we need to add
        addpixels = w - sum(widths)

        # Add one pixel to each window until we run out
        i = 0
        while addpixels > 0:
            widths[i % len(widths)] += 1
            i += 1
            addpixels -= 1

        s_x = x
        for i, child in enumerate(self.children):
            child._moveresize(s_x, y, widths[i], h)
            s_x += widths[i]

    def _string(self):
        return 'HORZ: (%d, %d) -- %dx%d' % (self.x, self.y, self.w, self.h)

class TileVerticalBox(TileBox):
    def select(self, where, x, y, w, h):
        assert where in ('up', 'right', 'down', 'left')
        assert self.children

        if where == 'up':
            return self.children[-1].select(where, x, y, w, h)
        elif where == 'down':
            return self.children[0].select(where, x, y, w, h)
        elif where in ('left', 'right'):
            if y is not None and h is not None:
                overlap = []
                for c in self.children:
                    overlap.append(_intoverlap(y, y + h, c.y, c.y + c.h))
                mi = overlap.index(max(overlap))
                
                return self.children[mi].select(where, x, y, w, h)
            else:
                return self.children[0].select(where, x, y, w, h)

    def proportion_direction(self, direction, child, prop_change):
        assert child in self.children

        if direction in ('left', 'right'):
            self.parent.proportion_direction(direction, self, prop_change)
        else:
            newprop = child.proportion + prop_change
            if newprop > 1 or newprop < 0:
                return

            if direction is 'up':
                allonside = self.children[:self.children.index(child)]
            else:
                allonside = self.children[self.children.index(child) + 1:]

            if allonside:
                add_to = -prop_change / len(allonside)
                for c in allonside:
                    c.proportion += add_to
                child.proportion += prop_change

    def _moveresize(self, x, y, w, h):
        TileBox._moveresize(self, x, y, w, h)

        # Since we represent window sizes by proportions, we must consider
        # rounding error. Since we truncate towards 0 with 'int()', we will
        # always have to *add* pixels, if there is any rounding error.
        # When there is rounding error, distribute the pixels across each
        # window.

        # First, calculate the heights of each child based on proportion.
        # We'll be either exactly correct or a few pixels short (rounding error)
        if len(self.children) > 1:
            heights = [int(h * c.proportion) for c in self.children]
        else:
            heights = [h]

        # Now determine how many pixels we need to add
        addpixels = h - sum(heights)

        # Add one pixel to each window until we run out
        i = 0
        while addpixels > 0:
            heights[i % len(heights)] += 1
            i += 1
            addpixels -= 1

        s_y = y
        for i, child in enumerate(self.children):
            child._moveresize(x, s_y, w, heights[i])
            s_y += heights[i]

    def _string(self):
        return 'VERT: (%d, %d) -- %dx%d' % (self.x, self.y, self.w, self.h)

def _intoverlap(s1, e1, s2, e2):
    assert e1 > s1 and e2 > s2

    L1, L2 = e1 - s1, e2 - s2

    if s2 <= s1 and e2 >= e1:
        return L1
    elif e2 < s1 or s2 > e1:
        return 0
    elif s2 >= s1 and e2 <= e1:
        return L2
    elif s2 < s1:
        return e2 - s1
    elif s2 < e1:
        return e1 - s2

    return None

tilers = {}

import layout.floater
import layout.tile

