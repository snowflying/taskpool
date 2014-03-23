# coding: utf-8
from __future__ import print_function
import time
import taskpool


def process(task_num, arg):
    print("Processor({0}): hello, {1}\n".format(task_num, arg), end='')
    time.sleep(0.1)


def create_pool(pools, tasks, typ):
    task = taskpool.TaskPool(pools, typ, processor=True)
    for i in range(tasks):
        task.spawn(process, i)
    return task


def test_reset_process():
    task = create_pool(2, 100, 'p')
    time.sleep(2)
    task.reset_size(5)
    num = task.get_untreated_task_num()
    while num > 0:
        time.sleep(1)
        num = task.get_untreated_task_num()


def test_processor_state_process():
    task = create_pool(2, 100, 'p')
    num = task.get_untreated_task_num()
    while num > 0:
        state = task.get_task_processor_state()
        print("Alive({0})  Die({1})\n".format(*state), end='')
        time.sleep(0.1)
        num = task.get_untreated_task_num()
    state = task.get_task_processor_state()
    print("Alive({0})  Die({1})\n".format(*state), end='')
    print("Have no tasks to be processed\n")


def test_untreated_task_num_process():
    task = create_pool(2, 100, 'p')
    num = task.get_untreated_task_num()
    while num > 0:
        print("Untreated task num: {0}\n".format(num), end='')
        time.sleep(0.1)
        num = task.get_untreated_task_num()
    print("Untreated task num: {0}\n".format(num), end='')


def test_terminate_task_pool_process():
    task = create_pool(5, 500, 'p')
    time.sleep(1)
    task.terminate_task_pools(timeout=0.5)
    state = task.get_task_processor_state()
    while state[0] > 0:
        print("Alive({0})  Die({1})\n".format(*state), end='')
        time.sleep(0.1)
        state = task.get_task_processor_state()
    print("Alive({0})  Die({1})\n".format(*state), end='')


def test_reset_thread():
    task = create_pool(2, 100, 't')
    time.sleep(2)
    task.reset_size(5)
    num = task.get_untreated_task_num()
    while num > 0:
        time.sleep(1)
        num = task.get_untreated_task_num()


def test_processor_state_thread():
    task = create_pool(2, 100, 't')
    num = task.get_untreated_task_num()
    while num > 0:
        state = task.get_task_processor_state()
        print("Alive({0})  Die({1})\n".format(*state), end='')
        time.sleep(0.1)
        num = task.get_untreated_task_num()
    state = task.get_task_processor_state()
    print("Alive({0})  Die({1})\n".format(*state), end='')
    print("Have no tasks to be processed\n")


def test_untreated_task_num_thread():
    task = create_pool(2, 100, 't')
    num = task.get_untreated_task_num()
    while num > 0:
        print("Untreated task num: {0}\n".format(num), end='')
        time.sleep(0.1)
        num = task.get_untreated_task_num()
    task.terminate_task_pools()


def test_terminate_task_pool_thread():
    task = create_pool(5, 500, 't')
    time.sleep(1)
    task.terminate_task_pools(timeout=0.5)
    state = task.get_task_processor_state()
    while state[0] > 0:
        print("Alive({0})  Die({1})\n".format(*state), end='')
        time.sleep(0.1)
        state = task.get_task_processor_state()
    print("Alive({0})  Die({1})\n".format(*state), end='')


if __name__ == "__main__":
    print("======================= Process =========================")
    print("\nTest reset")
    test_reset_process()

    print("\nTest processor state")
    test_processor_state_process()

    print("\nTest untreated task number")
    test_untreated_task_num_process()

    print("\nTest terminate task pool")
    test_terminate_task_pool_process()

    print('\n\n=======================  Thread ==========================')
    print("\nTest reset")
    test_reset_thread()

    print("\nTest processor state")
    test_processor_state_thread()

    print("\nTest untreated task number")
    test_untreated_task_num_thread()

    print("\nTest terminate task pool")
    test_terminate_task_pool_thread()
