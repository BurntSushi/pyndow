import xpybutil.ewmh as ewmh

import state
import focus

from layout import Layout, TileRoot, TileLeaf, TileHorizontalBox, \
                   TileVerticalBox, TileBox, tilers

class DirectionLayout(Layout):
    def __init__(self, workspace):
        assert False, 'subclass responsibility'

    def workarea_changed(self):
        self.place()

    def place(self, client=None):
        assert self.workspace.monitor is not None

        wa = self.workspace.workarea

        if self.workspace.alternate is self:
            for client in self.clients():
                client.frame_border()
            self.root.moveresize(wa['x'], wa['y'], wa['width'], wa['height'])

    def add(self, client, force_master=False, doplace=True):
        Layout.add(self, client)
        
        if force_master or self._masters() < self.maxmasters:
            self._add_master(client)
        else:
            if self._get_focused_section() is self.master:
                self._add_master(client)
            else:
                self._add_slave(client)

        if doplace:
            self.place()

    def remove(self, client):
        Layout.remove(self, client)

        for leaf in self.root.childs():
            if leaf.client == client:
                leaf.parent.remove_child(leaf)
                break

        client.frame_full()
        self._save_proportions() # just in case
        self._promote()
        self._cleanup()
        self.place()

    def master_size_increase(self):
        assert False, 'subclass responsibility'
        
    def master_size_decrease(self):
        assert False, 'subclass responsibility'

    def master_increment(self):
        self.maxmasters += 1
        self._promote()
        self.place()

    def master_decrement(self):
        self.maxmasters = max(0, self.maxmasters - 1)
        self._demote()
        self.place()

    def previous(self):
        tofocus = self._get_direction('previous')
        if tofocus is not None:
            tofocus.activate()

    def next(self):
        tofocus = self._get_direction('next')
        if tofocus is not None:
            tofocus.activate()

    def move_previous(self):
        movefrom = self._get_focused_leaf()
        moveto = self._get_direction('previous')

        if None not in (movefrom, moveto):
            movefrom.switch(moveto)
            self.place()

    def move_next(self):
        movefrom = self._get_focused_leaf()
        moveto = self._get_direction('next')

        if None not in (movefrom, moveto):
            movefrom.switch(moveto)
            self.place()

    def _cleanup(self):
        if not self._masters() and self.master in self.root.child.children:
            self._save_proportions()
            self.root.child.remove_child(self.master)

        if not self._slaves() and self.slave in self.root.child.children:
            self._save_proportions()
            self.root.child.remove_child(self.slave)

    def _promote(self):
        if self._masters() >= self.maxmasters or not self._slaves():
            return False

        topromote = self.slave.children[0]
        self.slave.remove_child(topromote)
        self._add_master(topromote.client, append=True)

        self._cleanup()

        return True

    def _demote(self):
        if not self._masters() or self._masters() <= self.maxmasters:
            return False

        demote = self.master.children[-1]
        self.master.remove_child(demote)
        self._add_slave(demote.client)

        self._cleanup()

        return True

    def _get_direction(self, action):
        assert False, 'subclass responsibility'

    def _get_focused_leaf(self):
        focused = focus.focused()
        for leaf in self.root.childs():
            if leaf.client is focused:
                return leaf

        return None

    def _get_focused_section(self):
        focused = focus.focused()

        for leaf in self.master.childs():
            if leaf.client is focused:
                return self.master
        for leaf in self.slave.childs():
            if leaf.client is focused:
                return self.slave

        return None

    def _get_focused_index(self, section):
        focused = focus.focused()

        if section is self.master:
            for i, leaf in enumerate(self.master.childs()):
                if leaf.client is focused:
                    return i

        if section is self.slave:
            for i, leaf in enumerate(self.slave.childs()):
                if leaf.client is focused:
                    return i

        return 0

    def _add_to(self, section, client):
        assert isinstance(section, TileBox)

        section.add_child(TileLeaf(section, client))

    def _add_master(self, client, append=False):
        assert self._masters() <= self.maxmasters

        if not self._masters():
            assert self.maxmasters > 0

            self._add_to(self.master, client)

            if self.master not in self.root.child.children:
                before_ind = 0 if self._slaves() else None
                self.root.child.add_child(self.master, before_index=before_ind)

            if self._slaves():
                self._restore_proportions()
        else:
            focused_ind = self._get_focused_index(self.master)
            self._section_split(self.master, focused_ind, client, append=append)
            self._demote()

    def _add_slave(self, client, append=False):
        if not self._slaves():
            self._add_to(self.slave, client)

            if self.slave not in self.root.child.children:
                self.root.child.add_child(self.slave)

            if self._masters():
                self._restore_proportions()
        else:
            focused_ind = self._get_focused_index(self.slave)
            self._section_split(self.slave, focused_ind, client, append=append)

    def _section_split(self, section, i, client, append=False):
        assert False, 'subclass responsibility'

    def _masters(self):
        cnt = 0
        if self.master is not None:
            for _ in self.master.childs():
                cnt += 1

        return cnt

    def _slaves(self):
        cnt = 0
        if self.slave is not None:
            for _ in self.slave.childs():
                cnt += 1

        return cnt

    def _save_proportions(self):
        # Only save if both master and slave are active
        if set(self.root.child.children) == set((self.master, self.slave)):
            self.proportions = (self.master.proportion, self.slave.proportion)

    def _restore_proportions(self):
        self.master.proportion, self.slave.proportion = self.proportions

class VerticalLayout(DirectionLayout):
    def __init__(self, workspace):
        Layout.__init__(self, workspace)

        self.maxmasters = 1

        self.root = TileRoot()
        self.root.add_child(TileHorizontalBox(self.root))
        self.master = TileVerticalBox(self.root.child)
        self.slave = TileVerticalBox(self.root.child)

        self.proportions = (0.5, 0.5)

    def _section_split(self, section, i, client, append=False):
        assert section in (self.master, self.slave)

        section.children[i].split('vertical', client, append=append)

    def master_size_increase(self):
        if self._masters() and self._slaves():
            self.root.child.proportion_direction('right', self.master, 0.02)
            self.place()
        
    def master_size_decrease(self):
        if self._masters() and self._slaves():
            self.root.child.proportion_direction('left', self.slave, 0.02)
            self.place()

    def _get_direction(self, action):
        assert action in ('previous', 'next')

        def opposite_for_prev(direction):
            if action == 'previous' and direction in ('up', 'down'):
                return { 'up': 'down', 'down': 'up' }[direction]
            return direction

        leaf = self._get_focused_leaf()
        tofocus = None

        if leaf.parent is self.master:
            tofocus = leaf.leaf_direction(opposite_for_prev('up'), 
                                          shallow=True)
            if tofocus is None and self._slaves():
                first_or_last = 0 if action is 'next' else -1
                tofocus = self.slave.children[first_or_last]
        else:
            tofocus = leaf.leaf_direction(opposite_for_prev('down'), 
                                          shallow=True)
            if tofocus is None and self._masters():
                first_or_last = -1 if action is 'next' else 0
                tofocus = self.master.children[first_or_last]

        return tofocus

class HorizontalLayout(DirectionLayout):
    def __init__(self, workspace):
        Layout.__init__(self, workspace)

        self.maxmasters = 1

        self.root = TileRoot()
        self.root.add_child(TileVerticalBox(self.root))
        self.master = TileHorizontalBox(self.root.child)
        self.slave = TileHorizontalBox(self.root.child)

        self.proportions = (0.5, 0.5)

    def _section_split(self, section, i, client, append=False):
        assert section in (self.master, self.slave)

        section.children[i].split('horizontal', client, append=append)

    def master_size_increase(self):
        if self._masters() and self._slaves():
            self.root.child.proportion_direction('down', self.master, 0.02)
            self.place()
        
    def master_size_decrease(self):
        if self._masters() and self._slaves():
            self.root.child.proportion_direction('up', self.slave, 0.02)
            self.place()

    def _get_direction(self, action):
        assert action in ('previous', 'next')

        def opposite_for_prev(direction):
            if action == 'previous' and direction in ('left', 'right'):
                return { 'left': 'right', 'right': 'left' }[direction]
            return direction

        leaf = self._get_focused_leaf()
        tofocus = None

        if leaf.parent is self.master:
            tofocus = leaf.leaf_direction(opposite_for_prev('left'), 
                                          shallow=True)
            if tofocus is None and self._slaves():
                first_or_last = 0 if action is 'next' else -1
                tofocus = self.slave.children[first_or_last]
        else:
            tofocus = leaf.leaf_direction(opposite_for_prev('right'), 
                                          shallow=True)
            if tofocus is None and self._masters():
                first_or_last = -1 if action is 'next' else 0
                tofocus = self.master.children[first_or_last]

        return tofocus

tilers[VerticalLayout.__name__] = VerticalLayout
tilers[HorizontalLayout.__name__] = HorizontalLayout

