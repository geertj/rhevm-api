#
# This file is part of RHEVM-API. RHEVM-API is free software that is made
# available under the MIT license. Consult the file "LICENSE" that is
# distributed together with this file for the exact licensing terms.
#
# RHEVM-API is copyright (c) 2010 by the RHEVM-API authors. See the file
# "AUTHORS" for a complete overview.

import time
import threading
import logging


class Pool(object):
    """A pool of available powershell objects."""

    # We keep a few PowerShell instances around as setup is expensive
    # (around 4 seconds on my system). This way interfaces on top of this API
    # can be more responsive.

    # The algorithm is adaptive so there should be little reason to change
    # these.
    minsize = 2
    maxival = 300
    maxlife = 3600
    maxcount = 100
    fast_delay = 5
    slow_delay = 60

    def __init__(self, type, constructor):
        """Constructor"""
        self.type = type
        self.constructor = constructor
        self.logger = logging.getLogger('rhevm.pool')
        self._pool = {}
        self._lock = threading.Lock()
        self._thread = None
        self._threads_to_join = []
        self._last_maintenance = time.time()
        self._last_full_maintenance = self._last_maintenance

    def get(self, args):
        """Return a new instance."""
        instance = self._get_instance(args)
        if not instance:
            instance = self._create_instance(args)
        return instance

    def put(self, instance):
        """Put an instance back into the pool."""
        instance.count += 1
        instance.last_time = time.time()
        self._add_instance(instance.args, instance)

    def clear(self):
        """Clear the pool (NOT thread safe)."""
        if self._thread:
            self._thread.join()
        terminate = []
        for key in self._pool:
            terminate += self._pool[key][1]
        self._pool.clear()
        for inst in terminate:
            self._terminate_instance(inst)
        if terminate:
            self.logger.debug('Cleared <%s> pool (%d instances)'
                              % (self._get_type(), len(terminate)))
        self._thread = None

    def size(self):
        """Return the size of the pool."""
        size = 0
        self._lock.acquire()
        try:
            for key in self._pool:
                size += len(self._pool[key][1])
        finally:
            self._lock.release()
        return size

    def maintenance(self):
        """Perform maintenance on the pool."""
        start = False
        self._lock.acquire()
        try:
            if self._thread and not self._thread.isAlive():
                self._thread.join()
                self._thread = None
            if self._thread is None and \
                    time.time() - self._last_maintenance > self.fast_delay:
                self._thread = threading.Thread(target=self._maintenance_thread)
                start = True
        finally:
            self._lock.release()
        if start:
            self._thread.start()
    
    def _maintenance_thread(self):
        """INTERNAL: perform maintenance on the pool."""
        self.logger.debug('Started maintenance thread.')
        if time.time() - self._last_full_maintenance > self.slow_delay:
            self._expire_instances()
            self._decrease_size()
            self._last_full_maintenance = time.time()
        self._increase_size()
        self.logger.debug('Maintenance complete - pool size is now %d' \
                          % self.size())
        self._last_maintenance = time.time()

    def _get_key(self, args):
        """INTERNAL: return a lookup key."""
        values = args.items()
        values.sort()
        key = [ '%s=%s' % (key, value) for (key, value) in values ]
        key = '/'.join(key)
        return key

    def _get_type(self):
        """INTERNAL: return a type identifier."""
        return self.type.__name__

    def _create_instance(self, args):
        """INTERNAL: create a new PowerShell instance."""
        instance = self.constructor(**args)
        instance.args = args
        instance.count = 0
        instance.created = time.time()
        instance.last_used = instance.created
        return instance

    def _terminate_instance(self, instance):
        try:
            instance.terminate()
        except Exception:
            pass

    def _get_instance(self, args):
        """INTERNAL: return an instance."""
        now = time.time()
        key = self._get_key(args)
        self._lock.acquire()
        try:
            if key not in self._pool or not self._pool[key][1]:
                return
            for ix,inst in enumerate(self._pool[key][1]):
                if now - inst.created < self.maxlife \
                        and now - inst.last_used < self.maxival \
                        and inst.count < self.maxcount:
                    del self._pool[key][1][ix]
                    return inst
        finally:
            self._lock.release()

    def _add_instance(self, args, instance):
        """INTERNAL: add a new instance to the pool."""
        key = self._get_key(args)
        self._lock.acquire()
        try:
            if key not in self._pool:
                self._pool[key] = (args, [])
            self._pool[key][1].append(instance)
            self._pool[key][1].sort(lambda x,y: cmp(y.last_used, x.last_used))
        finally:
            self._lock.release()

    def _increase_size(self):
        """INTERNAL: increase the size of the pool."""
        create = []
        self._lock.acquire()
        try:
            for key in self._pool:
                if len(self._pool[key][1]) < self.minsize:
                    create.append(self._pool[key][0])
        finally:
            self._lock.release()
        for args in create:
            instance = self._create_instance(args)
            self._add_instance(args, instance)
        if create:
            self.logger.debug('Created %d instances of type <%s>' \
                              % (len(create), self._get_type()))

    def _expire_instances(self):
        """INTERNAL: expire instance."""
        terminate = []
        now = time.time()
        self._lock.acquire()
        try:
            for key in self._pool:
                remove = []
                for inst in self._pool[key][1]:
                    if now - inst.created > self.maxlife \
                            or now - inst.last_used > self.maxival \
                            or inst.count > self.maxcount:
                        remove.append(inst)
                for inst in remove:
                    self._pool[key][1].remove(inst)
                terminate += remove
        finally:
            self._lock.release()
        for inst in terminate:
            self._terminate_instance(inst)
        if terminate:
            self.logger.debug('Expired %d instances of type <%s> due to age' \
                              % (len(terminate), self._get_type()))

    def _decrease_size(self):
        """INTERNAL: decrease size of the pool."""
        terminate = []
        self._lock.acquire()
        try:
            for key in self._pool:
                if len(self._pool[key][1]) > self.minsize:
                    terminate += self._pool[key][1][self.minsize:]
                    del self._pool[key][1][self.minsize:]
        finally:
            self._lock.release()
        for inst in terminate:
            self._terminate_instance(inst)
        if terminate:
            self.logger.debug('Removed %d instances of <%s> due to full pool' \
                              % (len(terminate), self._get_type()))
