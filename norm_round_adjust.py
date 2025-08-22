
import numpy as np


def norm_round_adjust(input, ndec=0):
    """ Normalizes input pd.Series to ndec decimals.
    If sum of rounded values != 0: Adjusts necessary number of items by 1^(ndec).
    """
    # Normalizing input data
    norm = input/input.sum()
    print('\nNormalized:\n')
    print(norm)
    # Normal rounding
    raw_rounded = norm.round(ndec)
    raw_rounded['SUM'] = raw_rounded.sum()
    print('\nRounded to {} decimals:\n'.format(ndec))
    print(raw_rounded)
    # Check if any non-zero items are rounded to zero
    n_rounded_to_0 = (raw_rounded==0).sum() - (input==0).sum()
    if ((raw_rounded==0).sum() > (input==0).sum()):
        print('WARNING: {} non-zero items rounded to zero. Consider increasing the precision.'.format(n_rounded_to_0))
    # Multiply with 10^decimals and round to integer
    target_sum = 10**ndec
    rounded = (norm*target_sum).round(0).astype(int)
    diff = target_sum - rounded.sum()
    if diff != 0:
        # Get indices of items to adjust (n largest items)
        sorted_index = rounded.sort_values(ascending=False).index
        adjust_items = sorted_index[0:abs(diff)]
        # Adjust the necessary number of items up or down.
        rounded[adjust_items] = rounded[adjust_items] + np.sign(diff)
        adjustment_value = np.sign(diff)/target_sum
        print('\nAdjusted {:d} item(s) with {:+g}'.format(len(adjust_items), adjustment_value))
        # Divide by target to return the corrected values
    else:
        print('\nNo adjustment necessary.')
    return rounded/target_sum


res = norm_round_adjust(input,3)



def round_adjust(input, ndec=1):
    """Runder input series til ndec desimaler
    Tilpasser slik at summen blir et heltall"""
    target_sum = input.sum().round(0)
    x = input.round(ndec)
    rounded_sum = x.sum()
    diff = (target_sum - rounded_sum).round(ndec)
    if diff != 0:
        # Number of items to adjust
        n_adjust = int(abs(diff*(10**ndec)))
        # Adjustment per item
        adjustment = np.sign(diff)*(10**-ndec)
        # Adjust n items
        x.iloc[0:n_adjust] = x.iloc[0:n_adjust] + adjustment
    return x

        

