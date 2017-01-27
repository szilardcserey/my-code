def calc_combinations(coin_types, remaining, i):
    if remaining == 0:
        return 1
    if (i+1) == len(coin_types) and remaining > 0:
        if remaining % coin_types[i] == 0:
            return 1
        else:
            return 0
    current = coin_types[i]
    return sum(calc_combinations(coin_types, remaining - q * current, i + 1)
               for q in range(int(remaining/current) + 1))


def main():
    coin_types = [1, 2, 5, 10, 20, 50, 100, 200]
    sum_of_coins = 200

    #coin_types = [2]
    #sum_of_coins = 5

    coin_types.sort(reverse=True)

    print calc_combinations(coin_types, sum_of_coins, 0)


if __name__ == '__main__':
    main()
