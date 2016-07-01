import itertools
import eventlet
import eventlet.tpool
import thread
import os
import multiprocessing
import datetime


NUM_PROC = 40
EVENTLET_THREADPOOL_SIZE = 1000


def check_sum_reached(sequence, coin_type_id, val, sum_of_coins):
    if sequence.index(coin_type_id) == len(sequence) - 1:
        if val == sum_of_coins:
            return True
    return False


def greenpool_calculate(sequence_list, quantity_lists, coins, sum_of_coins):
    pool = eventlet.GreenPool(size=1000)
    sem = eventlet.semaphore.Semaphore()

    occurrence_list = []

    for sequence in sequence_list:
        pool.spawn(parse_sequence, sequence, quantity_lists, coins, sum_of_coins, occurrence_list, sem)

    pool.waitall()

    return sum(occurrence_list)


def tpool_calculate(sequence_list, quantity_lists, coins, sum_of_coins):
    os.environ['EVENTLET_THREADPOOL_SIZE'] = EVENTLET_THREADPOOL_SIZE
    sem = eventlet.semaphore.Semaphore()

    occurrence_list = []

    for sequence in sequence_list:
        eventlet.tpool.execute(parse_sequence, sequence, quantity_lists, coins, sum_of_coins, occurrence_list, sem)

    del os.environ['EVENTLET_THREADPOOL_SIZE']
    return sum(occurrence_list)


def multiprocessing_calculate(sequence_list, quantity_lists, coins, sum_of_coins):

    pool = multiprocessing.Pool(NUM_PROC)
    occurrence = 0
    results = []

    for sequence in sequence_list:
        results.append(pool.apply_async(parse_sequence, (sequence, quantity_lists, coins, sum_of_coins,)))

    # Process results
    for result in results:
        occurrence += result.get()

    pool.close()
    pool.join()

    return occurrence


def parse_sequence(sequence, quantity_lists, coins, sum_of_coins, occurrence_list=None, semaphore=None):
    calc_list = []
    occurrence = 0

    for coin_type_id in sequence:
        calc_list_initially_empty = True if not calc_list else False
        aux_calc_list = []
        for quantity in quantity_lists[coin_type_id]:

            if calc_list_initially_empty:

                val = quantity * coins[coin_type_id]
                if check_sum_reached(sequence, coin_type_id, val, sum_of_coins):
                    occurrence += 1

                calc_list.append(val)

            else:

                new_calc_list = []
                for calc in calc_list:

                    val = calc + quantity * coins[coin_type_id]

                    if check_sum_reached(sequence, coin_type_id, val, sum_of_coins):
                        occurrence += 1

                    new_calc_list.append(val)

                aux_calc_list.extend(new_calc_list)

        if not calc_list_initially_empty:
            calc_list = aux_calc_list[:]

    if semaphore and occurrence_list is not None:
        if occurrence:
            with semaphore:
                occurrence_list.append(occurrence)
        print 'THREAD %s - OCCURRENCE_LIST %s' % (thread.get_ident(), occurrence_list)
    else:
        print 'OCCURRENCE %s' % occurrence
        return occurrence


def combinations(elements):
    for i in range(1, len(elements) + 1):
        yield list(itertools.combinations(elements, i))


def count_coins(sum_of_coins, coins):
    print 'COIN TYPES: %s' % coins
    print 'SUM OF COINS: %s' % sum_of_coins
    max_number_of_coins = [(sum_of_coins / coins[i]) for i in range(len(coins))]

    quantity_lists = []
    for i in range(len(coins)):
        quantity_lists.append([j for j in range(1, max_number_of_coins[i] + 1)])

    sequence_lists = list(combinations(range(len(coins))))
    print '\nCOIN TYPE COMBINATION SEQUENCE LISTS\n'
    for sequence_list in sequence_lists:
        print '%s\n' % sequence_list

    total_occurrence = 0
    for sequence_list in sequence_lists:
        print '\ncurrent SEQUENCE_LIST:\n%s\n' % sequence_list

        # occurrence = greenpool_calculate(sequence_list, quantity_lists, coins, sum_of_coins)
        # occurrence = tpool_calculate(sequence_list, quantity_lists, coins, sum_of_coins)
        occurrence = multiprocessing_calculate(sequence_list, quantity_lists, coins, sum_of_coins)

        total_occurrence += occurrence
        print '\ncurrent TOTAL OCCURRENCE: %s\n' % total_occurrence

    print 'TOTAL OCCURRENCE: %s' % total_occurrence


def main():
    coins = [1, 2, 5, 10, 20, 50, 100, 200]
    sum_of_coins = 200

    #coins = [1, 2, 5, 10]
    #sum_of_coins = 200

    start = datetime.datetime.now()
    count_coins(sum_of_coins, coins)
    end = datetime.datetime.now()
    print "\nTIME ELAPSED: %s" % (end - start)

if __name__ == '__main__':
    main()
