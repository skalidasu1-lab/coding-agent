from pricing import apply_discount


def total(prices, discount_percent=0):
    subtotal = sum(prices)
    if discount_percent:
        return apply_discount(subtotal, discount_percent)
    return subtotal
