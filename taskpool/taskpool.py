# coding: utf-8
import time
from threading import Thread, RLock as ThreadRLock
from multiprocessing import Process
from multiprocessing import Queue as ProcessQueue
try:
    from queue import Queue as ThreadQueue
except ImportError:
    from Queue import Queue as ThreadQueue

DEFAULT_TIMEOUT = 3   # second
TASK_MAX_NUM = 10000
NONE = (None, None, None, None)  # (func, args, kwargs, callback)


def set_task_max_num(size=None):
    if size and size > 0:
        global TASK_MAX_NUM
        TASK_MAX_NUM = size


def get_task_max_num():
    return TASK_MAX_NUM


class ArgError(Exception):
    pass


class Queue(object):
    def __init__(self, queue_type, maxsize=0):
        self.queue_type = queue_type
        self.queue = self.queue_type(maxsize)

    def qsize(self):
        return self.queue.qsize()

    def empty(self):
        return self.queue.empty()

    def full(self):
        return self.queue.full()

    def put(self, item, block=True, timeout=None):
        return self.queue.put(item, block, timeout)

    def put_nowait(self, item):
        return self.queue.put_nowait(item)

    def get(self, block=True, timeout=None):
        rtn = self.queue.get(block, timeout)
        self.task_done()
        return rtn

    def get_nowait(self):
        rtn = self.queue.get_nowait()
        self.task_done()
        return rtn

    def task_done(self):
        if hasattr(self.queue, 'task_done'):
            return self.queue.task_done()

    def join(self):
        if hasattr(self.queue, 'join'):
            return self.queue.join()


class TaskPool(object):
    def __init__(self, size=1000, pool_type="thread", task_recycle_interval=3600,
                 processor=False):
        """Create a new task pool object.

        `size` appoints the size of the task pool, default 1000.
        `pool_type` represents the type of the task processor in the task pool.
        It only supports "t" or "thread"(Thread), "p" or "process"(Process).
        If `task_recycle_interval` is great than 0, TaskPool will start a thread,
        and int the thread recycle the died task processor in TaskPool, and
        `task_recycle_interval` is the time interval each time the thread executes.
        `processor` represents whether the user want to care about the unique
        number of the task processor. If True, the unique number will be passed
        to the user as the first argument.
        """
        if size > get_task_max_num():
            raise ArgError("The size of pools is great than the maximum.")
        self.processor = processor

        if pool_type == 't' or pool_type == 'thread':
            self.task_type = Thread
            self._queue_type = ThreadQueue
        elif pool_type == 'p' or pool_type == 'process':
            self.task_type = Process
            self._queue_type = ProcessQueue
        else:
            raise ArgError("Do not support {0}".format(pool_type))

        self.pools = {}
        self._in_q = self.new_queue(get_task_max_num())
        self.next_task_seq = 1
        self.pool_lock = ThreadRLock()
        self._clean = False

        # Init the pool
        self._init(size)

        # Start a thread to recycle the terminated task processor.
        if task_recycle_interval > 0:
            self.recycle_thread = Thread(target=self._recycle_task_based_thread,
                                         args=(task_recycle_interval,))
            self.recycle_thread.daemon = True
            self.recycle_thread.start()
        else:
            self._clean = True

    def _clean_died_task_processors(self):
        _list = []
        for name in self.pools:
            if not self.pools[name].is_alive():
                # Notice: Can't delete with "del self.pools[name]" in multithread,
                # or raise RuntimeError: dictionary changed size during iteration
                _list.append(name)
        for name in _list:
            del self.pools[name]

    def _recycle_task_based_thread(self, sleep_time=0):
        if not sleep_time:
            sleep_time = 3600 * 24  # one day

        while True:
            time.sleep(sleep_time)
            self.clean_died_task_processors()

    def clean_died_task_processors(self):
        """Clean and recycle the died task processors.
        """
        self.pool_lock.acquire()
        self._clean_died_task_processors()
        self.pool_lock.release()

    def new_queue(self, maxsize=0):
        """Create a new queue, and its type is Queue in this module.

        Queue is compatible with threading.Queue and multiprocessing.Queue, but
        its interface is same as threading.Queue.

        `maxsize` is the size of the queue. If 0, it is unlimited.
        """
        return Queue(self._queue_type, maxsize)

    def _spawn_task_seq(self):
        next_seq = self.next_task_seq
        while next_seq in self.pools:
            next_seq += 1
        self.next_task_seq = next_seq + 1
        return next_seq

    def _init(self, size):
        self._add_task(size)

    def reset_size(self, size):
        """Reset the size of the task pool.

        `size` is the new size of the task pool. If it less than 1, do nothing;
        if great than the old size of the task pool, extend the task pool;
        if less than the old size, shrink the task pool.
        """
        if size < 1:
            return

        self.pool_lock.acquire()
        current = self._get_task_processor_state()[0]
        diff = size - current
        if diff != 0:
            self._add_task(diff)
        self.pool_lock.release()

    def _callback(self, callback, out_q):
        rtn = out_q.get()
        if callback:
            try:
                callback(rtn)
            finally:
                pass

    def _add_task(self, num):
        if num >= 0:
            for i in range(num):
                out_q = self.new_queue()
                task_seq = self._spawn_task_seq()
                task = self.task_type(target=self._process,
                                      name=str(task_seq),
                                      args=(task_seq, self._in_q, out_q))
                task.daemon = True
                task.start()
                self.pools[task_seq] = task
        else:
            self._terminate_task_pools(0-num)
            self._clean_died_task_processors()

    def _process(self, task_seq, in_q, out_q):
        while True:
            item = in_q.get()
            if item is None or not item[0]:
                break

            try:
                func, args, kwargs, callback = item
                if self.processor:
                    rtn = func(task_seq, *args, **kwargs)
                else:
                    rtn = func(*args, **kwargs)
            except Exception as e:
                rtn = e

            out_q.put(rtn)
            self._callback(callback, out_q)
            #in_q.task_done()

    def spawn(self, func, *args, **kwargs):
        """Put a task in the task queue.

        A task is (func, args, kwargs, callback). A task processor gets a task,
        and executes func(*args, **kwargs). If gived callback, the processor
        executes callback(result), and 'result' is the return value of `func`.

        Notice:
            1. Argument `callback` must be gived through the keyword argument,
               such as "callback=function".
            2. Except for the argument `callback`, others are passed to `func`
               as the position arguments and the keyword arguments.
        """
        callback = None
        safe = True
        clean = True
        if 'callback' in kwargs:
            callback = kwargs.pop('callback')
        if 'safe' in kwargs:
            safe = kwargs.pop('safe')
        if 'clean' in kwargs:
            clean = kwargs.pop('clean')

        if safe and not callable(func):
            return False
        _args = (func, args, kwargs, callback)
        self._in_q.put(_args)

        # If not the thread cleaning the died task, clean it.
        if clean and self._clean:
            self.clean_died_task_processors()

        return True

    def wait(self, timeout=None):
        """ If time out, return True; Or, return False.

        If timeout is None, False, or 0, etc, it block all the operate about
        task pool, such as change the pool size, recycle the died processor,
        or the task processor process the task when closing the recycle thread.

        Please carefully use the timeout=None and you should set a timeout
        instead of None.
        """
        if timeout:
            time.sleep(timeout)
            self.pool_lock.acquire()
            for i in self.pools:
                if self.pools[i].is_alive():
                    return True
            self.pool_lock.release()
        else:
            self.pool_lock.acquire()
            for i in self.pools:
                self.pools[i].join()
            self.pool_lock.release()
        return False

    def _get_untreated_task_num(self):
        return self._in_q.qsize()

    def get_untreated_task_num(self):
        """Get the number of the tasks untreated by the task processor in the
        task queue.
        """
        return self._get_untreated_task_num()

    def _get_task_processor_state(self):
        alive = died = 0
        for i in self.pools:
            if self.pools[i].is_alive():
                alive += 1
            else:
                died += 1
        return (alive, died)

    def get_task_processor_state(self):
        """Get the state of the task processor in this task pool.

        Return a tuple, (alive, died), and `alive` represents the number of the
        alive processor being able to continue to process the task, and `died`
        stands for the number of the died processor being unable to continue to
        process the task and it will be recycled in future.
        """
        self.pool_lock.acquire()
        rtn = self._get_task_processor_state()
        self.pool_lock.release()
        return rtn

    def _terminate_tasks(self, size=0, timeout=DEFAULT_TIMEOUT):
        try:
            if size:
                for i in range(size):
                    self._in_q.get(timeout=timeout)
                    #self._in_q.task_done()
            else:
                while True:
                    self._in_q.get(timeout=timeout)
                    #self._in_q.task_done()
        except:
            pass

    def terminate_tasks(self, size=0, timeout=DEFAULT_TIMEOUT):
        """Cancel the tasks having been not processed in the task queue.

        Args:
            `size`:    the number of the task being canceled.
                       If 0, cancel all the tasks; if a negative, nothing.
            `timeout`: the timeout(second) when canceling the tasks, default 3.

        Notice:
            1. Don't terminate the fetched and processing task.
            2. Since the task queue is FIFO, the canceled tasks are early, not
               latest.
        """
        return self._terminate_tasks(size, timeout)

    def _terminate_task_pools(self, size=0, timeout=DEFAULT_TIMEOUT):
        if size < 0:
            return

        current = self._get_task_processor_state()[0]

        if size > 0:
            if size > current:
                size = current
            for i in range(size):
                self._in_q.put(NONE)
        else:
            self._terminate_tasks(timeout=timeout)
            for i in range(current):
                self._in_q.put(NONE)

    def terminate_task_pools(self, size=0, timeout=DEFAULT_TIMEOUT):
        """Cancel the tasks in the task queue, and terminate the task processor
        in task pool. Additionally, it clean the died task processors.

        Args:
            `size`:    the number of the task processor being terminated.
                       If 0, terminate all the processors; if a negative, nothing.
            `timeout`: the timeout(second) when canceling the tasks in the task
                       queue, default 3 second.

        Notice:
            1. Don't terminate the processing task immediately, but maybe
               terminate it after processing the current task.
            2. Don't promise that recycle the terminated task processor, since
               it can not terminate some task processor immediately.
        """
        self.pool_lock.acquire()
        self._terminate_task_pools(size, timeout=timeout)
        self.pool_lock.release()
        self.clean_died_task_processors()
