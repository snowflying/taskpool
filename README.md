Python TaskPool
===============

A task pool, execute tasks in the thread pool or the process pool.

### 1 安装
    快速安装：  pip install taskpool

### 2 用法
    首先导入TaskPool类，并实例化一个对象：
        from taskpool import TaskPool
        taskpool = TaskPool(processor=True)
        def hello(processor_num, *args, **kwargs):
            print(processor_num, args, kwargs)
        def callback(result):
            print(result)

    TaskPool 类的接口是：
        def __init__(self, size=1000, pool_type="thread", task_recycle_interval=3600, processor=False)
    其中，size指明任务池中任务处理器（线程或进程）的个数，默认1000。
         pool_type指明任务处理器是线程（"thread"）还是进程（"process"）。
         task_recycle_interval指定是否启用后台处理器资源回收（当收缩任务池或明确调用terminate_task_pools方法时可能会终止任务池中的处理器，处理器虽然不再工作，但资源还有）。如果为0或负，则关闭后台回收；如果为正，则表示多长时间（单位秒）回收一次（默认3600，即1小时）。如果关闭后台回收，则每次调用spawn方法都会回收一次。
         processor表明用户是否关心处理器的唯一标识（一个唯一表示处理器的编号，从1开始）。如果为真，则将处理器的唯一标识作为第一个参数传递给用户；否则，不传递，即按用户规定的接口调用处理。

### 3 TaskPool方法
    def spawn(self, func, *args, **kwargs)
        将一个任务放到任务池中去执行；在任务池中将会执行 func(*args, **kwargs)。

        在调用此方法时，可以指定三个关键字参数：callback、clean和safe。其中，callback是个回调函数，用于处理func返回的结果；它只有一个参数，就是func的返回结果，如果func抛出一个异常，则该参数是异常对象；另外，如果callback回调函数也抛出一个异常，那么它将安静地结束，处理器将处理一个任务。clean是个真值（默认为True），当关闭后台处理器回收时，是否当调用spawn时回收处理器资源；如果为True，则执行回收；否则不回收。safe是真值（默认为True），表明如果func参数不是一个可调用对象，该方法如何对待：如果safe为True且func是个不可调用对象，那么spawn不再做任何处理，直接返回False；如果safe为False，则spawn不关心func是否是个可调用对象。如果func不是个可调用对象，那么按func抛出了个异常来处理。
        如：taskpool.spawn(hello, 1, 2, a=11, b=22, callback=callback)

    def clean_died_task_processors(self)
        清理、回收已终止的处理器的资源。调用该方法将明确回收已终止的处理器。
        如果在spawn方法中指定clean为True，可能将会自动调用该方法。

    def reset_size(self, size)
        重置任务池的大小，即处理器的个数（由size参数指定）。
        如果size小于1或等于当前任务池的大小,不做任何处理；如果比当前任务池的大小大，则自动扩张任务池的大小，直到size；否则，收缩任务池的大小，降至size。

    def wait(self, timeout=None)
        等待任务池中的所有处理器都终止。
        timeout参数指定超时时间（可以是个整数或浮点数，以秒为单位）。如果timeout为None为0，则将锁定整个任务池，并等待任务池中所有的处理器都终止；由于锁定了整个任务池，所有对任务池大小的更改都不能再操作，包括重置任务池大小、回收处理器资源（此时后台回收工作将永远被阻塞）等。该参数也将影响spawn方法，因为spawn中也有可能回收处理器资源；如果想避免影响，需要在spawn中指定clean=False。如果timeout指定了超时时间，那么该方法不会影响其他任何操作；如果超时时，还有处理器存活，则返回True，否则返回False。
        建议：如果使用此方法，最好为timeout参数指定一个超时时间。

    def get_untreated_task_num(self)
        获取任务队列中还未处理的任务的个数。

    def get_task_processor_state(self)
        获取任务池的状态。返回一个二元组(alive, died)，alive表示当前存活的处理器个数，died表示已经终止的处理器个数。这两个数相加，表示当前任务池中总的处理器数。

    def terminate_tasks(self, size=0, timeout=DEFAULT_TIMEOUT)
        取消任务队列中还未处理的任务。
        size指定取消的任务的个数；如果为0，则表明全部取消。
        timeout指定在取消任务时超时时间，默认是3秒。

    def terminate_task_pools(self, size=0, timeout=DEFAULT_TIMEOUT)
        终止任务池中的任务处理器。
        size指定终止的处理器的个数。如果为0，则表明全部终止，此时将先取消任务队列中所有的任务，然后终止所有的处理器，最后清理、回收处理器资源。如果大于0，仅终止并回收指定个数的处理器。如果小于0，则不做任何处理。
        timeout指定取消任务队列中所有任务时的超时时间。

### 4 备注
    TaskPool中的方法都是线程安全的，可以在多线程中的调用。
    TaskPool已经在 Python2.7.5+ 和 python3.3.2+ 下根据自带的简单测试脚本测试通过，符合预期结果。
    TaskPool没有经过大规模测试，即创建成千上万个处理器（线程或进程）。

